// Rwanda districts (Level-2)
var rw_l2 = ee.FeatureCollection('FAO/GAUL/2015/level2')
    .filter(ee.Filter.eq('ADM0_NAME', 'Rwanda'));

var TARGETS = ['Gatsibo', 'Musanze']; // change as needed
var districts = rw_l2.filter(ee.Filter.inList('ADM2_NAME', TARGETS));

// DEM
//var dem = ee.Image("USGS/SRTMGL1_003");
var dem = ee.Image('NASA/NASADEM_HGT/001').select('elevation');

// Terrain slope in degrees
var slopeDeg = ee.Terrain.slope(dem);

// Convert to percent slope
var slopePct = slopeDeg.tan().multiply(100);

// Define new thresholds in percent (tuned for hilly/mountainous areas)
var thresholds = [5, 10, 15, 20, 30];

// Apply classification
var slopeClass = slopePct.expression(
    "(b(0) <= 5) ? 1" +      // Gentle
    ": (b(0) <= 10) ? 2" +    // Moderate
    ": (b(0) <= 15) ? 3" +    // Moderately steep
    ": (b(0) <= 20) ? 4" +    // Steep
    ": (b(0) <= 30) ? 5" +    // Very steep
    ": 6",                    // Extremely steep
    { "b(0)": slopePct }
).toInt();

// Preview
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
            scale: 30,
            crs: 'EPSG:4326',
            maxPixels: 1e13
        });
    });
});