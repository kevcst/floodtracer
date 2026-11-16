/* Explorer: free exploration of four areas over a full-screen map (rewritten 2026-11-15).
   - Same top bar, palette and legend labels as the Story (lg_* below = story.js lg_*). No digits in STRINGS: every number comes
     from data/manifest.json (scripts/check_story_literals.py). No em dashes.
   - Two synced maps: the main one (right side) and a non-interactive copy clipped to the left of a divider. The divider
     compares two dates, or the map background against the radar image.
   - Roads come from data/impacto/caminos.geojson (whole OpenStreetMap ways) and are clipped here to the footprint of the
     radar image of each area, so no road is drawn outside the radar scene. */
const STRINGS = {
  en: {
    title: "Explore the map",
    app_name: "FloodTracer",
    app_tag: "An interactive flood explorer powered by NISAR",
    map_alt: "Map of eastern Uruguay with NISAR radar images and flood water",
    no_map: "The map library did not load (no internet?).",
    no_data: (msg) => `The data did not load (${msg}). Serve the app folder over http: python3 -m http.server -d app and open the page from localhost.`,
    file_proto: "This page needs to be served over http to load its data (python3 -m http.server -d app).",
    broke: (msg) => `Something broke while drawing the page: ${msg}`,
    divider: "Comparison divider",
    panel_title: "Explore the map",
    hide: "Hide", show: "Show",
    c_place: "Place", c_base: "Map background", c_what: "What to explore", c_date: "Radar pass",
    c_layers: "Layers on the map", c_compare: "Compare",
    l_note: "Turn on “Show colored areas” to choose what to explore.",
    cmp_note: "One comparison at a time: turning one on turns the other off.",
    c_before: "Before", c_after: "After",
    b_sat: "Satellite", b_osm: "Street map",
    b_note: "The satellite photo is background only: its date is not the radar date.",
    l_date: "Water detected by date", l_heat: "Where the water stayed longest",
    k_dates: "Compare two dates", k_radarcmp: "Compare the map with the radar image",
    k_polys: "Show colored areas", k_radar: "Show radar image", k_roads: "Highlight roads",
    ph_base: "before the storm", ph_after: "after the storm",
    opt_date: (d, ph) => `${d} · ${ph}`,
    lab_map: "Map", lab_radar: "Radar (NISAR)",
    lab_date: (d) => `NISAR ${d}`,
    stamp_pass: (date, zone) => `${zone} · NISAR pass of ${date}`,
    tap_hint: "Tap the map to see how long a place stayed under water.",
    // legends: same labels as the Story
    lg_base: "Water before the storm (baseline)",
    lg_after: "Water detected after the storm",
    lg_wet: "Water detected before the storm, from earlier rains (not counted)",
    lg_radar: "Radar: darker means water",
    lg_days: "Days under water",
    lg_roads: "Roads in flooded areas: days under water",
    lg_dmin: (d) => `${d} days`,
    lg_dmax: (d) => `${d} days`,
    // popups
    place_days: (d, w) => (w ? `About ${d} days under water, roughly ${w} weeks.` : `About ${d} days under water.`),
    place_days_min: (d, w) => (w ? `At least ${d} days under water (over ${w} weeks) and still wet at the end.` : `At least ${d} days under water.`),
    place_share: (p) => `${p}% of the land around this point was flooded.`,
    place_none: "The radar did not see a lasting flood here during the storm.",
    road_days: (d, a, b) => `The land under this road was flooded about ${d} days (between ${a} and ${b}).`,
    road_note: "A road in a flooded area is not always a cut road.",
    zonas: { treinta_y_tres: "Treinta y Tres", merin_arrozales: "Laguna Merín", rio_branco_jaguarao: "Río Branco / Jaguarão", rocha_norte: "Northern Rocha" },
    // information box, one per area
    i_tyt_tag: "A case where it did not work",
    i_tyt: () => [
      "The Olimar river is not detected as existing water. In the radar image the river looks bright instead of dark: the trees and vegetation along its banks bounce the signal back, so the detector cannot tell it is water.",
      "Drag the divider to compare the satellite photo (left) with the radar image (right) and follow the river.",
    ],
    i_mer_tag: "An error we found and fixed",
    i_mer: () => [
      "During the analysis we found that most of the Laguna Merín was not marked as existing water. On windy days the wind ripples the lagoon and the radar sees it bright, like land.",
      "Using wind data (ERA5) at the time of each pass, we took the existing water only from calm passes. Now the lagoon shows up as water before the storm (blue), and only what changed after the storm is orange.",
    ],
    i_rb_tag: "A case where it worked",
    i_rb: (a, b) => [
      "The Yaguarón river and the lagoons are detected as existing water (blue), and the fields flooded by the storm stand out in orange.",
      `Drag the divider: on the left the radar pass of ${a}, before the storm; on the right ${b}, after it.`,
    ],
    i_rn_tag: "The case study",
    i_rn: (ha, prev, half) => [
      `The area the Story is about. NISAR saw ${ha} ha flooded by the storm (seen wet on two or more passes); another ${prev} ha were already flooded before the storm, by earlier rains, and are not counted.`,
      `Half of the flooded land was dry again about ${half} days after the rain started, and the low wetlands kept water the longest. Turn on the roads to see which ones crossed flooded land.`,
    ],
    i_rn_link: "Read the story",
  },
  es: {
    title: "Explorar el mapa",
    app_name: "FloodTracer",
    app_tag: "Un explorador interactivo de inundaciones con NISAR",
    map_alt: "Mapa del este de Uruguay con imágenes del radar NISAR y agua de la inundación",
    no_map: "No cargó la biblioteca del mapa (¿sin internet?).",
    no_data: (msg) => `No cargaron los datos (${msg}). Serví la carpeta app por http: python3 -m http.server -d app y abrí la página desde localhost.`,
    file_proto: "Esta página necesita servirse por http para cargar sus datos (python3 -m http.server -d app).",
    broke: (msg) => `Algo falló al dibujar la página: ${msg}`,
    divider: "Divisor de la comparación",
    panel_title: "Explorar el mapa",
    hide: "Ocultar", show: "Mostrar",
    c_place: "Lugar", c_base: "Fondo del mapa", c_what: "Qué explorar", c_date: "Pasada del radar",
    c_layers: "Capas del mapa", c_compare: "Comparar",
    l_note: "Activá “Mostrar áreas de color” para elegir qué explorar.",
    cmp_note: "Una comparación a la vez: al activar una se apaga la otra.",
    c_before: "Antes", c_after: "Después",
    b_sat: "Satélite", b_osm: "Mapa de calles",
    b_note: "La foto satelital es sólo fondo: su fecha no es la del radar.",
    l_date: "Agua detectada por fecha", l_heat: "Dónde se quedó más tiempo el agua",
    k_dates: "Comparar dos fechas", k_radarcmp: "Comparar el mapa con la imagen de radar",
    k_polys: "Mostrar áreas de color", k_radar: "Mostrar imagen de radar", k_roads: "Resaltar caminos",
    ph_base: "antes de la tormenta", ph_after: "después de la tormenta",
    opt_date: (d, ph) => `${d} · ${ph}`,
    lab_map: "Mapa", lab_radar: "Radar (NISAR)",
    lab_date: (d) => `NISAR ${d}`,
    stamp_pass: (date, zone) => `${zone} · pasada NISAR del ${date}`,
    tap_hint: "Tocá el mapa para ver cuánto tiempo estuvo un lugar bajo agua.",
    lg_base: "Agua antes de la tormenta (referencia)",
    lg_after: "Agua detectada después de la tormenta",
    lg_wet: "Agua detectada antes de la tormenta, por lluvias anteriores (no se cuenta)",
    lg_radar: "Radar: más oscuro es agua",
    lg_days: "Días bajo agua",
    lg_roads: "Caminos en zonas inundadas: días bajo agua",
    lg_dmin: (d) => `${d} días`,
    lg_dmax: (d) => `${d} días`,
    place_days: (d, w) => (w ? `Unos ${d} días bajo agua, más o menos ${w} semanas.` : `Unos ${d} días bajo agua.`),
    place_days_min: (d, w) => (w ? `Al menos ${d} días bajo agua (más de ${w} semanas) y seguía mojado al final.` : `Al menos ${d} días bajo agua.`),
    place_share: (p) => `El ${p} % de la tierra alrededor de este punto se inundó.`,
    place_none: "El radar no vio una inundación duradera acá durante la tormenta.",
    road_days: (d, a, b) => `La tierra por la que pasa este camino estuvo inundada unos ${d} días (entre ${a} y ${b}).`,
    road_note: "Un camino en una zona inundada no siempre es un camino cortado.",
    zonas: { treinta_y_tres: "Treinta y Tres", merin_arrozales: "Laguna Merín", rio_branco_jaguarao: "Río Branco / Yaguarón", rocha_norte: "Rocha norte" },
    i_tyt_tag: "Un caso donde no funcionó",
    i_tyt: () => [
      "El río Olimar no se detecta como agua existente. En la imagen de radar el río se ve brillante en lugar de oscuro: los árboles y la vegetación de sus orillas devuelven la señal, así que el detector no lo reconoce como agua.",
      "Mové el divisor para comparar la foto satelital (izquierda) con la imagen de radar (derecha) y seguir el río.",
    ],
    i_mer_tag: "Un error que encontramos y corregimos",
    i_mer: () => [
      "Durante el análisis vimos que la mayor parte de la Laguna Merín no quedaba marcada como agua existente. Los días de viento la laguna se riza y el radar la ve brillante, como si fuera tierra.",
      "Con los datos de viento (ERA5) a la hora de cada pasada, tomamos el agua existente sólo de las pasadas en calma. Ahora la laguna aparece como agua antes de la tormenta (azul) y en naranja queda sólo lo que cambió después.",
    ],
    i_rb_tag: "Un caso donde funcionó",
    i_rb: (a, b) => [
      "El río Yaguarón y las lagunas se detectan como agua existente (azul), y los campos inundados por la tormenta se destacan en naranja.",
      `Mové el divisor: a la izquierda la pasada del ${a}, antes de la tormenta; a la derecha la del ${b}, después.`,
    ],
    i_rn_tag: "El caso de estudio",
    i_rn: (ha, prev, half) => [
      `La zona de la que trata la Historia. NISAR vio ${ha} ha inundadas por la tormenta (mojadas en dos o más pasadas); otras ${prev} ha ya estaban inundadas antes de la tormenta, por lluvias anteriores, y no se cuentan.`,
      `La mitad de la tierra inundada volvió a estar seca unos ${half} días después de que empezó a llover, y los bañados bajos fueron los que más tiempo retuvieron el agua. Activá los caminos para ver cuáles pasaban por tierra inundada.`,
    ],
    i_rn_link: "Leer la historia",
  },
};

