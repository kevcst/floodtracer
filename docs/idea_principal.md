# Idea principal — "How long does the water stay?" / "¿Cuánto tiempo se queda el agua?"

Decidida 2026-11-14. Contexto del evento: `contexto_nacional_ago2026.md`. EDA previo: `eda_T53D_F105.md`.

> **Estado (2026-11-14, noche):** la idea está implementada como app web en `app/` (ver README §1). Lo que sigue es el documento de diseño original; donde difiere, manda el README: el detector de agua pasó de umbral absoluto a **cambio respecto de la base del píxel**, la persistencia se reporta como intervalo combinando tracks, y hay validación con Sentinel-1 (`docs/validacion.md`) y agregaciones por camino, localidad, subcuenca y cobertura.

## 1. Pitch (1 línea)
Con el radar L-band de NISAR, que ve a través de las nubes cada 12 días, reconstruimos la crecida de agosto 2026 en Uruguay y medimos —para cada parcela, camino y barrio— **cuándo llegó el agua, hasta dónde llegó y cuánto tardó en irse**, y mostramos cómo la misma lluvia encadenó crecidas en distintas cuencas.

## 2. Pregunta y por qué importa
- No sólo "¿cuánto se inundó?" sino **"¿dónde se quedó el agua más tiempo?"**: la persistencia es lo que define el daño (viviendas, caminos cortados, pasturas, ganado, salud).
- El evento: 15–19 ago 2026, >250 mm en el este (317 mm en Laguna Merín), 2.229 desplazados (SINAE, 22/8), crecidas encadenadas Olimar → Yí → río Negro; El Niño activo hasta ≥ mayo 2027.

## 3. Análisis (sólo NISAR GCOV, 20 m)
Por zona y track (misma geometría), con umbral de agua abierta HH < −18 dB (calibrar por track con agua permanente):
| Métrica | Definición | Pregunta |
|---|---|---|
| Línea de base | Agua en jun–jul (antes del evento; ojo crecida del Yí ~23/7 en Durazno) | ¿Qué es agua "normal"? |
| Extensión máxima | Unión de fechas con agua nueva (no presente en la base) entre 10/8 y 10/9 | ¿Hasta dónde llegó? |
| Persistencia | N.º de pasadas consecutivas con agua nueva (× 12 días; ~6 días combinando tracks) | ¿Cuánto tiempo quedó? |
| Fecha de retiro | Primera fecha seca después del máximo | ¿Cuándo se puede volver? |
| Agua bajo vegetación | Aumento de HH (y HH−HV) por doble rebote en monte/bañado respecto a la base | Inundación que óptico y C-band no ven |
| % área con agua nueva | Por zona y fecha | Comparar cuencas y el desfase entre ellas |

Agregaciones: localidades, tramos de caminería (OSM/MTOP), subcuencas (DINAGUA), uso del suelo (arroz / pradera / bañado; MapBiomas sólo como capa de contexto).

Hipótesis físicas a discutir: lluvia extrema; relieve llano; suelos poco permeables; suelos saturados por la crecida de julio; arrozales con taipas que retienen agua; **remanso de la Laguna Merín** (laguna alta → el este drena lento); misma lluvia, dos vertientes de la Cuchilla Grande → picos desfasados (Olimar ~19–20/8, Yí 22/8, río Negro después).

## 4. Zonas y datos (definidas en `scripts/zonas.py`)
| Zona | Para qué | Tracks (fechas del evento) |
|---|---|---|
| `treinta_y_tres` | Ciudad + Olimar, ~1.600 desplazados | 132A-161 (08-10, 08-22, 09-03), 154D-105 (08-11, 08-23, 09-04) |
| `merin_arrozales` | Campos/arrozales, retiro lento, agua bajo vegetación | 53D-105 (08-16, **08-28**, 09-09) ya bajado; 132A-161; 154D-105 |
| `melo` | Arroyo Conventos | 31A-161 (**08-15 durante la lluvia**, 08-27), 154D-105 |
| `rio_branco_jaguarao` | Yaguarón, frontera UY/BR | 53D-105, 31A-161 |
| `durazno` | Río Yí: crecida de julio + pico 22/8 | 60A-161 (07-24, 08-17, 08-29) |
| `mercedes` | Río Negro aguas abajo | 10D-105 (08-25), 161A-161 (08-24), 60A-161 (08-17, 08-29) |

