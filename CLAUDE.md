# Dancing with the SARs — NASA Space Apps 2026 (equipo Uruguay)

Contexto para seguir trabajando con Claude Code. Idioma de trabajo: español. Entregables del hackatón: en inglés (requisito de Space Apps).

## El desafío
- Construir una app interactiva que use datos de radar **NISAR** (L-band) para rastrear y visualizar cambios en la superficie, e hipotetizar sus causas físicas/humanas. Ver `docs/challenge.md` y `docs/challenge_resources.txt`.
- Criterios: Influence, Creativity, Validity, Relevance, Presentation. Premios relevantes: *Local Impact*, *Best Storytelling*, *Best Use of Data*.

## IDEA PRINCIPAL (decidida 2026-11-14) — detalle completo en `docs/idea_principal.md`
**"How long does the water stay?" / "¿Cuánto tiempo se queda el agua?"** — reconstruir con NISAR la crecida del **15–19 ago 2026** y medir por píxel (20 m): extensión máxima, **persistencia** (días bajo agua), fecha de retiro y agua bajo vegetación (doble rebote L-band); agregar por localidad, camino rural, subcuenca y uso del suelo. Contexto país: crecidas encadenadas Olimar → Yí → río Negro y remanso de la Laguna Merín (`docs/contexto_nacional_ago2026.md`).
- Zonas: `treinta_y_tres`, `merin_arrozales`, `melo`, `rio_branco_jaguarao`, `durazno`, `mercedes` (AOIs y tracks en `scripts/zonas.py`).
- Uso social: SINAE/CECOED, caminería rural, productores/seguros, planificación de riesgo (El Niño 2026-27).
- Límites: revisita 12 días/track, urbano confuso, latencia → post-evento, no predicción.
- Capítulo secundario: arrozales — mismos lotes con agua "mala" (agosto) y "buena" (riego nov–dic).

## Reglas del equipo
1. El análisis se apoya en **NISAR**. Otras fuentes (Sentinel-1, INUMET, DINAGUA, SINAE, DIEA, Sentinel-2, MapBiomas) sólo como **validación independiente o contexto**, nunca para entrenar ni mezcladas en las series principales.
2. Series temporales: **un track por serie** (misma geometría); combinar tracks sólo a nivel de máscara de agua y con umbral calibrado por track.
3. **No mezclar PROVISIONAL y VALIDATED** sin normalizar (salto ~−1,7 dB HH / −2,2 dB HV en tierra).
4. Cifras de prensa = preliminares; confirmar con SINAE/CECOED antes de publicar.

## Historial de decisiones
- Idea original (predecir tendencia de inundaciones en Uruguay) descartada como núcleo: NISAR tiene poca historia y el desafío pide visualización.
- Primera elección: arrozales "agua buena vs. mala" → pasó a secundaria porque la inundación de riego aún no empezó (0,36 % agua nueva al 27/10) y el EDA mostró la crecida de agosto.
- Bañados del Este (agua bajo vegetación) → se incorpora como métrica dentro de la idea principal.
- 2026-11-14: detector de agua nueva pasa de umbral absoluto (HH < −17,5…−18,7 dB) a **cambio respecto de la base del mismo píxel** (armonizar_tracks.py duplicó la coincidencia entre tracks). Las cifras subieron (Merín 28.600 → ~75.000 ha confirmadas): el detector viejo se perdía agua somera (HH −14 a −17 dB) que Sentinel-1 también ve oscurecerse.
- 2026-11-14 (tarde): (1) horarios de órbita estaban invertidos en docs/app: ascendentes ~06:30, descendentes ~18:30 hora local; la explicación por viento se retiró. (2) ~1/3 del "agua nueva" ya estaba el 10–11/8 (antes de la lluvia) e inflaba persistencia, ha·día y días de corte (hasta 84 d): se separa como "agua previa" y la extensión arranca el 15/8. Cifras bajaron (Merín 75 → 48 mil ha).
- 2026-11-14: decisiones abiertas del plan tomadas por defecto (usuario ausente): mapa base OSM (CARTO pide API key), caminería OSM, Sentinel-1 sí como validación, arrozales queda como trabajo futuro.

