/* "How we did it": step-by-step method page with real panels of the case-study zone.
   Rules: every number comes from data/manifest.json (entry "metodo", scripts/exportar_metodo.py, plus the zone's
   results from scripts/exportar_app.py); every text lives in STRINGS. Checked by scripts/check_story_literals.py.
   Deep links: method.html#paso-1 … #paso-11. */
"use strict";

const STRINGS = {
  en: {
    title: "How we did it",
    app_name: "FloodTracer",
    app_tag: "An interactive flood explorer powered by NISAR",
    team_t: "Who made it",
    team: "FloodTracer was made by Kevin Castillos, Matias Ricardi and Sebastián Rodriguez, team “NASA Que Ver” at the NASA Space Apps Challenge, from Montevideo, Uruguay.",
    eyebrow: (z) => `Method · ${z}`,
    lede: "From raw radar images to a map of how long the water stayed, one step at a time, with the real images of the case study.",
    tech: "Technical detail",
    no_data: (msg) => `The data did not load (${msg}). Serve the app folder over http: python3 -m http.server -d app`,
    zone: { rocha_norte: "northern Rocha", merin_arrozales: "the Laguna Merín", treinta_y_tres: "Treinta y Tres", rio_branco_jaguarao: "Río Branco" },
    steps: [
      ["Why radar", "When it rains, clouds hide the ground from the satellites that take photos."],
      ["The data", "We need the same place, seen the same way, many times."],
      ["Cleaning the image", "Radar images are grainy, like an old photo."],
      ["What is normal for each place", "A dark field is not always a flooded field: some are always dark."],
      ["Finding new water", "We look for places that turned much darker than their own normal."],
      ["Combining orbits", "One orbit can be fooled; several that agree are hard to fool."],
      ["How long it stayed", "The satellite passes every few days, so time under water is a range, not a single number."],
      ["Water under the trees", "Under a forest, water does not look dark: it makes the forest brighter."],
      ["Checking our work", "We compared with another radar, between orbits and with what was reported."],
      ["What we learned and the limits", "What worked, what did not, and what the radar cannot see."],
      ["Reproduce it", "Everything is open: data, code and results."],
    ],
    // 1
    p1: "A radar satellite sends its own microwave pulse and listens to the echo, so it works through clouds and at night. What comes back depends on the surface:",
    mech: [["Calm water", "acts like a mirror: the pulse bounces away and the pixel looks dark."], ["Field or pasture", "scatters the pulse in all directions: some comes back, the pixel looks grey."],
      ["Flooded forest", "the pulse bounces between water and trunks and comes straight back: very bright."]],
    mech_alt: "Diagram of three surfaces: calm water reflects the radar away, a field scatters it, a flooded forest bounces it back twice.",
    f1_opt: (d) => `Sentinel-2 photo, ${d}`,
    f1_rad: (d) => `NISAR radar, ${d}`,
    t1: "<p>NISAR (NASA–ISRO) carries an L-band radar, with a wavelength about a hand span long. We use the level-two GCOV product: terrain-corrected backscatter (gamma-naught) in HH and HV polarizations, downloaded as small crops per area.</p>",
    // 2
    p2b: (tr) => `A third orbit (${tr}) also passes over this area; step six explains why we left it out.`,
    p2: (n, tr, res) => `Over this area we use ${n} NISAR passes between June and October, from ${tr} different orbits. Each pixel covers ${res} × ${res} metres. Each orbit always looks from the same angle, so a pixel can be compared with itself pass after pass.`,
    tl_alt: "Timeline of NISAR passes over the area for each orbit, with the storm and the gap in the data marked.",
    tl_rain: "storm",
    tl_gap: "no data in the archive",
    t2: "<p>Series are built one orbit at a time (same geometry); orbits are combined only at the level of water masks. Passes covering only an edge of the crop, or with broken calibration, are dropped. The ocean is masked out as no data: on calm days part of it looked like new water, and it says nothing about the fields.</p>",
    // 3
    p3: (w, km) => `Each radar pixel mixes many small echoes, which makes a salt-and-pepper grain called speckle. We average each pixel with its neighbours in a ${w} × ${w} window. Below, the same ${km} km patch before and after.`,
    f3_raw: "Raw radar",
    f3_clean: "After averaging",
    t3: (w) => `<p>Moving average of ${w} × ${w} pixels in linear power (not in dB), ignoring missing pixels so the crop edges are not eaten away.</p>`,
    // 4
    p4: (n) => `For every pixel we compute its typical value over the ${n} passes before the storm. That is its own "normal". Lakes and rivers that are always dark are marked as permanent water and left out.`,
    p4b: (nb, nc, z) => `Wind is a trap: it ripples open water and makes it bright. We saw it at ${z}: with all ${nb} passes before the storm, the lagoon looked only partly like water. Using only the ${nc} calm passes, it is solid water.`,
    f4_base: "Normal (median before the storm)",
    f4_all: "Permanent water, all passes",
    f4_calm: "Permanent water, calm passes only",
    t4: "<p>Baseline = per-pixel median of the passes before the event. Permanent water = darker than the track's calibrated threshold on most of the calm baseline passes (ERA5 wind at pass time below the calm limit, read over inland water, never over the ocean). Wind at each pass before the storm, for the example above:</p>",
    wind_row: (d, v, c) => `${d}: ${v} m/s${c ? " (calm)" : ""}`,
    // 5
    p5: "On each pass we subtract the pixel's normal. Pixels that turned much darker, and are dark enough to be water, become new water. A fixed darkness threshold alone misses shallow water; comparing each place with itself does not.",
    f5_peak: (d) => `Pass of ${d}`,
    f5_change: "Change vs. normal (blue = darker, red = brighter, dark grey = permanent water)",
    f5_new: (p) => `New water by change: ${p}% of the patch`,
    f5_old: (p) => `Fixed threshold: ${p}% of the patch`,
    px_title: "How dark each place looked to the radar, pass by pass",
    px_why: "Why it matters: this is the decision the detector makes for every pixel on every pass. A flood is not just a dark spot: it is a place that turns much darker than its own normal. Following real places shows that the same rule tells a lagoon from a flood, and a flood of a few days from one that lasted weeks, which is what the drying map is built on.",
    px_alt: "Line chart of how dark four real places looked to the radar on every pass: a lagoon, a field flooded briefly, a field flooded for weeks and a field that stayed dry.",
    px_types: { permanente: "Lagoon (always water)", rapido: "Field flooded briefly", tarde: "Field flooded for weeks", seco: "Field that stayed dry" },
    px_water: "dark enough to be water",
    px_base: "before the storm: each place's normal",
    k_radar: "Radar image: darker = smoother surface, possibly water",
    k_change: "Change vs. normal:",
    k_darker: "darker (possible water)",
    k_same: "no change",
    k_brighter: "brighter",
    k_perm: "Permanent water (not analysed)",
    k_none: "Not seen as water",
    lg_after: "Water detected after the storm",
    lg_base: "Water before the storm (baseline)",
    lg_wet: "Water detected before the storm, from earlier rains (not counted)",
    px_y: "Radar brightness (dB) · lower = darker",
    ser_y: "HH − HV vs. before the storm (dB)",
    px_note: "Each line follows the same place (a twenty-metre pixel) on every pass. The first points, before the storm, define each place's normal (dashed line). After the storm, a filled dot means the place was flagged as new water: much darker than its normal and inside the water zone. The lagoon is always water, so it is never counted as new water.",
    t5: (c, h, u) => `<p>New water when the change versus the baseline median is below ${c} dB (after removing the scene-wide offset on land) and the brightness is below ${h} dB, outside permanent water, in patches of at least ten pixels. The old fixed threshold was ${u} dB.</p>`,
    // 6
    p6b: (tr, p) => `We left a third orbit (${tr}) out. Its "normal" for permanent water came from a single calm pass, it recognized only ${p}% of the water a global record knows is there, and on its last pass before the storm it marked as already flooded land that another orbit saw dry the day before the rain. Mixing it in would have hidden part of the storm flooding.`,
    p6: (n, k) => `We combine ${n} orbits, which see the area on different days and from different angles. A pixel counts as flooded by the storm only if it was seen wet on at least ${k} passes. Land already flooded before the storm, by earlier rains (light blue), is kept apart.`,
    f6_track: (tr, d) => `Orbit ${tr}, ${d}`,
    f6_conf: "Confirmed flood",
    t6: "<p>Each orbit's masks are reprojected to a common grid. Confirmed extent = at least two wet observations between the start of the storm and the end of the event window, excluding pre-rain water. A pass counts as pre-rain by the time it was taken, not only its date: one orbit passed the morning before the rain started; it stays, as the last look before the storm. The excluded orbit is still processed, but it does not enter the combination or the maps; in the validation it appears only as a diagnostic (its share of the known water, in step nine).</p>",
    // 7
    p7: (m, a, b, s) => `For each pixel we know the first pass it was wet and the first pass it was dry again. The truth is somewhere in between, so time under water is a range; we use its midpoint. Among the fields that dried before the last pass, a typical one stayed ${m} days (between ${a} and ${b}); ${s}% were still wet at the last pass. To see where the water stayed longest, we go from pixels to a heat map in three steps:`,
    p7b: (c) => `Left: days under water of every flooded pixel. Middle: the average of the flooded pixels in each square of ${c} m, so small spots do not hide the pattern. Right: the heat map of the Story, where each square weighs its days times the share of it that flooded; the darker red, the longer and wider the water stayed.`,
    f7_days: "Days under water, per pixel",
    f7_ret: "Average per square",
    f7_heat: "Heat map: where the water stayed longest",
    lg_daysk: "Days under water:",
    lg_rng: (a, b) => `fewer to more (squares from ${a} to ${b} days; in the heat map, darker also means more of the area flooded)`,
    t7: "<p>Persistence is stored as an interval (minimum and maximum) and its midpoint. Retreat = two dry observations in a row; pixels still wet at the last pass use the lower bound (last pass minus first detection). Square value = mean midpoint days of its flooded pixels; heat-map weight = that value times the flooded share of the square (about hectare-days per hectare); squares less than five percent flooded are left out. From October on, cropland is treated as no data, because ploughing and rice preparation look as dark as water.</p>",
    // 8
    p8: "Radar does not see water under a forest as dark. Instead, the pulse bounces between the water surface and the trunks and comes back stronger. We compare riverside forest (low, next to a stream) with hillside forest on the same pass.",
    f8_map: "Riverside forest with water underneath (green)",
    ser_alt: "Line chart: change in the forest signal for riverside forest, hillside forest and open land, pass by pass.",
    ser_names: { ribereno: "Riverside forest", altura: "Hillside forest", no_monte: "Open land" },
    t8: "<p>Height above the nearest stream (HAND) from the DEM and OSM waterways; riverside = HAND below a few metres and close to a channel. Signal = HH − HV ratio relative to its baseline.</p>",
    // 9
    p9: (r, f, j, x) => `Against Europe's Sentinel-1 radar, NISAR found ${r}% of the new water Sentinel-1 saw (agreement score ${f} out of one). Two NISAR orbits a day apart, both after the rain started, marked largely the same water (agreement score ${j} out of one). And the flood is ${x} times larger than what the detector flags by mistake on dry passes.`,
    p9b: (a, b) => `It also recognizes ${a}% of the lakes and wetlands that a global record knows as permanent water; the weakest orbit only ${b}%.`,
    p9c: (a, b) => `It also recognizes ${a}% of the lakes and wetlands that a global record knows as permanent water. One of the three orbits recognized only ${b}%, one of the reasons we left it out.`,
    f9_s1: (d) => `Sentinel-1, ${d}`,
    f9_n: (d) => `NISAR, ${d}`,
    t9: "<p>Sentinel-1 (C-band) is only used to check, never to detect. Agreement between orbits is the Jaccard index on passes at most one day apart. The noise floor is the leave-one-out false alarm on the baseline passes; areas with a flood below twice that are marked not conclusive. Known water: JRC Global Surface Water (water at least three quarters of the time over decades), also only to check.</p>",
    // 10
    lessons_t: "Lessons",
    lessons: ["Compare each place with itself, not with a fixed darkness.", "Keep land that was already flooded before the storm apart.",
      "Calibrate permanent water with calm days only.", "Measure the detector's own noise before trusting a number.",
      "Leave out what you cannot measure, like the ocean.", "Check against water you already know is there."],
    limits_t: "Limits",
    next_t: "Next steps",
    next: ["Normalize the signal between orbits, so that all of them can feed one more complete timeline instead of using one orbit per series (today each orbit only joins at the level of water maps, and an orbit that does not fit has to be left out).",
      "Improve the water detection algorithm with machine learning, for example a model trained on hand-labelled examples that also uses the HV channel and the shape of each place's time series, while Sentinel-1 and the global water record stay for validation only."],
    lim: [(d) => `Each orbit passes every ${d} days: durations are ranges.`, () => "Inside towns the radar sees almost nothing.",
      (k, n) => `Wind: ${k} of ${n} storm passes on the main orbit were windy, so some water may be missed.`, () => "Data arrives days later: for response and recovery, not early warning.",
      (p) => `One of the orbits marks only ${p}% of the known water as permanent water, so it is the least reliable near lagoons and wetlands.`,
      (p) => `We left one of the three orbits out (it saw only ${p}% of the known water), so there are fewer passes to time the drying.`],
    // 11
    p11: "The whole pipeline is open source and runs on free data. In order:",
    pipe: ["Download crops per area", "Roads, towns, basins, land cover", "Weather at pass time", "Detect new water per orbit",
      "Combine orbits and set pre-rain water aside (detection runs again after this)", "Agreement between orbits", "Detector sensitivity",
      "Water under forests", "Impact tables", "Check with Sentinel-1 and with known water", "Case-study checks", "Export for this site"],
    code: "Code on GitHub",
  },
  es: {
    title: "Cómo lo hicimos",
    app_name: "FloodTracer",
    app_tag: "Un explorador interactivo de inundaciones con NISAR",
    team_t: "Quiénes lo hicimos",
    team: "FloodTracer lo hicimos Kevin Castillos, Matias Ricardi y Sebastián Rodriguez, el equipo “NASA Que Ver” del NASA Space Apps Challenge, desde Montevideo, Uruguay.",
    eyebrow: (z) => `Método · ${z}`,
    lede: "De las imágenes de radar crudas a un mapa de cuánto tiempo se quedó el agua, paso a paso, con las imágenes reales del caso de estudio.",
    tech: "Detalle técnico",
    no_data: (msg) => `No cargaron los datos (${msg}). Serví la carpeta app por http: python3 -m http.server -d app`,
    zone: { rocha_norte: "Rocha norte", merin_arrozales: "la Laguna Merín", treinta_y_tres: "Treinta y Tres", rio_branco_jaguarao: "Río Branco" },
    steps: [
      ["Por qué radar", "Cuando llueve, las nubes tapan el suelo para los satélites que sacan fotos."],
      ["Los datos", "Necesitamos el mismo lugar, visto de la misma forma, muchas veces."],
      ["Limpiar la imagen", "Las imágenes de radar tienen grano, como una foto vieja."],
      ["Qué es normal en cada lugar", "Un campo oscuro no siempre está inundado: algunos son oscuros siempre."],
      ["Encontrar el agua nueva", "Buscamos lugares que se oscurecieron mucho respecto de su propio normal."],
      ["Combinar órbitas", "Una órbita se puede equivocar; varias que coinciden, difícilmente."],
      ["Cuánto tiempo se quedó", "El satélite pasa cada algunos días, así que el tiempo bajo agua es un rango, no un número exacto."],
      ["Agua bajo los árboles", "Bajo el monte el agua no se ve oscura: hace que el monte se vea más brillante."],
      ["Verificar el trabajo", "Comparamos con otro radar, entre órbitas y con lo que se informó."],
      ["Lo que aprendimos y los límites", "Qué funcionó, qué no y qué no puede ver el radar."],
      ["Reproducirlo", "Todo es abierto: datos, código y resultados."],
    ],
    p1: "Un satélite radar manda su propio pulso de microondas y escucha el eco, así que funciona a través de las nubes y de noche. Lo que vuelve depende de la superficie:",
    mech: [["Agua quieta", "actúa como un espejo: el pulso rebota hacia otro lado y el píxel se ve oscuro."], ["Campo o pradera", "dispersa el pulso para todos lados: vuelve una parte y el píxel se ve gris."],
      ["Monte inundado", "el pulso rebota entre el agua y los troncos y vuelve directo: muy brillante."]],
    mech_alt: "Diagrama de tres superficies: el agua quieta refleja el radar hacia otro lado, un campo lo dispersa, un monte inundado lo devuelve con doble rebote.",
    f1_opt: (d) => `Foto Sentinel-2, ${d}`,
    f1_rad: (d) => `Radar NISAR, ${d}`,
    t1: "<p>NISAR (NASA–ISRO) lleva un radar en banda L, con una onda del largo de una cuarta. Usamos el producto GCOV de nivel dos: retrodispersión corregida por terreno (gamma-cero) en polarizaciones HH y HV, bajando sólo recortes chicos por zona.</p>",
    p2b: (tr) => `Una tercera órbita (${tr}) también pasa sobre esta zona; el paso seis explica por qué la dejamos afuera.`,
    p2: (n, tr, res) => `Sobre esta zona usamos ${n} pasadas de NISAR entre junio y octubre, de ${tr} órbitas distintas. Cada píxel cubre ${res} × ${res} metros. Cada órbita mira siempre desde el mismo ángulo, así que un píxel se puede comparar consigo mismo pasada tras pasada.`,
    tl_alt: "Línea de tiempo de las pasadas de NISAR sobre la zona para cada órbita, con la tormenta y el hueco de datos marcados.",
    tl_rain: "tormenta",
    tl_gap: "sin datos en el archivo",
    t2: "<p>Las series se arman de a una órbita (misma geometría); las órbitas se combinan sólo a nivel de máscaras de agua. Se descartan las pasadas que cubren sólo un borde del recorte o con la calibración rota. El océano se excluye como sin dato: los días de calma parte de él parecía agua nueva, y no dice nada de los campos.</p>",
    p3: (w, km) => `Cada píxel de radar mezcla muchos ecos chicos, lo que produce un grano de sal y pimienta llamado speckle. Promediamos cada píxel con sus vecinos en una ventana de ${w} × ${w}. Abajo, el mismo recorte de ${km} km antes y después.`,
    f3_raw: "Radar crudo",
    f3_clean: "Después de promediar",
    t3: (w) => `<p>Media móvil de ${w} × ${w} píxeles en potencia lineal (no en dB), ignorando los píxeles sin dato para no comerse los bordes del recorte.</p>`,
    p4: (n) => `Para cada píxel calculamos su valor típico en las ${n} pasadas anteriores a la tormenta. Ese es su propio "normal". Lagunas y ríos que son oscuros siempre se marcan como agua permanente y quedan afuera.`,
    p4b: (nb, nc, z) => `El viento es una trampa: riza el agua abierta y la vuelve brillante. Lo vimos en ${z}: con las ${nb} pasadas anteriores a la tormenta, la laguna parecía agua sólo en parte. Usando sólo las ${nc} pasadas de calma, es agua sólida.`,
    f4_base: "Normal (mediana antes de la tormenta)",
    f4_all: "Agua permanente, todas las pasadas",
    f4_calm: "Agua permanente, sólo pasadas de calma",
    t4: "<p>Línea de base = mediana por píxel de las pasadas anteriores al evento. Agua permanente = más oscuro que el umbral calibrado del track en la mayoría de las pasadas base de calma (viento ERA5 a la hora de la pasada por debajo del límite de calma, tomado sobre agua de tierra adentro, nunca sobre el océano). Viento en cada pasada anterior a la tormenta, para el ejemplo de arriba:</p>",
    wind_row: (d, v, c) => `${d}: ${v} m/s${c ? " (calma)" : ""}`,
    p5: "En cada pasada restamos el normal del píxel. Los píxeles que se oscurecieron mucho, y quedaron lo bastante oscuros para ser agua, pasan a ser agua nueva. Un umbral fijo de oscuridad pierde el agua somera; comparar cada lugar consigo mismo, no.",
    f5_peak: (d) => `Pasada del ${d}`,
    f5_change: "Cambio respecto del normal (azul = más oscuro, rojo = más brillante, gris oscuro = agua permanente)",
    f5_new: (p) => `Agua nueva por cambio: ${p} % del recorte`,
    f5_old: (p) => `Umbral fijo: ${p} % del recorte`,
    px_title: "Qué tan oscuro vio el radar cada lugar, pasada a pasada",
    px_why: "Por qué importa: esta es la decisión que toma el detector para cada píxel en cada pasada. Una inundación no es sólo un lugar oscuro: es un lugar que se vuelve mucho más oscuro que su propio normal. Seguir lugares reales muestra que la misma regla separa una laguna de una inundación, y una inundación de pocos días de una que duró semanas, que es la base del mapa de secado.",
    px_alt: "Gráfico de líneas de qué tan oscuros vio el radar cuatro lugares reales en cada pasada: una laguna, un campo inundado poco tiempo, uno inundado por semanas y uno que siguió seco.",
    px_types: { permanente: "Laguna (siempre agua)", rapido: "Campo inundado poco tiempo", tarde: "Campo inundado por semanas", seco: "Campo que siguió seco" },
    px_water: "lo bastante oscuro para ser agua",
    px_base: "antes de la tormenta: el normal de cada lugar",
    k_radar: "Imagen de radar: más oscuro = superficie más lisa, posible agua",
    k_change: "Cambio respecto del normal:",
    k_darker: "más oscuro (posible agua)",
    k_same: "sin cambio",
    k_brighter: "más brillante",
    k_perm: "Agua permanente (no se analiza)",
    k_none: "No se ve como agua",
    lg_after: "Agua detectada después de la tormenta",
    lg_base: "Agua antes de la tormenta (referencia)",
    lg_wet: "Agua detectada antes de la tormenta, por lluvias anteriores (no se cuenta)",
    px_y: "Brillo del radar (dB) · más abajo = más oscuro",
    ser_y: "HH − HV respecto de antes (dB)",
    px_note: "Cada línea sigue un mismo lugar (un píxel de veinte metros) en todas las pasadas. Los primeros puntos, antes de la tormenta, definen el normal de cada lugar (línea punteada). Después de la tormenta, un punto lleno quiere decir que el lugar se marcó como agua nueva: mucho más oscuro que su normal y dentro de la zona de agua. La laguna es agua siempre, así que nunca cuenta como agua nueva.",
    t5: (c, h, u) => `<p>Agua nueva cuando el cambio respecto de la mediana base es menor a ${c} dB (tras quitar el desplazamiento de toda la escena en tierra) y el brillo es menor a ${h} dB, fuera del agua permanente, en manchas de al menos diez píxeles. El umbral fijo viejo era ${u} dB.</p>`,
    p6b: (tr, p) => `Dejamos afuera una tercera órbita (${tr}). Su "normal" de agua permanente salía de una sola pasada de calma, reconocía sólo el ${p} % del agua que un registro global sabe que existe, y en su última pasada antes de la tormenta marcaba como ya inundada tierra que otra órbita vio seca el día antes de la lluvia. Mezclarla habría escondido parte de la inundación de la tormenta.`,
    p6: (n, k) => `Combinamos ${n} órbitas, que ven la zona en días distintos y desde ángulos distintos. Un píxel cuenta como inundado por la tormenta sólo si se vio mojado en al menos ${k} pasadas. La tierra ya inundada antes de la tormenta, por lluvias anteriores (celeste), queda aparte.`,
    f6_track: (tr, d) => `Órbita ${tr}, ${d}`,
    f6_conf: "Inundación confirmada",
    t6: "<p>Las máscaras de cada órbita se reproyectan a una grilla común. Extensión confirmada = al menos dos observaciones mojadas entre el inicio de la tormenta y el fin de la ventana del evento, sin el agua previa a la lluvia. Una pasada cuenta como previa por la hora en que se tomó, no sólo por la fecha: una órbita pasó la mañana antes de que empezara a llover; se mantiene, como la última mirada antes de la tormenta. La órbita excluida se sigue procesando, pero no entra a la combinación ni a los mapas; en la validación aparece sólo como diagnóstico (su parte del agua conocida, en el paso nueve).</p>",
    p7: (m, a, b, s) => `Para cada píxel sabemos la primera pasada en que estuvo mojado y la primera en que volvió a estar seco. La verdad está en el medio, así que el tiempo bajo agua es un rango; usamos su punto medio. Entre los campos que se secaron antes de la última pasada, uno típico estuvo ${m} días (entre ${a} y ${b}); el ${s} % seguía mojado en la última pasada. Para ver dónde se quedó más tiempo el agua, pasamos de los píxeles a un mapa de calor en tres pasos:`,
    p7b: (c) => `Izquierda: los días bajo agua de cada píxel inundado. Centro: el promedio de los píxeles inundados en cada cuadrado de ${c} m, para que las manchas chicas no tapen el patrón. Derecha: el mapa de calor de la Historia, donde cada cuadrado pesa sus días por la parte que se inundó; cuanto más rojo oscuro, más tiempo y más extensión tuvo el agua.`,
    f7_days: "Días bajo agua, por píxel",
    f7_ret: "Promedio por cuadrado",
    f7_heat: "Mapa de calor: dónde se quedó más tiempo el agua",
    lg_daysk: "Días bajo agua:",
    lg_rng: (a, b) => `de menos a más (cuadrados de ${a} a ${b} días; en el mapa de calor, más oscuro también es más superficie inundada)`,
    t7: "<p>La persistencia se guarda como intervalo (mínimo y máximo) y su punto medio. Retiro = dos observaciones secas seguidas; los píxeles que seguían mojados en la última pasada usan la cota inferior (última pasada menos primera detección). Valor del cuadrado = promedio de los días (punto medio) de sus píxeles inundados; peso en el mapa de calor = ese valor por la parte inundada del cuadrado (más o menos hectárea-días por hectárea); se descartan los cuadrados con menos del cinco por ciento inundado. Desde octubre las zonas de cultivo se tratan como sin dato, porque el laboreo y la preparación del arroz se ven tan oscuros como el agua.</p>",
    p8: "El radar no ve oscura el agua bajo el monte. En cambio, el pulso rebota entre la superficie del agua y los troncos y vuelve más fuerte. Comparamos el monte ribereño (bajo, junto a un arroyo) con el monte de loma en la misma pasada.",
    f8_map: "Monte ribereño con agua debajo (verde)",
    ser_alt: "Gráfico de líneas: cambio en la señal del monte ribereño, el monte de loma y el campo abierto, pasada a pasada.",
    ser_names: { ribereno: "Monte ribereño", altura: "Monte de loma", no_monte: "Campo abierto" },
    t8: "<p>Altura sobre el cauce más cercano (HAND) a partir del modelo de elevación y los cursos de agua de OSM; ribereño = HAND de pocos metros y cerca de un cauce. Señal = cociente HH − HV respecto de su línea de base.</p>",
    p9: (r, f, j, x) => `Frente al radar europeo Sentinel-1, NISAR encontró el ${r} % del agua nueva que vio Sentinel-1 (puntaje de acuerdo ${f} sobre uno). Dos órbitas de NISAR con un día de diferencia, ambas después de que empezó la lluvia, marcaron en gran parte la misma agua (puntaje de acuerdo ${j} sobre uno). Y la inundación es ${x} veces más grande que lo que el detector marca por error en pasadas secas.`,
    p9b: (a, b) => `Además reconoce el ${a} % de las lagunas y bañados que un registro global conoce como agua permanente; la órbita más débil, sólo el ${b} %.`,
    p9c: (a, b) => `Además reconoce el ${a} % de las lagunas y bañados que un registro global conoce como agua permanente. Una de las tres órbitas reconocía sólo el ${b} %, una de las razones por las que la dejamos afuera.`,
    f9_s1: (d) => `Sentinel-1, ${d}`,
    f9_n: (d) => `NISAR, ${d}`,
    t9: "<p>Sentinel-1 (banda C) se usa sólo para verificar, nunca para detectar. El acuerdo entre órbitas es el índice de Jaccard en pasadas a no más de un día. El piso de ruido es la falsa alarma dejando una afuera en las pasadas base; las zonas con una inundación menor al doble de eso se marcan como no concluyentes. Agua conocida: JRC Global Surface Water (agua al menos tres cuartos del tiempo durante décadas), también sólo para verificar.</p>",
    lessons_t: "Lecciones",
    lessons: ["Comparar cada lugar consigo mismo, no contra una oscuridad fija.", "Separar la tierra que ya estaba inundada antes de la tormenta.",
      "Calibrar el agua permanente sólo con días de calma.", "Medir el ruido del propio detector antes de confiar en una cifra.",
      "Dejar afuera lo que no se puede medir, como el océano.", "Chequear contra el agua que ya sabemos que existe."],
    limits_t: "Límites",
    next_t: "Próximos pasos",
    next: ["Normalizar la señal entre órbitas, para que todas puedan alimentar una línea temporal más completa en lugar de usar una órbita por serie (hoy cada órbita se suma sólo a nivel de mapas de agua, y una órbita que no encaja hay que dejarla afuera).",
      "Mejorar el algoritmo de detección de agua con aprendizaje automático, por ejemplo un modelo entrenado con ejemplos etiquetados a mano que use también el canal HV y la forma de la serie temporal de cada lugar, manteniendo Sentinel-1 y el registro global de agua sólo para validar."],
    lim: [(d) => `Cada órbita pasa cada ${d} días: las duraciones son rangos.`, () => "Dentro de las ciudades el radar casi no ve.",
      (k, n) => `Viento: ${k} de las ${n} pasadas de la tormenta en la órbita principal tuvieron viento, así que se puede perder parte del agua.`, () => "Los datos llegan días después: para la respuesta y la recuperación, no para la alerta temprana.",
      (p) => `Una de las órbitas marca como permanente sólo el ${p} % del agua conocida, así que es la menos confiable cerca de lagunas y bañados.`,
      (p) => `Dejamos afuera una de las tres órbitas (veía sólo el ${p} % del agua conocida), así que hay menos pasadas para medir el secado.`],
    p11: "Todo el análisis es de código abierto y usa datos gratuitos. En orden:",
    pipe: ["Bajar recortes por zona", "Caminos, localidades, cuencas, uso del suelo", "Clima a la hora de cada pasada", "Detectar agua nueva por órbita",
      "Combinar órbitas y apartar el agua previa a la lluvia (después la detección corre de nuevo)", "Acuerdo entre órbitas", "Sensibilidad del detector",
      "Agua bajo el monte", "Tablas de impacto", "Verificar con Sentinel-1 y con agua conocida", "Chequeos del caso de estudio", "Exportar para este sitio"],
    code: "Código en GitHub",
  },
};
// pipeline scripts in order (names only; descriptions in STRINGS.*.pipe)
const PIPELINE = ["descargar_zonas.py", "capas_contexto.py", "clima.py", "metricas_evento.py", "combinar_tracks.py + metricas_evento.py",
  "armonizar_tracks.py", "sensibilidad.py", "monte_ribereno.py", "agregar_impacto.py", "validar_s1.py + agua_conocida.py", "caso_rocha_norte.py",
  "exportar_optico.py + exportar_app.py + exportar_metodo.py"];