Ventana: 2026-06-15 → 2026-10-20, **sólo PROVISIONAL** (evita el salto de calibración con VALIDATED). Hueco NISAR 27/7–10/8 (sin datos).
Total: ~232 recortes HH/HV.

## 5. Pipeline
1. `python scripts/descargar_zonas.py listar` → inventario por zona (`data_nisar/zonas/inventario_zonas.csv`).
2. (opcional) reutilizar lo ya bajado de 53D: copiar `data_nisar/T53D_F105/2026-0[6-9]*.tif` y `2026-10-0*`, `2026-10-15*` a `data_nisar/zonas/merin_arrozales/T53D_F105/` (no copiar el 10-27, es VALIDATED). El script saltea lo que ya existe.
3. `python scripts/descargar_zonas.py descargar --zona todas --workers 4`.
4. `python scripts/descargar_zonas.py resumen` → `% agua` por zona/track/fecha (CSV + PNG) — primera vista del desfase entre cuencas.
5. **Por hacer**: `scripts/metricas_evento.py` → rasters por zona: base, extensión máx., persistencia, fecha de retiro, Δ doble rebote; filtro de speckle (media 5×5 en lineal o temporal); umbral por track.
6. **Por hacer**: agregaciones (localidades, caminos, subcuencas) → GeoJSON/CSV para la app.
7. **Por hacer**: exportar tiles/COGs livianos (EPSG:3857) para la web.

## 6. App / entregable (en inglés)
- Mapa con slider de fechas (jun → oct) por zona; toggle HH / máscara de agua.
- Capas: extensión máxima, persistencia (días bajo agua), fecha de retiro, agua bajo vegetación.
- Click en localidad / tramo de camino → línea de tiempo ("under water from Aug 16, dry on Sep 21").
- Vista país: mapa de Uruguay con las 6 zonas, curvas de % agua desfasadas (Olimar → Yí → Negro), desplazados SINAE como contexto, cuencas y Laguna Merín.
- Panel "límites del método".
- Capítulo secundario: mismos lotes de arroz inundados en agosto (agua "mala") y por riego en nov–dic (agua "buena").

## 7. Beneficio social (para Influence / Local Impact)
- **SINAE / CECOED**: dónde sigue el agua semanas después → priorizar asistencia, retorno de evacuados, riesgos sanitarios (leptospirosis, mosquitos).
- **Intendencias – caminería rural**: qué caminos quedan cortados y cuánto (escuelas rurales, leche, ambulancias).
- **Productores y seguros agropecuarios**: días bajo agua por predio como evidencia objetiva; cuándo reingresar ganado/maquinaria.
- **Planificación**: mapas de riesgo basados en un evento real; repetible en el próximo evento (El Niño 2026-27).
- **Por qué radar**: durante la tormenta las nubes ciegan a los satélites ópticos; NISAR no.

## 8. Límites (declararlos suma en Validity)
- Revisita 12 días/track (~6 combinando): el pico puede caer entre pasadas.
- Urbano: el doble rebote de edificios confunde; mejor en periurbano/rural.
- Latencia de datos: evaluación post-evento y planificación, no alerta temprana. No es predicción.
- PROVISIONAL vs VALIDATED: no mezclar sin normalizar.
- 20 m: caminos angostos se evalúan por tramo/buffer, no por píxel.

## 9. Validación independiente (no se usa para entrenar)
Avisos y lluvia INUMET; niveles Olimar/Yí (CECOED, DINAGUA); desplazados SINAE por departamento y fecha; prensa (caminos cortados); una Sentinel-1 de fecha cercana sólo como chequeo.
