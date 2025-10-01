import numpy as np
import rasterio
import os
from sklearn.linear_model import LinearRegression

# ------------- CONFIG -------------
DATA_DIR = os.environ.get("S2_DATA_DIR", r"C:/AI/data/rwanda/")
# DISTRICTS = ["North-Amajyaruguru", "East-Iburasirazuba"]  # edit as needed
DISTRICTS = ["Gatsibo", "Musanze"]  # edit as needed
LATEST_YEAR = 2023

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
    lo = np.nanpercentile(arr, 2)
    hi = np.nanpercentile(arr, 98)
    arr = np.clip(arr, lo, hi)
    norm = (arr - np.nanmin(arr)) / (np.nanmax(arr) - np.nanmin(arr) + 1e-6)
    return 1 - norm if invert else norm

# ------------- TREND -------------
def compute_ndvi_trend(file_paths):
    ndvi_stack = []
    years = []
    sample_profile = None

    for f in sorted(file_paths):
        year = None
        for p in os.path.basename(f).split("_"):
            if p.isdigit() and len(p) == 4:
                year = int(p); break
        if year is None:
            raise ValueError(f"Could not parse year from {f}")
        years.append(year)

        with rasterio.open(f) as src:
            bands = src.read()
            red = bands[2].astype(float)
            nir = bands[4].astype(float)
            ndvi_stack.append(ndvi(nir, red))
            if sample_profile is None:
                sample_profile = src.profile

    ndvi_stack = np.stack(ndvi_stack, axis=-1)
    years = np.array(years, dtype=float)

    X = years.reshape(-1, 1)
    rows, cols, T = ndvi_stack.shape
    slope = np.full((rows, cols), np.nan, dtype=float)

    model = LinearRegression()
    for i in range(rows):
        y_block = ndvi_stack[i, :, :]
        for j in range(cols):
            y = y_block[j, :]
            if np.any(np.isnan(y)):
                continue
            model.fit(X, y)
            slope[i, j] = model.coef_[0]

    return slope, sample_profile

# ------------- SNAPSHOT -------------
def process_snapshot(file_path):
    with rasterio.open(file_path) as src:
        bands = src.read()
        profile = src.profile

        b2 = bands[0].astype(float)
        b3 = bands[1].astype(float)
        b4 = bands[2].astype(float)
        b5 = bands[3].astype(float)
        b8 = bands[4].astype(float)
        b11 = bands[5].astype(float)

    return {
        "dswi": normalize(dswi(b8, b11)),
        "ndwi": normalize(ndwi(b8, b11), invert=True),
        "bright": normalize(brightness(b2, b4, b8)),
        "redness": normalize(redness(b4, b3, b2)),
        "psri": normalize(psri(b4, b2, b5))
    }, profile

# ------------- SLOPE -------------
def load_slope(district):
    slope_file = os.path.join(DATA_DIR, f"{district}_Slope_deg.tif")
    if not os.path.exists(slope_file):
        print(f"[WARN] No slope file for {district}, skipping slope")
        return None

    with rasterio.open(slope_file) as src:
        slope = src.read(1).astype(float)
    return normalize(slope)  # 0–90 deg → normalized 0–1

# ------------- COMBINE -------------
def combine_indices(ndvi_trend, snapshot_indices, slope_layer=None):
    trend_norm = normalize(ndvi_trend, invert=True)
    degradation = (
        0.35 * trend_norm +
        0.15 * snapshot_indices["dswi"] +
        0.15 * snapshot_indices["bright"] +
        0.15 * snapshot_indices["psri"] +
        0.15 * snapshot_indices["redness"]
    )
    if slope_layer is not None:
        degradation = degradation + 0.1 * slope_layer
    return degradation

def classify_5(degradation):
    bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
    return np.digitize(degradation, bins)

# ------------- DRIVER -------------
def run_for_district(district):
    files = [os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR)
             if f.startswith(district + "_") and f.endswith("_S2.tif")]
    if not files:
        print(f"[WARN] No Sentinel-2 files for {district}")
        return

    ndvi_slope, profile = compute_ndvi_trend(files)

    snapshot_file = next((f for f in files if f"_{LATEST_YEAR}_" in os.path.basename(f)), None)
    if snapshot_file is None:
        years = sorted([int(p.split("_")[1]) for p in map(os.path.basename, files)])
        snapshot_file = [f for f in files if f"_{years[-1]}_" in f][0]
        print(f"[INFO] Using latest available year {years[-1]} for snapshot.")

    snapshot_indices, _ = process_snapshot(snapshot_file)

    slope_layer = load_slope(district)

    degradation = combine_indices(ndvi_slope, snapshot_indices, slope_layer)
    classified = classify_5(degradation)

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
