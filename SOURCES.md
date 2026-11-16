# FloodTracer data sources

This document lists the external sources used by **FloodTracer** (Story, Explore and How we did it), their role, and where to access them.

Flood extent, percentages, duration estimates, and agreement statistics are **derived by this project's scripts**. They are not ready-made results supplied by NASA or the other providers. The published values and metadata are in [`app/data/manifest.json`](app/data/manifest.json).

## Primary observations and data access

| Source or service | How we use it | Resource |
| --- | --- | --- |
| **NASA/ISRO NISAR L2 GCOV**, distributed by **ASF DAAC** | Primary radar observations: detect changes consistent with flooding, estimate affected area, follow observations over time, estimate drying intervals, and investigate vegetation-related radar signals. | [NISAR data documentation](https://nisar-docs.asf.alaska.edu/) · [Find NISAR scenes in ASF Vertex](https://search.asf.alaska.edu/#/?dataset=NISAR) |
| **NASA Earthdata Login** | Account authentication and authorization for access to NISAR downloads through ASF. This is an access service, not a separate dataset or flood measurement. | [Earthdata Login](https://urs.earthdata.nasa.gov/) |

Implementation: [`scripts/descargar_zonas.py`](scripts/descargar_zonas.py), [`scripts/metricas_evento.py`](scripts/metricas_evento.py), and [`scripts/combinar_tracks.py`](scripts/combinar_tracks.py). Download instructions are in the [README](README.md).

## Comparison and supporting datasets

| Source | How we use it in the Story | Resource |
| --- | --- | --- |
| **Copernicus Sentinel-1 RTC**, accessed through **Microsoft Planetary Computer** | Compare C-band water detections with NISAR and calculate agreement metrics. It does not feed the main NISAR flood detector. These comparisons are not field-based ground truth. | [Sentinel-1 RTC collection](https://planetarycomputer.microsoft.com/dataset/sentinel-1-rtc) |
| **Copernicus Sentinel-2 L2A**, accessed through **Microsoft Planetary Computer** | Optical imagery and cloud-cover metadata for the optical-versus-radar explanation. Used as visual context, not to calculate flooded hectares. The displayed optical and radar observations have different dates. | [Sentinel-2 L2A collection](https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a) |
| **ERA5 / ERA5-Land**, accessed through the **Open-Meteo Historical Weather API** | Wind and rainfall context around the radar passes. Wind helps select calm baseline observations and flag potentially affected passes; the wind point is taken over inland water, never over the ocean. The hourly rainfall start also decides which passes count as before the rain (pre-storm water, shown apart). These are gridded estimates, not measurements at each field. | [Historical Weather API and model documentation](https://open-meteo.com/en/docs/historical-weather-api) |
| **JRC Global Surface Water** (occurrence 1984–2021) | Validation only: how much of the water known to be permanent NISAR marks as permanent water, per track. It is one of the reasons a track was left out in northern Rocha. It does not feed the detector. | [Global Surface Water Explorer](https://global-surface-water.appspot.com/) |
| **ESA WorldCover 2021 v200** | Group detected flooding by land cover, including grassland, herbaceous wetland, and cropland; support vegetation analysis, the selection of the weather-query location and the ocean mask; cropland is treated as no data from October (field preparation looks like water). WorldCover alone does not establish that cropland is rice. | [ESA WorldCover](https://esa-worldcover.org/) |
| **Copernicus DEM GLO-30** | Terrain context for the riverside vegetation analysis, including derived terrain and drainage-related classifications. It does not measure floodwater depth. | [Copernicus DEM public dataset and access information](https://registry.opendata.aws/copernicus-dem/) |
| **OpenStreetMap**, downloaded through **Geofabrik** | Rural road geometry crossed with detected flooded land. This identifies spatial overlap, not confirmed road closures. OpenStreetMap tiles also provide the Story's background map. | [Uruguay extract](https://download.geofabrik.de/south-america/uruguay.html) · [OpenStreetMap contributors and attribution](https://www.openstreetmap.org/copyright) |

Implementation: [`scripts/validar_s1.py`](scripts/validar_s1.py), [`scripts/agua_conocida.py`](scripts/agua_conocida.py), [`scripts/exportar_optico.py`](scripts/exportar_optico.py), [`scripts/clima.py`](scripts/clima.py), [`scripts/capas_contexto.py`](scripts/capas_contexto.py), [`scripts/monte_ribereno.py`](scripts/monte_ribereno.py), and [`scripts/agregar_impacto.py`](scripts/agregar_impacto.py).

## Reported event context

The Story contrasts the satellite analysis with preliminary reporting of **5,000–6,000 affected hectares and approximately 15,000 animals moved around 18 de Julio**. Reported estimates have different dates and geographic coverage from the satellite analysis. Multiple outlets may repeat the same original report; they are not necessarily independent measurements.

| Source | How we use it | Resource |
| --- | --- | --- |
| **APU / UyPress** | Reported flood impacts, livestock movements, and regional event context. | [APU article referenced by the project](https://www.apu.uy/noticias/lluvias-extraordinarias-rios-desbordados-y-una-emergencia-que-sigue-abierta) · [UyPress report](https://www.uypress.net/Actualidad/Aumentan-los-evacuados-en-Uruguay-los-rios-crecen-y-productores-movilizan-ganado-por-las-inundaciones-uc155574) |
| **InfoUruguay** | Reporting supporting the preliminary affected-area and livestock figures for Rocha. | [Flood impact report](https://www.infouruguay.com.uy/noticias/3768-inundaciones-avanzan-en-varios-departamentos-de-uruguay-evacuados-rutas-afectadas-y-miles-de-animales-trasladados) |
| **La R / Grupo R Multimedio** | Reported regional impacts and climate/emergency context; listed among the sources for the preliminary case figures. | [Article referenced by the project](https://grupormultimedio.com/el-nino-ya-enciende-alarmas-miles-de-evacuados-campos-bajo-agua-y-reclamo-de-recursos-nacionales-id204181/) |
| **Agrolatam** | Reported persistent flooding in northern Rocha around San Luis, Cebollati, and San Miguel, dated August 24 in the project notes. | [Project's recorded source notes](docs/event_context_aug2026.md). An exact article URL is not recorded; this reference still needs a direct link. |

The preliminary case figures are assembled in [`scripts/exportar_app.py`](scripts/exportar_app.py) (`PRENSA_CASO`).
