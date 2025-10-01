// Rwanda districts (Level-2)
var rw_l2 = ee.FeatureCollection('FAO/GAUL/2015/level2')
  .filter(ee.Filter.eq('ADM0_NAME', 'Rwanda'));

var TARGETS = ['Gatsibo','Musanze']; // change as needed
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
  {"b(0)": slopePct}
).toInt();

// Visual check
Map.centerObject(districts, 8);
Map.addLayer(slopeClass,
  {min:1, max:6, palette:['#edf8e9','#bae4b3','#74c476','#31a354','#006d2c','#00441b']},
  'Slope Classes (percent)');

// Export slope classes per district
districts.toList(districts.size()).evaluate(function(list) {
  list.forEach(function(f) {
    var ft = ee.Feature(f);
    var name = ee.String(ft.get('ADM2_NAME'));
    var slpClip = slopeClass.clip(ft.geometry());
    var fileBase = name.replace('/','-').cat('_slope_DEM');

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
});