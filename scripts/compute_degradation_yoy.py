import os
import numpy as np
import rasterio

# ---------------- CONFIG ----------------
DATA_DIR = os.environ.get("S2_DATA_DIR", r"C:/AI/data/rwanda/")
DISTRICTS = ["Gatsibo", "Musanze"]  # edit as needed

# ---------------- INDICES ----------------
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

# ---------------- SNAPSHOT ----------------
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
        "ndvi": normalize(ndvi(b8, b4)),
        "dswi": normalize(dswi(b8, b11)),
        "ndwi": normalize(ndwi(b8, b11), invert=True),
        "bright": normalize(brightness(b2, b4, b8)),
        "redness": normalize(redness(b4, b3, b2)),
        "psri": normalize(psri(b4, b2, b5))
    }, profile

# ---------------- COMPARISON ----------------
def compare_years(indices_curr, indices_prev):
    """
    Compare index values between two years.
    Positive = degradation increase, negative = improvement.
    """
    diff = (
        0.4 * (indices_curr["ndvi"] - indices_prev["ndvi"]) * -1 +  # NDVI drop = degradation
        0.15 * (indices_curr["dswi"] - indices_prev["dswi"]) +
        0.15 * (indices_curr["bright"] - indices_prev["bright"]) +
        0.15 * (indices_curr["psri"] - indices_prev["psri"]) +
        0.15 * (indices_curr["redness"] - indices_prev["redness"])
    )
    return diff

# ---------------- DRIVER ----------------
def run_for_district(district):
    # Collect all Sentinel-2 files for district
    files = [os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR)
             if f.startswith(district + "_") and f.endswith("_S2.tif")]
    if not files:
        print(f"[WARN] No Sentinel-2 files for {district}")
        return

    # Sort files by year
    file_map = {}
    for f in files:
        year = None
        for p in os.path.basename(f).split("_"):
            if p.isdigit() and len(p) == 4:
                year = int(p); break
        if year:
            file_map[year] = f
    years = sorted(file_map.keys())

    for i in range(1, len(years)):
        y_prev, y_curr = years[i-1], years[i]
        f_prev, f_curr = file_map[y_prev], file_map[y_curr]

        indices_prev, profile = process_snapshot(f_prev)
        indices_curr, _ = process_snapshot(f_curr)

        degradation_change = compare_years(indices_curr, indices_prev)

        out_file = os.path.join(DATA_DIR, f"{district}_degradation_{y_curr}_vs_{y_prev}.tif")
        profile.update(dtype=rasterio.float32, count=1, compress="lzw")

        with rasterio.open(out_file, "w", **profile) as dst:
            dst.write(degradation_change.astype(np.float32), 1)

        print(f"✅ Saved: {out_file}")

if __name__ == "__main__":
    print(f"[INFO] Using DATA_DIR={DATA_DIR}")
    for d in DISTRICTS:
        run_for_district(d)
