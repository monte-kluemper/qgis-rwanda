# Rwanda Land Degradation Mask (Sentinel‑2 Based)

This package generates **land degradation maps** for Rwandan districts using Sentinel‑2. 
It combines **NDVI trends (2018–2023)** with **2023 soil/stress indices** to output:
- a continuous **degradation index** (0–1), and
- a **5‑level classification** (Very Low → Very High).

## Requirements
- Windows 10/11 (64‑bit)
- Python 3.9+ (Anaconda recommended)
- QGIS 3.22+ (for visualization)

### Python deps
See `requirements.txt`.

## Install
```bash
# (optional) create env
conda create -n degradation python=3.9 -y
conda activate degradation

# install deps
pip install -r requirements.txt
```

## Data
Export Sentinel‑2 L2A seasonal composites from **Google Earth Engine**:
- Years: **2018–2023**
- Season: **May–July**
- Bands: **B2, B3, B4, B5, B8, B11**
- One file per **district × year**, e.g. `Gatsibo_2018_S2.tif`.

Use the provided GEE script: `gee_scripts/gee_export_rwanda.js`.
Put downloaded files into a folder, e.g. `C:/data/sentinel2_rwanda/`.

> A small **Kigali 2023 sample** script is in `gee_scripts/gee_export_kigali_sample.js`.
Place the exported `Kigali_2023_S2.tif` inside `sample_data/` to test quickly.

## Run (NDVI trend + classification)
Edit paths inside `scripts/1_compute_degradation_trend.py` to point to your data folder.
Then run:
```bash
python scripts/1_compute_degradation_trend.py
```

Outputs per district:
- `*_degradation_index.tif` (0–1)
- `*_degradation_class.tif` (1..5; 1=Very Low → 5=Very High)

## Visualize in QGIS
1. Load `*_degradation_class.tif`
2. Right‑click → **Properties → Symbology**
3. **Style → Load Style…** → `qgis_styles/degradation_class.qml`
4. For continuous map, load `*_degradation_index.tif` with `qgis_styles/degradation_index.qml`.

## Notes
- Trend uses linear slope of NDVI over 2018–2023; negative = degradation.
- Snapshot indices (DSWI, Brightness, PSRI, Redness) from 2023 refine severity.
- Thresholding uses equal‑width bins (configurable).

## Credits
Aligned with UNCCD SDG 15.3.1 concepts. Uses Sentinel‑2 L2A (Surface Reflectance).
