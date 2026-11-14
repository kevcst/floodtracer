# Plan de desarrollo: de la POC a la entrega principal

Escrito el 2026-11-14. Cubre sólo desarrollo. La logística de la submission (link público, licencia, video, página del proyecto) queda para después.
Punto de partida: la POC (`poc/`) y el pipeline (`scripts/`) descritos en el [README](../README.md).

## Estado (2026-11-14, ejecutado de corrido)

| Paso | Estado | Dónde |
|---|---|---|
| A1 Armonizar tracks | Hecho. Se reemplazó el umbral por detección por cambio + normalización por escena; Jaccard medio por zona 0,18–0,49 → 0,27–0,58. No se llega a 0,6 en Mercedes (poca agua) ni en el par 27–28/8 de Río Branco (cambio real probable). | `armonizar_tracks.py`, `metricas_evento.py` |
| A2 Persistencia combinada | Hecho, con intervalo y extensión confirmada (≥ 2 obs.). | `combinar_tracks.py` |
| A3 Incertidumbre | Hecho (bandas de parámetros). | `sensibilidad.py` |
| A4 Validación | Sentinel-1: hecho. Crestas: fechas de prensa. Niveles DINAGUA: no disponibles por API. | `validar_s1.py`, `docs/validacion.md` |
| A5 Agua bajo monte | Hecho con HAND sobre drenaje OSM (sin pysheds). | `monte_ribereno.py` |
| A6 Higiene | VALIDATED fuera por ventana de fechas. QA_REPORT pendiente. | — |
| B1 Capas | Hecho (OSM Geofabrik, HydroBASINS L8, WorldCover; MTOP/DINAGUA no). | `capas_contexto.py` |
| B2 Agregaciones | Hecho. | `agregar_impacto.py` |
| C App | Hecho: `app/` estática con MapLibre; requiere servidor http. | `exportar_app.py`, `app/index.html` |
| D Narrativa | Hecho dentro de la app (secciones Why, Method, Limits). | `app/index.html` |
| E Arrozales nov–dic | No hecho (trabajo futuro). | — |

Decisiones abiertas, tomadas por defecto: mapa base **OpenStreetMap** (CARTO ahora exige API key), caminería **OSM**, **Sentinel-1 sí**, arrozales **future work**.

## Objetivo

Una app web estática, en inglés, que responda **"How long does the water stay?"** para las 6 zonas con:

1. Métricas por píxel (extensión, persistencia, retiro, agua bajo monte) confiables entre tracks y con incertidumbre.
2. Al menos una validación independiente.
3. Impacto agregado por localidad, camino rural, subcuenca y uso del suelo.
4. Una narrativa de causas físicas.

## Resumen de fases

| Fase | Qué resuelve | Depende de | Tamaño |
|---|---|---|---|
| **A. Ciencia robusta** | Armonizar tracks, persistencia combinada, incertidumbre, validación | — | L |
| **B. Contexto e impacto** | Capas vectoriales y agregaciones (km de camino, ha de arroz…) | A1–A2 (para cifras finales; se puede arrancar en paralelo) | M |
| **C. App** | Mapa con zoom, 6 zonas, vista país, impacto, descargas | B para la vista de impacto; el resto en paralelo | L |
| **D. Narrativa** | Causas físicas, Mercedes/Durazno, aplicaciones futuras | A4, B2 | S |
| **E. Opcional** | Capítulo arrozales nov–dic, pulido | todo lo anterior | M |

Camino crítico: **A1 → A2 → B2 → C (vista impacto) → D**. C1–C2 (mapa y vistas) y B1 (capas) pueden avanzar en paralelo desde el día 1.

---

## Fase A: ciencia robusta

### A1. Armonizar umbrales entre tracks  ·  `scripts/armonizar_tracks.py` (nuevo)
**Problema.** Pasadas separadas por 1 día ven áreas de agua muy distintas en el pico (Jaccard 0,17–0,40; en TyT y Merín 154D ve 2,5× más agua que 132A). Por eso la persistencia combinada se llena de "1 día" artificiales.

