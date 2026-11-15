# Immersive map

Branch: `feat/map-immersive`. Based directly on main commit `bf0fc92`.

The explorer is now the landing screen and starts the existing guided tour automatically. The original site palette (including automatic light/dark mode), fonts, published datasets, calculations and five tour steps are preserved.

The tour offers Previous, Next, chapter shortcuts, source inspection and Skip. Finishing or skipping reveals free exploration: all six locations, five scientific layers, visibility switches, comparison dates, opacity, downloads and spot histories remain available. The active location and layer stay visible in the header. Context, impact tables, graphs, validation, methods and downloads are available through Study & results instead of preceding the map. Sources & limits opens the contextual source panel without requiring tour completion.

Presentation-specific behavior: the map fills the viewport, the tour floats at the left, and tools open at the right.

On small screens the story becomes a compact lower panel and tools open as a full-screen panel. The map supports pan, zoom and the existing Before / After divider. Navigation is restricted to the selected study area, using the published layer corners. A small viewport-dependent context margin preserves the full overview on wide and narrow screens. Bounds update when selecting another area, moving between tour chapters or resizing the map; the comparison view follows the same camera. Chapters are manual and Next waits for loading. No analytical outputs were regenerated or scientifically revalidated by this presentation change.

Run from the repository root:

```bash
python3 -m http.server 8003 --bind 127.0.0.1 --directory app
```

Open http://127.0.0.1:8003. No build or backend is required.

The Basemap selector switches between OpenStreetMap and Esri World Imagery without rebuilding water polygons or changing the selected dates, area or tour chapter. Both comparison panes share the chosen background. Satellite tiles load directly in the browser, with provider attribution; no backend or imagery files are required. The selector and map key explain that this satellite/aerial mosaic has varying acquisition dates and is context, not a photograph of the selected NISAR observation. Source: https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer.

For Water by date on the satellite basemap, the display palette uses bright orange (#ff9d24) for candidate new water, cyan-blue (#00d9ff) for baseline water and light grey (#edf2f7) for land already wet before the rain. Stronger outlines improve separation from the imagery. The map key follows the palette, including in Before / After mode. This is a renderer-only recoloring: mask decoding, cached geometry, published data and the street-map palette are unchanged. The opacity slider still controls the fill transparency.

All scientific polygon layers start at 95% fill opacity on satellite imagery, with a slider that reaches 100% for fully solid colors. Opacity choices are remembered separately for satellite and street-map styles during the session.

Satellite styling also applies to Flood extent (bright orange and light grey), Days under water (an ordered ice-blue to vivid-blue scale), Date it dried (an ordered cream-to-coral scale) and Under the trees (bright mint green). Magenta distinguishes the separate no-dry-observation class in both temporal scales. Legends use the exact same display classes as the renderer. Published interval labels and measurements are preserved; roads keep their separate exposure scale.

Road exposure uses a separate light-to-dark purple scale for the existing duration bins, with a dark casing and white outer halo above the polygon layers. This styling is shared by street and satellite basemaps and both comparison panes. The Flooded roads switch controls all three strokes together. Road values, geometries, bin thresholds and popups are unchanged; the legend shows the five duration bins.

The observation timeline is centered at the bottom of the map during free exploration of Water by date, including Before / After mode. Flood extent, Days under water, Date it dried and Under the trees are event-wide products, so they hide the timeline rather than imply that moving a date slider changes those results. The map key moves above the timeline when it is visible and returns to the bottom for static layers. The guided tour keeps its existing chapter navigation.
