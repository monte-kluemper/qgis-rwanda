# Land Degradation Analysis (Sentinel-2)

This package provides tools to analyze **land degradation** using **Sentinel-2 imagery** following UN-aligned indicators.  
It includes Earth Engine (GEE) scripts to export annual composites and Python scripts to calculate degradation indices and change maps.

---

## 1. Export Sentinel-2 Data from GEE

### a) Load Rwanda districts
In the [Google Earth Engine Code Editor](https://code.earthengine.google.com/), use the export_s2.js script in the gee_scripts directory:


### b) Download
- Run exports from the **Tasks** tab in GEE.  
- Files will appear in **Google Drive → EarthEngine/** as GeoTIFFs (one per district/year).  
- Download them to a local folder, e.g. `C:/data/sentinel2_rwanda/`.

---

## 2. Python Setup

### Requirements
- Python 3.9+  
- Install packages:
  ```bash
  pip install rasterio numpy scikit-learn
  ```

### Configure
- Set your data folder:
  ```powershell
  $env:S2_DATA_DIR="C:/data/sentinel2_rwanda/"
  ```

- Place all `District_YYYY_S2.tif` files in that folder.

---

## 3. Scripts

### a) Long-term Degradation Trend
Script: `compute_degradation_trend.py`

- Uses **all years of Sentinel-2 data** for each district.  
- Computes the **NDVI trend (linear regression)** plus soil/vegetation condition indices.  
- Outputs:
  - `District_degradation_index.tif` → continuous raster (0–1).  
  - `District_degradation_class.tif` → categorical raster (1–5 classes).  

Run:
```bash
python compute_degradation_trend.py
```

---

### b) Year-over-Year Change
Script: `compute_degradation_yoy.py`

- Compares each year’s indices to the **previous year**.  
- Highlights **areas of degradation (positive values)** and **improvement (negative values)**.  
- Outputs one raster per year pair:
  - `District_degradation_2020_vs_2019.tif`  
  - `District_degradation_2021_vs_2020.tif`  
  - etc.

Run:
```bash
python compute_degradation_yoy.py
```

---

## 4. Visualization in QGIS
- Load the output rasters.  
- For **classification rasters (1–5)** → use *Singleband pseudocolor* with discrete classes (green → yellow → red).  
- For **year-over-year rasters** → use a diverging palette (green = improvement, red = degradation).  

---

## 5. Workflow Summary
1. Export annual Sentinel-2 composites per district with GEE.  
2. Download TIFFs to your local `S2_DATA_DIR`.  
3. Run `compute_degradation_trend.py` for long-term patterns.  
4. Run `compute_degradation_yoy.py` for year-to-year changes.  
5. Visualize results in QGIS.  

---

📌 **Note**: This workflow only uses **Sentinel-2 data**. Terrain slope and other covariates can be added later, but are not required for the baseline trend/change analysis.  
