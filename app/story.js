/* "After the rain": story of the case study (northern Rocha), one slide at a time over a fixed MapLibre map.
   No page scroll: ◀ ▶ buttons, arrow keys, or the contents menu; #scene-N deep links. English by default.
   Rules: every number comes from data/manifest.json (scripts/exportar_app.py) and is said once in the story; every
   visible text lives in STRINGS (en/es), with no em dashes; map legends use the same labels everywhere (lg_*).
   Checked by scripts/check_story_literals.py. The case-study zone is manifest.contexto.caso. */
"use strict";

const STRINGS = {
  en: {
    title: "FloodTracer",
    app_name: "FloodTracer",
    app_tag: "An interactive flood explorer powered by NISAR",
    subtitle: (z) => `How long did ${z} stay under water?`,
    hero_eyebrow: "NASA Space Apps · NASA Que Ver team · Uruguay · a proof of concept",
    hero_why: "Floods are usually reported as hectares reached and people displaced. For fields, roads and cattle, what decides the damage is how long the water stays, and that is rarely measured: during a storm, clouds hide the ground from the satellites that take photos.",
    hero_what: (z, when) => `We took the ${when} storm in ${z}, Uruguay, and followed it with NISAR, a NASA and ISRO radar satellite that sees through clouds, pass after pass. This first analysis measures where the water reached and how long it stayed, and compares the results with another radar and with press reports. The results are promising, not final.`,
    hero_next: "What you'll see",
    hero_cap: (z, d) => `Map: NISAR radar over ${z} on ${d}.`,
    start: "Start the story",
    prev: "Previous", next: "Next", toc: "Contents",
    toc_label: (i, n, title) => `${i} / ${n} · ${title}`,
    map_alt: "Map of northern Rocha, Uruguay, showing radar images and flood water",
    how: "How do we know?",
    loading: "Loading…",
    no_map: "The map library did not load (no internet?). The text and numbers still work.",
    no_data: (msg) => `The data did not load (${msg}). Serve the app folder over http: python3 -m http.server -d app and open the page from localhost.`,
    file_proto: "This page needs to be served over http to load its data (python3 -m http.server -d app).",
    broke: (msg) => `Something broke while drawing the page: ${msg}`,
    reset_view: "⤢ Show the whole area",

    // map legends: the same label for the same layer on every slide
    lg_base: "Water before the storm (baseline)",
    lg_after: "Water detected after the storm",
    lg_after2: "Water detected after the storm (on two or more passes)",
    lg_wet: "Water detected before the storm, from earlier rains (not counted)",
    lg_radar: "Radar: darker means water",
    lg_days: "Days under water",
    lg_area: "Study area",
    lg_veg: "Vegetation with water underneath",
    lg_roads: "Roads in flooded areas: days under water",
    lg_dmin: (d) => `${d} days`,
    lg_dmax: (d) => `${d} days`,
    stamp_pass: (date, zone) => `${zone} · NISAR pass of ${date}`,

    // 1
    s1_eyebrow: "The storm",
    s1_title: "The week satellites went blind",
    s1_body: "In mid-August a storm parked over eastern Uruguay. Optical satellites work like cameras: they record the sunlight reflected by the ground, so clouds block them and at night they see nothing. NISAR is a radar: it sends its own microwave pulse, with a wavelength far longer than cloud and rain droplets, so the pulse goes through them and comes back, day or night. Calm water reflects it away like a mirror, so water looks dark.",
    s1_anchor: (date) => `First NISAR look after the rain: ${date}.`,
    s1_swipe_left: (d) => `Optical (Sentinel-2), ${d}`,
    s1_swipe_right: (d) => `Radar (NISAR), ${d}`,
    s1_swipe_alt: (d1, d2) => `Before and after slider. Left: Sentinel-2 photo of ${d1}, almost all cloud. Right: NISAR radar of ${d2} over the same fields.`,
    s1_catalog: (a, b, items) => `Every Sentinel-2 image of these fields between ${a} and ${b} was cloudy: ${items}. The photo is only context; it is never used to detect water.`,
    s1_cat_item: (d, p) => `${d}, ${p}% cloud`,
    s1_no_optical: (a, b) => `No usable optical image between ${a} and ${b}.`,
    swipe_handle: "Move the divider",

    // 2
    s2_eyebrow: "The impact",
    s2_title: "What was reported, and what the radar adds",
    count_intro: (d, place) => `Around ${d}, the press reported flooded low fields and cattle moved to higher ground near ${place}. Those are early, local estimates from one moment. NISAR measured the footprint of the storm over the whole study area, across all its passes, and which kind of land it covered.`,
    c_press_ha: (a, b) => `${a}–${b}`,
    c_press_ha_l: "ha of low fields flooded (press)",
    c_cattle_l: "cattle moved to higher ground (press)",
    c_press_src: (src) => `Preliminary · ${src}`,
    c_nisar_l: "ha under water (NISAR)",
    c_nisar_src: () => "Seen on two or more passes. A first estimate from this proof of concept: it depends on the detector settings and is not a final figure.",
    count_why: "The radar measures more because it sees shallow water among the grass, hard to notice from the ground, and covers the whole area, not only the places reported.",
    lu_title: "Which land went under water",
    lu_row: (ha, p) => `${ha} ha · ${p}% of it`,
    lc: { "Grassland": "Grassland", "Herbaceous wetland": "Wetland", "Cropland (rice)": "Rice" },
    count_note: (ha) => `Another ${ha} ha were already flooded by earlier rains (July and early August): shown apart in light blue, not counted.`,

    // 3
    s3_eyebrow: "Pass by pass",
    s3_title: "The water arrived… and stayed",
    s3_body: (n) => `Step through it pass by pass: every ${n} days the same orbit came back over these fields.`,
    s3_still: "of the flooded area still wet",
    s3_before_big: "before the storm",
    s3_pass_new: (v, lo, hi) => `Water detected on this pass: ${v}% of the area (${lo}–${hi}%, depending on detector settings).`,
    s3_pass_before: (v) => `Before the storm: ${v}% already looked like water, because the fields were already flooded from July.`,
    s3_windy: (v) => `Windy pass (${v} m/s): wind makes water look brighter, so some may be missed. Lower confidence.`,
    s3_anchor: (d1, w, p1, d2, m, p2) => `On ${d1}, ${w} weeks after the rain, ${p1}% of the flooded area was still under water. On ${d2}, about ${m} months later, still ${p2}%.`,
    s3_how: "<p><b>Change, not darkness:</b> each pixel is compared with its own look before the storm, on the same orbit. <b>Seen twice:</b> only land seen wet on at least two passes counts. <b>Already flooded:</b> water from earlier rains, shown in light blue and not counted. <b>Wind:</b> hollow dots mark windy passes.</p>",
    pass_prev: "◀ Previous pass", pass_next: "Next pass ▶",
    chart_alt: (d1, p1, d2, p2) => `Line chart: share of the flooded area still wet. ${p1}% on ${d1}, ${p2}% on ${d2}.`,
    chart_rain: "rain",
    chart_gap: "no data",
    chart_gap_tip: (a, b) => `No NISAR data anywhere between ${a} and ${b}: a gap in the mission's archive, not a dry spell.`,
    chart_rain_tip: (a, b) => `Storm: ${a} to ${b}`,
    chart_pt: (d, p) => `${d}: ${p}% still wet`,
    chart_pt_windy: (d, p, v) => `${d}: ${p}% still wet · windy pass (${v} m/s), lower confidence`,
    chart_key: "Hollow dot: windy pass, lower confidence.",

    // 4
    s4_eyebrow: "Where to act first",
    s4_title: "Where the water stayed longest",
    dry_calc: (m) => `How it is calculated: we split the area into cells of about ${m} m. For each cell we count the days between the first pass that saw it wet and the first passes that saw it dry again. The longer it stayed wet, the darker the cell on the map.`,
    dry_half: (d1, d2, w1, w2) => `Half of the flooded land only dried between ${d1} and ${d2}, ${w1} to ${w2} weeks after the storm.`,
    s4_how: (d) => `<p>Days come from the dates of the passes, so they are accurate to about one revisit. Counted field by field, from the moment each one was seen wet, a typical flooded field stayed under water about ${d} days; the half-dry dates refer to the whole flooded area since the storm.</p>`,
    ex_title: "A worked example",
    ex_body: (n, km) => `The same ${km} km patch on the first ${n} passes after the storm (orange: water detected). A place that stays wet pass after pass ends up dark red on the drying map.`,
    ex_days: "Days under water",
    tap_hint: "Tap the map to see how long a place stayed under water.",
    place_days: (d, w) => (w ? `About ${d} days under water, roughly ${w} weeks.` : `About ${d} days under water.`),
    place_days_min: (d, w) => (w ? `At least ${d} days under water (over ${w} weeks) and still wet at the end.` : `At least ${d} days under water.`),
    place_dates: (a, b) => `First seen wet on ${a}, dry again on ${b}.`,
    place_first: (a) => `First seen wet on ${a}.`,
    place_share: (p) => `${p}% of the land around this point was flooded.`,
    place_none: "The radar did not see a lasting flood here during the storm.",
    place_outside: "Outside the study area: tap inside the dashed box.",

    // 5
    r_eyebrow: "Roads in flooded areas",
    r_title: "Which roads ran through flooded land",
    r_what: "What we did: we crossed the flood map with the rural road network from OpenStreetMap. Each road segment gets the days its land stayed under water, and the map colours it accordingly: darker roads crossed land that stayed flooded for longer.",
    r_use: "Why it could help: days after a storm, without waiting for reports, a departmental government could see which rural roads to inspect first, plan detours, and know which farms may have been cut off. This shows the idea; it is not a count of cut roads.",
    r_scale: "Days the land under each road stayed flooded",
    r_caveat: (m) => `Each radar pixel is about ${m} m and many rural roads run on raised banks, so a road in a flooded area is not always a cut road. It has to be checked on the ground.`,

    // 6
    s5_eyebrow: "What only L-band can see",
    s5_title: "Water that other satellites miss",
    tab_grass: "Under grass and rice",
    tab_veg: "Under vegetation",
    s5a_why: "Radar waves bounce off things about their own size. Europe's Sentinel-1 uses C-band, a wave a few centimetres long, similar to leaves and blades of grass: in a flooded pasture it bounces off the plants and misses the water below. NISAR uses L-band, a wave several times longer: it passes between the stems and reaches the water, which reflects it away like a mirror.",
    s5a_body: "Over open water both radars agree: slide the divider. Where they differ, NISAR usually sees more. We think it is shallow water under grass and rice, the most common kind of flooding in these fields, which is easy to underestimate.",
    s5_pair_left: (d) => `Sentinel-1 (C-band), ${d}`,
    s5_pair_right: (d) => `NISAR (L-band), ${d}`,
    s5_pair_alt: (d, a, b) => `Before and after slider over the same fields around ${d}. Sentinel-1 marks ${a}% of the view as water after the storm; NISAR marks ${b}%.`,
    s5_pair_note: (dt, a, b, km) => `${dt} days apart, same fields (${km} km across): Sentinel-1 saw water after the storm on ${a}% of the view, NISAR on ${b}%.`,
    s5b_why: "Why it matters: in wetlands and riverside forests the water hides under the plants, but it still drowns pasture, blocks access and keeps cattle away. Photos and short-wave radars mostly see the leaves, so that water goes uncounted.",
    s5b_body: "Why NISAR can see it: its long wave goes through the canopy, bounces off the water, hits the stems or trunks and comes straight back. That double bounce makes flooded vegetation brighter. In the marked area the radar came back much brighter after the storm: the signature of water under the plants.",
    veg_left: "Before the storm (June and July)",
    veg_right: (d) => `After the storm, ${d}`,
    veg_alt: (d) => `Before and after slider of vegetation by a stream: inside the green outlines the radar signal turns from dark to light after the storm (${d}).`,
    veg_key: "Lighter means a stronger bounce between water and stems. Green outline: vegetation with water underneath (forest or wetland). Blue: water before the storm.",

    // 7
    bal_eyebrow: "Balance",
    bal_title: "A promising analysis, with work ahead",
    bal_lede: "In northern Rocha the results are promising and partly agree with other sources. They are not validated enough to rely on yet, and taking the method to the whole country needs more work.",
    bal_ok_t: "What looks promising",
    ok_s1_t: "Another radar sees similar water",
    ok_s1: (r, n) => `Where Europe's Sentinel-1 saw water after the storm, NISAR found ${r}% of it. That is only ${n} comparisons.`,
    ok_orbit_t: "Two NISAR orbits agree",
    ok_orbit: (j, n) => `Two passes a day apart, from different angles, marked largely the same water: an agreement score of ${j} out of one (${n} pairs).`,
    ok_press_t: "Same order as reported",
    ok_press: "NISAR measured more than the press figures, which fits a wider area and shallow water in the grass that is hard to notice by eye.",
    ok_noise_t: "The signal stands out",
    ok_noise: (x) => `The flooded area is ${x} times what the detector flags by mistake on dry days.`,
    ok_known_t: "It recognizes water we already know",
    ok_known: (p) => `Of the lakes, lagoons and wetlands that a global record has seen as water for decades, NISAR marks ${p}% as permanent water.`,
    bal_todo_t: "Not solved yet",
    todo_wind_t: "Wind hides water",
    todo_wind: (k, n) => `${k} of the ${n} storm passes were windy, and wind makes water harder to see. Those dates are marked, not corrected.`,
    todo_low_t: "The lowest fields are left out",
    todo_low: (h) => `Land already flooded before the storm (${h} ha) is left out. Those are often the lowest fields, which dry last, so drying may look faster than it was.`,
    todo_till_t: "Ploughed fields look like water",
    todo_till: "In October, ploughed fields look as dark as water, so from then on we stop reading cropland and do not know when it dried.",
    todo_orbit_t: "One orbit sees much less",
    todo_orbit: (p) => `One orbit marks only ${p}% of that known water as permanent, so its passes are less reliable near lagoons and wetlands.`,
    todo_out_t: "One orbit left out",
    todo_out: (p) => `One of the three orbits saw only ${p}% of that known water and marked pre-storm water the others did not, so we left it out: fewer passes to time the drying.`,
    todo_sea_t: "The sea is left out",
    todo_sea: "On calm days part of the ocean looked like new water, so we mask it out. It does not touch the fields, but shows how much calm water can fool the detector.",
    todo_veg_t: "Forest and wetland get mixed up",
    todo_veg: "The signal of water under trees also lights up in wetlands with tall grass. We do not separate them well yet.",
    todo_half_t: "The half-dry date is borderline",
    todo_half: (d, p, n) => `On ${d}, ${p}% of the flooded land was still wet, just under half. A slightly different detector could move the half-dry date to the next pass, ${n} days later.`,
    todo_val_t: "Drying times are not validated",
    todo_val: "Sentinel-1 is compared pass by pass; the drying curve itself has no independent check yet, and with passes days apart durations are ranges.",
    bal_sum: (m, rb, tt) => `We also looked at three more areas, open in the explorer (their figures are not validated): Laguna Merín (${m} ha flooded), where wind data fixed how the lagoon was read; Río Branco / Jaguarão (${rb} ha), where the result looks most promising; and Treinta y Tres (${tt} ha), where the Olimar river is not seen as water because of the vegetation on its banks. In towns NISAR counts land, not people, and data arrives days later: it serves the response, not early warning. Next steps: normalize the signal between orbits for a fuller timeline and improve the detection with machine learning.`,
    s7_body: "NISAR passes over all of Uruguay every few days and its data is free. With the method tuned and validated, every rain alert could be followed, days later, by a map of where the water stayed and for how long.",
    uses_title: "What it could be used for",
    uses: [
      ["SINAE / CECOED", "Send help and inspections first to the places that stay wet longest."],
      ["Departmental governments", "Plan rural road repairs by how long each road was in flooded land."],
      ["MGAP · producers · insurers", "Back aid and claims with a dated map of flooded fields."],
      ["DINAGUA · INUMET", "See which rain left water on the ground and which basins drain slowest."],
    ],
    lk_method: "How we did it",
    lk_code: "Code",
    cta_explore: "Want to look for yourself? Explore the radar maps of northern Rocha and three other areas.",
    cta_explore_btn: "Explore the map",

    zonas: { rocha_norte: "northern Rocha" },
  },
  es: {
    title: "FloodTracer",
    app_name: "FloodTracer",
    app_tag: "Un explorador interactivo de inundaciones con NISAR",
    subtitle: (z) => `¿Cuánto tiempo estuvo ${z} bajo el agua?`,
    hero_eyebrow: "NASA Space Apps · equipo NASA Que Ver · Uruguay · una prueba de concepto",
    hero_why: "Las inundaciones se suelen informar en hectáreas alcanzadas y personas desplazadas. Para los campos, los caminos y el ganado, lo que define el daño es cuánto tiempo se queda el agua, y eso casi nunca se mide: durante una tormenta, las nubes tapan el suelo para los satélites que sacan fotos.",
    hero_what: (z, when) => `Tomamos la tormenta de ${when} en ${z}, Uruguay, y la seguimos con NISAR, un satélite radar de la NASA y la ISRO que ve a través de las nubes, pasada tras pasada. Este primer análisis mide hasta dónde llegó el agua y cuánto tiempo se quedó, y compara los resultados con otro radar y con la prensa. Los resultados son prometedores, no definitivos.`,
    hero_next: "Qué vas a ver",
    hero_cap: (z, d) => `Mapa: radar NISAR sobre ${z} el ${d}.`,
    start: "Empezar la historia",
    prev: "Anterior", next: "Siguiente", toc: "Índice",
    toc_label: (i, n, title) => `${i} / ${n} · ${title}`,
    map_alt: "Mapa del norte de Rocha, Uruguay, con imágenes de radar y agua de la inundación",
    how: "¿Cómo lo sabemos?",
    loading: "Cargando…",
    no_map: "No cargó la biblioteca del mapa (¿sin internet?). Los textos y las cifras funcionan igual.",
    no_data: (msg) => `No cargaron los datos (${msg}). Serví la carpeta app por http: python3 -m http.server -d app y abrí la página desde localhost.`,
    file_proto: "Esta página tiene que servirse por http para cargar sus datos (python3 -m http.server -d app).",
    broke: (msg) => `Algo falló al dibujar la página: ${msg}`,
    reset_view: "⤢ Ver toda la zona",

    lg_base: "Agua antes de la tormenta (referencia)",
    lg_after: "Agua detectada después de la tormenta",
    lg_after2: "Agua detectada después de la tormenta (en dos o más pasadas)",
    lg_wet: "Agua detectada antes de la tormenta, por lluvias anteriores (no se cuenta)",
    lg_radar: "Radar: más oscuro es agua",
    lg_days: "Días bajo agua",
    lg_area: "Zona de estudio",
    lg_veg: "Vegetación con agua debajo",
    lg_roads: "Caminos en zonas inundadas: días bajo agua",
    lg_dmin: (d) => `${d} días`,
    lg_dmax: (d) => `${d} días`,
    stamp_pass: (date, zone) => `${zone} · pasada NISAR del ${date}`,

    s1_eyebrow: "La tormenta",
    s1_title: "La semana en que los satélites quedaron ciegos",
    s1_body: "A mediados de agosto una tormenta se instaló sobre el este de Uruguay. Los satélites ópticos funcionan como cámaras: registran la luz del sol que refleja el suelo, así que las nubes los tapan y de noche no ven nada. NISAR es un radar: manda su propio pulso de microondas, con una onda mucho más larga que las gotas de las nubes y la lluvia, así que las atraviesa y vuelve, de día o de noche. El agua quieta lo refleja hacia otro lado como un espejo, por eso el agua se ve oscura.",
    s1_anchor: (date) => `Primera mirada de NISAR después de la lluvia: ${date}.`,
    s1_swipe_left: (d) => `Óptico (Sentinel-2), ${d}`,
    s1_swipe_right: (d) => `Radar (NISAR), ${d}`,
    s1_swipe_alt: (d1, d2) => `Deslizador antes y después. Izquierda: foto Sentinel-2 del ${d1}, casi toda nube. Derecha: radar NISAR del ${d2} sobre los mismos campos.`,
    s1_catalog: (a, b, items) => `Todas las imágenes Sentinel-2 de estos campos entre el ${a} y el ${b} estaban nubladas: ${items}. La foto es sólo contexto; nunca se usa para detectar agua.`,
    s1_cat_item: (d, p) => `${d}, ${p} % de nubes`,
    s1_no_optical: (a, b) => `No hay imagen óptica utilizable entre el ${a} y el ${b}.`,
    swipe_handle: "Mover el divisor",

    s2_eyebrow: "El impacto",
    s2_title: "Lo que se informó, y lo que el radar agrega",
    count_intro: (d, place) => `Alrededor del ${d}, la prensa informó campos bajos anegados y ganado trasladado a zonas altas cerca de ${place}. Son estimaciones tempranas y locales, de un momento. NISAR midió la huella de la tormenta en toda la zona de estudio, en todas sus pasadas, y qué tipo de tierra cubrió.`,
    c_press_ha: (a, b) => `${a}–${b}`,
    c_press_ha_l: "ha de campos bajos anegados (prensa)",
    c_cattle_l: "vacunos trasladados a zonas altas (prensa)",
    c_press_src: (src) => `Preliminar · ${src}`,
    c_nisar_l: "ha bajo agua (NISAR)",
    c_nisar_src: () => "Vistas en dos o más pasadas. Es una primera estimación de esta prueba de concepto: depende de los parámetros del detector y no es una cifra final.",
    count_why: "El radar mide más porque ve el agua poco profunda entre el pasto, que casi no se nota desde el suelo, y cubre toda la zona, no sólo los lugares informados.",
    lu_title: "Qué tierra quedó bajo agua",
    lu_row: (ha, p) => `${ha} ha · ${p} % de esa cobertura`,
    lc: { "Grassland": "Pradera", "Herbaceous wetland": "Bañado", "Cropland (rice)": "Arroz" },
    count_note: (ha) => `Otras ${ha} ha ya estaban inundadas por lluvias anteriores (julio y principios de agosto): se muestran aparte en celeste y no se cuentan.`,

    s3_eyebrow: "Pasada a pasada",
    s3_title: "El agua llegó… y se quedó",
    s3_body: (n) => `Avanzá pasada por pasada: cada ${n} días la misma órbita volvió sobre estos campos.`,
    s3_still: "del área inundada sigue mojada",
    s3_before_big: "antes de la tormenta",
    s3_pass_new: (v, lo, hi) => `Agua detectada en esta pasada: ${v} % del área (${lo}–${hi} %, según los parámetros del detector).`,
    s3_pass_before: (v) => `Antes de la tormenta: el ${v} % ya parecía agua, porque los campos venían inundados de julio.`,
    s3_windy: (v) => `Pasada con viento (${v} m/s): el viento aclara el agua y se puede perder una parte. Confianza menor.`,
    s3_anchor: (d1, w, p1, d2, m, p2) => `El ${d1}, ${w} semanas después de la lluvia, el ${p1} % del área inundada seguía bajo agua. El ${d2}, unos ${m} meses después, todavía el ${p2} %.`,
    s3_how: "<p><b>Cambio, no oscuridad:</b> cada píxel se compara con su propio aspecto antes de la tormenta, desde la misma órbita. <b>Visto dos veces:</b> sólo cuenta la tierra vista mojada en al menos dos pasadas. <b>Ya inundado:</b> agua de lluvias anteriores, en celeste y sin contar. <b>Viento:</b> los puntos huecos marcan pasadas con viento.</p>",
    pass_prev: "◀ Pasada anterior", pass_next: "Pasada siguiente ▶",
    chart_alt: (d1, p1, d2, p2) => `Gráfico de línea: parte del área inundada que sigue mojada. ${p1} % el ${d1}, ${p2} % el ${d2}.`,
    chart_rain: "lluvia",
    chart_gap: "sin datos",
    chart_gap_tip: (a, b) => `Sin datos de NISAR en ningún lugar entre el ${a} y el ${b}: un hueco en el archivo de la misión, no un período seco.`,
    chart_rain_tip: (a, b) => `Tormenta: del ${a} al ${b}`,
    chart_pt: (d, p) => `${d}: ${p} % sigue mojado`,
    chart_pt_windy: (d, p, v) => `${d}: ${p} % sigue mojado · pasada con viento (${v} m/s), confianza menor`,
    chart_key: "Punto hueco: pasada con viento, confianza menor.",

    s4_eyebrow: "Dónde actuar primero",
    s4_title: "Dónde se quedó más tiempo el agua",
    dry_calc: (m) => `Cómo se calcula: dividimos la zona en celdas de unos ${m} m. Para cada celda contamos los días entre la primera pasada que la vio mojada y las primeras que la vieron seca otra vez. Cuanto más tiempo estuvo mojada, más oscura se ve en el mapa.`,
    dry_half: (d1, d2, w1, w2) => `La mitad de la tierra inundada se secó recién entre el ${d1} y el ${d2}, ${w1} a ${w2} semanas después de la tormenta.`,
    s4_how: (d) => `<p>Los días salen de las fechas de las pasadas, así que tienen la precisión de una revisita. Contado campo por campo, desde que cada uno se vio mojado, un campo inundado típico estuvo unos ${d} días bajo agua; las fechas de la mitad seca se refieren a toda el área inundada desde la tormenta.</p>`,
    ex_title: "Un ejemplo",
    ex_body: (n, km) => `El mismo recorte de ${km} km en las primeras ${n} pasadas después de la tormenta (naranja: agua detectada). Un lugar que sigue mojado pasada tras pasada queda rojo oscuro en el mapa de secado.`,
    ex_days: "Días bajo agua",
    tap_hint: "Tocá el mapa para ver cuánto tiempo estuvo un lugar bajo agua.",
    place_days: (d, w) => (w ? `Unos ${d} días bajo agua, más o menos ${w} semanas.` : `Unos ${d} días bajo agua.`),
    place_days_min: (d, w) => (w ? `Al menos ${d} días bajo agua (más de ${w} semanas) y seguía mojado al final.` : `Al menos ${d} días bajo agua.`),
    place_dates: (a, b) => `Visto mojado por primera vez el ${a}, seco de nuevo el ${b}.`,
    place_first: (a) => `Visto mojado por primera vez el ${a}.`,
    place_share: (p) => `El ${p} % de la tierra alrededor de este punto se inundó.`,
    place_none: "El radar no vio una inundación duradera acá durante la tormenta.",
    place_outside: "Fuera de la zona de estudio: tocá dentro del recuadro punteado.",

    r_eyebrow: "Caminos en zonas inundadas",
    r_title: "Qué caminos pasaban por tierra inundada",
    r_what: "Qué hicimos: cruzamos el mapa de la inundación con la red de caminos rurales de OpenStreetMap. Cada tramo recibe los días que su tierra estuvo bajo agua y el mapa lo pinta según eso: los caminos más oscuros cruzaron tierra que estuvo inundada por más tiempo.",
    r_use: "Para qué podría servir: días después de una tormenta, sin esperar reportes, una intendencia podría ver qué caminos rurales revisar primero, planificar desvíos y saber qué establecimientos pudieron quedar aislados. Esto muestra la idea; no es un conteo de caminos cortados.",
    r_scale: "Días que estuvo inundada la tierra bajo cada camino",
    r_caveat: (m) => `Cada píxel del radar mide unos ${m} m y muchos caminos rurales van sobre terraplenes, así que un camino en una zona inundada no siempre es un camino cortado. Hay que verificarlo en el terreno.`,

    s5_eyebrow: "Lo que sólo ve la banda L",
    s5_title: "Agua que otros satélites no ven",
    tab_grass: "Bajo el pasto y el arroz",
    tab_veg: "Bajo la vegetación",
    s5a_why: "Las ondas de radar rebotan en cosas de su mismo tamaño. Sentinel-1, el radar europeo, usa banda C, una onda de unos pocos centímetros, parecida a las hojas y las briznas de pasto: en un campo inundado rebota en las plantas y no ve el agua de abajo. NISAR usa banda L, una onda varias veces más larga: pasa entre los tallos y llega al agua, que la refleja hacia otro lado como un espejo.",
    s5a_body: "Sobre el agua abierta los dos radares coinciden: mové el divisor. Donde difieren, NISAR suele ver más. Creemos que es agua poco profunda bajo el pasto y el arroz, la forma más común de inundación en estos campos, que es fácil de subestimar.",
    s5_pair_left: (d) => `Sentinel-1 (banda C), ${d}`,
    s5_pair_right: (d) => `NISAR (banda L), ${d}`,
    s5_pair_alt: (d, a, b) => `Deslizador antes y después sobre los mismos campos alrededor del ${d}. Sentinel-1 marca el ${a} % de la vista como agua después de la tormenta; NISAR, el ${b} %.`,
    s5_pair_note: (dt, a, b, km) => `Con ${dt} días de diferencia, mismos campos (${km} km de lado): Sentinel-1 vio agua después de la tormenta en el ${a} % de la vista; NISAR, en el ${b} %.`,
    s5b_why: "Por qué importa: en los bañados y los montes ribereños el agua queda escondida bajo las plantas, pero igual ahoga la pastura, corta el acceso y aleja al ganado. Las fotos y los radares de onda corta ven sobre todo las hojas, así que esa agua no se cuenta.",
    s5b_body: "Por qué NISAR la puede ver: su onda larga atraviesa el follaje, rebota en el agua, pega en los tallos o troncos y vuelve directo. Ese doble rebote hace que la vegetación inundada se vea más brillante. En la zona marcada el radar volvió mucho más brillante después de la tormenta: es la firma del agua debajo de las plantas.",
    veg_left: "Antes de la tormenta (junio y julio)",
    veg_right: (d) => `Después de la tormenta, ${d}`,
    veg_alt: (d) => `Deslizador antes y después de vegetación junto a un arroyo: dentro de los contornos verdes la señal del radar pasa de oscura a clara después de la tormenta (${d}).`,
    veg_key: "Más claro es más rebote entre agua y tallos. Contorno verde: vegetación con agua debajo (monte o bañado). Azul: agua antes de la tormenta.",

    bal_eyebrow: "Balance",
    bal_title: "Un análisis prometedor, con trabajo por delante",
    bal_lede: "En Rocha norte los resultados son prometedores y coinciden en parte con otras fuentes. Todavía no están lo bastante validados como para usarlos con confianza, y llevar el método a todo el país requiere más trabajo.",
    bal_ok_t: "Lo que se ve prometedor",
    ok_s1_t: "Otro radar ve un agua parecida",
    ok_s1: (r, n) => `Donde Sentinel-1, el radar europeo, vio agua después de la tormenta, NISAR encontró el ${r} % de esa agua. Son sólo ${n} comparaciones.`,
    ok_orbit_t: "Dos órbitas de NISAR coinciden",
    ok_orbit: (j, n) => `Dos pasadas con un día de diferencia, desde ángulos distintos, marcaron en gran parte la misma agua: un puntaje de acuerdo de ${j} sobre uno (${n} pares).`,
    ok_press_t: "Mismo orden que lo reportado",
    ok_press: "NISAR midió más que las cifras de prensa, lo que es coherente con un área más grande y con el agua poco profunda entre el pasto que a simple vista no se nota.",
    ok_noise_t: "La señal se destaca",
    ok_noise: (x) => `Lo inundado es ${x} veces lo que el detector marca por error en días secos.`,
    ok_known_t: "Reconoce el agua que ya conocemos",
    ok_known: (p) => `De las lagunas, lagos y bañados que un registro global ve como agua desde hace décadas, NISAR marca el ${p} % como agua permanente.`,
    bal_todo_t: "Lo que todavía no está resuelto",
    todo_wind_t: "El viento esconde agua",
    todo_wind: (k, n) => `En ${k} de las ${n} pasadas de la tormenta había viento, y el viento hace que el agua se vea menos. Esas fechas están marcadas, no corregidas.`,
    todo_low_t: "Quedan afuera los campos más bajos",
    todo_low: (h) => `La tierra ya inundada antes de la tormenta (${h} ha) queda afuera. Suelen ser los campos más bajos, que se secan último, así que el secado puede parecer más rápido.`,
    todo_till_t: "Los campos arados parecen agua",
    todo_till: "En octubre, las chacras aradas se ven tan oscuras como el agua, así que desde entonces no leemos las zonas de cultivo ni sabemos cuándo se secaron.",
    todo_out_t: "Una órbita quedó afuera",
    todo_out: (p) => `Una de las tres órbitas veía sólo el ${p} % de esa agua y marcaba agua previa que las otras no veían, así que la dejamos afuera: quedan menos pasadas para medir el secado.`,
    todo_orbit_t: "Una órbita ve mucho menos",
    todo_orbit: (p) => `Una órbita marca como permanente sólo el ${p} % de esa agua conocida, así que sus pasadas son menos confiables cerca de lagunas y bañados.`,
    todo_sea_t: "El mar queda afuera",
    todo_sea: "Con el mar calmo, parte del océano parecía agua nueva, así que lo excluimos. No afecta a los campos, pero muestra cuánto puede engañar el agua calma.",
    todo_veg_t: "Monte y bañado se confunden",
    todo_veg: "La señal de agua bajo los árboles también se enciende en bañados con pasto alto; todavía no los separamos bien.",
    todo_half_t: "La fecha de mitad seca está al límite",
    todo_half: (d, p, n) => `El ${d} seguía mojado el ${p} % de la tierra inundada, apenas menos de la mitad. Con un detector un poco distinto, la mitad seca podría pasar a la pasada siguiente, ${n} días después.`,
    todo_val_t: "Los tiempos de secado no están validados",
    todo_val: "Sentinel-1 se compara pasada a pasada; la curva de secado todavía no tiene un control independiente y, con pasadas cada algunos días, las duraciones son rangos.",
    bal_sum: (m, rb, tt) => `También miramos otras tres zonas, abiertas en el explorador (sus cifras no están validadas): la Laguna Merín (${m} ha inundadas), donde el viento corrigió cómo se leía la laguna; Río Branco / Yaguarón (${rb} ha), donde el resultado se ve más prometedor; y Treinta y Tres (${tt} ha), donde el río Olimar no se ve como agua por la vegetación de sus orillas. En las ciudades NISAR cuenta tierra, no personas, y los datos llegan días después: sirve para la respuesta, no para la alerta temprana. Próximos pasos: normalizar la señal entre órbitas para una línea temporal más completa y mejorar la detección con aprendizaje automático.`,
    s7_body: "NISAR pasa sobre todo Uruguay cada pocos días y sus datos son gratuitos. Con el método ajustado y validado, cada alerta de lluvia podría venir acompañada, días después, de un mapa de dónde quedó el agua y cuánto tiempo se queda.",
    uses_title: "Para qué podría servir",
    uses: [
      ["SINAE / CECOED", "Mandar ayuda e inspecciones primero a los lugares que siguen mojados más tiempo."],
      ["Intendencias", "Planificar arreglos de caminos rurales según cuánto tiempo estuvo inundado cada uno."],
      ["MGAP · productores · seguros", "Respaldar ayudas y reclamos con un mapa fechado de los campos inundados."],
      ["DINAGUA · INUMET", "Ver qué lluvia dejó agua en el suelo y qué cuencas drenan más lento."],
    ],
    lk_method: "Cómo lo hicimos",
    lk_code: "Código",
    cta_explore: "¿Querés mirarlo por tu cuenta? Explorá los mapas de radar de Rocha norte y de otras tres zonas.",
    cta_explore_btn: "Explorar el mapa",

    zonas: { merin_arrozales: "Arrozales de la Laguna Merín", rocha_norte: "Rocha norte" },
  },
};
const REPO = "https://github.com/kevcst/floodtracer";