## Resultados EDA (2026-11-14) — `docs/eda_T53D_F105.md`
- 53D-105 (arrozales): agua 4–5 % → 10 % (08-16) → **14 % (08-28)** → 8 % (09-09) → 5 % (09-21). 85 % del agua nueva se retiró al 21/9.
- Otsu global no funciona (histograma no bimodal) → umbral fijo ~−18/−19 dB (agua permanente ~−22,5 dB) u Otsu por tiles.
- El 27/10 (VALIDATED) muestra un salto de calibración, no agua real.

## Datos NISAR (verificado 2026-11-14)
- Producto **L2 GCOV** (gamma0 RTC, HDF5), `HHHH` y `HVHV` en `/science/LSAR/GCOV/grids/frequencyA/`. Escenas DHDH de 1–2 GB → bajar sólo recortes.
- PROVISIONAL: 2026-06-17 → ~10-23. VALIDATED: desde 10-21 (sigue entrando). Sin BETA sobre Uruguay. Reprocesamiento VALIDATED del backlog: 2027.
- **Hueco global**: 2026-07-27 → 08-10.
- Cobertura del evento por zona: ver tabla en `docs/idea_principal.md` §4 y `docs/contexto_nacional_ago2026.md`.

## Setup (ver README.md §3)
Earthdata Login + `~/.netrc`; GDAL CLI (`brew install gdal`); `python -m venv .venv && pip install -r requirements.txt`.