**Pares casi simultáneos disponibles** (fechas del evento):

| Zona | Tracks | Pares (Δ 1 día) |
|---|---|---|
| treinta_y_tres | 132A ↔ 154D | 08-10/11, 08-22/23, 09-03/04, 09-15/16 |
| merin_arrozales | 132A ↔ 154D | ídem (y 53D intercalado 08-16, 08-28…) |
| rio_branco_jaguarao | 31A ↔ 53D | 08-15/16, 08-27/28, 09-08/09, 09-20/21 |
| mercedes | 161A ↔ 10D | 08-24/25, 09-05/06, 09-17/18 |
| melo | 31A ↔ 154D | sólo Δ 4 días: usar con cautela o no usar |
| durazno | 60A | un solo track: no aplica |

**Método.**
1. Reproyectar cada par a una grilla común (la del track de referencia, la que tenga más fechas).
2. Diagnosticar la causa antes de ajustar: comparar HH de agua permanente y de tierra estable entre tracks, y el efecto del **ángulo de incidencia** (near vs far range, ascendente vs descendente). Si la diferencia depende del ángulo, corregir con un umbral variable por ángulo y no con un offset fijo.
3. Ajustar el umbral de cada track (o un offset en dB) para maximizar la coincidencia en los pares, usando sólo píxeles fuera de agua permanente. Validar con *leave-one-pair-out*.
4. Probar **HV** (o HH+HV) como detector alternativo de agua abierta. Puede ser menos sensible al viento y al ángulo.
5. Guardar `data_nisar/zonas/umbrales_armonizados.csv` (zona, track, umbral, método, Jaccard antes y después).

**Cambios.** `metricas_evento.py --umbrales umbrales_armonizados.csv` (umbral forzado por track, ya existe `umbral_forzado`).

**Hecho cuando** el Jaccard en el pico sea ≥ 0,6 en los pares de TyT, Merín, Río Branco y Mercedes, o esté documentado por qué no se puede llegar.

### A2. Persistencia combinada  ·  `combinar_tracks.py`
- Re-correr con los umbrales armonizados. Con 3 tracks en Merín la revisita efectiva baja de 12 días a unos 4–6.
- Reportar la persistencia como **intervalo**: un píxel visto mojado en t1 y seco en t2 se retiró entre t1 y t2. Guardar `persistencia_min` y `persistencia_max` y mostrar el punto medio con barra de error.
- Mantener la regla de retiro (2 observaciones secas seguidas) y evaluar si con la armonización alcanza con 1.

**Hecho cuando** el histograma de persistencia combinada no tenga picos artificiales en 1 día y las cifras por zona sean coherentes con las de cada track.

### A3. Incertidumbre  ·  `scripts/sensibilidad.py` (nuevo)
- Barrer el umbral ±1 dB en pasos de 0,5 y recalcular la extensión máxima y el % mojado por fecha.
- Guardar `sensibilidad.csv` (zona, track, fecha, ha_min, ha_central, ha_max).
- La app muestra bandas, no una cifra única. Las cifras del texto pasan a "~28.600 ha (24–33 mil)".

### A4. Validación independiente  ·  `scripts/validar.py` (nuevo) + `docs/validacion.md`
Regla 1: estas fuentes **sólo validan**. No entran en las series ni en los umbrales.
1. **Niveles de río (DINAGUA)**: Olimar en Treinta y Tres, Yí en Durazno, Negro en Mercedes y Cebollatí. Comparar la fecha del pico y la forma de la recesión con la curva NISAR (correlación de rangos y desfase del pico).
2. **SINAE**: desplazados por fecha contra el % mojado en TyT, Durazno y Mercedes. Es una comparación cualitativa de fechas, no de magnitudes.
3. **Sentinel-1 GRD**, 1–2 fechas cercanas al pico (por ejemplo Merín el 08-28): máscara de agua independiente (umbral VV) y matriz de confusión contra NISAR en la misma fecha, ±1 día.
4. Opcional: Sentinel-2 en alguna fecha despejada como chequeo visual.

