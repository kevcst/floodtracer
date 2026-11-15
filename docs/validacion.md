# Validación de los mapas de agua NISAR (2026-11-14)

Regla 1: ninguna de estas fuentes entra en las series ni en los umbrales. Sólo prueban el resultado.
Detector evaluado: **cambio** (ΔHH < −3 dB vs. la base del píxel, HH < −14 dB, MMU 10 px), comparado contra el detector viejo (**umbral** absoluto por track).

## 1. NISAR contra NISAR: tracks a ≤ 1 día (`armonizar_tracks.py`)

Dos pasadas de órbitas distintas separadas por 1 día deberían ver casi la misma agua. Jaccard = intersección / unión de las máscaras de agua nueva, sobre píxeles válidos fuera del agua base.

| | Umbral | Cambio |
|---|---|---|
| Media de 23 pares del evento/post con agua (≥ 0,5 %) | 0,32 | **0,48** |
| Treinta y Tres (132A ↔ 154D) | 0,18 | 0,48 |
| Merín (132A ↔ 154D) | 0,49 | 0,58 |
| Río Branco (31A ↔ 53D) | 0,39 | 0,56 |
| Mercedes (161A ↔ 10D) | 0,18 | 0,27 |

- Con umbral fijo, en el pico (22–23/8) los **descendentes** veían 2–3× más agua que los **ascendentes**. NISAR vuela en órbita amanecer–atardecer. Según los nombres de las escenas (UTC), los **ascendentes pasan ~09:30–10:00 UTC = 06:30–07:00 hora local** y los **descendentes ~21:35–22:00 UTC = 18:35–19:00**. O sea: las pasadas de la **tarde** ven más agua. (Una versión anterior de este documento tenía los horarios invertidos y lo atribuía al viento calmo del amanecer; eso no cierra.) Causa abierta: ángulo y dirección de observación de cada track, rocío matinal sobre pasto y cultivo que aclara el agua somera en los ascendentes, o una combinación. Comparar cada píxel contra su propia base cancela todas esas causas sin necesidad de saber cuál domina.
- La normalización por escena corrigió la pasada del 27/9 (132A, TyT), que estaba 1,4 dB más oscura en toda la escena (de 5,7 % de agua falsa a 1,2 %).
- Barrido de parámetros (`--barrido`): meseta en Jaccard ≈ 0,48–0,49; el elegido (−3 / −14 / 10 px) está a 0,01 del mejor.
- Lo que no llega: Mercedes tiene muy poca agua abierta (ruido de borde) y el par 27–28/8 de Río Branco (4 % vs. 13 %) probablemente es un cambio real en un día de crecida del Yaguarón.

## 2. Sentinel-1 RTC, banda C (`validar_s1.py`)

Microsoft Planetary Computer, colección `sentinel-1-rtc` (VV, 10 m → 20 m por promedio sobre la grilla NISAR). Una escena S1 a ≤ 2 días de cada pasada NISAR del 10/8 al 22/9 (el mismo día para el track 154D: órbita relativa 97). Base S1: escenas de la misma órbita de jun–jul.
Agua S1 **estricta**: ΔVV < −3 dB y VV < −15 dB, fuera del agua base. Agua S1 **laxa**: misma caída con VV < −12 dB (agua somera o parcial).

32 comparaciones con agua S1 ≥ 0,5 %:

| | Cambio | Umbral |
|---|---|---|
| Exhaustividad (agua S1 que NISAR también marca) | **0,66** | — |
| F1 contra S1 estricta | 0,45 | 0,43 |
| F1 contra S1 laxa | **0,52** | 0,39 |

Por zona (detector por cambio):

| Zona | F1 estricta | F1 laxa | F1 umbral | Exhaustividad | Precisión |
|---|---|---|---|---|---|
| Treinta y Tres | 0,47 | 0,64 | 0,49 | 0,83 | 0,33 |
| Merín | 0,42 | 0,61 | 0,47 | 0,76 | 0,31 |
| Río Branco | 0,53 | 0,54 | 0,36 | 0,71 | 0,45 |
| Mercedes | 0,45 | 0,34 | 0,36 | 0,41 | 0,56 |
| Melo | ~0,4 (casi sin agua) | | | | |
| Durazno | 0,14 (casi sin agua; NISAR sobredetecta ruido) | | | | |
| Rocha norte (agregada 15/11) | **0,60** | **0,66** | 0,43 | 0,75 | 0,51 |
| Castillos (agregada 15/11) | 0,54 | 0,58 | 0,40 | 0,64 | 0,48 |
| Paysandú (evento de octubre) | 0,20 | 0,17 | 0,13 | 0,19 | 0,21 |
| Salto, Artigas (octubre) | sin agua nueva en ninguno de los dos sensores (S1 0–0,2 %) | | | | |