## Entrega principal: app web (2026-11-14)
- `app/index.html` (inglés, MapLibre 4.7.1 + teselas OSM) + `app/data/` generado por `scripts/exportar_app.py` (versionado, ~18 MB). Servir: `python3 -m http.server -d app 8000`. **Ninguna cifra escrita a mano en el HTML**: todo sale de `app/data/manifest.json` (excepto la línea de tiempo de prensa).
- Pipeline completo y método: README §4–5. Plan y estado: `docs/plan_desarrollo.md`. Validación: `docs/validacion.md`.
- La POC (`poc/`, artifact https://claude.ai/artifact/VPErQm7A1EwbxTKpgqEj7n) quedó histórica con el detector viejo.

## Scripts (orden del pipeline)
`descargar_zonas.py` → `metricas_evento.py` → `armonizar_tracks.py` → `combinar_tracks.py` → `sensibilidad.py` → `capas_contexto.py` → `monte_ribereno.py` → `agregar_impacto.py` → `validar_s1.py` (opcional, lento la 1ª vez) → `exportar_app.py`. Correr desde `scripts/` o la raíz; los CSV globales sólo se escriben sin `--zona`.
- `descargar_zonas.py listar|descargar|resumen`: recortes GCOV por zona → `data_nisar/zonas/{zona}/T{track}{dir}_F{frame}/{fecha}_{HH|HV}.tif`. Prefiere modo principal `2005_..._M_..._N_F_`. Sintaxis GDAL `HDF5:"/vsicurl/URL"://ruta` (GDAL ≥ 3.13).
- `metricas_evento.py`: **detector por cambio** (desde 2026-11-14): ΔHH vs mediana base del mismo píxel/track < −3 dB, HH < −14 dB, normalización por mediana de escena, MMU 10 px; agua base con umbral absoluto calibrado por track. Persistencia = intervalo (`persistencia_min/max.tif`, punto medio en `persistencia_dias.tif`). `--metodo umbral` = detector viejo.
- `armonizar_tracks.py`: Jaccard entre tracks a ≤ 1 día. Umbral → cambio: TyT 0,18→0,48, Merín 0,49→0,58, Río Branco 0,39→0,56, Mercedes 0,18→0,27 (poca agua). Hallazgo: con umbral fijo los descendentes (~18:30 hora local) ven 2–3× más agua que los ascendentes (~06:30); causa abierta (ángulo/dirección de cada track, rocío matinal), el viento no lo explica. Horarios verificados en los nombres de escena (UTC).
- `combinar_tracks.py`: máscaras de todos los tracks; `agua_previa.tif` (mojada el 10–14/8, antes de la lluvia: aparte y fuera de todo); `extension_confirmada.tif` (≥ 2 obs. mojadas en 15/8–10/9, sin previa) = cifra principal; retiro = 2 obs. secas seguidas.
- `sensibilidad.py`: barrido caída {−2…−4} × techo {−13,−14,−15} → banda min/central/max.
- `capas_contexto.py`: OSM Geofabrik (driver OSM de GDAL; ojo: un WHERE con OR pierde las relaciones administrativas), HydroBASINS L8, ESA WorldCover → `data_nisar/contexto/capas/{zona}.gpkg`, `T*/contexto/worldcover.tif`.
- `monte_ribereno.py`: HAND con drenaje OSM; ribereño HAND < 4 m y < 1 km del cauce; exceso = subida ribereño − subida altura; mapa `metricas/veg_inundada_ribereno.tif`.
- `agregar_impacto.py`: caminos (por way OSM, con "x km NE de <localidad>"), localidades (adentro + anillo 500 m), subcuencas (nombre del curso principal), departamentos, cobertura → `data_nisar/zonas/impacto/`.
- `validar_s1.py`: Sentinel-1 RTC de Planetary Computer (token SAS anónimo), ±2 días, misma órbita para la base; sólo valida (regla 1). Caché en `data_nisar/validacion/s1/`.
- `exportar_app.py`: manifest + WebP/PNG con esquinas lon/lat + `sonda.bin` (200 m) + GeoJSON + descargas.
- `zonas.py`: AOIs, tracks, `serie` (track de la serie principal por zona, regla 2), `fin_base` (Durazno 2026-07-20).
- Históricos: `nisar_eda_uruguay.py` (otros importan `OUT`, `POLS`, `gdal_prefijo`), `eda_extra_T53D.py`, `exportar_poc.py`/`build_poc.py`.

## Resultados actuales (detector por cambio, sin agua previa)
- Inundado por la tormenta (≥ 2 obs., 15/8–10/9): Merín 47.927 ha (53D solo 30–67 mil), TyT 6.290, Río Branco 2.510, Durazno 341, Mercedes 180, Melo 35 (≈ 57.300 ha). Ya mojado antes de la lluvia (10–14/8): ≈ 31.100 ha, aparte. Merín 53D: 70 % mojado el 28/8, 15 % el 21/9. Persistencia típica 6 d Merín, 10 d TyT, 18 d Río Branco.
- Caminos: Merín 42 km (29 km > 1 semana), TyT 13 km; máximo 66 días. Dentro de las ciudades el radar da ~0 (doble rebote): usar anillo 500 m.
- Monte ribereño: exceso positivo en Mercedes (3 tracks), Río Branco, Merín; no en TyT, Melo, Durazno.

## Próximos pasos
**Plan: `docs/plan_desarrollo.md`.** Hecho A1–A6, B1–B2, C, D. Pendiente: capítulo arrozales (E, requiere normalizar VALIDATED), publicar la app (GitHub Pages), video/slides, niveles DINAGUA por API (no conseguidos), revisar `QA_REPORT.pdf`.

## Referencias clave
- NISAR Data User Guide: https://nisar-docs.asf.alaska.edu/ (availability, gdal, harmony, asf-search)
- ASF Vertex: https://search.asf.alaska.edu/#/?dataset=NISAR · Worldview (capas GCOV): https://worldview.earthdata.nasa.gov/
- Earthdata Search + Harmony (recorte a COG sin código): https://search.earthdata.nasa.gov/
- Banda C vs L en río Santa Lucía (Boletín Geográfico 2024): https://doaj.org/article/bb87ff3d27a24e2c83dcdac1aedc53ba
- Judging guide: https://www.spaceappschallenge.org/resources/judging-awards-guide
- SAR/NISAR data discussion: https://github.com/nasa/spaceapps/discussions/1324