**Hecho cuando** haya una figura por fuente y una tabla de acuerdo (pico, desfase, F1 contra S1).

### A5. Agua bajo monte  ·  `monte_ribereno.py`
- Reemplazar la altura relativa (mínimo en 3 km) por una **HAND real** calculada sobre la red de drenaje (por ejemplo con `pysheds` sobre el Copernicus DEM) o por la distancia al río (OSM `waterway`).
- Restar el componente general de humedad: exceso ribereño = Δ(HH−HV) ribereño − Δ(HH−HV) de altura, por fecha.
- Producir un mapa `veg_inundada_ribereno.tif` restringido a monte con HAND < 4 m y exceso > umbral.

**Hecho cuando** Mercedes, Río Branco y Merín tengan un mapa de "agua bajo monte" defendible y TyT, Melo y Durazno estén explicados.

### A6. Higiene de datos
- Excluir o marcar las escenas VALIDATED (salto de calibración, regla 3). Ya están afuera de la ventana; dejar un assert en `cargar_track`.
- Revisar `QA_REPORT.pdf` de las escenas descartadas por grilla no modal.

---

## Fase B: contexto e impacto

### B1. Capas vectoriales  ·  `scripts/capas_contexto.py` (nuevo) → `data_nisar/contexto/*.gpkg`
Overpass no respondía, así que conviene bajar el **extracto de Uruguay de Geofabrik** (`.osm.pbf`) y filtrar localmente con `osmium` u `ogr2ogr`.

| Capa | Fuente sugerida | Uso |
|---|---|---|
| Localidades (puntos y manchas urbanas) | INE / OSM `place`, `landuse=residential` | Agua a < 500 m, días |
| Caminería rural y rutas | MTOP / OSM `highway` | km cortados, días de corte |
| Subcuencas | DINAGUA (nivel 3–4) o HydroBASINS | ha·día por subcuenca |
| Departamentos | INE | Agregación administrativa |
| Uso del suelo / arroz | MGAP-DIEA o MapBiomas Pampa (contexto) | ha de arroz, pradera y monte afectadas |
| Ríos | OSM `waterway` | A5 y mapa |

Todas las capas se recortan a las AOIs de `zonas.py` y se reproyectan a la grilla de cada zona.

### B2. Agregaciones  ·  `scripts/agregar_impacto.py` (nuevo)
Por entidad (localidad, tramo de camino, subcuenca, uso del suelo):
- ha de extensión máxima, **ha·día** (integral de la persistencia), fecha del primer agua y del retiro.
- Caminos: km bajo agua por fecha, **días de corte** por tramo y tramos que siguen cortados al final.
- Localidades: % del área urbana con agua y días con agua a < 500 m.

Salida: `impacto_{entidad}.csv` + GeoJSON simplificado para la app. Las cifras usan el combinado armonizado (A2) con bandas de A3.

**Hecho cuando** existan rankings por zona del tipo "top 10 caminos por días de corte" con incertidumbre.

---

## Fase C: app

### C1. Arquitectura
- **Sigue siendo estática** (sin backend): HTML + JS + datos pregenerados.
- Mapa con **MapLibre GL** (CDN, versión fija) y mapa base de teselas públicas. Esto requiere internet; el `dist/` autocontenido pasa a ser una carpeta `app/dist/` con `assets/`.
- Raster: overlays georreferenciados por zona, fecha y capa a **resolución completa** (PNG con transparencia, 20 m), cargados de forma diferida (*lazy*). Si el peso se dispara, pasar a teselas XYZ con `gdal2tiles` sólo para HH y agua por fecha.
- **Contrato de datos**: `app/data/manifest.json` (zonas, tracks, fechas, capas, bounds, cifras y bandas) generado por `exportar_app.py`, que evoluciona desde `exportar_poc.py`.
- **Ninguna cifra escrita a mano en el HTML**: todos los números del texto salen del manifest, para que no queden desactualizados al re-correr.

