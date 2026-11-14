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

## Scripts
- `scripts/descargar_zonas.py` (**usar este para la idea principal**):
  ```
  python scripts/descargar_zonas.py listar                  # inventario por zona (sin login)
  python scripts/descargar_zonas.py descargar --zona todas --workers 4
  python scripts/descargar_zonas.py descargar --zona treinta_y_tres
  python scripts/descargar_zonas.py resumen                 # % agua por zona/track/fecha -> CSV + PNG
  ```
  Salida: `data_nisar/zonas/{zona}/T{track}{dir}_F{frame}/{fecha}_{HH|HV}.tif`. Ventana 2026-06-15 → 10-20, sólo PROVISIONAL por defecto. ~232 recortes. Saltea archivos existentes (se puede re-correr).
  Para no re-bajar 53D: copiar `data_nisar/T53D_F105/*.tif` (excepto `2026-10-27_*`) a `data_nisar/zonas/merin_arrozales/T53D_F105/`.
  Si hay varias escenas por fecha prefiere modo principal `2005_..._M_..._N_F_` (corregido 2026-11-14: antes elegía escenas parciales `4005_..._A_..._P_` de 10 m en merin 154D).
- `scripts/metricas_evento.py`: por zona/track → `metricas/` con agua_base, extension_max, primera_fecha, fecha_retiro, persistencia_dias, delta_hh_db, veg_inundada (GeoTIFF) + `mapas_agua.png`; resumen en `data_nisar/zonas/metricas_resumen.csv` y `metricas_por_fecha.csv` (incluye HH y HH−HV medianos del monte por fecha). Umbral por track = agua perm + 0,3·(tierra − agua), recortado a [−20, −17,5] dB.
  También guarda `metricas/agua_nueva_por_fecha.tif` (una banda por fecha, 255 = sin dato) para combinar tracks.
- `scripts/combinar_tracks.py`: junta las máscaras de agua nueva de todos los tracks de una zona (grilla del track con más fechas) → `zonas/{zona}/combinado/` + `combinado_resumen.csv`/`combinado_persistencia.png`. Retiro = 2 observaciones secas seguidas.
- `scripts/monte_ribereno.py`: clasifica monte ribereño (altura rel. < 4 m) vs de altura (> 12 m) con Copernicus DEM GLO-30 (contexto, AWS público; OSM Overpass no respondía) y compara HH−HV por fecha → `monte_ribereno.csv/.png`.
- `scripts/exportar_poc.py` (baja contornos world-atlas a `data_nisar/contexto/` si faltan) → `poc/data/` (JPEG HH + PNG agua por fecha, extensión, persistencia, `poc.json`). Página POC: `poc/index.html` (inglés, fuente) → `python scripts/build_poc.py` arma `poc/dist/index.html` autocontenido (datos e imágenes embebidos; publicar ése), publicada como artifact privado https://claude.ai/artifact/VPErQm7A1EwbxTKpgqEj7n (2026-11-14). Contornos: world-atlas@2.0.2 (Natural Earth).
- `scripts/zonas.py`: AOIs (WKT), tracks por zona, ventana de fechas; `fin_base` opcional por zona (Durazno: 2026-07-20, por la crecida de julio del Yí).
- `scripts/nisar_eda_uruguay.py`: script original (inventario/descarga/explorar de un track sobre `AOI_RECORTE`); `descargar_zonas.py` importa de acá `OUT`, `POLS`, `gdal_prefijo`.
- `scripts/eda_extra_T53D.py`: análisis exploratorio extra (percentiles, mapas de agua, dispersores persistentes).

## Próximos pasos
1. Correr `listar` → `descargar --zona todas` → `resumen`; revisar si se ve el desfase Olimar → Yí → Negro.
2. ~~Crear `scripts/metricas_evento.py`~~ hecho. Hallazgo: en Durazno/Mercedes la crecida casi no se ve como agua abierta (ríos angostos a 100 m de suavizado, umbral −16 tomaba potreros) sino como **subida de HH−HV en monte (+1–1,8 dB)** durante el evento. Ojo: la subida aparece en todas las zonas (incluido Melo) → separar monte ribereño vs monte de altura (HAND/distancia al río) antes de afirmar que es agua bajo vegetación y no suelo húmedo. Persistencia mediana = 12 días en casi todo = resolución de revisita → combinar tracks.
3. ~~Combinar tracks~~ hecho, pero **los tracks no coinciden bien**: pasadas a 1 día de distancia tienen Jaccard 0,17–0,40 en el pico (154D ve 2,5× más agua que 132A en TyT/Merín) → la persistencia combinada se llena de "1 día" artificiales. Pendiente: armonizar umbrales entre tracks usando esos pares casi simultáneos. Mientras tanto usar persistencia por track (12 d) y el combinado sólo para extensión máxima.
3b. Monte ribereño vs de altura: exceso ribereño claro en Mercedes (+0,5 a +0,9 dB sobre el de altura, 3 tracks), Río Branco y Merín 132A/53D; **no** en Treinta y Tres, Melo ni Durazno. Hay un componente general de humedad (+0,3–1 dB también en monte de altura).
4. Capas vectoriales de contexto: localidades, caminería (OSM/MTOP), subcuencas (DINAGUA), departamentos; agregaciones → GeoJSON/CSV.
5. Validación: comparar curvas con niveles Olimar/Yí y desplazados SINAE por fecha.
6. App web (inglés): slider de fechas, capas de métricas, timeline por localidad/camino, vista país con las 6 zonas.
7. Revisar `QA_REPORT.pdf` de escenas raras antes de descartarlas.

## Referencias clave
- NISAR Data User Guide: https://nisar-docs.asf.alaska.edu/ (availability, gdal, harmony, asf-search)
- ASF Vertex: https://search.asf.alaska.edu/#/?dataset=NISAR · Worldview (capas GCOV): https://worldview.earthdata.nasa.gov/
- Earthdata Search + Harmony (recorte a COG sin código): https://search.earthdata.nasa.gov/
- Banda C vs L en río Santa Lucía (Boletín Geográfico 2024): https://doaj.org/article/bb87ff3d27a24e2c83dcdac1aedc53ba
- Judging guide: https://www.spaceappschallenge.org/resources/judging-awards-guide
- SAR/NISAR data discussion: https://github.com/nasa/spaceapps/discussions/1324