Con las 11 zonas: 47 comparaciones con agua S1 ≥ 0,5 %, exhaustividad 0,60, F1 0,44 estricta / 0,49 laxa (umbral viejo 0,38 / 0,34). Las zonas de agosto viejas no cambian.

Lectura:
- **NISAR mapea más agua que S1** (precisión baja contra S1 estricta) pero encuentra casi todo lo que ve S1. El 54 % de los píxeles que sólo marca NISAR también se oscurecen en S1 (ΔVV < −2 dB), sin llegar a su umbral; en TyT y Merín es el 66–68 %. En esos píxeles NISAR cae en mediana −5,8 dB y HV −3,6 dB: es agua somera, parcial o con vegetación emergente (arroz, pradera), donde la banda C se satura y la L todavía ve el agua. Contra la referencia laxa, el acuerdo sube a 0,61–0,64.
- El detector viejo empataba en F1 estricta porque se perdía esa agua somera (exhaustividad baja).
- Casos malos: Durazno, Mercedes y Melo tienen < 2 % de agua abierta y F1 inestable. En Mercedes, el 18–22/9, ambos sensores marcan ~1–2 % en lugares distintos.
- Las cifras de extensión de la app son por lo tanto **cota alta** respecto de un mapa de agua abierta en banda C. La banda de sensibilidad (`sensibilidad.py`) cubre parte de esa diferencia.

**Evento de octubre (litoral).** S1 confirma de forma independiente que la creciente del río Uruguay y del Cuareim dejó muy poca agua abierta nueva en los recortes: Salto y Artigas ~0 % en ambos sensores, Paysandú 0,6–1,3 % en S1 y 0,2–1,2 % en NISAR. El acuerdo píxel a píxel en Paysandú es bajo (F1 0,2): las dos manchas son angostas (costa e islas) y caen en bordes. Parte del agua de Paysandú está bajo el monte de las islas (exceso ribereño positivo en los 3 tracks, `monte_ribereno_resumen.csv`), que la banda C no ve.

## 3. Crestas reportadas (prensa / SINAE, contexto)

NISAR pasa cada 12 días por track y no puede fechar la cresta. Pico de agua nueva (track de la serie, 10/8–10/9) contra la cresta reportada:

| Zona | Cresta reportada | Pico NISAR |
|---|---|---|
| Treinta y Tres | Olimar ~8,6 m, 19–20/8 | 23/8 (+4 d), 8,0 % |
| Río Branco | Yaguarón, 18–19/8 | 28/8 (+9 d), 13,1 % |
| Melo | Conventos, 17–20/8 | 27/8, 0,1 % (casi sin agua abierta) |
| Durazno | Yí 9,75 m, 22/8 | 10/9, 0,7 % (señal débil) |
| Mercedes | Río Negro ~21–25/8 | 6/9, 1,8 % (señal débil) |
| Salto | Río Uruguay ~12 m, 10–11/10 | sin agua nueva |
| Paysandú | Río Uruguay 6,32 m, ~12–16/10 | 12/10 (serie 10D), señal débil (< 1 %) |
| Artigas | Cuareim > 11,5 m, 1/10 | 16/10, 1,1 % en 60A, pero S1 da 0 % ese día: probable falsa alarma. La primera pasada (4/10) ya es posterior a la cresta |

En el este el pico NISAR es la primera pasada después de la cresta y el agua se retira después. En la cuenca del Negro el agua abierta es poca y la señal está bajo el monte (`monte_ribereno.py`), así que el "pico" es poco informativo.

## No hecho
- Niveles de río DINAGUA (series horarias): no se encontró API pública; usar fechas de prensa.
- Sentinel-2 (nubes durante el evento).
