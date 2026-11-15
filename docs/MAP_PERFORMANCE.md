# Prepared map polygons

The static website loads polygons generated from the existing published display masks. It does not re-run NISAR processing, change detections, simplify geometry or recalculate measurements.

## Build and publication

From the repository root, after exporting updated app/data inputs:

```bash
PYTHON=.venv/bin/python node scripts/build_map_vectors.mjs
python3 -m http.server 8003 --bind 127.0.0.1 --directory app
```

The build requires Node.js and Python with Pillow. On a machine without the project virtual environment, install Pillow and omit the PYTHON prefix. The exporter calls the unchanged app/vector-worker.js with the shared app/vector-classes.js definitions, including the original six-decimal coordinates and classification labels. All date-series masks use their series corners; all four event masks use their event corners.

The exporter writes 79 compressed GeoJSON views and data/vectors/index.json for the current published dataset. The prepared JSON totals approximately 109 MB uncompressed and 27 MB compressed, distributed across individually requested files. No full-dataset download is needed. These files are display derivatives; use the original published tables and rasters for measurements.

Each filename fingerprints its source mask, corner coordinates, classes and exporter implementation. The index records the source mask hash, raw GeoJSON hash, vertex count and sizes. The index is published only after every view has been generated successfully. Re-running the exporter reuses unchanged outputs and removes obsolete generated files. Run it whenever masks, corners or decoding change. GitHub Pages builds it before uploading app/, replacing the historical poc/dist deployment. No backend, access token or service worker is required.

## Browser behavior

- Prepared geometries load on demand. The gzip payload is decompressed in the browser, so the host does not need custom compression headers. Both raw gzip and server-decompressed responses are supported.
- The current view takes priority. Changing views aborts obsolete prepared-file requests and background prefetch. Stale results never replace the latest selected view.
- After rendering, at most three nearby views are prefetched sequentially: the next tour step, adjacent dates, or the next event layer. Prefetch is disabled when the browser reports data-saving mode or a 2G connection.
- Decoded geometry is retained in a memory LRU with a 24 MiB JSON-size budget (actual JavaScript heap use is larger). A single oversize view can remain by itself. Optional Cache Storage retains up to 64 MiB of compressed responses across visits, scoped to this site's path. Content-addressed files and index revalidation prevent reuse of old versions. Where Web Crypto is available, the index must also match the currently loaded manifest hash; otherwise the browser uses the original mask renderer. Obsolete files are removed from this application's cache when the index loads.
- Cached payloads are checked against their SHA-256 hash where Web Crypto is available. Corrupted persistent entries are removed and fetched again. Private browsing, quota limits or disabled storage do not block normal loading.
- The original contour worker remains a compatibility fallback when the prepared index is absent, decoding definitions differ, or gzip streams are unsupported. No background mask tracing is scheduled in that mode.
- Timeline dragging waits 120 ms between requested updates and commits immediately on release. The previous rendered geometry stays behind the loading overlay until its replacement is ready. Geometry is not cleared and uploaded twice. Visual switches reuse an unchanged selected view.
- Map colors are applied from class labels independently of cached geometry, preserving the street/satellite palettes, opacity and comparison behavior.

Prepared files remove mask decoding and contour calculation from the normal browsing path. MapLibre must still process and draw the selected geometry, and basemap tiles still need to load. Merín's duration mask has more than 530,000 vertices; a slower device can still take noticeable time. Vector tiles would be a separate next step if rendering remains the main bottleneck. This change does not claim instant transitions or a measured speedup factor.

During timeline playback, observation changes run without the blocking loading overlay. The current polygons stay visible while the next view loads, and playback waits for rendering to finish before requesting another observation. Manual date or layer selection still shows the overlay; load failures still stop playback and show the retry message. This changes transition presentation, not the observations or their timing in the dataset.
