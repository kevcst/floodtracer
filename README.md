# Dancing with the SARs — NASA Space Apps 2026 (equipo Uruguay)

**Idea: "How long does the water stay?" / "¿Cuánto tiempo se queda el agua?"**

Con el radar **NISAR** (banda L, NASA/ISRO), que ve a través de las nubes cada 12 días, reconstruimos la crecida del **15–19 de agosto de 2026** en Uruguay y medimos dónde apareció agua nueva, hasta dónde llegó, cuánto tardó en irse y dónde quedó agua bajo el monte. Comparamos la cuenca de la Laguna Merín (Olimar, Cebollatí, Yaguarón) con la del río Negro (Yí, Mercedes).

- **Entrega principal (app web, inglés):** `app/`. Se sirve con `python3 -m http.server -d app 8000` → http://localhost:8000. Ver [Ver la app](#1-ver-la-app).
- POC original (histórica, se abre con doble clic): `poc/dist/index.html`.
- Plan de desarrollo POC → entrega: `docs/plan_desarrollo.md`. Validación: `docs/validacion.md`. Detalle de la idea: `docs/idea_principal.md`. Contexto del evento (prensa, SINAE): `docs/contexto_nacional_ago2026.md`. EDA inicial: `docs/eda_T53D_F105.md`.
- Desafío oficial: `docs/challenge.md`. Los entregables del hackatón van en **inglés**; el trabajo interno, en español.

---