const REPO = "https://github.com/kevcst/floodtracer";

(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  let lang = (window.SiteNav && window.SiteNav.lang) || new URLSearchParams(location.search).get("lang") || "en";
  if (!STRINGS[lang]) lang = "en";
  const t = (k, ...a) => { const v = STRINGS[lang][k] ?? STRINGS.en[k]; return typeof v === "function" ? v(...a) : v; };
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const nf = (v, d = 0) => (v == null || isNaN(v) ? "–" : new Intl.NumberFormat(lang === "es" ? "es-UY" : "en-US", { maximumFractionDigits: d, minimumFractionDigits: d }).format(v));
  const fdate = (s, long) => new Date(s + "T12:00:00Z").toLocaleDateString(lang === "es" ? "es-UY" : "en-GB",
    long ? { day: "numeric", month: "long", timeZone: "UTC" } : { day: "numeric", month: "short", timeZone: "UTC" });
  const trk = (s) => (/T(\d+[AD])/.exec(s) || [, s])[1];
  const SVGNS = "http://www.w3.org/2000/svg";
  let M = null;

  const fig = (src, cap) => `<figure class="fig"><img src="${esc(src)}" alt="${esc(cap)}" loading="lazy"><figcaption>${esc(cap)}</figcaption></figure>`;
  const figs = (items, cls = "") => `<div class="figs ${cls}">${items.join("")}</div>`;
  // color keys under the image panels: same colors as exportar_app / exportar_metodo, same labels as the Story (lg_*)
  const AZUL = "rgb(42,120,214)", NARANJA = "rgb(235,104,52)";
  const key = (color, text, extra = "") => `<span><i style="background:${color}${extra}"></i>${esc(text)}</span>`;
  const keys = (items) => `<div class="keys img-keys">${items.join("")}</div>`;

  // ---------- small SVG charts ----------
  function svgEl(tag, attrs, parent) { const n = document.createElementNS(SVGNS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; }
  function lineChart(host, series, opts) {
    const W = 560, l = 64, r = 12, tp = opts.baseLabel || opts.rainLabel ? 30 : 12, H = 218 + tp, b = 26;   // labels go in the top margin
    const all = series.flatMap((s) => s.pts.filter((p) => p.v != null));
    const t0 = Math.min(...all.map((p) => Date.parse(p.f))), t1 = Math.max(...all.map((p) => Date.parse(p.f)));
    let lo = Math.min(...all.map((p) => p.v), ...(opts.extra || [])), hi = Math.max(...all.map((p) => p.v), ...(opts.extra || []));
    const pad = (hi - lo) * 0.08 || 1; lo -= pad; hi += pad;
    const x = (f) => l + (Date.parse(f) - t0) / Math.max(1, t1 - t0) * (W - l - r), y = (v) => tp + (hi - v) / (hi - lo) * (H - tp - b);
    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart", role: "img", "aria-label": opts.alt }, null);
    if (opts.water != null && opts.water > lo) {      // zone dark enough to be water (detector ceiling)
      svgEl("rect", { x: l, y: y(Math.min(opts.water, hi)), width: W - r - l, height: H - b - y(Math.min(opts.water, hi)), class: "waterzone" }, svg);
      svgEl("line", { x1: l, x2: W - r, y1: y(opts.water), y2: y(opts.water), class: "waterline" }, svg);
      svgEl("text", { x: l + 6, y: y(opts.water - 3.5) + 4, class: "lab water" }, svg).textContent = opts.waterLabel || "";   // between grid lines
    }
    if (opts.rain) { const rr = svgEl("rect", { x: x(opts.rain[0]), y: tp, width: Math.max(3, x(opts.rain[1]) - x(opts.rain[0])), height: H - tp - b, class: "rain" }, svg);
      if (opts.rainLabel) svgEl("text", { x: (x(opts.rain[0]) + x(opts.rain[1])) / 2, y: tp - 8, "text-anchor": "middle", class: "lab" }, svg).textContent = opts.rainLabel; }
    if (opts.baseEnd && opts.baseLabel) {               // passes before the storm: they define each place's normal
      const xb = x(opts.baseEnd) + 6;
      svgEl("path", { d: `M${l + 2},${tp - 2}V${tp - 6}H${xb}V${tp - 2}`, fill: "none", class: "bracket" }, svg);
      svgEl("text", { x: (l + xb) / 2, y: tp - 10, "text-anchor": "middle", class: "lab" }, svg).textContent = opts.baseLabel;
    }
    // y axis: round ticks with their values, the zero line when it is in range, and the axis title (opts.yLabel)
    const span = hi - lo, step = [0.5, 1, 2, 5, 10, 20].find((st) => span / st <= 6) || 50;
    for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) {
      const vv = Math.round(v * 100) / 100;
      svgEl("line", { x1: l, x2: W - r, y1: y(vv), y2: y(vv), class: vv === 0 && opts.zero ? "zero" : "grid" }, svg);
      svgEl("text", { x: l - 6, y: y(vv) + 4, "text-anchor": "end", class: "tick" }, svg).textContent = (opts.signed && vv > 0 ? "+" : "") + nf(vv, step < 1 ? 1 : 0);
    }
    svgEl("line", { x1: l, x2: l, y1: tp, y2: H - b, class: "axis" }, svg);
    if (opts.yLabel) svgEl("text", { x: 12, y: (tp + H - b) / 2, "text-anchor": "middle", class: "lab", transform: `rotate(-90 12 ${(tp + H - b) / 2})` }, svg).textContent = opts.yLabel;
    const months = [...new Set(all.map((p) => p.f.slice(0, 7)))];
    for (const m of months) { const f = m + "-15"; if (Date.parse(f) >= t0 && Date.parse(f) <= t1) svgEl("text", { x: x(f), y: H - 8, "text-anchor": "middle", class: "tick" }, svg).textContent = new Date(f + "T12:00:00Z").toLocaleDateString(lang === "es" ? "es-UY" : "en-GB", { month: "short", timeZone: "UTC" }); }
    series.forEach((s) => {
      const pts = s.pts.filter((p) => p.v != null);
      if (s.base != null) svgEl("line", { x1: l, x2: W - r, y1: y(s.base), y2: y(s.base), stroke: s.color, "stroke-dasharray": "4 4", "stroke-opacity": 0.6 }, svg);
      svgEl("path", { d: pts.map((p, k) => (k ? "L" : "M") + x(p.f).toFixed(1) + "," + y(p.v).toFixed(1)).join(""), fill: "none", stroke: s.color, "stroke-width": 2.2 }, svg);
      for (const p of pts) {
        if (p.nd) {                                       // no data on that pass (e.g. cropland from October): a grey cross, not a dot
          const cx = x(p.f), cy = y(p.v), d = 4;
          svgEl("path", { d: `M${cx - d},${cy - d}L${cx + d},${cy + d}M${cx - d},${cy + d}L${cx + d},${cy - d}`, class: "nodata" }, svg);
          continue;
        }
        const c = svgEl("circle", { cx: x(p.f), cy: y(p.v), r: 3.5, fill: p.on ? s.color : "var(--surface)", stroke: s.color, "stroke-width": 1.6 }, svg);
        svgEl("title", {}, c).textContent = `${s.name} · ${fdate(p.f)}`; }
    });
    host.appendChild(svg);
    host.insertAdjacentHTML("beforeend", `<div class="keys">${series.map((s) => `<span><i style="background:${s.color}"></i>${esc(s.name)}</span>`).join("")}</div>`);
  }
  function timeline(host, m) {
    const tracks = Object.entries(m.pasadas), W = 560, rowH = 26, l = 70, r = 12, tp = 8, H = tp + tracks.length * rowH + 26;
    const dates = tracks.flatMap(([, f]) => f), t0 = Math.min(...dates.map(Date.parse)), t1 = Math.max(...dates.map(Date.parse));
    const x = (f) => l + (Date.parse(f) - t0) / (t1 - t0) * (W - l - r);
    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart", role: "img", "aria-label": t("tl_alt") }, null);
    const g = svgEl("rect", { x: x(m.hueco[0]), y: tp, width: Math.max(0, x(m.hueco[1]) - x(m.hueco[0])), height: tracks.length * rowH, class: "gap" }, svg);
    svgEl("title", {}, g).textContent = t("tl_gap");
    svgEl("rect", { x: x(m.lluvia[0]), y: tp, width: Math.max(3, x(m.lluvia[1]) - x(m.lluvia[0])), height: tracks.length * rowH, class: "rain" }, svg);
    svgEl("text", { x: x(m.lluvia[1]) + 4, y: tp + 10, class: "lab" }, svg).textContent = t("tl_rain");
    tracks.forEach(([tr, fs], k) => {
      const yy = tp + k * rowH + rowH / 2;
      svgEl("text", { x: l - 8, y: yy + 4, "text-anchor": "end", class: "tick" }, svg).textContent = trk(tr);
      svgEl("line", { x1: l, x2: W - r, y1: yy, y2: yy, class: "grid" }, svg);
      for (const f of fs) { const c = svgEl("circle", { cx: x(f), cy: yy, r: 5, class: "pass" }, svg); svgEl("title", {}, c).textContent = `${trk(tr)} · ${fdate(f, true)}`; }
    });
    const months = [...new Set(dates.map((f) => f.slice(0, 7)))].sort();
    for (const mo of months) { const f = mo + "-15"; if (Date.parse(f) >= t0 && Date.parse(f) <= t1) svgEl("text", { x: x(f), y: H - 6, "text-anchor": "middle", class: "tick" }, svg).textContent = new Date(f + "T12:00:00Z").toLocaleDateString(lang === "es" ? "es-UY" : "en-GB", { month: "short", timeZone: "UTC" }); }
    host.appendChild(svg);
  }
  function mechanisms() {
    // three simple scattering sketches: specular (water), diffuse (field), double bounce (flooded forest)
    const mk = (k) => {
      const s = [`<svg viewBox="0 0 160 110" class="mech" aria-hidden="true">`, `<rect x="0" y="80" width="160" height="30" class="${k === 1 ? "soil" : "water"}"/>`,
        `<path d="M20 10 L70 78" class="ray"/><circle cx="20" cy="10" r="5" class="sat"/>`];
      if (k === 0) s.push(`<path d="M74 78 L140 12" class="ray out"/>`);
      if (k === 1) s.push(`<path d="M72 78 L40 30 M72 78 L72 26 M72 78 L110 34 M72 78 L135 50" class="ray out"/>`, `<path d="M0 80 Q20 70 40 80 T80 80 T120 80 T160 80" class="grass"/>`);
      if (k === 2) s.push(`<rect x="88" y="34" width="8" height="46" class="trunk"/><path d="M70 78 L88 60 L22 14" class="ray back"/>`);
      return s.join("") + "</svg>";
    };
    return `<div class="mechs" role="img" aria-label="${esc(t("mech_alt"))}">${t("mech").map(([h, p], k) => `<div>${mk(k)}<b>${esc(h)}</b><p>${esc(p)}</p></div>`).join("")}</div>`;
  }

  // ---------- content of each step ----------
  function content() {
    const m = M.metodo, z = m.zona, Zd = M.zonas[z], r = Zd.resumen, v = Zd.validacion, o = (M.contexto.optico || {})[z], p9 = M.contexto.s1_vs_nisar;
    const pl = Object.values(m.pasadas), nPass = pl.reduce((a, f) => a + f.length, 0);
    // wind limit: only the storm passes (fase "evento"), not the whole period after the rain
    const ev = Zd.fechas.filter((p) => p.fase === "evento" && p.remaining != null), windy = ev.filter((p) => p.confianza === "baja").length;
    const c = {};
    // agua conocida (JRC, sólo valida) y track excluido de la zona (zonas.excluir_tracks → validacion.agua_conocida[].excluido)
    const kw = ((v && v.agua_conocida) || []).filter((a) => a.pct_detectada != null), kSerie = kw.find((a) => a.serie),
      kOut = kw.find((a) => a.excluido), kWorst = kOut ? null : kw.reduce((mm, a) => (!mm || a.pct_detectada < mm.pct_detectada ? a : mm), null);
    c[1] = `<p>${esc(t("p1"))}</p>${mechanisms()}` + (o && o.optico ? figs([fig(o.optico, t("f1_opt", fdate(o.fecha_s2, true))), fig(o.nisar, t("f1_rad", fdate(o.fecha_nisar, true)))]) : "");
    c[2] = `<p>${esc(t("p2", nf(nPass), nf(pl.length), nf(m.resolucion_m)))}${kOut ? " " + esc(t("p2b", trk(kOut.track))) : ""}</p><div class="tl-host"></div>`;
    c[3] = `<p>${esc(t("p3", nf(m.speckle.ventana_px), nf(m.speckle.lado_km, 1)))}</p>` + figs([fig(m.speckle.crudo, t("f3_raw")), fig(m.speckle.filtrado, t("f3_clean"))], "pix");
    c[4] = `<p>${esc(t("p4", nf(m.detector.n_base)))}</p>` + figs([fig(m.detector.base, t("f4_base"))]) +
      `<p>${esc(t("p4b", nf(m.permanente.n_base), nf(m.permanente.n_calma), (t("zone") || {})[m.permanente.zona || z] || M.zonas[m.permanente.zona || z].nombre))}</p>` + figs([fig(m.permanente.todas, t("f4_all")), fig(m.permanente.calma, t("f4_calm"))]);
    c[5] = `<p>${esc(t("p5"))}</p>` + figs([fig(m.detector.pico, t("f5_peak", fdate(m.fecha_pico, true))), fig(m.detector.cambio, t("f5_change")),
      fig(m.detector.nueva, t("f5_new", nf(m.detector.pct_nueva, 1))), fig(m.detector.umbral, t("f5_old", nf(m.detector.pct_umbral, 1)))], "four") +
      keys([key("linear-gradient(90deg,#111,#ddd)", t("k_radar")),
        `<span>${esc(t("k_change"))} <i style="background:rgb(0,0,255)"></i>${esc(t("k_darker"))} <i style="background:#fff;border:1px solid var(--line)"></i>${esc(t("k_same"))} <i style="background:rgb(255,0,0)"></i>${esc(t("k_brighter"))}</span>`,
        key("rgb(70,70,70)", t("k_perm"))]) +
      keys([key(NARANJA, t("lg_after")), key(AZUL, t("lg_base")), key(M.leyendas.previa, t("lg_wet"))]) +
      `<h3>${esc(t("px_title"))}</h3><p>${esc(t("px_why"))}</p><div class="px-host"></div><p class="note">${esc(t("px_note"))}</p>`;
    c[6] = `<p>${esc(t("p6", nf(m.combinado.tracks.length), nf(m.combinado.min_obs)))}</p>` +
      (kOut ? `<p>${esc(t("p6b", trk(kOut.track), nf(kOut.pct_detectada)))}</p>` : "") +
      figs([...m.combinado.tracks.map((x) => fig(x.img, t("f6_track", trk(x.track), fdate(x.fecha, true)))), fig(m.combinado.confirmada, t("f6_conf"))], "four") +
      keys([key(NARANJA, t("lg_after")), key(M.leyendas.previa, t("lg_wet")), key("rgb(40,40,40)", t("k_none"))]);
    const sc = m.secado || {}, ramp = "linear-gradient(90deg,#fee090,#fdae61 17%,#f46d43 33%,#d73027 66%,#67001f)";
    c[7] = `<p>${esc(t("p7", nf(r.persist_mid), nf(r.persist_min), nf(r.persist_max), nf(r.pct_sigue)))}</p>` +
      (sc.pixel ? figs([fig(sc.pixel, t("f7_days")), fig(sc.celdas, t("f7_ret")), fig(sc.heat, t("f7_heat"))], "tall three") +
        `<p>${esc(t("p7b", nf(sc.celda_m)))}</p>` +
        keys([`<span>${esc(t("lg_daysk"))} <i class="ramp-i" style="background:${ramp}"></i> ${esc(t("lg_rng", nf(sc.dias_min), nf(sc.dias_max)))}</span>`]) : "");
    c[8] = `<p>${esc(t("p8"))}</p>` + figs([fig(m.monte.mapa, t("f8_map"))]) + `<div class="ser-host"></div>`;
    c[9] = (v ? `<p>${esc(t("p9", nf(100 * v.s1_medias.recall), nf(v.s1_medias.f1, 2), nf(v.jaccard_evento || 0, 2), nf(r.ha_inundada / r.ha_ruido)))}` +
      (kSerie && kOut ? ` ${esc(t("p9c", nf(kSerie.pct_detectada), nf(kOut.pct_detectada)))}` : kSerie && kWorst ? ` ${esc(t("p9b", nf(kSerie.pct_detectada), nf(kWorst.pct_detectada)))}` : "") + `</p>` : "") +
      (p9 ? figs([fig(p9.s1, t("f9_s1", fdate(p9.fecha_s1, true))), fig(p9.nisar, t("f9_n", fdate(p9.fecha_nisar, true)))]) : "");
    const lim = t("lim"), limArgs = [[nf(M.cifras.revisita_dias)], [], [nf(windy), nf(ev.length)], [], [kWorst ? nf(kWorst.pct_detectada) : null], [kOut ? nf(kOut.pct_detectada) : null]];
    c[10] = `<div class="cols"><div><h3>${esc(t("lessons_t"))}</h3><ul>${t("lessons").map((s) => `<li>${esc(s)}</li>`).join("")}</ul></div>` +
      `<div><h3>${esc(t("limits_t"))}</h3><ul>${lim.map((f, k) => ((k === 2 && !windy) || (k === 4 && !kWorst) || (k === 5 && !kOut) ? "" : `<li>${esc(f(...limArgs[k]))}</li>`)).join("")}</ul></div></div>` +
      `<h3>${esc(t("next_t"))}</h3><ul>${t("next").map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`;
    c[11] = `<p>${esc(t("p11"))}</p><ol class="pipe">${t("pipe").map((s, k) => `<li>${esc(s)} <code>${esc(PIPELINE[k])}</code></li>`).join("")}</ol>` +
      `<p><a href="${REPO}" target="_blank" rel="noopener">${esc(t("code"))}</a></p>`;
    const tech = { 1: t("t1"), 2: t("t2"), 3: t("t3", nf(m.speckle.ventana_px)), 5: t("t5", nf(m.detector.caida_db), nf(m.detector.techo_db), nf(m.detector.umbral_db, 1)),
      6: t("t6"), 7: t("t7"), 8: t("t8"), 9: t("t9"),
      4: t("t4") + `<p>${m.permanente.viento_base.map((w) => esc(t("wind_row", fdate(w.fecha), nf(w.viento_ms, 1), w.calma))).join(" · ")}</p>` };
    return { c, tech };
  }

  function render() {
    document.documentElement.lang = lang;
    document.title = `${t("app_name")} · ${t("title")}`;
    $$("[data-i18n]").forEach((n) => { if (typeof STRINGS[lang][n.dataset.i18n] === "string") n.textContent = t(n.dataset.i18n); });
    const steps = t("steps");
    // step ids are 1-based for deep links (method.html#paso-3); the number is the position, not a figure
    $("#toc").innerHTML = steps.map(([title], i) => `<li><a href="#paso-${i + 1}">${esc(title)}</a></li>`).join("");
    const cc = M && M.metodo ? content() : { c: {}, tech: {} };
    $("#steps").innerHTML = steps.map(([title, problem], i) => `<section class="step" id="paso-${i + 1}">
        <span class="num" aria-hidden="true">${i + 1}</span><div class="body"><h2>${esc(title)}</h2>
        <p class="problem">${esc(problem)}</p><div class="content">${cc.c[i + 1] || ""}</div>
        ${cc.tech[i + 1] ? `<details class="tech"><summary>${esc(t("tech"))}</summary><div class="tech-body">${cc.tech[i + 1]}</div></details>` : ""}</div></section>`).join("");
    if (M && M.metodo) {
      const m = M.metodo, z = m.zona;
      $(".eyebrow").textContent = t("eyebrow", (t("zone") || {})[z] || M.zonas[z].nombre);
      timeline($("#paso-2 .tl-host"), m);
      const COL = { permanente: "#2a6fc4", rapido: "#f08455", tarde: "#b44216", seco: "#8a95a1" };
      lineChart($("#paso-5 .px-host"), m.pixeles.map((p) => ({ name: t("px_types")[p.tipo], color: COL[p.tipo], base: p.base_db,
        pts: p.serie.map((s) => ({ f: s.fecha, v: s.hh_db, on: s.nueva, nd: s.sin_dato })) })),
        { alt: t("px_alt"), rain: m.lluvia, rainLabel: t("tl_rain"), extra: [...m.pixeles.map((p) => p.base_db), m.detector.techo_db - 2], yLabel: t("px_y"),
          water: m.detector.techo_db, waterLabel: t("px_water"),
          baseEnd: m.pixeles[0].serie.map((s) => s.fecha).filter((f) => f < m.lluvia[0]).pop(), baseLabel: t("px_base") });
      const SC = { ribereno: "#1a8f66", altura: "#8a6d3b", no_monte: "#8a95a1" };
      lineChart($("#paso-8 .ser-host"), Object.entries(m.monte.series).map(([k, s]) => ({ name: t("ser_names")[k] || k, color: SC[k] || "#888",
        pts: s.map((p) => ({ f: p.fecha, v: p.v, on: true })) })), { alt: t("ser_alt"), rain: m.lluvia, extra: [0], yLabel: t("ser_y"), zero: true, signed: true });
      $("#foot").textContent = `${t("app_name")} · ${M.generado}`;
      const team = document.getElementById("team");
      if (team) team.innerHTML = `<h2 id="team-title">${esc(t("team_t"))}</h2><p>${esc(t("team"))}</p>`;
    }
    if (location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
  }
  window.addEventListener("site-lang", (e) => { if (STRINGS[e.detail]) { lang = e.detail; render(); } });
  render();
  fetch("data/manifest.json", { cache: "no-cache" }).then((r) => r.json()).then((m) => { M = m; render(); })
    .catch((e) => { const el = $("#err"); el.textContent = t("no_data", e.message); el.style.display = "block"; });
})();
