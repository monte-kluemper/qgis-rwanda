// Rwanda districts (Level-2)
var rw_l2 = ee.FeatureCollection('FAO/GAUL/2015/level2')
    .filter(ee.Filter.eq('ADM0_NAME', 'Rwanda'));

var TARGETS = ['Gatsibo', 'Musanze']; // change as needed
var districts = rw_l2.filter(ee.Filter.inList('ADM2_NAME', TARGETS));

// DEM (use mosaic for 30 m, or switch to GLO90 if needed)
var dem = ee.ImageCollection("COPERNICUS/DEM/GLO30").mosaic();

// Terrain slope in degrees
var slopeDeg = ee.Terrain.slope(dem);

// Convert to percent slope
var slopePct = slopeDeg.tan().multiply(100);

// Define thresholds in percent
var thresholds = [5, 10, 15, 20, 30];

// Apply classification
var slopeClass = slopePct.expression(
    "(b(0) <= 5) ? 1" +
    ": (b(0) <= 10) ? 2" +
    ": (b(0) <= 15) ? 3" +
    ": (b(0) <= 20) ? 4" +
    ": (b(0) <= 30) ? 5" +
    ": 6",
    { "b(0)": slopePct }
).toInt();

// Visual check
Map.centerObject(districts, 8);
Map.addLayer(slopeClass,
    { min: 1, max: 6, palette: ['#edf8e9', '#bae4b3', '#74c476', '#31a354', '#006d2c', '#00441b'] },
    'Slope Classes (percent)');

// Export slope classes per district
districts.toList(districts.size()).evaluate(function (list) {
    list.forEach(function (f) {
        var ft = ee.Feature(f);
        var name = ee.String(ft.get('ADM2_NAME'));
        var slpClip = slopeClass.clip(ft.geometry());
        var fileBase = name.replace('/', '-').cat('_SlopeClass');

        Export.image.toDrive({
            image: slpClip,
            description: fileBase.getInfo(),
            folder: 'EarthEngine',
            fileNamePrefix: fileBase.getInfo(),
            region: ft.geometry(),
            scale: 30,    // Copernicus DEM native resolution
            crs: 'EPSG:4326',
            maxPixels: 1e13
        });
    });
});// ================== SETTINGS ==================
var YEARS = [2018, 2019, 2020, 2021, 2022, 2023];
var START = '05-01';
var END   = '07-31';
var DRIVE_FOLDER = 'EarthEngine';   // where files land in Google Drive
var BAND_LIST = ['B2','B3','B4','B5','B8','B11']; // 10/20 m (export at 10 m)

// Level-2 = districts in GAUL (Level-1 are provinces)
var rw_l2 = ee.FeatureCollection('FAO/GAUL/2015/level2')
  .filter(ee.Filter.eq('ADM0_NAME', 'Rwanda'));

// Choose your districts here:
var TARGETS = ['Gatsibo','Musanze'];  // <-- edit freely
var districts = rw_l2.filter(ee.Filter.inList('ADM2_NAME', TARGETS));

// ================== HELPERS ==================
function maskS2_QA60(img) {
  // QA60 bits 10 (cloud) and 11 (cirrus)
  var qa = img.select('QA60');
  var cloudBitMask  = 1 << 10;
  var cirrusBitMask = 1 << 11;
  var mask = qa.bitwiseAnd(cloudBitMask).eq(0)
               .and(qa.bitwiseAnd(cirrusBitMask).eq(0));
  // Keep reflectance bands and apply mask
  return img.updateMask(mask);
}

function getIC(geom, year) {
  return ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(geom)
    .filterDate(year + '-' + START, year + '-' + END)
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    .map(maskS2_QA60)
    .select(BAND_LIST);  // select on the collection (safer)
}

function exportDistrictYear(ft, year) {
  var name = ee.String(ft.get('ADM2_NAME'));
  var geom = ft.geometry();
  var ic   = getIC(geom, year);
  var n    = ic.size();

  // Log size so you can see what's happening
  print('Images for', name, year, ':', n);

  // Decide client-side whether to export
  n.gt(0).evaluate(function(ok) {
    if (!ok) {
      print('⚠️ Skipping', name.getInfo(), year, '- no images after filters.');
      return;
    }
    var composite = ic.median().clip(geom);
    // Safe file name (no slashes)
    var fileBase = name.replace('/','-')
      .cat('_').cat(ee.Number(year)).cat('_S2');

    Export.image.toDrive({
      image: composite,
      description: fileBase.getInfo(),          // task name
      folder: DRIVE_FOLDER,                     // Google Drive folder
      fileNamePrefix: fileBase.getInfo(),       // file name
      region: geom,
      scale: 10,                                // export at 10 m
      crs: 'EPSG:4326',
      maxPixels: 1e13
    });
  });
}

// ================== RUN ==================
Map.centerObject(districts, 8);
Map.addLayer(districts, {color:'red'}, 'Selected districts');

districts.toList(districts.size()).evaluate(function(list) {
  list.forEach(function(f) {
    var ft = ee.Feature(f);
    YEARS.forEach(function(y) {
      exportDistrictYear(ft, y);
    });
  });
});