## Índice
1. [Ver la app](#1-ver-la-app)
2. [Estructura del repo](#2-estructura-del-repo)
3. [Setup (una sola vez)](#3-setup-una-sola-vez)
4. [Pipeline completo: de la descarga a la app](#4-pipeline-completo-de-la-descarga-a-la-app)
5. [Qué hace cada paso (método)](#5-qué-hace-cada-paso-método)
6. [Zonas y tracks](#6-zonas-y-tracks)
7. [Reglas del equipo](#7-reglas-del-equipo)
8. [Resultados](#8-resultados-2026-11-14-detector-por-cambio)
9. [Limitaciones y pendientes](#9-limitaciones-y-pendientes)
10. [Problemas frecuentes](#10-problemas-frecuentes)
11. [Referencias](#11-referencias)

---

## 1. Ver la app

`app/` es una página estática: `index.html` + `data/` (≈18 MB, ya versionado). No necesita Python ni los datos NISAR, pero **sí un servidor http** (el navegador bloquea `fetch` y las texturas del mapa sobre `file://`) e internet (MapLibre, mapa base de OpenStreetMap y tipografías).

```bash
python3 -m http.server -d app 8000     # desde la raíz del repo
# abrir http://localhost:8000
```

Secciones: cifras clave · mapa del país con las 6 zonas y línea de tiempo · "pulso" de agua por zona con banda de incertidumbre y cresta reportada · **explorador** (MapLibre: radar y agua por fecha con slider/play, extensión, días bajo agua, fecha de retiro, agua bajo monte, caminos inundados, localidades, y clic en cualquier punto para ver su historia de radar) · impacto (caminos, cobertura del suelo, localidades, subcuencas, resumen de las 6 zonas) · agua bajo el monte · causas físicas · validación (tracks, Sentinel-1, crestas) · método y límites · descargas (CSV + GeoTIFF).

**Ninguna cifra está escrita a mano en el HTML**: todo sale de `app/data/manifest.json`, que genera `scripts/exportar_app.py`. La excepción es la línea de tiempo de prensa (contexto).

La POC vieja sigue en `poc/` (ver `poc/README.md`); quedó con las cifras del detector anterior.

---

## 2. Estructura del repo

```
CLAUDE.md                 Contexto y decisiones para trabajar con Claude Code (la "memoria" del proyecto)
README.md                 Este archivo
requirements.txt          Dependencias Python
docs/                     Desafío, idea, plan de desarrollo, validación, contexto del evento, EDA
scripts/
  zonas.py                Zonas (AOI en WKT), tracks por zona, track de la serie principal, ventana de fechas
  descargar_zonas.py      1  Inventario y descarga de recortes NISAR por zona
  metricas_evento.py      2  Agua base / agua nueva (detector por cambio), extensión, persistencia (intervalo)
  armonizar_tracks.py     3  Coincidencia entre tracks a ≤1 día (justifica el detector)
  combinar_tracks.py      4  Combina tracks de una zona: extensión confirmada, persistencia con ~1–6 días
  sensibilidad.py         5  Banda de incertidumbre (barrido de parámetros del detector)
  capas_contexto.py       6  OSM (Geofabrik), HydroBASINS, ESA WorldCover por zona
  monte_ribereno.py       7  HAND con drenaje OSM, monte ribereño vs de altura, mapa de agua bajo monte
  agregar_impacto.py      8  Caminos, localidades, subcuencas, departamentos, cobertura del suelo
  validar_s1.py           9  Validación con Sentinel-1 RTC (sólo valida)
  exportar_app.py         10 app/data/ (manifest.json, imágenes, sonda, GeoJSON, descargas)
  exportar_poc.py, build_poc.py   POC histórica
  nisar_eda_uruguay.py    Script original; otros importan de acá
  eda_extra_T53D.py       EDA histórico del track 53D
app/
  index.html              App (inglés)
  data/                   Generado por exportar_app.py (versionado)
poc/                      POC histórica
data_nisar/               DATOS (no se versiona: ~6 GB). Se genera con los scripts
```

`data_nisar/` está en `.gitignore`, igual que `*.tif` (salvo los GeoTIFF livianos de `app/data/descargas/`), `*.h5`, `.venv/` y `.netrc`.

---

## 3. Setup (una sola vez)

Probado en macOS con Python 3.11 y GDAL 3.13. En Linux debería funcionar igual. En Windows recomendamos **WSL**: el script guarda cookies de GDAL en `/tmp`.

### 3.1 Cuenta de NASA Earthdata
1. Crear usuario en https://urs.earthdata.nasa.gov/ (gratis).
2. La primera descarga de ASF puede pedir autorizar la aplicación **"Alaska Satellite Facility Data Access"**. Si la descarga da `401`/`403`, entrar a Earthdata → *Applications → Authorized Apps*, autorizarla y aceptar el EULA.

### 3.2 Credenciales en `~/.netrc`
GDAL lee usuario y contraseña de ese archivo, en **tu home**, nunca dentro del repo:

```bash
printf 'machine urs.earthdata.nasa.gov\n    login TU_USUARIO\n    password TU_PASSWORD\n' > ~/.netrc
chmod 600 ~/.netrc     # obligatorio: si otros pueden leerlo, curl/GDAL lo ignoran
```

Si la contraseña tiene espacios o `#`, conviene cambiarla.

### 3.3 GDAL (línea de comandos)
```bash
brew install gdal          # macOS
sudo apt install gdal-bin  # Ubuntu/Debian (verificar versión con gdalinfo --version)
```
Con GDAL ≥ 3.13 se usa el driver HDF5 nativo. Con versiones anteriores el script cambia solo al driver `NETCDF:`.

### 3.4 Entorno Python
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 4. Pipeline completo: de la descarga a la app

Todos los comandos se corren **desde la raíz del repo** con el venv activado (`source .venv/bin/activate`).

| Paso | Comando | Qué genera | Tiempo |
|---|---|---|---|
| 0 (opcional) | `python scripts/descargar_zonas.py listar` | `data_nisar/zonas/inventario_zonas.csv` (sin login) | < 1 min |
| 1 | `python scripts/descargar_zonas.py descargar --zona todas --workers 4` | `data_nisar/zonas/{zona}/T{track}{dir}_F{frame}/{fecha}_{HH\|HV}.tif` (~3 GB) | 30–90 min |
| 2 | `python scripts/metricas_evento.py` | `.../T*/metricas/*.tif`; `metricas_resumen.csv`, `metricas_por_fecha.csv` | ~1,5 min |
| 3 | `python scripts/armonizar_tracks.py` | `armonizacion_pares.csv/.png` (con `--barrido`: barrido de parámetros, lento) | ~3 min |
| 4 | `python scripts/combinar_tracks.py` | `{zona}/combinado/*.tif`; `combinado_resumen.csv` | < 1 min |
| 5 | `python scripts/sensibilidad.py` | `sensibilidad_por_fecha.csv`, `sensibilidad_resumen.csv` | ~5 min |
| 6 | `python scripts/capas_contexto.py` | `data_nisar/contexto/capas/{zona}.gpkg`, `.../T*/contexto/worldcover.tif` (baja OSM ~57 MB, HydroBASINS ~30 MB) | ~1 min |
| 7 | `python scripts/monte_ribereno.py` | `.../T*/contexto/{dem,hand,dist_rio,clase_monte}.tif`, `veg_inundada_ribereno.tif`; `monte_ribereno*.csv` (baja DEM Copernicus de AWS) | ~2 min |
| 8 | `python scripts/agregar_impacto.py` | `data_nisar/zonas/impacto/*.csv/.geojson` | < 1 min |
| 9 | `python scripts/validar_s1.py` | `validacion_s1.csv/.png` (baja recortes Sentinel-1 de Planetary Computer, anónimo; se cachean) | ~1–2 h la primera vez |
| 10 | `python scripts/exportar_app.py` | `app/data/` | < 1 min |
| 11 | `python3 -m http.server -d app 8000` | Ver la app | |

Una vez descargados los datos (el paso 9 es opcional: sin él, la sección de Sentinel-1 queda vacía):

```bash
cd scripts && python metricas_evento.py && python armonizar_tracks.py && python combinar_tracks.py \
  && python sensibilidad.py && python capas_contexto.py && python monte_ribereno.py && python agregar_impacto.py \
  && python exportar_app.py && cd .. && python3 -m http.server -d app 8000
```

### Notas sobre la descarga (paso 1)
- **Se puede volver a correr sin miedo:** saltea los archivos que ya existen y escribe primero a `.part.tif`, así que un corte no deja archivos rotos. Si hubo errores de red, alcanza con volver a correrlo.
- Se esperan **232 recortes**, de los cuales **226** se pueden bajar. Los 6 restantes dan `ERROR ... HVHV` porque son escenas **SHSH** (sólo HH, sin HV). Es normal.
- Para probar rápido con una sola zona: `--zona treinta_y_tres` (~0,5 GB) o `--zona durazno` (~0,07 GB). La app necesita **todas**.
- `merin_arrozales` es la zona pesada (~2,6 GB): el AOI es grande.
- Se baja **sólo el recorte** de cada escena, vía `gdalwarp` sobre `/vsicurl/`. Las escenas completas pesan 1–2 GB cada una.
- Ventana: 2026-06-15 → 2026-10-20, sólo madurez **PROVISIONAL** (ver reglas). Para incluir VALIDATED: `--madurez PROVISIONAL VALIDATED`, pero no las mezclen sin normalizar.

### Correr una sola zona
`--zona <nombre>` (en `metricas_evento`, `combinar_tracks`, `monte_ribereno`, `validar_s1`) sirve para iterar rápido, pero los CSV globales sólo se escriben con todas las zonas. Antes de `exportar_app.py`, corran todo sin `--zona`.

### Scripts históricos (opcionales)
- `python scripts/nisar_eda_uruguay.py inventario | descargar --track 53 --dir D --frame 105 | explorar --track 53 --dir D --frame 105`: primer EDA sobre un solo track. Escribe en `data_nisar/T53D_F105/`.
- `python scripts/eda_extra_T53D.py`: percentiles, Otsu, mapas y dispersores persistentes de ese track. Escribe en `/tmp/eda`. Sus conclusiones están en `docs/eda_T53D_F105.md`.

---

## 5. Qué hace cada paso (método)

**Producto:** NISAR **L2 GCOV** (gamma0 RTC, 20 m, HDF5): `HHHH` (HH) y `HVHV` (HV) de `/science/LSAR/GCOV/grids/frequencyA/`. Cada recorte queda en la proyección nativa del frame (UTM 21S/22S), con la misma grilla en todas las fechas de un track.

**Por qué se ve el agua:** el agua calma refleja el radar como un espejo y se ve muy oscura (HH ≈ −22 dB). Bajo árboles, la señal rebota entre agua y troncos (*doble rebote*) y vuelve **más fuerte** (HH sube respecto de HV). La banda L penetra el follaje; la banda C y los ópticos, en general, no.

1. **`descargar_zonas.py`:** busca escenas GCOV con `asf_search` y recorta cada una al AOI. Si hay varias escenas por fecha prefiere el modo principal (`2005_..._M_..._N_F_`).
2. **`metricas_evento.py`**, por zona y track:
   - Speckle: media 5×5 en lineal (~100 m).
   - **Agua base** (permanente): HH bajo el umbral calibrado por track (agua perm. + 30 % de la distancia a tierra, en [−20, −17,5] dB) en la mayoría de las fechas de la línea de base (antes del 27/7; Durazno antes del 20/7).
   - **Agua nueva (detector por cambio):** HH del día − mediana HH de la base del mismo píxel < **−3 dB**, HH < **−14 dB**, fuera del agua base, manchas ≥ **10 px** (0,4 ha). Antes, cada pasada se normaliza restando la mediana del cambio en toda la escena (corrige pasadas enteras más oscuras/claras). `--metodo umbral` reproduce el detector viejo.
   - **Persistencia como intervalo:** mín = última pasada mojada − primera; máx = primera pasada seca − pasada previa a la llegada del agua (nunca antes del 15/8). Se guarda el punto medio y ambas cotas.
3. **`armonizar_tracks.py`:** mide la coincidencia (Jaccard) entre tracks distintos a ≤ 1 día. Con umbral absoluto daba 0,18–0,49 por zona; con el detector por cambio 0,27–0,58 (Merín 0,58, Río Branco 0,56, TyT 0,48; Mercedes 0,27, con muy poca agua). Hallazgo: con umbral fijo los tracks **descendentes** (~18:30 hora local, atardecer) veían 2–3× más agua que los **ascendentes** (~06:30, amanecer). Causa abierta: ángulo y dirección de observación de cada track, rocío matinal sobre la vegetación (aclara el agua somera en los ascendentes), o una combinación. Comparar cada píxel contra sí mismo cancela todas a la vez.
4. **`combinar_tracks.py`:** junta las máscaras de todos los tracks (grilla del track con más fechas). **Agua previa** = mojada en alguna pasada del 10–14/8, después del hueco de datos y antes de la lluvia (venía de julio): se reporta aparte (`agua_previa.tif`) y queda fuera de extensión, persistencia, ha·día y caminos. **Extensión confirmada** = agua nueva en ≥ 2 observaciones del 15/8 al 10/9 (cifra principal). Retiro = 2 observaciones secas seguidas. Persistencia con intervalo. Un track sin pasada antes del 15/8 (53D) usa la previa del combinado (`previa_en_grilla`).
5. **`sensibilidad.py`:** barre caída ∈ {−2…−4} dB × techo ∈ {−13, −14, −15} dB. El rango mín–máx es la banda de la app (no es un intervalo estadístico).
6. **`capas_contexto.py`:** sólo contexto. OSM (localidades, manchas urbanas, caminos, ríos, departamentos) desde el extracto de Geofabrik con el driver OSM de GDAL; HydroBASINS nivel 8; ESA WorldCover 2021 reproyectado por moda a cada track.
7. **`monte_ribereno.py`:** HAND = suelo (mínimo de 500 m sobre el DSM) − suelo del cauce OSM más cercano. Ribereño = monte con HAND < 4 m y < 1 km del cauce; de altura = HAND > 12 m. Exceso ribereño = subida de HH−HV del ribereño − subida del de altura (resta la humedad general). Mapa `veg_inundada_ribereno.tif`: píxel ribereño que sube > 2 dB más que el monte de altura y con HH > +1 dB.
8. **`agregar_impacto.py`:** caminos (puntos cada 20 m sobre el eje; km bajo agua y días máximos; con nombre se agrupan, sin nombre cada way de OSM con referencia "x km NE de <localidad>"), localidades (adentro y anillo de 500 m), subcuencas (nombradas por su curso de agua principal), departamentos, cobertura del suelo. Hectárea-día = ha × días bajo agua.
9. **`validar_s1.py`:** ver `docs/validacion.md`.
10. **`exportar_app.py`:** `manifest.json` con todas las cifras, radar en WebP con alfa y capas PNG con sus 4 esquinas en lon/lat (image source de MapLibre), sonda de 200 m para el clic, GeoJSON y descargas.

---

## 6. Zonas y tracks

Definidas en `scripts/zonas.py`. Track = `{número}{A=ascendente | D=descendente}`, más el frame.

| Zona | Para qué | Tracks (fechas del evento) |
|---|---|---|
| `treinta_y_tres` | Ciudad + bajo Olimar, ~1.600 desplazados | 132A-161 (08-10, 08-22, 09-03), 154D-105 (08-11, 08-23, 09-04) |
| `merin_arrozales` | Arrozales Cebollatí–Tacuarí, borde de la Laguna Merín | 53D-105 (08-16, 08-28, 09-09), 132A-161, 154D-105 |
| `melo` | Arroyo Conventos | 31A-161 (08-15, 08-27), 154D-105 |
| `rio_branco_jaguarao` | Río Yaguarón, frontera UY/BR | 53D-105, 31A-161 |
| `durazno` | Río Yí: crecida de julio y pico del 22/8 | 60A-161 (07-24, 08-17, 08-29) |
| `mercedes` | Río Negro aguas abajo | 10D-105, 161A-161, 60A-161 |

**Hueco global de datos NISAR:** 2026-07-27 → 2026-08-10 (no hay pasadas en ninguna zona).

---

## 7. Reglas del equipo

1. El análisis se apoya en **NISAR**. Otras fuentes (Sentinel-1/2, INUMET, DINAGUA, SINAE, DIEA, MapBiomas, DEM, OSM) sólo como **contexto o validación independiente**: nunca para entrenar ni mezcladas en las series principales.
2. **Un track por serie temporal** (misma geometría). Los tracks se combinan sólo a nivel de máscara de agua, con umbral calibrado por track.
3. **No mezclar PROVISIONAL y VALIDATED** sin normalizar: hay un salto de calibración de ~−1,7 dB en HH y ~−2,2 dB en HV en tierra.
4. Las cifras de prensa son preliminares: confirmarlas con SINAE/CECOED antes de publicarlas.

---

## 8. Resultados (2026-11-14, detector por cambio, sin agua previa)

- **Inundado por la tormenta (≥ 2 observaciones, 15/8–10/9):** Merín 47.927 ha (track 53D solo: 30–67 mil según parámetros) · Treinta y Tres 6.290 · Río Branco 2.510 · Durazno 341 (un track) · Mercedes 180 · Melo 35. Total ≈ 57.300 ha.
- **Ya mojado antes de la lluvia (10–14/8, aparte):** ≈ 31.100 ha (Merín 27.700, TyT 3.100, Mercedes 240). La tormenta cayó sobre suelos ya saturados por las lluvias de julio.
- **Retiro en Merín (53D):** 70 % del área inundada seguía mojada el 28/8, 15 % el 21/9. Persistencia típica 6 días (intervalo mediano 1–12) en Merín, 10 en TyT, 18 en Río Branco.
- **Caminos:** 42 km de caminería rural bajo agua en Merín (29 km más de una semana), 13 km en TyT. Máximo 66 días (desde el 15/8 hasta el fin de la serie).
- **Cobertura en Merín:** 24.600 ha de pradera, 14.100 de cultivo (arroz), 7.800 de humedal.
- **Agua bajo el monte:** exceso ribereño positivo en los 3 tracks de Mercedes, en Río Branco y en Merín; nulo o negativo en Treinta y Tres, Melo y Durazno.
- **Validación** (`docs/validacion.md`): Jaccard entre tracks a ≤ 1 día 0,32 → 0,48; contra Sentinel-1 NISAR encuentra el 66 % del agua S1, F1 0,45 (estricta) / 0,52 (laxa); NISAR mapea más agua somera que la banda C → las extensiones son cota alta. Débil en Durazno.

---

## 9. Limitaciones y pendientes

- Revisita de 12 días por track: la persistencia tiene precisión de días (intervalos), no horas; el 37–40 % de los píxeles se ve mojado en una sola observación.
- Mercedes tiene poca agua abierta y la coincidencia entre tracks es baja (0,27): es ruido de borde de detección.
- Las ciudades confunden al radar (doble rebote de edificios): dentro de las manchas urbanas da ~0; usar el anillo de 500 m.
- Los caminos van en terraplén: el píxel de 20 m mezcla camino y banquina. Se presenta como "camino en riesgo de corte".
- Niveles de río DINAGUA: no se consiguieron por API; la validación de crestas usa fechas de prensa.
- Post-evento y planificación, no alerta temprana.
- **Pendientes:** capítulo arrozales (riego nov–dic, requiere normalizar VALIDATED), publicar la app (GitHub Pages), video/slides.

---

## 10. Problemas frecuentes

| Síntoma | Causa / solución |
|---|---|
| `HTTP response code: 401` o `403` | Credenciales: revisar `~/.netrc` (máquina `urs.earthdata.nasa.gov`, `chmod 600`) y autorizar la app de ASF en Earthdata (ver 3.1). |
| `HTTP response code: 404` en todas las escenas | Sintaxis de la ruta GDAL. Los scripts usan `HDF5:"/vsicurl/URL"://science/...`; sin el prefijo del driver, GDAL toma todo como una URL. No cambiarlo. |
| `ERROR ... HVHV` en algunas fechas | Escenas SHSH (sólo HH). Es esperable: son 6. |
| Errores sueltos de red durante la descarga | Volver a correr el paso 1: saltea lo existente. |
| `CERTIFICATE_VERIFY_FAILED` al bajar contornos | Ya se usa `certifi`. Si persiste, actualizar `pip install -U certifi`. |
| La app muestra "needs to be served over http" | Se abrió con doble clic: servirla con `python3 -m http.server -d app 8000`. |
| El mapa queda gris | Sin internet no cargan MapLibre ni el mapa base; los gráficos y tablas funcionan igual. |
| La app no incluye todas las zonas | Correr los pasos 2–8 **sin** `--zona` antes de `exportar_app.py`. |
| `validar_s1.py` muy lento | La primera vez baja recortes de Sentinel-1 (Merín es la grilla grande); después usa la caché en `data_nisar/validacion/s1/`. |
| `gdalinfo: command not found` | Instalar GDAL (3.3). El paquete Python `rasterio` no instala la CLI. |

---

## 11. Referencias

- NISAR Data User Guide: https://nisar-docs.asf.alaska.edu/ (disponibilidad, GDAL, Harmony, asf-search)
- ASF Vertex (buscar escenas a mano, *GDAL Snippet Exporter*): https://search.asf.alaska.edu/#/?dataset=NISAR
- Earthdata Search + Harmony: https://search.earthdata.nasa.gov/ · Worldview (capas GCOV): https://worldview.earthdata.nasa.gov/
- Copernicus DEM GLO-30 en AWS: `s3://copernicus-dem-30m/` (acceso público)
- Sentinel-1 RTC (validación): Microsoft Planetary Computer, colección `sentinel-1-rtc`
- OpenStreetMap Uruguay (Geofabrik): https://download.geofabrik.de/south-america/uruguay.html · HydroBASINS: https://www.hydrosheds.org/products/hydrobasins · ESA WorldCover: https://esa-worldcover.org/
- Banda C vs L en el río Santa Lucía (Boletín Geográfico 2024): https://doaj.org/article/bb87ff3d27a24e2c83dcdac1aedc53ba
- Guía de evaluación de Space Apps: https://www.spaceappschallenge.org/resources/judging-awards-guide
- Discusión SAR/NISAR de Space Apps: https://github.com/nasa/spaceapps/discussions/1324

**Si usan Claude Code:** `CLAUDE.md` tiene todo el contexto, las decisiones y el historial del proyecto, y se carga solo en cada sesión. Cuando tomen decisiones nuevas, actualícenlo.
