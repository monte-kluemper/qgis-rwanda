import numpy as np
import rasterio
import os
from sklearn.linear_model import LinearRegression

# ------------- CONFIG -------------
# Folder containing per-district, per-year GeoTIFFs exported from GEE.
# File name pattern assumed: <District>_<YEAR>_S2.tif  (e.g., Gatsibo_2019_S2.tif)
DATA_DIR = os.environ.get("S2_DATA_DIR", r"C:/AI/rwanda_degradation_mask/sample_data")

# Choose which district to process (matching file prefixes).
DISTRICTS = ["North-Amajyaruguru", "East-Iburasirazuba"]  # edit as needed
LATEST_YEAR = 2023                   # snapshot year for soil/stress indices

# ------------- INDICES -------------
def ndvi(nir, red):
    return (nir - red) / (nir + red + 1e-6)

def dswi(nir, swir1):
    return nir / (swir1 + 1e-6)

def ndwi(nir, swir1):
    return (nir - swir1) / (nir + swir1 + 1e-6)

def brightness(b2, b4, b8):
    return np.sqrt(b2**2 + b4**2 + b8**2) / 3.0

def redness(b4, b3, b2):
    return (b4**2) / (b3 * b2 + 1e-6)

def psri(b4, b2, b5):
    return (b4 - b2) / (b5 + 1e-6)

def normalize(arr, invert=False):
    # robust scaling to [0,1] using 2nd..98th percentiles to reduce outliers
    lo = np.nanpercentile(arr, 2)
    hi = np.nanpercentile(arr, 98)
    arr = np.clip(arr, lo, hi)
    norm = (arr - np.nanmin(arr)) / (np.nanmax(arr) - np.nanmin(arr) + 1e-6)
    return 1 - norm if invert else norm

# ------------- TREND -------------
def compute_ndvi_trend(file_paths):
    """Compute per-pixel linear slope of NDVI across years."""
    ndvi_stack = []
    years = []

    sample_profile = None
    for f in sorted(file_paths):
        # Expect filename like: District_YYYY_S2.tif
        parts = os.path.basename(f).split("_")
        # Find the year token (robustness: find a 4-digit int in parts)
        year = None
        for p in parts:
            if p.isdigit() and len(p) == 4:
                year = int(p); break
        if year is None:
            raise ValueError(f"Could not parse year from filename: {f}")
        years.append(year)

        with rasterio.open(f) as src:
            bands = src.read()  # [B2,B3,B4,B5,B8,B11] in this order per GEE script
            red = bands[2].astype(float)
            nir = bands[4].astype(float)
            ndvi_img = ndvi(nir, red)
            ndvi_stack.append(ndvi_img)
            if sample_profile is None:
                sample_profile = src.profile

    ndvi_stack = np.stack(ndvi_stack, axis=-1)  # (rows, cols, T)
    years = np.array(years, dtype=float)

    # Precompute regression X
    X = years.reshape(-1, 1)
    rows, cols, T = ndvi_stack.shape
    slope = np.full((rows, cols), np.nan, dtype=float)

    # Fit pixel-wise linear regression
    model = LinearRegression()
    for i in range(rows):
        # optional: show progress every N rows
        y_block = ndvi_stack[i, :, :]  # (cols, T)
        for j in range(cols):
            y = y_block[j, :]
            if np.any(np.isnan(y)):
                continue
            model.fit(X, y)
            slope[i, j] = model.coef_[0]

    return slope, sample_profile

# ------------- SNAPSHOT (LATEST YEAR) -------------
def process_snapshot(file_path):
    with rasterio.open(file_path) as src:
        bands = src.read()
        profile = src.profile

        b2 = bands[0].astype(float)   # Blue
        b3 = bands[1].astype(float)   # Green
        b4 = bands[2].astype(float)   # Red
        b5 = bands[3].astype(float)   # Red Edge
        b8 = bands[4].astype(float)   # NIR
        b11 = bands[5].astype(float)  # SWIR

    dswi_val = dswi(b8, b11)
    ndwi_val = ndwi(b8, b11)
    bright_val = brightness(b2, b4, b8)
    redness_val = redness(b4, b3, b2)
    psri_val = psri(b4, b2, b5)

    dswi_n = normalize(dswi_val)                # higher stress => higher score
    ndwi_n = normalize(ndwi_val, invert=True)   # lower moisture => higher score
    bright_n = normalize(bright_val)            # brighter => higher score
    redness_n = normalize(redness_val)          # redder => higher score
    psri_n = normalize(psri_val)                # more senescence => higher score

    return {"dswi": dswi_n, "ndwi": ndwi_n, "bright": bright_n,
            "redness": redness_n, "psri": psri_n}, profile

# ------------- COMBINE -------------
def combine_indices(ndvi_trend, snapshot_indices):
    # Normalize NDVI slope: more negative = more degraded
    trend_norm = normalize(ndvi_trend, invert=True)
    # Weighted composite (adjustable)
    degradation = (
        0.4 * trend_norm +
        0.15 * snapshot_indices["dswi"] +
        0.15 * snapshot_indices["bright"] +
        0.15 * snapshot_indices["psri"] +
        0.15 * snapshot_indices["redness"]
    )
    return degradation

def classify_5(degradation):
    # 5 equal-width bins across [0,1]
    bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
    return np.digitize(degradation, bins)  # 1..5

# ------------- DRIVER -------------
def run_for_district(district):
    # collect all years for this district
    print("district="+district)
    files = [os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR)
             if f.startswith(district + "_") and f.endswith("_S2.tif")]
    if len(files) == 0:
        print(f"[WARN] No files for district '{district}' in {DATA_DIR}")
        return

    # Trend across available years
    ndvi_slope, profile = compute_ndvi_trend(files)

    # Latest snapshot (LATEST_YEAR)
    snapshot_file = None
    for f in files:
        if f"_{LATEST_YEAR}_" in os.path.basename(f):
            snapshot_file = f; break
    if snapshot_file is None:
        # fallback: pick max year
        years = sorted([int(p.split("_")[1]) for p in map(os.path.basename, files)])
        snapshot_file = [f for f in files if f"_{years[-1]}_" in f][0]
        print(f"[INFO] Using latest available year {years[-1]} for snapshot.")

    snapshot_indices, _ = process_snapshot(snapshot_file)

    # Combine & classify
    degradation = combine_indices(ndvi_slope, snapshot_indices)
    classified = classify_5(degradation)

    # Save outputs
    profile.update(dtype=rasterio.float32, count=1, compress='lzw')

    out_deg = os.path.join(DATA_DIR, f"{district}_degradation_index.tif")
    out_cls = os.path.join(DATA_DIR, f"{district}_degradation_class.tif")

    with rasterio.open(out_deg, 'w', **profile) as dst:
        dst.write(degradation.astype(np.float32), 1)
    with rasterio.open(out_cls, 'w', **profile) as dst:
        dst.write(classified.astype(np.float32), 1)

    print(f"✅ Saved: {out_deg}")
    print(f"✅ Saved: {out_cls}")

if __name__ == "__main__":
    print(f"[INFO] Using DATA_DIR={DATA_DIR}")
    for d in DISTRICTS:
        run_for_district(d)
