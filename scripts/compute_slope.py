import rasterio
import numpy as np
import os

# ---------------- CONFIG ----------------
# Input slope GeoTIFF (degrees, from Copernicus DEM export in GEE)
DATA_DIR = os.environ.get("S2_DATA_DIR", r"C:/AI/data/rwanda")
# DISTRICTS = ["North-Amajyaruguru", "East-Iburasirazuba"]  # edit as needed
DISTRICTS = ["Musanze", "Gatsibo"]  # edit as needed

# Thresholds (percent slope)
THRESHOLDS = [5, 10, 15, 20, 30]

# ---------------- FUNCTIONS ----------------
def slope_degrees_to_percent(slope_deg):
    """
    Convert slope in degrees to percent slope = 100 * tan(deg).
    """
    return np.tan(np.deg2rad(slope_deg)) * 100

def classify_slope(slope_percent, thresholds):
    """
    Classify slope percent into bins defined by thresholds.
    Returns integer classes 1..N+1.
    """
    bins = [0] + thresholds + [np.inf]
    classes = np.digitize(slope_percent, bins, right=False)
    return classes

# ---------------- MAIN ----------------
def run_for_district(district):
    # collect all years for this district
    print("district="+district)
    input_file = DATA_DIR+"/"+district+"_slope_NASA.tif"

    with rasterio.open(input_file) as src:
        slope_deg = src.read(1).astype(float)
        profile = src.profile

    # Convert to percent
    slope_percent = slope_degrees_to_percent(slope_deg)

    # Classify
    slope_class = classify_slope(slope_percent, THRESHOLDS)

    # Update profile
    profile.update(dtype=rasterio.uint8, count=1, compress='lzw')

    output_file = DATA_DIR+"/"+district+"_slope_class_NASA.tif"
    with rasterio.open(output_file, "w", **profile) as dst:
        dst.write(slope_class.astype(rasterio.uint8), 1)

    print(f"✅ Saved classified slope raster: {output_file}")
    print("Classes:")
    print("  1 = 0–5%")
    print("  2 = 5–10%")
    print("  3 = 10–15%")
    print("  4 = 15–20%")
    print("  5 = 20–30%")
    print("  6 = >30%")

if __name__ == "__main__":
    print(f"[INFO] Using DATA_DIR={DATA_DIR}")
    for d in DISTRICTS:
        run_for_district(d)