### C2. Vistas
1. **País**: mapa de Uruguay con las 6 zonas coloreadas por % mojado en la fecha del slider, small multiples del pulso y línea de tiempo de crestas Olimar → Yí → Negro (con niveles DINAGUA de A4 como contexto).
2. **Zona**: mapa con zoom, slider y play por fecha. Capas: HH, agua por fecha, extensión máxima, persistencia (con intervalo), fecha de retiro y agua bajo monte. Selector de track o vista combinada. **Clic en un píxel** abre la serie HH/HV y el estado mojado/seco por fecha.
3. **Impacto**: tablas y rankings de B2 (caminos, localidades, subcuencas, usos). Al hacer clic, el mapa vuela al lugar.
4. **Método y validación**: cómo se detecta el agua, armonización, incertidumbre, figuras de A4 y límites.
5. **Descargas**: GeoTIFF de métricas por zona y GeoJSON/CSV de impacto.

### C3. Calidad
- Mobile (gutter de 16 px, sin scroll horizontal), modo oscuro, leyendas siempre visibles y vista en tabla para cada gráfico.
- Rendimiento: < 3 s a primera vista con datos de la vista país; zonas y fechas bajo demanda.
- Probar el build en jsdom (como se hizo con la POC) y en un navegador real.

**Hecho cuando** las 6 zonas sean navegables con zoom a 20 m y todas las cifras salgan del manifest.

---

## Fase D: narrativa (en la app, en inglés)

1. **Causas físicas**: crecidas encadenadas (desfase de picos entre zonas, medido con NISAR y contrastado con DINAGUA), remanso de la Laguna Merín (por qué Merín drena más lento), doble rebote en monte inundado y qué aporta HH frente a HV.
2. **Mercedes y Durazno**: por qué casi no hay agua abierta (ríos angostos frente a la resolución, crecida dentro del monte) y qué sí muestra el radar. Presentarlo como hallazgo.
3. **Límites**: revisita, zonas urbanas, latencia (post-evento, no predicción) y el salto PROVISIONAL → VALIDATED.
4. **Aplicaciones futuras**: uso operativo post-evento para SINAE, CECOED e intendencias; caminería; seguros agrícolas; preparación para El Niño 2026-27.

---

## Fase E: opcional

- **Capítulo arrozales**: bajar noviembre y diciembre (ampliar `FECHA_FIN`). Es VALIDATED, así que hay que normalizar contra PROVISIONAL con blancos estables antes de comparar (regla 3). Mostrar los mismos lotes con agua "mala" (agosto) y "buena" (riego).
- HAND real para toda la cuenca y mapa nacional de "agua bajo monte".

---

## Decisiones abiertas para el equipo

1. **Mapa base**: teselas OSM, Esri imagery o CARTO. Implica aceptar que la app necesita internet.
2. **Fuente de caminería**: MTOP (oficial, ¿disponible?) u OSM (completa pero heterogénea).
3. **Sentinel-1 para validación**: ¿vale el tiempo? Es la validación más fuerte para el jurado.
4. **Alcance del capítulo arrozales**: ¿entra o queda como "future work"?

## Reparto sugerido (3–4 personas)

- **Persona 1**: A1 → A2 → A3 (ciencia, camino crítico).
- **Persona 2**: A4 + A5 (validación y monte).
- **Persona 3**: B1 → B2 (capas e impacto).
- **Persona 4**: C1 → C2 → C3 (app), consumiendo el manifest con datos de la POC hasta que lleguen los finales. Después, D.