(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  // ---------- language (owned by the shared menu, nav.js): English unless ?lang=es ----------
  let lang = (window.SiteNav && window.SiteNav.lang) || new URLSearchParams(location.search).get("lang") || "en";
  if (!STRINGS[lang]) lang = "en";
  const t = (k, ...a) => { const v = STRINGS[lang][k] ?? STRINGS.en[k]; return typeof v === "function" ? v(...a) : (v ?? k); };
  const locale = () => (lang === "es" ? "es-UY" : "en-US");
  const nf = (v, d = 0) => (v == null || isNaN(v) ? "–" : new Intl.NumberFormat(locale(), { maximumFractionDigits: d, minimumFractionDigits: d }).format(v));
  const monthYear = (s) => new Date(s + "T12:00:00Z").toLocaleDateString(lang === "es" ? "es-UY" : "en-GB", { month: "long", year: "numeric", timeZone: "UTC" });
  const pct = (v, d = 0) => (lang === "es" ? `${nf(v, d)} %` : `${nf(v, d)}%`);
  const fdate = (s, long) => new Date(s + "T12:00:00Z").toLocaleDateString(lang === "es" ? "es-UY" : "en-GB",
    long ? { day: "numeric", month: "long", timeZone: "UTC" } : { day: "numeric", month: "short", timeZone: "UTC" });
  const days = (a, b) => (Date.parse(b) - Date.parse(a)) / 864e5;

  function showError(msg) { const e = $("#err"); e.textContent = msg; e.style.display = "block"; }
  window.addEventListener("error", (e) => showError(t("broke", e.message)));
  if (location.protocol === "file:") showError(t("file_proto"));

  // ---------- state ----------
  let M, Z, CZ, map, mapReady = false, scene = null, curKey = null;
  const renders = [];             // functions re-run on language change
  const onLang = (fn) => { renders.push(fn); fn(); };
  const zn = (z) => (STRINGS[lang].zonas || {})[z] || Z[z].nombre;
  const lastPass = (z) => { const f = Z[z].capas.serie.fechas; return f[f.length - 1]; };
  const R = () => Z[CZ].resumen;
  const EV = () => Z[CZ].evento || M.evento;

  function applyStatic() {
    document.documentElement.lang = lang;
    document.title = t("title");
    $$("[data-i18n]").forEach((n) => { n.textContent = t(n.dataset.i18n); });
    $$("[data-i18n-html]").forEach((n) => { n.innerHTML = t(n.dataset.i18nHtml); });   // trusted: STRINGS only
    $$("[data-i18n-aria]").forEach((n) => { n.setAttribute("aria-label", t(n.dataset.i18nAria)); });
  }
  function setLang(l) {
    if (!STRINGS[l]) return;
    lang = l;
    applyStatic(); renders.forEach((fn) => fn());
    if (scene) enterScene(scene, true, curKey);
    navUpdate();
  }
  window.addEventListener("site-lang", (e) => setLang(e.detail));
  applyStatic();

  // heat-map colour ramp (density → colour), identical to the explorer's drying map
  const HEAT_RAMP = [[0, "rgba(255,237,160,0)"], [0.15, "rgba(255,237,160,0.6)"], [0.35, "#fdae61"], [0.55, "#f46d43"], [0.75, "#d73027"], [1, "#67001f"]];
  const FOREST = "rgb(27,175,122)";   // same green as monte.png (exportar_app.MONTE)

  // ---------- geometry helpers ----------
  const img = (z, f) => `data/${z}/${f}`;
  const bboxOf = (pts) => { const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]); return [[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]]; };
  const zoneBox = (z) => { const b = M.contexto.zonas[z]; return [[b[0], b[1]], [b[2], b[3]]]; };
  const grow = (b, k) => { const cx = (b[0][0] + b[1][0]) / 2, cy = (b[0][1] + b[1][1]) / 2, dx = (b[1][0] - b[0][0]) * k / 2, dy = (b[1][1] - b[0][1]) * k / 2;
    return [[cx - dx, cy - dy], [cx + dx, cy + dy]]; };
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const isMobile = () => matchMedia("(max-width: 760px)").matches;
  function padding() {
    const card = $(".step.active"), bar = 56, navH = 72;
    if (isMobile() || !card) return { top: bar + 12, bottom: navH, left: 16, right: 16 };
    return { top: bar + 16, bottom: 40, left: Math.min(card.getBoundingClientRect().right + 24, innerWidth - 200), right: 32 };
  }

  // ---------- map ----------
  function maplibreReady() {
    if (window.maplibregl) return Promise.resolve(true);
    const el = document.getElementById("maplibre-js");
    return new Promise((res) => { el.addEventListener("load", () => res(true)); el.addEventListener("error", () => res(false)); });
  }
  async function initMap() {
    if (!(await maplibreReady())) { showError(t("no_map")); return; }
    map = new maplibregl.Map({
      container: "map", attributionControl: { compact: true }, interactive: true, cooperativeGestures: true, maxZoom: 15,
      style: { version: 8, sources: { base: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, maxzoom: 19, attribution: "© OpenStreetMap contributors" } },
        layers: [{ id: "base", type: "raster", source: "base", paint: { "raster-saturation": -0.7, "raster-opacity": 0.85 } }] },
      bounds: bboxOf(Z[CZ].capas.serie.esquinas), fitBoundsOptions: { padding: padding() },
    });
    map.scrollZoom.disable();
    window.__storyMap = map;   // handle for automated checks and the browser console
    return new Promise((res) => map.on("load", () => {
      const zs = Z[CZ].capas.serie, f0 = peakDate();
      Object.assign(imgState, { z: CZ, f: f0 });
      map.addSource("hh", { type: "image", url: img(CZ, `hh_${f0}.webp`), coordinates: zs.esquinas });
      map.addLayer({ id: "hh", type: "raster", source: "hh", paint: { "raster-opacity": 0.95, "raster-fade-duration": 0 } });
      map.addSource("agua", { type: "image", url: img(CZ, `agua_${f0}.png`), coordinates: zs.esquinas });
      map.addLayer({ id: "agua", type: "raster", source: "agua", paint: { "raster-opacity": 0.95, "raster-fade-duration": 0 } });
      map.addSource("ctx", { type: "image", url: img(CZ, "extension.png"), coordinates: Z[CZ].capas.evento.esquinas });
      Object.assign(ctxState, { url: img(CZ, "extension.png") });
      map.addLayer({ id: "ctx", type: "raster", source: "ctx", layout: { visibility: "none" }, paint: { "raster-opacity": 0.95, "raster-fade-duration": 0 } });
      const b = M.contexto.zonas[CZ];
      map.addSource("areas", { type: "geojson", data: { type: "Feature", properties: {},
        geometry: { type: "Polygon", coordinates: [[[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]], [b[0], b[1]]]] } } });
      // only the case-study area; hidden until a slide asks for it
      map.addLayer({ id: "areas", type: "line", source: "areas", layout: { visibility: "none" },
        paint: { "line-color": css("--flood-map"), "line-width": 1.6, "line-dasharray": [2, 1.5] } });
      map.addSource("box", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({ id: "box", type: "line", source: "box", layout: { visibility: "none" }, paint: { "line-color": "#ffffff", "line-width": 3 } });
      map.addLayer({ id: "box-in", type: "line", source: "box", layout: { visibility: "none" }, paint: { "line-color": css("--flood-map"), "line-width": 1.5, "line-dasharray": [2, 1] } });
      map.on("click", (e) => { if (scene === "dry") placeAt(e.lngLat); });
      sourceLoaded(["hh", "agua", "ctx"]).then(() => { mapReady = true; res(); });
    }));
  }
  // Image swaps are serialized: MapLibre aborts (and logs) an in-flight image load if updateImage is called again.
  const preloaded = new Map();
  const preload = (url) => { if (!preloaded.has(url)) { const im = new Image(); im.src = url; preloaded.set(url, im.decode().catch(() => null)); } return preloaded.get(url); };
  const imgState = { z: null, f: null, want: null, busy: false };
  function sourceLoaded(ids) {
    return new Promise((res) => {
      const left = new Set(ids), done = () => { map.off("sourcedata", on); clearTimeout(to); res(); };
      const on = (e) => { if (left.has(e.sourceId) && e.isSourceLoaded) { left.delete(e.sourceId); if (!left.size) done(); } };
      const to = setTimeout(done, 3000);
      map.on("sourcedata", on);
    });
  }
  async function pump() {
    if (imgState.busy) return;
    imgState.busy = true;
    while (imgState.want && (imgState.want.z !== imgState.z || imgState.want.f !== imgState.f)) {
      const { z, f } = imgState.want, e = Z[z].capas.serie.esquinas;
      await Promise.all([preload(img(z, `hh_${f}.webp`)), preload(img(z, `agua_${f}.png`))]);
      if (imgState.want.z !== z || imgState.want.f !== f) continue;
      const loaded = sourceLoaded(["hh", "agua"]);
      map.getSource("hh").updateImage({ url: img(z, `hh_${f}.webp`), coordinates: e });
      map.getSource("agua").updateImage({ url: img(z, `agua_${f}.png`), coordinates: e });
      await loaded;
      Object.assign(imgState, { z, f });
    }
    imgState.busy = false;
  }
  function showPass(z, fecha) { if (!mapReady) return; imgState.want = { z, f: fecha }; pump(); }
  const ctxState = { url: null, want: null, busy: false };
  async function ctxPump() {
    if (ctxState.busy) return;
    ctxState.busy = true;
    while (ctxState.want && ctxState.want.url !== ctxState.url) {
      const { url, corners } = ctxState.want;
      await preload(url);
      if (ctxState.want.url !== url) continue;
      const loaded = sourceLoaded(["ctx"]);
      map.getSource("ctx").updateImage({ url, coordinates: corners });
      await loaded;
      ctxState.url = url;
    }
    ctxState.busy = false;
  }
  function showCtx(url, corners) { if (!mapReady) return; ctxState.want = { url, corners }; ctxPump(); }
  // drying heat map (~2 MB of GeoJSON): added only when its slide is first shown
  function ensureHeat() {
    if (!mapReady || map.getSource("secado")) return;
    map.addSource("secado", { type: "geojson", data: M.secado.archivo });
    const wmax = Math.max(1, M.secado.w_max), only = ["==", ["get", "z"], CZ];
    map.addLayer({ id: "heat", type: "heatmap", source: "secado", maxzoom: 13, filter: only, layout: { visibility: "none" }, paint: {
      "heatmap-weight": ["min", 1, ["/", ["get", "w"], wmax]],
      "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 6, 0.22, 8, 0.4, 10, 0.8, 12, 1.5],
      "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 6, 5, 8, 9, 10, 16, 12, 32],
      "heatmap-opacity": ["interpolate", ["linear"], ["zoom"], 11, 0.9, 13, 0.5],
      "heatmap-color": ["interpolate", ["linear"], ["heatmap-density"], ...HEAT_RAMP.flatMap(([s, c]) => [s, c])] } }, "box");
    map.addLayer({ id: "cells", type: "circle", source: "secado", minzoom: 11, filter: only, layout: { visibility: "none" }, paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 11, 3, 14, 9],
      "circle-color": ["interpolate", ["linear"], ["get", "d"], 0, "#fee090", 7, "#fdae61", 14, "#f46d43", 28, "#d73027", 42, "#67001f"],
      "circle-opacity": 0.85, "circle-stroke-width": 0.5, "circle-stroke-color": "#fff" } }, "box");
  }
  // rural roads coloured by days the land under them stayed flooded (explorer palette, manifest day ranges)
  const ROAD_PALETTE = ["#f1e7ff", "#dac2ff", "#b68aff", "#8e54ee", "#6430bd"];   // = explorer.html roadPalette()
  const roadSteps = () => M.leyendas.persistencia.map((b) => parseInt(b.rango, 10));  // range starts, e.g. "8–14" → 8
  function ensureRoads() {
    if (!mapReady || map.getSource("roads")) return;
    map.addSource("roads", { type: "geojson", data: "data/impacto/caminos.geojson" });
    const st = roadSteps(), color = ["step", ["get", "dias_mid"], ROAD_PALETTE[0]];
    st.slice(1).forEach((v, k) => color.push(v, ROAD_PALETTE[k + 1]));
    const only = ["all", ["==", ["get", "zona"], CZ], [">", ["get", "dias_mid"], 0]];
    const w = (x) => ["interpolate", ["linear"], ["zoom"], 8, 2 + x, 13, 5 + x];
    map.addLayer({ id: "roads-case", type: "line", source: "roads", filter: only, layout: { visibility: "none", "line-cap": "round" }, paint: { "line-color": "#171321", "line-width": w(3) } }, "box");
    map.addLayer({ id: "roads", type: "line", source: "roads", filter: only, layout: { visibility: "none", "line-cap": "round" }, paint: { "line-color": color, "line-width": w(0) } }, "box");
  }
  const LAYERS = ["hh", "agua", "areas", "heat", "cells", "ctx", "box", "box-in", "roads-case", "roads"];
  function layers(on) {
    if (!mapReady) return;
    if (on.includes("heat")) ensureHeat();
    if (on.includes("roads")) { ensureRoads(); on = [...on, "roads-case"]; }
    if (on.includes("box")) on = [...on, "box-in"];
    for (const id of LAYERS) if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", on.includes(id) ? "visible" : "none");
    map.setPaintProperty("ctx", "raster-opacity", on.includes("roads") ? 0.7 : 0.95);
  }
  function showBox(corners) {
    if (!mapReady) return;
    map.getSource("box").setData({ type: "FeatureCollection", features: corners ? [{ type: "Feature", properties: {},
      geometry: { type: "Polygon", coordinates: [[...corners, corners[0]]] } }] : [] });
  }
  let lastBounds = null;
  function fly(bounds) { lastBounds = bounds; if (map) map.fitBounds(bounds, { padding: padding(), duration: reduced ? 0 : 1400, essential: true }); }
  let pop = null;
  function popup(ll, html) { if (pop) pop.remove(); pop = new maplibregl.Popup({ closeButton: true, maxWidth: "300px", className: "story-pop" }).setLngLat(ll).setHTML(html).addTo(map); }

  // ---------- legends: one label per layer, the same on every slide ----------
  const row = (color, text) => `<div class="row"><span class="sw" style="background:${color}"></span>${esc(text)}</div>`;
  const dash = (color, text) => `<div class="row"><span class="sw" style="background:transparent;border:2px dashed ${color}"></span>${esc(text)}</div>`;
  const LG = {
    base: () => row(css("--still"), t("lg_base")),
    after: () => row(css("--flood-map"), t("lg_after")),
    after2: () => row(css("--flood-map"), t("lg_after2")),
    wet: () => row(M.leyendas.previa, t("lg_wet")),
    radar: () => `<div class="row"><span class="sw" style="background:linear-gradient(90deg,#111,#ddd)"></span>${esc(t("lg_radar"))}</div>`,
    area: () => dash(css("--flood-map"), t("lg_area")),
  };
  function roadScale() {
    return `<div class="road-scale">${M.leyendas.persistencia.map((b, k) => `<span><i style="background:${ROAD_PALETTE[k]}"></i>${esc(b.rango)}</span>`).join("")}</div>`;
  }
  function heatScale() {
    const grad = HEAT_RAMP.filter(([s]) => s > 0).map(([s, c]) => `${c} ${Math.round(100 * s)}%`).join(","), d = (M.secado.dias || {})[CZ] || {};
    return `<div class="ramp" style="background:linear-gradient(90deg,${grad})"></div><div class="ramp-labels"><span>${esc(t("lg_dmin", nf(d.min)))}</span><span>${esc(t("lg_dmax", nf(d.max)))}</span></div>`;
  }
  function legend(kind) {
    const L = $("#legend");
    if (kind === "pass") L.innerHTML = LG.after() + LG.base() + (R().ha_previa ? LG.wet() : "") + LG.radar();
    else if (kind === "extent") L.innerHTML = LG.after2() + LG.wet() + LG.area();
    else if (kind === "heat") L.innerHTML = `<div class="row"><b>${esc(t("lg_days"))}</b></div>` + heatScale() + LG.area();
    else if (kind === "veg") L.innerHTML = row(FOREST, t("lg_veg")) + LG.base();
    else if (kind === "roads") L.innerHTML = LG.after2() + LG.wet() + `<div class="row"><b>${esc(t("lg_roads"))}</b></div>` + roadScale();
    else L.innerHTML = "";
  }
  const stamp = (txt) => { $("#stamp").textContent = txt || ""; };

  // ---------- map state per slide ----------
  const peakDate = () => { const f = Z[CZ].fechas.filter((p) => p.remaining != null); return f.reduce((a, p) => (p.remaining > a.remaining ? p : a), f[0]).fecha; };
  const firstAfterRain = (z) => { const ev = Z[z].evento || M.evento; return Z[z].capas.serie.fechas.find((f) => f >= ev.lluvia[0]); };
  const evBox = () => bboxOf(Z[CZ].capas.evento.esquinas);
  let lbTab = "lb-grass";
  const SCENES = {
    hero() { layers(["hh", "agua"]); showPass(CZ, peakDate()); fly(bboxOf(Z[CZ].capas.serie.esquinas)); legend("pass"); stamp(""); },
    blind() { const f = firstAfterRain(CZ), o = (M.contexto.optico || {})[CZ]; layers(["hh", "agua", "box"]); showPass(CZ, f); showBox(o && o.esquinas);
      fly(bboxOf(Z[CZ].capas.serie.esquinas)); legend("pass"); stamp(t("stamp_pass", fdate(f), zn(CZ))); },
    count() { layers(["ctx", "areas"]); showCtx(img(CZ, "extension.png"), Z[CZ].capas.evento.esquinas); fly(evBox()); legend("extent"); stamp(zn(CZ)); },
    stays() { layers(["hh", "agua"]); fly(bboxOf(Z[CZ].capas.serie.esquinas)); legend("pass"); player.show(); },
    dry() { const e = M.contexto.secado_ejemplo; layers(["heat", "cells", "areas", "box"]); showBox(e && e.esquinas); fly(zoneBox(CZ)); legend("heat"); stamp(t("tap_hint")); },
    roads() { layers(["ctx", "roads", "areas"]); showCtx(img(CZ, "extension.png"), Z[CZ].capas.evento.esquinas); fly(zoneBox(CZ)); legend("roads"); stamp(zn(CZ)); },
    lband() { (lbTab === "lb-veg" ? SCENES.veg : SCENES.grass)(); },
    grass() { const p = M.contexto.s1_vs_nisar; if (!p) return SCENES.count();
      layers(["ctx", "areas", "box"]); showCtx(p.nisar, p.esquinas); showBox(p.esquinas); fly(grow(bboxOf(p.esquinas), 1.4)); legend("pass"); stamp(t("stamp_pass", fdate(p.fecha_nisar), zn(CZ))); },
    veg() { const mc = M.contexto.monte_caso; layers(["ctx", "areas", "box"]); showCtx(img(CZ, "monte.png"), Z[CZ].capas.evento.esquinas); showBox(mc && mc.esquinas);
      fly(mc ? grow(bboxOf(mc.esquinas), 5) : evBox()); legend("veg"); stamp(zn(CZ)); },
    balance() { layers(["ctx"]); showCtx(img(CZ, "extension.png"), Z[CZ].capas.evento.esquinas); fly(evBox()); legend("none"); stamp(""); },
  };
  function enterScene(id, force, step) {
    const key = step && SCENES[step] ? step : id;
    if (key === curKey && !force) return;
    if (pop && id !== scene) { pop.remove(); pop = null; }
    scene = id; curKey = key;
    (SCENES[key] || SCENES.balance)();
    if (id === "count") countUp();
  }

  /* ---------- tabs ---------- */
  function initTabs() {
    $$(".tabs").forEach((bar) => bar.querySelectorAll("[role=tab]").forEach((b) => b.addEventListener("click", () => {
      bar.querySelectorAll("[role=tab]").forEach((x) => {
        const on = x === b; x.setAttribute("aria-selected", String(on));
        const panel = document.getElementById(x.dataset.tab); if (panel) panel.hidden = !on;
        const text = document.getElementById(x.dataset.tab + "-text"); if (text) text.hidden = !on;
      });
      if (b.dataset.tab.startsWith("lb-")) { lbTab = b.dataset.tab; SCENES.lband(); }
    })));
  }

  /* ---------- slides ---------- */
  let slides = [], cur = 0;
  const slideTitle = (s) => (s.querySelector(s.dataset.toc === "eyebrow" ? ".eyebrow" : "h1, h2") || s).textContent.trim();
  function go(k, push = true) {
    k = Math.max(0, Math.min(slides.length - 1, k));
    slides.forEach((s, i) => { s.classList.toggle("active", i === k); s.setAttribute("aria-hidden", String(i !== k)); s.inert = i !== k; });
    cur = k;
    const s = slides[k];
    if (push) history.replaceState(null, "", `${location.search}#${s.id}`);
    enterScene(s.dataset.scene, false, s.dataset.step);
    navUpdate();
  }
  function navUpdate() {
    if (!slides.length) return;
    $("#prev").textContent = "◀ " + t("prev"); $("#next").textContent = t("next") + " ▶";
    $("#prev").disabled = cur === 0; $("#next").disabled = cur === slides.length - 1;
    $("#toc-btn").textContent = t("toc_label", nf(cur + 1), nf(slides.length), slideTitle(slides[cur])) + " ▾";
    $("#toc-btn").setAttribute("aria-label", t("toc"));
    $("#toc-list").innerHTML = slides.map((s, i) => `<li><button type="button" data-k="${i}"${i === cur ? ' aria-current="step"' : ""}>${esc(slideTitle(s))}</button></li>`).join("");
    $$("#toc-list button").forEach((b) => b.addEventListener("click", () => { toc(false); go(+b.dataset.k); }));
    $("#progress").style.width = (100 * (cur + 1) / slides.length) + "%";
    document.body.classList.toggle("on-hero", cur === 0);
    // the opening card lists the parts of the tour (from the slides themselves)
    $("#hero-toc").innerHTML = slides.slice(1).map((s, i) => `<li><button type="button" data-k="${i + 1}">${esc(slideTitle(s))}</button></li>`).join("");
    $$("#hero-toc button").forEach((b) => b.addEventListener("click", () => go(+b.dataset.k)));
  }
  function toc(open) { $("#toc-list").hidden = !open; $("#toc-btn").setAttribute("aria-expanded", String(open)); }
  function initSlides() {
    slides = $$("#story .step");
    $$("[data-go]").forEach((b) => b.addEventListener("click", () => go(cur + (b.dataset.go === "next" ? 1 : -1))));
    $("#toc-btn").addEventListener("click", () => toc($("#toc-list").hidden));
    document.addEventListener("click", (e) => { if (!e.target.closest(".sn-menu")) toc(false); });
    addEventListener("keydown", (e) => {
      if (e.target.closest("input, textarea, select") || e.metaKey || e.ctrlKey || e.altKey) return;
      if (["ArrowRight", "PageDown"].includes(e.key)) { e.preventDefault(); go(cur + 1); }
      if (["ArrowLeft", "PageUp"].includes(e.key)) { e.preventDefault(); go(cur - 1); }
      if (e.key === "Home") go(0);
      if (e.key === "End") go(slides.length - 1);
      if (e.key === "Escape") toc(false);
    });
    addEventListener("hashchange", () => { const k = slides.findIndex((s) => "#" + s.id === location.hash); if (k >= 0 && k !== cur) go(k, false); });
    addEventListener("resize", () => { if (scene) enterScene(scene, true, curKey); });
    const k = slides.findIndex((s) => "#" + s.id === location.hash);
    go(k >= 0 ? k : 0, false);
  }

  onLang(() => { $("#reset-view").textContent = t("reset_view"); });
  $("#reset-view").addEventListener("click", () => { if (lastBounds) fly(lastBounds); });

  /* ---------- SwipeCompare ---------- */
  function swipe(host, left, right, alt) {
    host.insertAdjacentHTML("beforeend", `<figure class="swipe" role="group"><div class="sw-frame">
        <img class="sw-r" alt="" src="${esc(right.src)}"><img class="sw-l" alt="" src="${esc(left.src)}">
        <span class="sw-line"></span><span class="sw-tag l">${esc(left.label)}</span><span class="sw-tag r">${esc(right.label)}</span></div>
      <input type="range" class="sw-range"><figcaption class="sr-only"></figcaption></figure>`);
    const fig = host.querySelector("figure.swipe:last-of-type"), frame = fig.querySelector(".sw-frame"), rng = fig.querySelector(".sw-range");
    fig.setAttribute("aria-label", alt); fig.querySelector("figcaption").textContent = alt;
    Object.assign(rng, { min: 0, max: 100, step: 1, value: 50 });
    rng.setAttribute("aria-label", t("swipe_handle"));
    const set = (v) => { frame.style.setProperty("--x", v + "%"); rng.value = v; };
    rng.addEventListener("input", () => set(+rng.value));
    let drag = false;
    const at = (e) => { const b = frame.getBoundingClientRect(); set(Math.max(0, Math.min(100, Math.round(100 * (e.clientX - b.left) / b.width)))); };
    frame.addEventListener("pointerdown", (e) => { drag = true; frame.setPointerCapture(e.pointerId); at(e); });
    frame.addEventListener("pointermove", (e) => { if (drag) at(e); });
    frame.addEventListener("pointerup", () => { drag = false; });
    set(50);
  }

  /* ---------- 0 · opening card ---------- */
  function buildHero() {
    onLang(() => {
      $("#hero-sub").textContent = t("subtitle", zn(CZ));
      $("#hero-what").textContent = t("hero_what", zn(CZ), monthYear(EV().lluvia[0]));
      $("#hero-cap").textContent = t("hero_cap", zn(CZ), fdate(peakDate(), true));
    });
  }

  /* ---------- 1 · optical vs radar ---------- */
  function buildBlind() {
    onLang(() => {
      const o = (M.contexto.optico || {})[CZ];
      $("#blind-anchor").textContent = t("s1_anchor", fdate(firstAfterRain(CZ), true));
      $("#swipe-host").innerHTML = ""; $("#blind-note").textContent = "";
      if (!o) return;
      const cat = o.catalogo.map((c) => t("s1_cat_item", fdate(c.fecha), nf(c.nubes))).join(" · ");
      if (o.optico) swipe($("#swipe-host"), { src: o.optico, label: t("s1_swipe_left", fdate(o.fecha_s2)) }, { src: o.nisar, label: t("s1_swipe_right", fdate(o.fecha_nisar)) },
        t("s1_swipe_alt", fdate(o.fecha_s2, true), fdate(o.fecha_nisar, true)));
      else $("#swipe-host").innerHTML = `<p class="placeholder">${esc(t("s1_no_optical", fdate(o.buscado[0], true), fdate(o.buscado[1], true)))}</p>`;
      $("#blind-note").textContent = cat ? t("s1_catalog", fdate(o.buscado[0], true), fdate(o.buscado[1], true), cat) : "";
    });
  }

  /* ---------- 2 · reported vs measured ---------- */
  let counted = false;
  const LANDUSE = ["Grassland", "Herbaceous wetland", "Cropland (rice)"];   // WorldCover classes that flood in the case zone
  function buildCount() {
    onLang(() => {
      const r = R(), pr = M.contexto.prensa_caso;
      $("#count-intro").textContent = t("count_intro", fdate(pr.fecha, true), pr.lugar);
      const num = (v) => `<span data-to="${v}">${esc(nf(counted || reduced ? v : 0, v % 1 ? 1 : 0))}</span>`;
      const card = (cls, big, label, src) => `<div class="counter ${cls}"><div class="big">${big}</div><div class="big-label">${esc(label)}</div><p class="note">${esc(src)}</p></div>`;
      $("#counters").innerHTML = `<div class="counters three">` +
        card("press", esc(t("c_press_ha", nf(pr.ha_min), nf(pr.ha_max))), t("c_press_ha_l"), t("c_press_src", pr.fuentes.join(", "))) +
        card("press", num(pr.vacunos), t("c_cattle_l"), "") +
        card("land", num(r.ha_inundada), t("c_nisar_l"), t("c_nisar_src")) + `</div>`;
      $("#count-why").textContent = t("count_why");
      const us = Z[CZ].uso_suelo.filter((u) => LANDUSE.includes(u.clase)).sort((a, b) => b.ha_inundada - a.ha_inundada);
      const top = Math.max(...us.map((u) => u.ha_inundada));
      $("#landuse").innerHTML = `<h3 class="mini">${esc(t("lu_title"))}</h3><ul class="bars">` + us.map((u) =>
        `<li><span class="nm">${esc(t("lc")[u.clase] || u.clase)}</span><span class="bbar"><i style="width:${(100 * u.ha_inundada / top).toFixed(1)}%"></i></span><span class="vv">${esc(t("lu_row", nf(u.ha_inundada), nf(u.pct_clase_inundada, 1)))}</span></li>`).join("") + "</ul>";
      $("#count-note").textContent = t("count_note", nf(r.ha_previa));
    });
  }
  function countUp() {
    if (counted) return; counted = true;
    if (reduced) return;
    const els = $$("#counters [data-to]"), t0 = performance.now(), D = 1200;
    const tick = (now) => { const k = Math.min(1, (now - t0) / D), e = 1 - Math.pow(1 - k, 3);
      els.forEach((n) => { const v = +n.dataset.to; n.textContent = nf(v * e, v % 1 ? 1 : 0); }); if (k < 1) requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  }

  /* ---------- 3 · pass by pass ---------- */
  let player = { show() {} };
  function buildStays() {
    const zd = Z[CZ], ev = EV(), all = zd.capas.serie.fechas;
    const dates = all.slice(Math.max(0, all.findIndex((f) => f >= ev.ventana[0]) - 1));   // last dry pass → end
    const byDate = Object.fromEntries(zd.fechas.map((p) => [p.fecha, p]));
    let i = 0;
    function set(k) {
      i = Math.max(0, Math.min(dates.length - 1, k)); const f = dates[i], p = byDate[f];
      $("#pass-date").textContent = fdate(f, true);
      $("#pass-prev").disabled = i === 0; $("#pass-next").disabled = i === dates.length - 1;
      if (scene === "stays") { showPass(CZ, f); stamp(t("stamp_pass", fdate(f), zn(CZ))); }
      $("#stays-big").innerHTML = p.remaining == null
        ? `<div class="big muted">–</div><div class="big-label">${esc(t("s3_before_big"))}</div>`
        : `<div class="big">${esc(pct(p.remaining))}</div><div class="big-label">${esc(t("s3_still"))}</div>`;
      $("#pass-note").innerHTML = esc(p.remaining == null ? t("s3_pass_before", nf(p.v, 1)) : t("s3_pass_new", nf(p.v, 1), nf(p.lo, 1), nf(p.hi, 1))) +
        (p.confianza === "baja" ? `<br><span class="warn">⚠ ${esc(t("s3_windy", nf(p.viento_ms, 1)))}</span>` : "");
      chartCursor(f);
    }
    $("#pass-prev").addEventListener("click", () => set(i - 1));
    $("#pass-next").addEventListener("click", () => set(i + 1));
    player = { show: () => set(i), set: (f) => set(dates.indexOf(f)) };
    onLang(() => {
      $("#s3-body").textContent = t("s3_body", nf(M.cifras.revisita_dias));
      $("#pass-prev").textContent = t("pass_prev"); $("#pass-next").textContent = t("pass_next");
      const after = zd.fechas.filter((p) => p.remaining != null && p.fecha > peakDate() && p.confianza === "normal");
      const a = after[0], b = after[after.length - 1];
      $("#stays-anchor").textContent = a && b && a !== b
        ? t("s3_anchor", fdate(a.fecha, true), nf(days(ev.lluvia[0], a.fecha) / 7), nf(a.remaining), fdate(b.fecha, true), nf(days(ev.lluvia[0], b.fecha) / 30.4), nf(b.remaining)) : "";
      stayChart(dates); set(i);
    });
  }
  const SVGNS = "http://www.w3.org/2000/svg";
  const sv = (tag, attrs, parent) => { const n = document.createElementNS(SVGNS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; };
  let chartX = null;
  function stayChart(dates) {
    const zd = Z[CZ], ev = EV(), W = 460, H = 130, l = 34, r = 10, tp = 8, b = 22;
    const ms = (s) => Date.parse(s), t0 = ms(dates[0]), t1 = ms(dates[dates.length - 1]);
    const x = (s) => l + (Math.min(Math.max(ms(s), t0), t1) - t0) / (t1 - t0) * (W - l - r), y = (v) => tp + (100 - v) / 100 * (H - tp - b);
    const pts = zd.fechas.filter((p) => p.remaining != null && dates.includes(p.fecha));
    const P1 = pts.reduce((a, p) => (p.remaining > a.remaining ? p : a), pts[0]), P2 = pts[pts.length - 1];
    const host = $("#stays-chart"); host.innerHTML = "";
    const svg = sv("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart", role: "img", "aria-label": t("chart_alt", fdate(P1.fecha), nf(P1.remaining), fdate(P2.fecha), nf(P2.remaining)) }, host);
    const pat = sv("pattern", { id: "hatch", width: 6, height: 6, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" }, sv("defs", {}, svg));
    sv("line", { x1: 0, y1: 0, x2: 0, y2: 6, class: "hatch-line" }, pat);
    const gap = sv("rect", { x: x(ev.hueco[0]), y: tp, width: Math.max(0, x(ev.hueco[1]) - x(ev.hueco[0])), height: H - tp - b, fill: "url(#hatch)", class: "gap" }, svg);
    sv("title", {}, gap).textContent = t("chart_gap_tip", fdate(ev.hueco[0], true), fdate(ev.hueco[1], true));
    const rain = sv("rect", { x: x(ev.lluvia[0]), y: tp, width: Math.max(3, x(ev.lluvia[1]) - x(ev.lluvia[0])), height: H - tp - b, class: "rain" }, svg);
    sv("title", {}, rain).textContent = t("chart_rain_tip", fdate(ev.lluvia[0], true), fdate(ev.lluvia[1], true));
    sv("text", { x: x(ev.lluvia[1]) + 4, y: tp + 10, class: "lab" }, svg).textContent = t("chart_rain");
    sv("text", { x: (x(ev.hueco[0]) + x(ev.hueco[1])) / 2, y: H - b - 4, class: "lab", "text-anchor": "middle" }, svg).textContent = t("chart_gap");
    for (const v of [0, 50, 100]) {
      sv("line", { x1: l, x2: W - r, y1: y(v), y2: y(v), class: v ? "grid" : "axis" }, svg);
      sv("text", { x: l - 4, y: y(v) + 3, "text-anchor": "end", class: "tick" }, svg).textContent = pct(v);
    }
    dates.forEach((f, k) => { if (k % 2 === 0 || k === dates.length - 1) sv("text", { x: x(f), y: H - 7, "text-anchor": "middle", class: "tick" }, svg).textContent = fdate(f); });
    sv("path", { d: pts.map((p, k) => (k ? "L" : "M") + x(p.fecha).toFixed(1) + "," + y(p.remaining).toFixed(1)).join(""), class: "line" }, svg);
    for (const p of pts) {
      const windy = p.confianza === "baja";
      const c = sv("circle", { cx: x(p.fecha), cy: y(p.remaining), r: windy ? 5 : 4.5, class: windy ? "dot windy pick" : "dot pick" }, svg);
      sv("title", {}, c).textContent = windy ? t("chart_pt_windy", fdate(p.fecha), nf(p.remaining), nf(p.viento_ms, 1)) : t("chart_pt", fdate(p.fecha), nf(p.remaining));
      c.addEventListener("click", () => player.set(p.fecha));
    }
    sv("line", { class: "cursor", y1: tp, y2: H - b, x1: 0, x2: 0 }, svg);
    if (pts.some((p) => p.confianza === "baja")) host.insertAdjacentHTML("beforeend", `<p class="note">○ ${esc(t("chart_key"))}</p>`);
    chartX = x;
  }
  function chartCursor(f) { const c = $("#stays-chart .cursor"); if (c && chartX) { c.setAttribute("x1", chartX(f)); c.setAttribute("x2", chartX(f)); } }

  /* ---------- 4 · where the water stayed longest ---------- */
  let secado = null;
  function halfDry() {
    const ps = Z[CZ].fechas.filter((p) => p.remaining != null), k = ps.findIndex((p) => p.fecha === peakDate());
    const j = ps.findIndex((p, i) => i > k && p.remaining < 50);
    return j > 0 ? [ps[j - 1].fecha, ps[j].fecha] : null;
  }
  function buildDry() {
    onLang(() => {
      const ev = EV(), h = halfDry();
      $("#dry-calc").textContent = t("dry_calc", nf(M.secado.celda_m));
      $("#dry-half").textContent = h ? t("dry_half", fdate(h[0], true), fdate(h[1], true), nf(days(ev.lluvia[0], h[0]) / 7), nf(days(ev.lluvia[0], h[1]) / 7)) : "";
      $("#dry-how").innerHTML = t("s4_how", nf(R().persist_mid));
      const e = M.contexto.secado_ejemplo, host = $("#dry-example");
      if (!e) { host.innerHTML = ""; return; }
      const grad = e.colores.map((c, k) => `${c.color} ${Math.round(100 * k / (e.colores.length - 1))}%`).join(",");
      host.innerHTML = `<div class="strip">${e.pasadas.map((p) => `<figure><img src="${esc(p.img)}" alt="${esc(t("stamp_pass", fdate(p.fecha, true), zn(CZ)))}"><figcaption>${esc(fdate(p.fecha))}</figcaption></figure>`).join("")}` +
        `<span class="arrow" aria-hidden="true">→</span><figure class="res"><img src="${esc(e.dias)}" alt="${esc(t("ex_days"))}"><figcaption>${esc(t("ex_days"))}</figcaption></figure></div>` +
        `<p class="note">${esc(t("ex_body", nf(e.pasadas.length), nf(e.lado_km)))}</p>`;
    });
  }
  const loadSecado = async () => secado || (secado = (await (await fetch(M.secado.archivo)).json()).features);
  let sonda = null;
  const loadSonda = async () => sonda || (sonda = new Uint8Array(await (await fetch(`data/${CZ}/sonda.bin`)).arrayBuffer()));
  const WET = 50;   // a ~200 m probe cell counts as "wet" on a pass when most of it is water detected after the storm
  async function sondaDates(ll) {
    const d = Z[CZ], s = d.capas.sonda, [tl, tr, , bl] = s.esquinas, ev = EV();
    const ax = tr[0] - tl[0], ay = tr[1] - tl[1], bx = bl[0] - tl[0], by = bl[1] - tl[1], px = ll.lng - tl[0], py = ll.lat - tl[1], det = ax * by - ay * bx;
    const u = (px * by - py * bx) / det, v = (ax * py - ay * px) / det;
    if (u < 0 || u >= 1 || v < 0 || v >= 1) return null;
    const a = await loadSonda(), N = s.ancho * s.alto, idx = Math.floor(v * s.alto) * s.ancho + Math.floor(u * s.ancho);
    const rows = d.capas.serie.fechas.map((f, i) => ({ f, w: a[(2 * i + 1) * N + idx] })).filter((r) => r.f >= ev.tormenta[0] && r.w !== 255);
    const k = rows.findIndex((r) => r.w >= WET);
    if (k < 0) return null;
    const dry = rows.slice(k + 1).find((r) => r.w < WET);
    return { first: rows[k].f, dry: dry ? dry.f : null };
  }
  // tap on the drying map → a tooltip next to the point (no title: it would always be the same area)
  async function placeAt(ll) {
    const out = [], b = M.contexto.zonas[CZ];
    const show = () => popup(ll, out.map((x) => `<p>${esc(x)}</p>`).join(""));
    if (!(ll.lng >= b[0] && ll.lng <= b[2] && ll.lat >= b[1] && ll.lat <= b[3])) { out.push(t("place_outside")); return show(); }
    out.push(t("loading")); show(); out.length = 0;
    const feats = await loadSecado(), kx = Math.cos(ll.lat * Math.PI / 180) * 111320, ky = 110540, lim = M.secado.celda_m * 0.75;
    let best = null, bd = Infinity;
    for (const f of feats) { if (f.properties.z !== CZ) continue; const [x, y] = f.geometry.coordinates, dd = Math.hypot((x - ll.lng) * kx, (y - ll.lat) * ky); if (dd < bd) { bd = dd; best = f; } }
    if (best && bd <= lim) {
      const p = best.properties, w = p.d >= 14 ? (p.s > 0.5 ? Math.floor : Math.round)(p.d / 7) : null;   // lower bound → floor ("over N weeks")
      out.push(t(p.s > 0.5 ? "place_days_min" : "place_days", nf(p.d), w && nf(w)));
      const sd = await sondaDates(ll);
      if (sd) out.push(sd.dry ? t("place_dates", fdate(sd.first, true), fdate(sd.dry, true)) : t("place_first", fdate(sd.first, true)));
      out.push(t("place_share", nf(100 * p.f)));
    } else out.push(t("place_none"));
    if (scene === "dry") show();
  }

  /* ---------- 5 · roads in flooded areas ---------- */
  function buildRoads() {
    onLang(() => {
      $("#roads-scale").innerHTML = `<h3 class="mini">${esc(t("r_scale"))}</h3>` + roadScale();
      $("#roads-caveat").textContent = t("r_caveat", nf((M.metodo || {}).resolucion_m));
    });
  }

  /* ---------- 6 · what only L-band sees ---------- */
  function buildLband() {
    onLang(() => {
      const p = M.contexto.s1_vs_nisar, mc = M.contexto.monte_caso;
      $("#s1-host").innerHTML = ""; $("#forest-host").innerHTML = "";
      if (p) {
        swipe($("#s1-host"), { src: p.s1, label: t("s5_pair_left", fdate(p.fecha_s1)) }, { src: p.nisar, label: t("s5_pair_right", fdate(p.fecha_nisar)) },
          t("s5_pair_alt", fdate(p.fecha_nisar, true), nf(p.pct_s1_ventana, 1), nf(p.pct_nisar_ventana, 1)));
        $("#s1-host").insertAdjacentHTML("beforeend", `<p class="note">${esc(t("s5_pair_note", nf(days(p.fecha_nisar, p.fecha_s1)), nf(p.pct_s1_ventana, 1), nf(p.pct_nisar_ventana, 1), nf(p.lado_km)))}</p>`);
      }
      if (mc) {
        swipe($("#forest-host"), { src: mc.base, label: t("veg_left") }, { src: mc.post, label: t("veg_right", fdate(mc.fecha_post)) }, t("veg_alt", fdate(mc.fecha_post, true)));
        $("#forest-host").insertAdjacentHTML("beforeend", `<p class="note">${esc(t("veg_key"))}</p>`);
      }
    });
  }

  /* ---------- 7 · balance (tabs) ---------- */
  function buildBalance() {
    onLang(() => {
      const v = Z[CZ].validacion, r = R();
      // agua conocida (JRC, sólo valida): la del track de la serie y la peor órbita si queda muy por debajo
      const kw = (v && v.agua_conocida || []).filter((a) => a.pct_detectada != null);
      const used = kw.filter((a) => !a.excluido);
      const known = { serie: kw.find((a) => a.serie), out: kw.find((a) => a.excluido),
        worst: used.reduce((m, a) => (!m || a.pct_detectada < m.pct_detectada ? a : m), null) };
      if (known.worst && known.serie && known.serie.pct_detectada - known.worst.pct_detectada < 20) known.worst = null;
      const card = (cls, icon, title, txt) => `<div class="check ${cls}"><h4>${icon} ${esc(title)}</h4><p>${esc(txt)}</p></div>`;
      $("#bal-ok").innerHTML = (v ? card("ok", "✓", t("ok_s1_t"), t("ok_s1", nf(100 * v.s1_medias.recall), nf(v.s1_medias.n))) : "") +
        (v && v.jaccard_evento != null ? card("ok", "✓", t("ok_orbit_t"), t("ok_orbit", nf(v.jaccard_evento, 2), nf(v.n_pares_evento))) : "") +
        card("ok", "✓", t("ok_press_t"), t("ok_press")) + (r.ha_ruido ? card("ok", "✓", t("ok_noise_t"), t("ok_noise", nf(r.ha_inundada / r.ha_ruido))) : "") +
        (known.serie ? card("ok", "✓", t("ok_known_t"), t("ok_known", nf(known.serie.pct_detectada))) : "");
      const ev = Z[CZ].fechas.filter((p) => p.remaining != null), storm = ev.filter((p) => p.fase === "evento"),
        windy = storm.filter((p) => p.confianza === "baja").length;   // wind: only the storm passes
      // half-dry date at the edge: the first pass under half is within two points of the cut (halfDry, slide 4)
      const hd = halfDry(), hk = hd ? ev.findIndex((p) => p.fecha === hd[1]) : -1;
      const half = hk >= 0 && ev[hk].remaining > 48 && ev[hk + 1] ? { p: ev[hk], n: days(ev[hk].fecha, ev[hk + 1].fecha) } : null;
      $("#bal-todo").innerHTML = (windy ? card("todo", "🛠", t("todo_wind_t"), t("todo_wind", nf(windy), nf(storm.length))) : "") +
        (known.out ? card("todo", "🛠", t("todo_out_t"), t("todo_out", nf(known.out.pct_detectada))) : "") +
        (known.worst ? card("todo", "🛠", t("todo_orbit_t"), t("todo_orbit", nf(known.worst.pct_detectada))) : "") +
        card("todo", "🛠", t("todo_low_t"), t("todo_low", nf(r.ha_previa))) + card("todo", "🛠", t("todo_till_t"), t("todo_till")) +
        card("todo", "🛠", t("todo_sea_t"), t("todo_sea")) + card("todo", "🛠", t("todo_veg_t"), t("todo_veg")) +
        (half ? card("todo", "🛠", t("todo_half_t"), t("todo_half", fdate(half.p.fecha, true), nf(half.p.remaining, 1), nf(half.n))) : "") +
        card("todo", "🛠", t("todo_val_t"), t("todo_val"));
      // the three other areas of the app (explorer.js INFO tells the same three cases)
      const ha = (z) => nf(Z[z] ? Z[z].resumen.ha_inundada : null);
      $("#bal-summary").textContent = t("bal_sum", ha("merin_arrozales"), ha("rio_branco_jaguarao"), ha("treinta_y_tres"));
      $("#uses-host").innerHTML = t("uses").map(([n, d]) => `<div class="use"><b>${esc(n)}</b><p>${esc(d)}</p></div>`).join("");
      $("#links-host").innerHTML = `<div class="links"><a href="method.html?lang=${lang}">${esc(t("lk_method"))}</a>` +
        `<a href="${REPO}" target="_blank" rel="noopener">${esc(t("lk_code"))}</a></div>`;
      $("#foot").textContent = `${t("title")} · ${M.generado}`;
      const cta = $("#cta-explore"); if (cta) cta.href = `explorer.html?lang=${lang}`;
    });
  }

  document.getElementById("scene-0").classList.add("active");
  (async function main() {
    try { M = await (await fetch("data/manifest.json", { cache: "no-cache" })).json(); }
    catch (e) { showError(t("no_data", e.message)); return; }
    Z = M.zonas; CZ = M.contexto.caso || "rocha_norte";
    buildHero(); buildBlind(); buildCount(); buildStays(); buildDry(); buildRoads(); buildLband(); buildBalance();
    initTabs();
    initSlides();
    await initMap();
    if (scene) enterScene(scene, true, curKey);
  })().catch((e) => showError(t("broke", e.message)));
})();
