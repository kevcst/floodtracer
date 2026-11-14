# Dancing with the SARs — NASA Space Apps 2026 (equipo Uruguay)

**Idea: "How long does the water stay?" / "¿Cuánto tiempo se queda el agua?"**

Con el radar **NISAR** (banda L, NASA/ISRO), que ve a través de las nubes cada 12 días, reconstruimos la crecida del **15–19 de agosto de 2026** en Uruguay y medimos dónde apareció agua nueva, hasta dónde llegó, cuánto tardó en irse y dónde quedó agua bajo el monte. Comparamos la cuenca de la Laguna Merín (Olimar, Cebollatí, Yaguarón) con la del río Negro (Yí, Mercedes).

- **POC para discutir en el equipo:** `poc/dist/index.html`. Se abre con doble clic, ver [Ver la POC](#1-ver-la-poc-sin-instalar-nada).
- Detalle de la idea: `docs/idea_principal.md`. Contexto del evento (prensa, SINAE): `docs/contexto_nacional_ago2026.md`. EDA inicial: `docs/eda_T53D_F105.md`.
- Desafío oficial: `docs/challenge.md`. Los entregables del hackatón van en **inglés**; el trabajo interno, en español.

---

## Índice
1. [Ver la POC (sin instalar nada)](#1-ver-la-poc-sin-instalar-nada)
2. [Estructura del repo](#2-estructura-del-repo)
3. [Setup (una sola vez)](#3-setup-una-sola-vez)
4. [Pipeline completo: de la descarga a la POC](#4-pipeline-completo-de-la-descarga-a-la-poc)
5. [Qué hace cada paso (método)](#5-qué-hace-cada-paso-método)
6. [Zonas y tracks](#6-zonas-y-tracks)
7. [Reglas del equipo](#7-reglas-del-equipo)
8. [Resultados hasta ahora](#8-resultados-hasta-ahora)
9. [Limitaciones y pendientes](#9-limitaciones-y-pendientes)
10. [Problemas frecuentes](#10-problemas-frecuentes)
11. [Referencias](#11-referencias)

---

## 1. Ver la POC (sin instalar nada)

`poc/dist/index.html` es autocontenido: datos e imágenes van embebidos (~6 MB). Después de clonar:

```bash
open poc/dist/index.html        # macOS
xdg-open poc/dist/index.html    # Linux
start poc\dist\index.html       # Windows
```

No hace falta servidor ni Python. Con internet se cargan las tipografías de Google Fonts; sin internet la página funciona igual con fuentes del sistema.

Qué muestra: cifras clave, mapa de contexto con las 6 zonas, línea de tiempo del evento, visor de radar con slider de fechas (Merín y Treinta y Tres), el "pulso" de agua por zona, agua bajo el monte en Mercedes y una sección "¿seguimos con esta idea?" con lo que funciona y lo que todavía no.

Para **editar** la página ver `poc/README.md`.

---

## 2. Estructura del repo

```
CLAUDE.md                 Contexto y decisiones para trabajar con Claude Code (léanlo: es la "memoria" del proyecto)
README.md                 Este archivo
requirements.txt          Dependencias Python
docs/                     Desafío, idea principal, contexto del evento, EDA, inventario NISAR
scripts/
  zonas.py                Definición de zonas (AOI en WKT), tracks por zona, ventana de fechas
  descargar_zonas.py      Paso 1: inventario y descarga de recortes NISAR por zona
  metricas_evento.py      Paso 2: máscaras de agua y métricas por zona/track
  combinar_tracks.py      Paso 3: combina tracks de una zona (máscaras)
  monte_ribereno.py       Paso 4: monte ribereño vs de altura (agua bajo vegetación)
  exportar_poc.py         Paso 5: exporta capas y datos livianos para la web
  build_poc.py            Paso 6: arma poc/dist/index.html autocontenido
  nisar_eda_uruguay.py    Script original (inventario/descarga/explorar de un track); otros scripts importan de acá
  eda_extra_T53D.py       Análisis exploratorio extra del track 53D (histórico)
poc/
  index.html              Fuente de la página (carga datos desde poc/data/)
  data/                   Capas PNG/JPEG + poc.json (generado por exportar_poc.py)
  dist/index.html         Página publicable, todo embebido (generado por build_poc.py)
data_nisar/               DATOS (no se versiona: ~5 GB). Se genera con los scripts
```

`data_nisar/` está en `.gitignore`, igual que `*.tif`, `*.h5`, `.venv/` y `.netrc`. Cada uno se baja los datos con el pipeline.

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

## 4. Pipeline completo: de la descarga a la POC

Todos los comandos se corren **desde la raíz del repo** con el venv activado (`source .venv/bin/activate`).

| Paso | Comando | Qué genera | Tiempo / tamaño |
|---|---|---|---|
| 0 (opcional) | `python scripts/descargar_zonas.py listar` | `data_nisar/zonas/inventario_zonas.csv`: qué escenas hay por zona y track. No requiere login | < 1 min |
| 1 | `python scripts/descargar_zonas.py descargar --zona todas --workers 4` | `data_nisar/zonas/{zona}/T{track}{dir}_F{frame}/{fecha}_{HH\|HV}.tif` | ~3 GB; de decenas de minutos a más de una hora según la conexión |
| 2 | `python scripts/metricas_evento.py` | `.../T*/metricas/*.tif` + `mapas_agua.png`; `data_nisar/zonas/metricas_resumen.csv`, `metricas_por_fecha.csv` | ~1 min |
| 3 | `python scripts/combinar_tracks.py` | `data_nisar/zonas/{zona}/combinado/*.tif`; `combinado_resumen.csv`, `combinado_persistencia.png` | < 1 min |
| 4 | `python scripts/monte_ribereno.py` | `.../T*/contexto/{dem,altura_rel,clase_monte}.tif`; `monte_ribereno.csv/.png`. Baja el DEM Copernicus de AWS (público, sin login) | ~1 min |
| 5 | `python scripts/exportar_poc.py` | `poc/data/` (capas + `poc.json`). Baja los contornos de países la primera vez | < 1 min, ~4 MB |
| 6 | `python scripts/build_poc.py` | `poc/dist/index.html` autocontenido | segundos, ~6 MB |
| 7 | `open poc/dist/index.html` | Ver la POC | |

En una línea, una vez descargados los datos:

```bash
python scripts/metricas_evento.py && python scripts/combinar_tracks.py && python scripts/monte_ribereno.py \
  && python scripts/exportar_poc.py && python scripts/build_poc.py && open poc/dist/index.html
```

### Notas sobre la descarga (paso 1)
- **Se puede volver a correr sin miedo:** saltea los archivos que ya existen y escribe primero a `.part.tif`, así que un corte no deja archivos rotos. Si hubo errores de red, alcanza con volver a correrlo.
- Se esperan **232 recortes**, de los cuales **226** se pueden bajar. Los 6 restantes dan `ERROR ... HVHV` porque son escenas **SHSH** (sólo HH, sin HV). Es normal.
- Para probar rápido con una sola zona: `--zona treinta_y_tres` (~0,5 GB) o `--zona durazno` (~0,07 GB). La POC necesita **todas**, porque el gráfico de pulso usa las 6 zonas y el de monte usa Mercedes.
- `merin_arrozales` es la zona pesada (~2,6 GB): el AOI es grande.
- Se baja **sólo el recorte** de cada escena, vía `gdalwarp` sobre `/vsicurl/`. Las escenas completas pesan 1–2 GB cada una.
- Ventana: 2026-06-15 → 2026-10-20, sólo madurez **PROVISIONAL** (ver reglas). Para incluir VALIDATED: `--madurez PROVISIONAL VALIDATED`, pero no las mezclen sin normalizar.

### Correr una sola zona en los pasos 2–4
`--zona <nombre>` sirve para iterar rápido. Los CSV globales (`metricas_resumen.csv`, `combinado_resumen.csv`, `monte_ribereno.csv`) sólo se escriben con todas las zonas, porque la POC se arma desde ellos. Antes de exportar la POC, corran los pasos 2–4 sin `--zona`.

### Scripts históricos (opcionales)
- `python scripts/nisar_eda_uruguay.py inventario | descargar --track 53 --dir D --frame 105 | explorar --track 53 --dir D --frame 105`: primer EDA sobre un solo track. Escribe en `data_nisar/T53D_F105/`.
- `python scripts/eda_extra_T53D.py`: percentiles, Otsu, mapas y dispersores persistentes de ese track. Escribe en `/tmp/eda`. Sus conclusiones están en `docs/eda_T53D_F105.md`.

---

## 5. Qué hace cada paso (método)

**Producto:** NISAR **L2 GCOV** (gamma0 con corrección radiométrica de terreno, 20 m, HDF5). Usamos `HHHH` (HH) y `HVHV` (HV) de `/science/LSAR/GCOV/grids/frequencyA/`. Cada recorte queda en la proyección nativa del frame (UTM 21S o 22S), con la misma grilla en todas las fechas de un track.

**Por qué se ve el agua:** el agua calma refleja el radar como un espejo y se ve muy oscura (HH ≈ −22 dB). Cuando el agua está bajo árboles, la señal rebota entre agua y troncos (*doble rebote*) y vuelve **más fuerte**. La banda L penetra el follaje y lo ve; la banda C y los satélites ópticos, en general, no.

1. **`descargar_zonas.py`** busca escenas GCOV con `asf_search` por zona, filtra los tracks definidos en `zonas.py` y recorta cada escena al AOI. Si en una fecha hay varias escenas, prefiere el modo principal (`2005_..._M_..._N_F_`, 20 MHz, frame completo) y descarta las auxiliares o parciales (`4005_..._A_..._P_`, 10 m, cubren sólo una parte).
2. **`metricas_evento.py`**, por zona y track:
   - Filtro de speckle: media 5×5 en lineal (~100 m), sin "comerse" los bordes.
   - **Umbral de agua abierta por track:** agua permanente + 30 % de la distancia a tierra, acotado a [−20, −17,5] dB. Si no hay suficiente agua permanente en el recorte, usa −18 dB. Otsu global **no** sirve, porque el histograma no es bimodal (ver EDA).
   - **Línea de base:** fechas antes del hueco global de datos (27/7). En Durazno, sólo hasta el 20/7, porque la pasada del 24/7 ya tiene la crecida de julio del Yí. Es "agua base" lo que es agua en la mayoría de esas fechas.
   - **Agua nueva** = agua en una fecha que no es agua base.
   - **Extensión máxima:** agua nueva en alguna pasada entre el 10/8 y el 10/9.
   - **Persistencia:** días entre la primera pasada del evento con agua y la primera pasada seca posterior. Resolución de 12 días (un track).
   - **ΔHH y candidato a agua bajo vegetación:** subida de HH durante el evento en zonas con vegetación.
   - Salidas: GeoTIFF (`agua_base`, `extension_max`, `primera_fecha`, `fecha_retiro`, `persistencia_dias`, `delta_hh_db`, `veg_inundada`, `agua_nueva_por_fecha`) y un panel `mapas_agua.png` por track, útil para diagnosticar.
3. **`combinar_tracks.py`:** junta las máscaras de agua nueva de todos los tracks de una zona en una grilla común (revisita ~6 días en vez de 12). Cada track conserva su umbral y su línea de base. Para el retiro exige 2 observaciones secas seguidas.
4. **`monte_ribereno.py`:** separa **monte ribereño** de **monte de altura** con el DEM Copernicus GLO-30. El DEM se usa sólo para clasificar píxeles; no entra en las series. La altura relativa sobre el fondo del valle es un proxy de HAND. Monte = HH base > −7 dB y HV base > −14 dB. Si sube HH−HV en el ribereño y no en el de altura, es agua bajo los árboles y no sólo suelo húmedo.
5. **`exportar_poc.py`:** para el visor usa un track por zona (Merín 53D, Treinta y Tres 154D). Genera JPEG de HH y PNG de agua por fecha (reducidos ×4 y ×2), extensión, persistencia, series para los gráficos y contornos de países (Natural Earth vía `world-atlas`).
6. **`build_poc.py`:** embebe `poc.json` y las imágenes como data URIs en `poc/dist/index.html`.

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

## 8. Resultados hasta ahora

- **La crecida de agosto se ve clara en la cuenca de la Laguna Merín y en Treinta y Tres,** con subida, pico y retiro, en tres tracks independientes. Arrozales (53D): 28.600 ha de agua nueva; el 82 % estaba bajo agua el 28/8, el 20 % el 21/9 y el 8 % el 15/10.
- **Pico de agua nueva por zona:** Merín 154D 12,4 % (23/8) · Río Branco 53D 6 % (28/8) · Treinta y Tres 154D 4,5 % (23/8) · Mercedes < 3 % · Durazno y Melo < 1 %.
- **Agua bajo el monte (banda L):** en Mercedes, el monte ribereño sube +1,1 a +2,0 dB en HH−HV durante el evento contra +0,2 a +1,1 dB del monte de altura, en los 3 tracks. También hay exceso ribereño en Río Branco y Merín. No aparece en Treinta y Tres, Melo ni Durazno.
- En Durazno y Mercedes la crecida casi no se ve como agua abierta: los ríos son angostos para 100 m de suavizado y el agua queda bajo el monte.

---

## 9. Limitaciones y pendientes

- **Persistencia gruesa:** con un track la resolución es de 12 días. Combinar tracks debería dar ~6, pero **los tracks no coinciden bien:** pasadas tomadas con 1 día de diferencia se solapan sólo 17–40 % (Jaccard) en el pico. **Próximo paso:** armonizar los umbrales entre tracks usando esos pares casi simultáneos. Mientras tanto, persistencia por track y el combinado sólo como cota superior de la extensión.
- La subida de HH−HV en el monte tiene un componente general de humedad (+0,3–1 dB también en lomas).
- Las ciudades confunden al radar (doble rebote de edificios).
- Los datos llegan días después de cada pasada: es evaluación post-evento y planificación, no alerta temprana ni predicción.
- **Pendientes:** capas de localidades, caminería y subcuencas (OSM/MTOP/DINAGUA) para agregar por camino o barrio; validación contra niveles del Olimar/Yí y desplazados SINAE; capítulo secundario de arrozales (agua "mala" en agosto vs riego "bueno" en nov–dic, con las nuevas pasadas VALIDATED).

---

## 10. Problemas frecuentes

| Síntoma | Causa / solución |
|---|---|
| `HTTP response code: 401` o `403` | Credenciales: revisar `~/.netrc` (máquina `urs.earthdata.nasa.gov`, `chmod 600`) y autorizar la app de ASF en Earthdata (ver 3.1). |
| `HTTP response code: 404` en todas las escenas | Sintaxis de la ruta GDAL. Los scripts usan `HDF5:"/vsicurl/URL"://science/...`; sin el prefijo del driver, GDAL toma todo como una URL. No cambiarlo. |
| `ERROR ... HVHV` en algunas fechas | Escenas SHSH (sólo HH). Es esperable: son 6. |
| Errores sueltos de red durante la descarga | Volver a correr el paso 1: saltea lo existente. |
| `CERTIFICATE_VERIFY_FAILED` al bajar contornos | Ya se usa `certifi`. Si persiste, actualizar `pip install -U certifi`. |
| La POC se ve vacía | Regenerar con los pasos 5–6 y abrir **`poc/dist/index.html`**, no `poc/index.html` (ése necesita servidor). Si hay un error, la página lo muestra arriba del mapa. |
| La POC no incluye todas las zonas | Correr los pasos 2–4 **sin** `--zona` antes de exportar. |
| `gdalinfo: command not found` | Instalar GDAL (3.3). El paquete Python `rasterio` no instala la CLI. |

---

## 11. Referencias

- NISAR Data User Guide: https://nisar-docs.asf.alaska.edu/ (disponibilidad, GDAL, Harmony, asf-search)
- ASF Vertex (buscar escenas a mano, *GDAL Snippet Exporter*): https://search.asf.alaska.edu/#/?dataset=NISAR
- Earthdata Search + Harmony: https://search.earthdata.nasa.gov/ · Worldview (capas GCOV): https://worldview.earthdata.nasa.gov/
- Copernicus DEM GLO-30 en AWS: `s3://copernicus-dem-30m/` (acceso público)
- Banda C vs L en el río Santa Lucía (Boletín Geográfico 2024): https://doaj.org/article/bb87ff3d27a24e2c83dcdac1aedc53ba
- Guía de evaluación de Space Apps: https://www.spaceappschallenge.org/resources/judging-awards-guide
- Discusión SAR/NISAR de Space Apps: https://github.com/nasa/spaceapps/discussions/1324

**Si usan Claude Code:** `CLAUDE.md` tiene todo el contexto, las decisiones y el historial del proyecto, y se carga solo en cada sesión. Cuando tomen decisiones nuevas, actualícenlo.
