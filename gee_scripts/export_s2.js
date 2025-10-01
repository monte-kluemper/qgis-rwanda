/************************************************************
 * Sentinel-2 Multi-Year Seasonal Composites Export Script
 * Rwanda District Example (Gatsibo & Musanze)
 *
 * Exports May–July median composites (2018–2023)
 * with bands: B2, B3, B4, B5, B8, B11
 * Output: One GeoTIFF per district per year
 ************************************************************/

var years = [2018, 2019, 2020, 2021, 2022, 2023];
var startMonth = '05-01';
var endMonth = '07-31';

// Level-2 = districts
var rw_l2 = ee.FeatureCollection('FAO/GAUL/2015/level2')
    .filter(ee.Filter.eq('ADM0_NAME', 'Rwanda'));

print('Count (Level-2 features in Rwanda):', rw_l2.size());
print('Property names:', rw_l2.first().propertyNames());

// See some rows
print('First 5 features:', rw_l2.limit(5));

// List distinct district names
print('ADM2 names (first 25):',
    rw_l2.aggregate_array('ADM2_NAME').distinct().sort().slice(0, 25)
);

// Visual check on map
Map.centerObject(rw_l2, 7);
Map.addLayer(rw_l2, {}, 'Rwanda Level-2 (Districts)');

var targets = ['Gatsibo', 'Musanze'];
var districts = rw_l2.filter(ee.Filter.inList('ADM2_NAME', targets));

print('Selected districts:', districts);              // shows a small FC
Map.addLayer(districts, { color: 'red' }, 'Selected');  // visualize

function seasonalComposite(year, geom) {
    var start = ee.Date(year + '-' + startMonth);
    var end = ee.Date(year + '-' + endMonth);
    var s2 = ee.ImageCollection("COPERNICUS/S2_SR")
        .filterBounds(geom)
        .filterDate(start, end)
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
        .median()
        .select(['B2', 'B3', 'B4', 'B5', 'B8', 'B11']);
    return s2.clip(geom);
}

years.forEach(function (year) {
    districts.toList(districts.size()).evaluate(function (list) {
        list.forEach(function (f) {
            var feature = ee.Feature(f);
            var name = feature.get('ADM2_NAME');
            print("Export: " + name)
            var composite = seasonalComposite(year, feature.geometry());
            Export.image.toDrive({
                image: composite,
                description: ee.String(name).cat('_').cat(ee.Number(year)).cat('_S2').getInfo(),
                folder: 'EarthEngine',
                fileNamePrefix: ee.String(name).cat('_').cat(ee.Number(year)).cat('_S2').getInfo(),
                region: feature.geometry(),
                scale: 10,
                crs: 'EPSG:4326',
                maxPixels: 1e13
            });
        });
    });
});