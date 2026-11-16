# FloodTracer — NASA Space Apps 2026 (team "NASA Que Ver", Montevideo, Uruguay)

App **FloodTracer** ("An interactive flood explorer powered by NISAR"); team: Kevin Castillos, Matias Ricardi, Sebastián Rodriguez. Repo: `github.com/kevcst/floodtracer` (GitHub Pages publishes `app/`). Challenge: `docs/challenge.md`.
Working language with the team: Spanish. Everything in the repository (README, docs, this file) and the app texts are in English; the app also has Spanish texts, English by default (the language travels only in `?lang=`).

## What it is
With NISAR (L-band, L2 GCOV) we follow the storm of 15–19 Aug 2026 in eastern Uruguay: where water appeared, how far it reached and how long it stayed. Case study: **northern Rocha**. The explorer adds Treinta y Tres, Laguna Merín and Río Branco. The README has the setup, pipeline, method and current results.

## Team rules
1. NISAR is the main source; other sources may improve the detection if the improvement is measured (ERA5 wind to pick calm passes). Validation sources (Sentinel-1, JRC) never enter the calculation. Never used for training.
2. One track per time series; tracks are combined only at the mask level.
3. Do not mix PROVISIONAL and VALIDATED without normalizing.
4. Press figures are preliminary and shown with their source.

## App conventions (`app/`)
- **No hand-written figures**: everything comes from `app/data/manifest.json` (`exportar_app.py` + the `metodo` entry from `exportar_metodo.py`). `python scripts/check_story_literals.py` checks there are no digits in STRINGS or in the HTML (proper names with digits are listed in its `NOMBRES`).
- Every visible text lives in `STRINGS = {en, es}` in each JS file. No em dashes. Honest tone: "promising", never "it works".
- Same legends on the three pages: orange "Water detected after the storm", blue "Water before the storm (baseline)", cyan `(60,200,230)` "Water detected before the storm, from earlier rains (not counted)". The pre-storm colour comes from `M.leyendas.previa`.
- Own CSS/JS files are loaded with `?v=` in `index.html`, `explorer.html`, `method.html`: bump it when publishing changes.
- **Story** (`index.html`, `story.js`, `story.css`): eight slides without scrolling, checked at 1280×720, 1366×768 and 1920×1080 (EN and ES). Mobile is out of scope. A button to the explorer at the end.
- **Explore** (`explorer.html`, `explorer.js`, `explorer.css`): four areas; `PRESETS` (default view: satellite, radar on, roads off) and `INFO` (text per area: Treinta y Tres negative case, Merín error fixed with wind, Río Branco success case, Rocha summary) in `explorer.js`. Two synced maps with a divider (dates, or map vs radar). Roads clipped to the radar footprint.
- **How we did it** (`method.html`, `method.js`, `method.css`): eleven steps with panels from `app/data/metodo/`; team credits at the end.

## Pipeline (`scripts/`, order in README §4)
- Run **without `--zona`** before exporting (with `--zona` the global CSV files are not written). `metricas_evento` and `combinar_tracks` run twice (pre-rain water of the combination). `exportar_metodo` always after `exportar_app`.
- `zonas.py`: areas, tracks, series, `mar_wkt` (ocean as no data), `excluir_tracks` (T132A in northern Rocha), `OUT`, `POLS`, `gdal_prefijo`.
- `metricas_evento.py`: change detector (−3 dB against the normal, −14 dB ceiling, 10-pixel minimum patch), permanent water from calm passes, pre-rain water by time of pass (`previa_hasta`), cropland as no data from 1 Oct, `tracks_zona()` (without excluded tracks).
- Main processing decisions (all in the code): ocean masked as no data (`mar_wkt`), pre-rain water by time of pass, permanent water written as 255 in the per-date stack, cropland as no data from October, ERA5 wind point over inland water, JRC known-water check, T132A excluded in northern Rocha (permanent water from one calm pass, 57% of JRC water), pre-storm water shown in cyan.

## Results
Current figures live in `app/data/manifest.json` (summary table in README §8). Northern Rocha: 9,373 ha confirmed, half dry day 25 but 49.6% on 9 Sep (at the edge of the cut). T31A and T132A both pass in the morning (~06:30 local time): do not call T132A "the morning orbit".

## Open items
- Half dry at the edge of the 50% cut: show it as a range (day 25 to 37) or interpolate.
- Wind: 2 of the 3 storm passes of the main track have > 3 m/s; today they are only flagged; a control inside each pass (permanent water below the ceiling, its change vs calm passes) would replace the ERA5 cut.
- Next method steps: normalize between tracks for a more complete timeline; improve water detection with ML (trained on hand-labelled examples, never on the validation sources).
- Safari not tested.
