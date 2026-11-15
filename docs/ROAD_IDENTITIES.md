# Road identification enrichment

This change enriches only road identification. It leaves app/data/manifest.json, the published road GeoJSON, all source masks, all geometries and all scientific metrics untouched.

## Source and result

The official source is the MTOP departmental road network advertised by OPP: https://www.opp.gub.uy/sites/default/files/documentos/2019-10/Base%20cartogr%C3%A1fica%20de%20caminos%20codificados%20%28Geoservicio%20WFS%29.pdf

Service: https://geoservicios.mtop.gub.uy/geoserver/caminerias_intendencias/wfs?service=WFS&request=GetCapabilities

The six queried departmental layers cover Treinta y Tres, Rocha, Cerro Largo, Durazno, Soriano and Río Negro within the bounding rectangle of the six study areas. They contain 5,900 road features in the retrieved subset; some lack usable names/codes. The source's acquisition/update date is not asserted: the metadata records the retrieval time and snapshot hashes.

Of 199 unnamed segments in the published set of 215 segments, 16 receive an identification: nine have an official name and code, and seven have a code only. Existing OSM names are preserved. Examples include Punta Carretero (UYRO0167), Camino a La Balsa (UYTT0147), and Camino Paso De Las Gallinas (UYTT0146). Proper names are kept verbatim; UI explanations remain in English. No name is invented for an unmatched segment. The three unnamed example roads audited earlier, including the tour road with 3.80 km exposed, do not have a sufficiently supported match and remain unchanged.

## Matching policy

Matching uses the existing road's complete geometry in EPSG:32721, without changing it:

- At least 95% of the OSM segment length must fall within 25 m of one official road identity.
- A competing identity must cover no more than 10% of the segment.
- The 95th percentile of sampled distances must be at most 15 m.
- Tangents must agree within 30 degrees, allowing reversed line direction, at at least 90% of samples. This rejects crossings and short endpoints that proximity alone would misidentify.
- An official name is used only if the named official geometry supports at least 90% of the segment. Otherwise only the verified code is displayed.

For the accepted matches, coverage is at least 99.08%, sampled p95 distance is at most 10.10 m and direction agreement is at least 96.77%. These are geometric correspondence checks against the official records, not field verification of road names or road closures.

## Storage and presentation

app/data/impacto/road-identities.json is a separate metadata file. It includes source requests, snapshot hashes, official feature gids, road codes, matching evidence and links to the official records. Road and manifest SHA-256 fingerprints prevent the lookup from being applied to a different export.

app/road-identities.js applies display labels in memory. The road popups show the official name/code and source link. Three unambiguously corresponding rows in the existing top-road tables also receive display labels. Unmatched rows and published CSV/GeoJSON downloads retain their original OSM labels. Geometry, road class, exposed kilometres, duration intervals, wet/dry status and the road selected by the tour are unchanged. There are no browser calls to MTOP; GitHub Pages serves only the small prepared metadata file.

To regenerate from the official service:

```bash
.venv/bin/python scripts/enrich_road_names.py
```

The script caches source snapshots under ignored data_nisar/contexto/road_names_mtop and writes only app/data/impacto/road-identities.json as its published output. To use existing snapshots, pass --sources /path/to/snapshots --offline. It does not call the NISAR analysis or export pipeline. Regenerate this metadata after changing the underlying road export or manifest. Missing/incompatible metadata falls back to the existing OSM labels.