(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  let lang = (window.SiteNav && window.SiteNav.lang) || new URLSearchParams(location.search).get("lang") || "en";
  if (!STRINGS[lang]) lang = "en";
  const t = (k, ...a) => { const v = STRINGS[lang][k] ?? STRINGS.en[k]; return typeof v === "function" ? v(...a) : (v ?? k); };
  const nf = (v, d = 0) => (v == null || isNaN(v) ? "–" : new Intl.NumberFormat(lang === "es" ? "es-UY" : "en-US", { maximumFractionDigits: d, minimumFractionDigits: d }).format(v));
  const fdate = (s, long) => new Date(s + "T12:00:00Z").toLocaleDateString(lang === "es" ? "es-UY" : "en-GB",
    long ? { day: "numeric", month: "long", timeZone: "UTC" } : { day: "numeric", month: "short", timeZone: "UTC" });
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  function showError(msg) { const e = $("#err"); e.textContent = msg; e.style.display = "block"; }
  window.addEventListener("error", (e) => showError(t("broke", e.message)));
  if (location.protocol === "file:") showError(t("file_proto"));

  // same constants as story.js
  const HEAT_RAMP = [[0, "rgba(255,237,160,0)"], [0.15, "rgba(255,237,160,0.6)"], [0.35, "#fdae61"], [0.55, "#f46d43"], [0.75, "#d73027"], [1, "#67001f"]];
  const ROAD_PALETTE = ["#f1e7ff", "#dac2ff", "#b68aff", "#8e54ee", "#6430bd"];
  const ZONES = ["treinta_y_tres", "merin_arrozales", "rio_branco_jaguarao", "rocha_norte"];
  const DEFAULT_ZONE = "rocha_norte";
  const img = (z, f) => `data/${z}/${f}`;

  let M, Z, mapR, mapL, ready = false;
  const S = { z: null, layer: "date", date: null, before: null, compare: "none", basemap: "sat", polys: true, radar: false, roads: false, split: 50 };
  const zn = (z) => t("zonas")[z] || Z[z].nombre;
  const dates = () => Z[S.z].capas.serie.fechas;
  const phase = (z, f) => (Z[z].fechas.find((p) => p.fecha === f) || {}).fase;
  const peak = (z) => { const f = Z[z].fechas.filter((p) => p.remaining != null); return f.reduce((a, p) => (p.remaining > a.remaining ? p : a), f[0]).fecha; };
  const lastBase = (z) => Z[z].fechas.filter((p) => p.fase === "base").at(-1).fecha;

  // Default view of each area (requested by the team): what the information box talks about.
  const PRESETS = {
    treinta_y_tres: (z) => ({ basemap: "sat", layer: "date", compare: "radar", polys: false, radar: true, roads: false, date: lastBase(z) }),
    merin_arrozales: (z) => ({ basemap: "sat", layer: "date", compare: "none", polys: true, radar: true, roads: false, date: peak(z) }),
    rio_branco_jaguarao: (z) => ({ basemap: "sat", layer: "date", compare: "dates", polys: true, radar: true, roads: false, before: lastBase(z), date: peak(z) }),
    rocha_norte: (z) => ({ basemap: "sat", layer: "date", compare: "none", polys: true, radar: true, roads: false, date: peak(z) }),
  };
  const INFO = {
    treinta_y_tres: () => ({ cls: "neg", tag: t("i_tyt_tag"), body: t("i_tyt") }),
    merin_arrozales: () => ({ cls: "fix", tag: t("i_mer_tag"), body: t("i_mer") }),
    rio_branco_jaguarao: (z) => ({ cls: "ok", tag: t("i_rb_tag"), body: t("i_rb", fdate(lastBase(z), true), fdate(peak(z), true)) }),
    rocha_norte: (z) => { const r = Z[z].resumen;
      return { cls: "", tag: t("i_rn_tag"), body: t("i_rn", nf(r.ha_inundada), nf(r.ha_previa), nf(r.dia_mitad_seca)),
        link: `<a href="index.html?lang=${lang}">${esc(t("i_rn_link"))}</a>` }; },
  };

  // ---------- static text ----------
  function applyStatic() {
    document.documentElement.lang = lang;
    document.title = `${t("app_name")} · ${t("title")}`;
    $$("[data-i18n]").forEach((n) => { n.textContent = t(n.dataset.i18n); });
    $$("[data-i18n-aria]").forEach((n) => { n.setAttribute("aria-label", t(n.dataset.i18nAria)); });
    $("#panel-toggle").textContent = $("#panel").classList.contains("closed") ? t("show") : t("hide");
  }
  applyStatic();

  // ---------- maps ----------
  function maplibreReady() {
    if (window.maplibregl) return Promise.resolve(true);
    const el = document.getElementById("maplibre-js");
    return new Promise((res) => { el.addEventListener("load", () => res(true)); el.addEventListener("error", () => res(false)); });
  }
  // keep the radar scene clear of the information box (left) and the panel (right)
  const pad = () => { const bar = 50, w = innerWidth, info = $("#info").getBoundingClientRect(), panel = $("#panel").getBoundingClientRect();
    const left = Math.min(info.right + 16, w * 0.35), right = Math.min(w - panel.left + 16, w * 0.3);
    return { top: bar + 20, bottom: 30, left, right }; };
  const bboxOf = (pts) => { const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]); return [[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]]; };
  function style() {
    return { version: 8,
      sources: {
        osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, maxzoom: 19, attribution: "© OpenStreetMap contributors" },
        sat: { type: "raster", tiles: ["https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"], tileSize: 256, maxzoom: 19,
          attribution: "Imagery © Esri, Maxar, Earthstar Geographics" },
      },
      layers: [
        { id: "osm", type: "raster", source: "osm", layout: { visibility: "none" }, paint: { "raster-saturation": -0.7, "raster-opacity": 0.85 } },
        { id: "sat", type: "raster", source: "sat", paint: { "raster-fade-duration": 0 } },
      ] };
  }
  function newMap(container, interactive) {
    // the left copy starts hidden (size 0): it gets its camera from the main map (syncCam), not from bounds
    const view = interactive ? { bounds: bboxOf(Z[S.z].capas.serie.esquinas), fitBoundsOptions: { padding: pad() } } : { center: [0, 0], zoom: 1 };
    return new maplibregl.Map({ container, style: style(), interactive, attributionControl: interactive ? { compact: true } : false, maxZoom: 16, fadeDuration: 0, ...view });
  }
  function addLayers(m) {
    const e = Z[S.z].capas.serie.esquinas, f = sideCfg(m === mapR ? "R" : "L").date;
    m.addSource("hh", { type: "image", url: img(S.z, `hh_${f}.webp`), coordinates: e });
    m.addLayer({ id: "hh", type: "raster", source: "hh", layout: { visibility: "none" }, paint: { "raster-opacity": 0.95, "raster-fade-duration": 0 } });
    m.addSource("agua", { type: "image", url: img(S.z, `agua_${f}.png`), coordinates: e });
    m.addLayer({ id: "agua", type: "raster", source: "agua", layout: { visibility: "none" }, paint: { "raster-opacity": 0.95, "raster-fade-duration": 0 } });
    m.addSource("frame", { type: "geojson", data: frameGeo() });
    // the image slots start with the URLs just added, so the first render does not reload (and abort) them
    slots.set((m === mapR ? "R" : "L") + "hh", { cur: img(S.z, `hh_${f}.webp`), want: null, busy: false });
    slots.set((m === mapR ? "R" : "L") + "agua", { cur: img(S.z, `agua_${f}.png`), want: null, busy: false });
    m.addLayer({ id: "frame", type: "line", source: "frame", paint: { "line-color": "#ffffff", "line-width": 1.2, "line-opacity": 0.8, "line-dasharray": [3, 2] } });
  }
  const frameGeo = () => { const e = Z[S.z].capas.serie.esquinas;
    return { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[...e, e[0]]] } }; };

  // Image swaps are serialized per map and source: MapLibre aborts an in-flight image load if updateImage is called again.
  const preloaded = new Map();
  const preload = (url) => { if (!preloaded.has(url)) { const im = new Image(); im.src = url; preloaded.set(url, im.decode().catch(() => null)); } return preloaded.get(url); };
  function srcLoaded(m, id) {
    return new Promise((res) => {
      const on = (e) => { if (e.sourceId === id && e.isSourceLoaded) done(); };
      const done = () => { m.off("sourcedata", on); clearTimeout(to); res(); };
      const to = setTimeout(done, 3000);
      m.on("sourcedata", on);
    });
  }
  const slots = new Map();
  function setImage(m, id, url, coords) {
    const key = (m === mapR ? "R" : "L") + id;
    if (!slots.has(key)) slots.set(key, { cur: null, want: null, busy: false });
    const s = slots.get(key);
    s.want = { url, coords };
    if (s.busy) return;
    s.busy = true;
    (async () => {
      while (s.want && s.want.url !== s.cur) {
        const w = s.want;
        await preload(w.url);
        if (s.want !== w) continue;
        const loaded = srcLoaded(m, id);
        m.getSource(id).updateImage({ url: w.url, coordinates: w.coords });
        await loaded;
        s.cur = w.url;
      }
      s.busy = false;
    })();
  }

  // ---------- drying heat map (lazy, ~2 MB) ----------
  let secado = null;
  function ensureHeat(m) {
    if (m.getSource("secado")) return;
    m.addSource("secado", { type: "geojson", data: M.secado.archivo });
    const wmax = Math.max(1, M.secado.w_max), only = ["==", ["get", "z"], S.z];
    m.addLayer({ id: "heat", type: "heatmap", source: "secado", maxzoom: 13, filter: only, layout: { visibility: "none" }, paint: {
      "heatmap-weight": ["min", 1, ["/", ["get", "w"], wmax]],
      "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 6, 0.22, 8, 0.4, 10, 0.8, 12, 1.5],
      "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 6, 5, 8, 9, 10, 16, 12, 32],
      "heatmap-opacity": ["interpolate", ["linear"], ["zoom"], 11, 0.9, 13, 0.5],
      "heatmap-color": ["interpolate", ["linear"], ["heatmap-density"], ...HEAT_RAMP.flatMap(([s, c]) => [s, c])] } }, "frame");
    m.addLayer({ id: "cells", type: "circle", source: "secado", minzoom: 11, filter: only, layout: { visibility: "none" }, paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 11, 3, 14, 9],
      "circle-color": ["interpolate", ["linear"], ["get", "d"], 0, "#fee090", 7, "#fdae61", 14, "#f46d43", 28, "#d73027", 42, "#67001f"],
      "circle-opacity": 0.85, "circle-stroke-width": 0.5, "circle-stroke-color": "#fff" } }, "frame");
  }
  async function loadSecado() {
    if (!secado) secado = fetch(M.secado.archivo).then((r) => r.json()).then((g) => g.features);
    return secado;
  }

  // ---------- roads, clipped to the radar footprint ----------
  // Clips a polyline to a convex quadrilateral (Cyrus-Beck per segment); returns the pieces inside.
  function clipLine(coords, quad) {
    const c = [quad.reduce((a, p) => a + p[0], 0) / quad.length, quad.reduce((a, p) => a + p[1], 0) / quad.length];
    const edges = quad.map((p, i) => { const q = quad[(i + 1) % quad.length], ex = q[0] - p[0], ey = q[1] - p[1];
      return { p, ex, ey, s: Math.sign(ex * (c[1] - p[1]) - ey * (c[0] - p[0])) }; });
    const f = (e, x, y) => e.s * (e.ex * (y - e.p[1]) - e.ey * (x - e.p[0]));
    const out = []; let cur = null;
    for (let i = 0; i < coords.length - 1; i++) {
      const A = coords[i], B = coords[i + 1]; let t0 = 0, t1 = 1;
      for (const e of edges) {
        const fa = f(e, A[0], A[1]), fb = f(e, B[0], B[1]);
        if (fa < 0 && fb < 0) { t0 = 1; t1 = 0; break; }
        if (fa < 0) t0 = Math.max(t0, fa / (fa - fb)); else if (fb < 0) t1 = Math.min(t1, fa / (fa - fb));
      }
      if (t0 >= t1) { if (cur) { out.push(cur); cur = null; } continue; }
      const P = (u) => [A[0] + u * (B[0] - A[0]), A[1] + u * (B[1] - A[1])];
      if (!cur || t0 > 0) { if (cur) out.push(cur); cur = [P(t0)]; }
      cur.push(P(t1));
      if (t1 < 1) { out.push(cur); cur = null; }
    }
    if (cur) out.push(cur);
    return out.filter((l) => l.length > 1);
  }
  let roadsByZone = null;
  async function loadRoads() {
    if (roadsByZone) return roadsByZone;
    const g = await (await fetch("data/impacto/caminos.geojson")).json();
    roadsByZone = Object.fromEntries(ZONES.map((z) => [z, { type: "FeatureCollection", features: [] }]));
    for (const ft of g.features) {
      const p = ft.properties, z = p.zona;
      if (!roadsByZone[z] || !(p.dias_mid > 0)) continue;
      const quad = Z[z].capas.serie.esquinas;
      const lines = ft.geometry.type === "LineString" ? [ft.geometry.coordinates] : ft.geometry.coordinates;
      const parts = lines.flatMap((l) => clipLine(l, quad));
      if (parts.length) roadsByZone[z].features.push({ type: "Feature", properties: p, geometry: { type: "MultiLineString", coordinates: parts } });
    }
    return roadsByZone;
  }
  const roadSteps = () => M.leyendas.persistencia.map((b) => parseInt(b.rango, 10));
  async function ensureRoads(m) {
    const data = (await loadRoads())[S.z];
    if (m.getSource("roads")) { m.getSource("roads").setData(data); return; }
    m.addSource("roads", { type: "geojson", data, attribution: "© OpenStreetMap contributors" });
    const color = ["step", ["get", "dias_mid"], ROAD_PALETTE[0]];
    roadSteps().slice(1).forEach((v, k) => color.push(v, ROAD_PALETTE[k + 1]));
    const w = (x) => ["interpolate", ["linear"], ["zoom"], 8, 2 + x, 13, 5 + x];
    m.addLayer({ id: "roads-case", type: "line", source: "roads", layout: { visibility: "none", "line-cap": "round" }, paint: { "line-color": "#171321", "line-width": w(3) } });
    m.addLayer({ id: "roads", type: "line", source: "roads", layout: { visibility: "none", "line-cap": "round" }, paint: { "line-color": color, "line-width": w(0) } });
  }

  // ---------- apply state to one map ----------
  function sideCfg(side) {
    const left = side === "L";
    return {
      date: S.compare === "dates" && left ? S.before : S.date,
      radar: S.compare === "radar" ? !left : S.radar,
    };
  }
  const vis = (m, id, on) => { if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", on ? "visible" : "none"); };
  async function applyMap(m, side) {
    const c = sideCfg(side), e = Z[S.z].capas.serie.esquinas;
    vis(m, "sat", S.basemap === "sat"); vis(m, "osm", S.basemap === "osm");
    setImage(m, "hh", img(S.z, `hh_${c.date}.webp`), e);
    setImage(m, "agua", img(S.z, `agua_${c.date}.png`), e);
    vis(m, "hh", c.radar);
    vis(m, "agua", S.layer === "date" && S.polys);
    m.getSource("frame").setData(frameGeo());
    if (S.layer === "heat") ensureHeat(m);
    if (m.getLayer("heat")) { const only = ["==", ["get", "z"], S.z]; m.setFilter("heat", only); m.setFilter("cells", only); }
    vis(m, "heat", S.layer === "heat" && S.polys); vis(m, "cells", S.layer === "heat" && S.polys);
    if (S.roads || m.getSource("roads")) await ensureRoads(m);
    vis(m, "roads", S.roads); vis(m, "roads-case", S.roads);
  }

  // ---------- divider ----------
  function setSplit(x) {
    S.split = Math.max(0, Math.min(100, x));
    $("#divider").style.setProperty("--x", S.split + "%");
    $("#map-left").style.clipPath = `inset(0 ${100 - S.split}% 0 0)`;
    $("#div-handle").setAttribute("aria-valuenow", Math.round(S.split));
  }
  function initDivider() {
    const h = $("#div-handle");
    const drag = (ev) => { const b = $("#stage").getBoundingClientRect(); setSplit(100 * (ev.clientX - b.left) / b.width); };
    h.addEventListener("pointerdown", (ev) => { ev.preventDefault(); h.setPointerCapture(ev.pointerId); drag(ev); });
    h.addEventListener("pointermove", (ev) => { if (h.hasPointerCapture(ev.pointerId)) drag(ev); });
    h.addEventListener("pointerup", (ev) => { if (h.hasPointerCapture(ev.pointerId)) h.releasePointerCapture(ev.pointerId); });
    h.addEventListener("keydown", (ev) => { const d = { ArrowLeft: -2, ArrowRight: 2 }[ev.key]; if (d) { ev.preventDefault(); setSplit(S.split + d); } });
    setSplit(50);
  }

  // ---------- legend, stamp, info ----------
  const row = (color, text) => `<div class="row"><span class="sw" style="background:${color}"></span>${esc(text)}</div>`;
  function legend() {
    let h = "";
    const radarShown = S.radar || S.compare === "radar";
    if (S.polys && S.layer === "date") h += row(css("--flood-map"), t("lg_after")) + row(css("--still"), t("lg_base")) + (Z[S.z].resumen.ha_previa ? row(M.leyendas.previa, t("lg_wet")) : "");
    if (S.polys && S.layer === "heat") {
      const grad = HEAT_RAMP.filter(([s]) => s > 0).map(([s, c]) => `${c} ${Math.round(100 * s)}%`).join(","), d = (M.secado.dias || {})[S.z] || {};
      h += `<div class="row ttl">${esc(t("lg_days"))}</div><div class="ramp" style="background:linear-gradient(90deg,${grad})"></div>` +
        `<div class="ramp-labels"><span>${esc(t("lg_dmin", nf(d.min)))}</span><span>${esc(t("lg_dmax", nf(d.max)))}</span></div>`;
    }
    if (radarShown) h += `<div class="row"><span class="sw" style="background:linear-gradient(90deg,#111,#ddd)"></span>${esc(t("lg_radar"))}</div>`;
    if (S.roads) h += `<div class="row ttl">${esc(t("lg_roads"))}</div><div class="road-scale">${M.leyendas.persistencia.map((b, k) => `<span><i style="background:${ROAD_PALETTE[k]}"></i>${esc(b.rango)}</span>`).join("")}</div>`;
    $("#legend").innerHTML = h;
  }
  function stamp() {
    let s = "";
    if (S.compare === "none") s = S.layer === "heat" ? t("tap_hint") : t("stamp_pass", fdate(S.date, true), zn(S.z));
    else if (S.compare === "radar") s = t("stamp_pass", fdate(S.date, true), zn(S.z));
    $("#stamp").textContent = s;
    $("#lab-l").textContent = S.compare === "dates" ? t("lab_date", fdate(S.before, true)) : t("lab_map");
    $("#lab-r").textContent = S.compare === "dates" ? t("lab_date", fdate(S.date, true)) : t("lab_radar");
  }
  function info() {
    const i = INFO[S.z](S.z), box = $("#info");
    box.className = "info " + (i.cls || "");
    $("#info-tag").textContent = i.tag;
    $("#info-title").textContent = zn(S.z);
    $("#info-body").innerHTML = i.body.map((p) => `<p>${esc(p)}</p>`).join("") + (i.link ? `<p>${i.link}</p>` : "");
  }

  // ---------- controls ----------
  const optLabel = (f) => t("opt_date", fdate(f, true), phase(S.z, f) === "base" ? t("ph_base") : t("ph_after"));
  function fillSelect(sel, list, value, short) {
    sel.innerHTML = list.map((f) => `<option value="${f}">${esc(short ? fdate(f, true) : optLabel(f))}</option>`).join("");
    sel.value = value;
  }
  function syncControls() {
    $("#zone").value = S.z;
    $$("#basemap button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.v === S.basemap));
    $("#layer").value = S.layer;
    $("#layer").disabled = !S.polys;            // what to explore = which colored areas: needs them on
    $("#layer-note").hidden = S.polys;
    const fe = dates();
    fillSelect($("#date"), fe, S.date);
    fillSelect($("#before"), fe.filter((f) => f < S.date), S.before, true);
    fillSelect($("#after"), fe.filter((f) => f > S.before), S.date, true);
    $("#date").disabled = S.compare === "dates";     // the two dates of the comparison take its place
    $("#dates-fields").hidden = S.compare !== "dates";
    $("#chk-dates").checked = S.compare === "dates";
    $("#chk-radarcmp").checked = S.compare === "radar";
    $("#chk-polys").checked = S.polys; $("#chk-radar").checked = S.radar; $("#chk-roads").checked = S.roads;
  }
  function zoneButtons() {
    $("#zone").innerHTML = ZONES.map((z) => `<option value="${z}">${esc(zn(z))}</option>`).join("");
    if (S.z) $("#zone").value = S.z;
  }
  function render() {
    syncControls(); legend(); stamp(); info();
    const cmp = S.compare !== "none";
    $("#map-left").hidden = !cmp; $("#divider").hidden = !cmp;
    if (!ready) return;
    applyMap(mapR, "R");
    if (cmp) { mapL.resize(); syncCam(); applyMap(mapL, "L"); }
  }
  function setZone(z) {
    S.z = z;
    Object.assign(S, { before: null }, PRESETS[z](z));
    if (!S.before) S.before = lastBase(z);
    if (S.before >= S.date) S.before = dates()[0];
    if (popup) popup.remove();
    if (ready) { mapR.fitBounds(bboxOf(Z[z].capas.serie.esquinas), { padding: pad(), duration: 0 }); syncCam(); }
    setSplit(50);
    render();
  }
  function initControls() {
    zoneButtons();
    $("#zone").addEventListener("change", (e) => setZone(e.target.value));
    $$("#basemap button").forEach((b) => b.addEventListener("click", () => { S.basemap = b.dataset.v; render(); }));
    $("#layer").addEventListener("change", (e) => { S.layer = e.target.value; render(); });
    $("#date").addEventListener("change", (e) => { S.date = e.target.value; if (S.before >= S.date) S.before = dates()[0]; render(); });
    $("#before").addEventListener("change", (e) => { S.before = e.target.value; render(); });
    $("#after").addEventListener("change", (e) => { S.date = e.target.value; render(); });
    $("#chk-dates").addEventListener("change", (e) => {
      S.compare = e.target.checked ? "dates" : "none";
      // default pair: last pass before the storm vs. the current pass, or vs. the wettest one if the current pass is before the storm
      if (S.compare === "dates") { if (S.date <= lastBase(S.z)) S.date = peak(S.z); S.before = lastBase(S.z); }
      render();
    });
    $("#chk-radarcmp").addEventListener("change", (e) => { S.compare = e.target.checked ? "radar" : "none"; render(); });
    $("#chk-polys").addEventListener("change", (e) => { S.polys = e.target.checked; render(); });
    $("#chk-radar").addEventListener("change", (e) => { S.radar = e.target.checked; render(); });
    $("#chk-roads").addEventListener("change", (e) => { S.roads = e.target.checked; render(); });
    $("#panel-toggle").addEventListener("click", () => {
      const p = $("#panel"); p.classList.toggle("closed");
      $("#panel-toggle").setAttribute("aria-expanded", String(!p.classList.contains("closed")));
      $("#panel-toggle").textContent = p.classList.contains("closed") ? t("show") : t("hide");
    });
    window.addEventListener("site-lang", (e) => { if (!STRINGS[e.detail]) return; lang = e.detail; applyStatic(); zoneButtons(); render(); });
  }

  // ---------- popups ----------
  let popup = null;
  function pop(ll, html) { if (popup) popup.remove(); popup = new maplibregl.Popup({ closeButton: true, maxWidth: "300px", className: "story-pop" }).setLngLat(ll).setHTML(html).addTo(mapR); }
  async function placeAt(ll) {
    const feats = await loadSecado(), kx = Math.cos(ll.lat * Math.PI / 180) * 111320, ky = 110540, lim = M.secado.celda_m * 0.75;
    let best = null, bd = Infinity;
    for (const f of feats) { if (f.properties.z !== S.z) continue; const [x, y] = f.geometry.coordinates, dd = Math.hypot((x - ll.lng) * kx, (y - ll.lat) * ky); if (dd < bd) { bd = dd; best = f; } }
    const out = [];
    if (best && bd <= lim) {
      const p = best.properties, w = p.d >= 14 ? (p.s > 0.5 ? Math.floor : Math.round)(p.d / 7) : null;
      out.push(t(p.s > 0.5 ? "place_days_min" : "place_days", nf(p.d), w && nf(w)), t("place_share", nf(100 * p.f)));
    } else out.push(t("place_none"));
    pop(ll, out.map((x) => `<p>${esc(x)}</p>`).join(""));
  }
  function roadPopup(e) {
    const p = e.features[0].properties;   // no title: almost every OSM road here is unnamed
    pop(e.lngLat, `<p>${esc(t("road_days", nf(+p.dias_mid), nf(+p.dias_min), nf(+p.dias_max)))}</p><p>${esc(t("road_note"))}</p>`);
  }

  function syncCam() { if (mapL && mapR) mapL.jumpTo({ center: mapR.getCenter(), zoom: mapR.getZoom(), bearing: mapR.getBearing(), pitch: mapR.getPitch() }); }

  // ---------- start ----------
  (async function main() {
    try { M = await (await fetch("data/manifest.json", { cache: "no-cache" })).json(); }
    catch (e) { showError(t("no_data", e.message)); return; }
    Z = M.zonas;
    const q = new URLSearchParams(location.search).get("zona");
    initControls(); initDivider();
    setZone(ZONES.includes(q) ? q : DEFAULT_ZONE);
    if (!(await maplibreReady())) { showError(t("no_map")); return; }
    mapR = newMap("map", true); mapL = newMap("map-left", false);
    mapR.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    window.__explorerMap = mapR;
    await Promise.all([mapR, mapL].map((m) => new Promise((res) => m.on("load", () => { addLayers(m); res(); }))));
    mapR.on("move", syncCam);
    const roadAt = (pt) => (S.roads && mapR.getLayer("roads") ? mapR.queryRenderedFeatures(pt, { layers: ["roads"] }) : []);
    mapR.on("click", (e) => {
      const r = roadAt(e.point);
      if (r.length) return roadPopup({ features: r, lngLat: e.lngLat });
      if (S.layer === "heat" && S.polys) placeAt(e.lngLat);
    });
    mapR.on("mousemove", (e) => { mapR.getCanvas().style.cursor = roadAt(e.point).length ? "pointer" : ""; });
    ready = true;
    syncCam();
    render();
  })().catch((e) => showError(t("broke", e.message)));
})();
