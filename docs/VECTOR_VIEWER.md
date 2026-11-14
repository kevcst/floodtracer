# Vector viewer integration

Branch: `feat/vector-viewer-from-main`. Base: main commit `8cd219b`.

This change only replaces the default presentation of the existing explorer with interactive water polygons over OpenStreetMap. The radar photograph is optional and off by default. Area/date/layer controls, roads, towns, the point-history probe, charts, statistics and existing validation sections are retained. Polygon opacity and downloading the current view as GeoJSON are added.

## Existing data only

No files in `app/data/` are modified. No processing, detection, metric, validation or export script is changed or run. The page continues to read its existing manifest and existing categorical PNG display masks. Its original published numbers remain unchanged.

The browser reads the selected mask's categorical colors into a non-visible canvas, traces contours in a Web Worker, maps the resulting GeoJSON using the same published four geographic corners, and draws it with MapLibre. The mask image is an input to the display adapter; it is not shown over the street map. Raster radar photographs are only requested if the user explicitly enables the optional radar control. A small bounded session cache reuses recent geometry.

This is a display integration, not a new scientific data product. GeoJSON boundaries are traced from the already-exported display grid and follow a contouring convention. They should not be treated as native-resolution analytical flood boundaries or used to recalculate hectare estimates. A validation of the new presentation can be performed separately; this change introduces no new validation conclusions.

## Local preview

```bash
python3 -m http.server 8003 --bind 127.0.0.1 --directory app
```

Open http://127.0.0.1:8003/#explore. There is no build step for the current `app/` website and no application backend. The historical `poc/` build is untouched.

Added dependencies are vendored D3 Array 3.2.4 and D3 Contour 4.0.2, with their ISC licenses in `app/vendor/`. Existing MapLibre/OpenStreetMap loading is unchanged. The new worker and vendor files must be published alongside `app/index.html`.

## Compare dates and inspect provenance

Enable **Before / After** to compare two published passes from the area's primary orbit track. Choose an earlier and a later date, then drag the map divider or use the comparison slider. The divider supports arrow keys and Home/End. Both views share the same camera; optional radar imagery and the polygon visibility and opacity controls apply to both. Selecting an event layer exits date comparison. Charts and the GeoJSON download refer to the After date while comparing. Context roads describe the event as a whole, not date-specific closures.

The expandable **Where does this result come from?** panel updates for each area, layer and date selection. It explains the baseline, processing method, intended interpretation and limitations, and links the published display masks and result tables. Sentinel-1 agreement is reported only for the open-water detector; it does not validate the duration or forest-signal products. The panel explicitly identifies the single-observation extent criterion and single-date baseline used for Durazno. These explanations do not constitute new validation or change the underlying published outputs.
