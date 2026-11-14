"""
Exporta todo lo que necesita la app web (app/index.html) a app/data/. Reemplaza a exportar_poc.py para la entrega.

  python scripts/exportar_app.py

Requiere haber corrido: metricas_evento → combinar_tracks → sensibilidad → monte_ribereno → capas_contexto →
agregar_impacto → armonizar_tracks → validar_s1 (este último opcional: si falta, la sección de validación S1 queda vacía).

Sale en app/data/:
  manifest.json                 TODO número que muestra la app (nada escrito a mano en el HTML)
  {zona}/hh_{fecha}.webp        HH en gris (WebP con alfa) del track de la serie (una imagen por pasada)
  {zona}/agua_{fecha}.png       agua base (azul) + agua nueva (naranja) de esa pasada
  {zona}/extension.png · persistencia.png · retiro.png · monte.png   capas del evento (grilla del combinado)
  {zona}/sonda.bin              HH y agua por fecha a ~200 m para el clic en el mapa (uint8; ver manifest.sonda)
  impacto/*.geojson             caminos, localidades, subcuencas (WGS84)
  descargas/                    CSV de resultados + GeoTIFF por zona (banda 1 extensión, 2 persistencia en días)

Las imágenes llevan las 4 esquinas en lon/lat para un "image source" de MapLibre.
"""
import json
import shutil
import warnings
from datetime import date

import numpy as np
import pandas as pd
import rasterio
from PIL import Image
from rasterio.warp import Resampling, reproject
from rasterio.warp import transform as warp_transform

from exportar_poc import COUNTRIES, bajar_countries, contexto
from metricas_evento import BASE, EVENTO, INICIO_LLUVIA, cargar_track, previa_en_grilla
from zonas import ZONAS

warnings.filterwarnings("ignore")
RAIZ = BASE.parents[1]
APP = RAIZ / "app"
SAL = APP / "data"
IMP = BASE / "impacto"

DESCRIPCION = {
    "treinta_y_tres": "Treinta y Tres city and the lower Olimar river, where ~1,600 people left their homes.",
    "merin_arrozales": "Rice fields and wetlands of the Cebollatí–Tacuarí plain, on the shore of the Laguna Merín.",
    "melo": "Melo and the Arroyo Conventos, upper Tacuarí basin (drains to the Laguna Merín).",
    "rio_branco_jaguarao": "Río Branco (Uruguay) and Jaguarão (Brazil) on the Yaguarón border river.",
    "durazno": "Durazno on the Río Yí, which crested at 9.75 m on 22 August.",
    "mercedes": "Mercedes on the lower Río Negro, downstream of the Yí, with wide gallery forest.",
}
NOMBRES = {"treinta_y_tres": ("Treinta y Tres", "Olimar"), "merin_arrozales": ("Laguna Merín rice fields", "Cebollatí–Tacuarí"),
           "melo": ("Melo", "Arroyo Conventos"), "rio_branco_jaguarao": ("Río Branco / Jaguarão", "Yaguarón"),
           "durazno": ("Durazno", "Yí"), "mercedes": ("Mercedes", "Río Negro")}
CUENCA = {"treinta_y_tres": "merin", "merin_arrozales": "merin", "melo": "merin", "rio_branco_jaguarao": "merin",
          "durazno": "negro", "mercedes": "negro"}
# crestas reportadas por prensa/SINAE (contexto y validación cualitativa, regla 1)
CRESTAS = {"treinta_y_tres": ("2026-08-19", "Olimar ~8.6 m (19–20 Aug)"),
           "melo": ("2026-08-18", "Arroyo Conventos overflow (17–20 Aug)"),
           "rio_branco_jaguarao": ("2026-08-19", "Yaguarón: Jaguarão emergency, peak 18–19 Aug"),
           "durazno": ("2026-08-22", "Yí 9.75 m (22 Aug, 22 h)"),
           "mercedes": ("2026-08-25", "Río Negro: evacuation alert ~21–25 Aug")}
NARANJA, AZUL = (235, 104, 52), (42, 120, 214)
# persistencia (días, punto medio del intervalo): secuencial azul claro → oscuro; "sigue" el más oscuro
PERS_BINS = [(0, 7, (198, 219, 245)), (8, 14, (138, 182, 238)), (15, 28, (74, 140, 222)), (29, 42, (36, 98, 176)),
             (43, 9999, (18, 64, 124))]
SIGUE = (9, 38, 77)
RETIRO_BINS = [("2026-08-10", "2026-08-31", (253, 219, 199)), ("2026-09-01", "2026-09-15", (247, 166, 122)),
               ("2026-09-16", "2026-09-30", (230, 110, 60)), ("2026-10-01", "2026-10-20", (180, 66, 22))]
MONTE = (27, 175, 122)
PREVIA = (138, 149, 161)          # ya mojado antes de la lluvia (10–14/8): gris, fuera de la tormenta
MAX_LADO = 2200
SONDA_M = 200.0


def leer(p, banda=1):
    with rasterio.open(p) as r:
        return r.read(banda), r.profile


def esquinas(perfil, f=1):
    t = perfil["transform"]
    W, H = perfil["width"], perfil["height"]
    xs = [t.c, t.c + t.a * W, t.c + t.a * W, t.c]
    ys = [t.f, t.f, t.f + t.e * H, t.f + t.e * H]
    lon, lat = warp_transform(perfil["crs"], "EPSG:4326", xs, ys)
    return [[round(a, 6), round(b, 6)] for a, b in zip(lon, lat)]           # TL, TR, BR, BL (orden MapLibre)


def a_grilla(arr, src, dst, nodata=0, res=Resampling.nearest):
    out = np.full((dst["height"], dst["width"]), nodata, arr.dtype)
    reproject(arr, out, src_transform=src["transform"], src_crs=src["crs"], dst_transform=dst["transform"],
              dst_crs=dst["crs"], src_nodata=nodata, dst_nodata=nodata, resampling=res)
    return out


def png(path, rgba):
    Image.fromarray(rgba).save(path, optimize=True)


def rgba(shape):
    return np.zeros(shape + (4,), "uint8")


def factor(perfil):
    return 1 if max(perfil["width"], perfil["height"]) <= MAX_LADO else int(np.ceil(max(perfil["width"], perfil["height"]) / MAX_LADO))


def doy_fecha(d):
    return str((pd.Timestamp("2025-12-31") + pd.Timedelta(days=int(d))).date())


def capas_zona(zona, out):
    """Imágenes por fecha (serie) y del evento (combinado o track único). Devuelve dict para el manifest."""
    serie = ZONAS[zona]["serie"]
    tdir = BASE / zona / serie
    fechas, hh, _, perfil_s = cargar_track(tdir)
    with rasterio.open(tdir / "metricas" / "agua_nueva_por_fecha.tif") as r:
        pila, desc = r.read(), list(r.descriptions)
    base, _ = leer(tdir / "metricas" / "agua_base.tif")
    f = factor(perfil_s)
    previa_s = previa_en_grilla(zona, perfil_s)[::f, ::f]   # agua ya mojada antes de la lluvia: gris también por fecha
    fechas_info = []
    for i, fe in enumerate(fechas):
        d = str(fe.date())
        g = np.clip((hh[i] + 22) / 20 * 255, 0, 255)
        ok = np.isfinite(hh[i])[::f, ::f]
        g = np.where(np.isfinite(hh[i]), g, 0).astype("uint8")[::f, ::f]
        # WebP con alfa: los bordes sin dato quedan transparentes (JPEG los pintaba de negro)
        Image.fromarray(np.dstack([g, g, g, np.where(ok, 255, 0).astype("uint8")]), "RGBA").save(
            out / f"hh_{d}.webp", quality=78, method=4)
        m = pila[desc.index(d)][::f, ::f]
        o = rgba(m.shape)
        o[base[::f, ::f] == 1] = (*AZUL, 255)
        o[m == 1] = (*NARANJA, 255)
        if fe >= EVENTO[0]:                                  # en la base no aplica
            o[(m == 1) & previa_s] = (*PREVIA, 255)
        png(out / f"agua_{d}.png", o)
        fechas_info.append(d)
    capas = dict(serie=dict(track=serie, esquinas=esquinas(perfil_s), fechas=fechas_info, factor=f,
                            ancho=perfil_s["width"] // f, alto=perfil_s["height"] // f))

    # capas del evento: combinado si existe, si no el track de la serie
    comb = BASE / zona / "combinado"
    if (comb / "extension_confirmada.tif").exists():
        ext, perfil_e = leer(comb / "extension_confirmada.tif")
        d_e = comb
    else:
        ext, perfil_e = leer(tdir / "metricas" / "extension_max.tif")
        d_e = tdir / "metricas"
    pers, _ = leer(d_e / "persistencia_dias.tif")
    ret, _ = leer(d_e / "fecha_retiro.tif")
    fe_ = factor(perfil_e)
    sl = (slice(None, None, fe_), slice(None, None, fe_))
    ext, pers, ret = ext[sl] == 1, pers[sl], ret[sl]
    previa = (leer(d_e / "agua_previa.tif")[0][sl] == 1) if (d_e / "agua_previa.tif").exists() else np.zeros(ext.shape, bool)
    o = rgba(ext.shape)
    o[previa] = (*PREVIA, 255)
    o[ext] = (*NARANJA, 255)
    png(out / "extension.png", o)
    o = rgba(ext.shape)
    for a, b, c in PERS_BINS:
        o[ext & (pers >= a) & (pers <= b)] = (*c, 255)
    o[ext & (ret == 999)] = (*SIGUE, 255)
    png(out / "persistencia.png", o)
    o = rgba(ext.shape)
    doy = lambda s: pd.Timestamp(s).day_of_year
    for a, b, c in RETIRO_BINS:
        o[ext & (ret >= doy(a)) & (ret <= doy(b))] = (*c, 255)
    o[ext & (ret == 999)] = (*SIGUE, 255)
    png(out / "retiro.png", o)
    # agua bajo monte ribereño: unión de los tracks llevada a la grilla del evento
    veg = np.zeros((perfil_e["height"], perfil_e["width"]), "uint8")
    for t in sorted((BASE / zona).glob("T*_F*/metricas/veg_inundada_ribereno.tif")):
        v, pv = leer(t)
        veg |= a_grilla(v.astype("uint8"), pv, perfil_e)
    o = rgba(ext.shape)
    o[veg[sl] == 1] = (*MONTE, 255)
    png(out / "monte.png", o)
    capas["evento"] = dict(esquinas=esquinas(perfil_e), ancho=ext.shape[1], alto=ext.shape[0],
                           fuente="combined" if d_e == comb else "single track")

    # sonda: HH (dB) y fracción de agua nueva por fecha a ~200 m, track de la serie
    k = max(1, int(round(SONDA_M / abs(perfil_s["transform"].a))))
    H, W = (perfil_s["height"] // k) * k, (perfil_s["width"] // k) * k
    bloques = []
    for i, fe in enumerate(fechas):
        x = hh[i][:H, :W].reshape(H // k, k, W // k, k)
        lin = np.nanmean(10 ** (x / 10), axis=(1, 3))
        db = 10 * np.log10(lin)
        hcode = np.where(np.isfinite(db), np.clip(np.round((db + 30) * 5), 0, 254), 255).astype("uint8")
        m = pila[desc.index(str(fe.date()))][:H, :W].reshape(H // k, k, W // k, k)
        ok = (m != 255).sum(axis=(1, 3))
        frac = np.where(ok > 0, np.round(100 * (m == 1).sum(axis=(1, 3)) / np.maximum(ok, 1)), 255).astype("uint8")
        bloques += [hcode, frac]
    np.stack(bloques).tofile(out / "sonda.bin")
    capas["sonda"] = dict(ancho=W // k, alto=H // k, n=len(fechas), celda_m=k * abs(perfil_s["transform"].a),
                          esquinas=esquinas(dict(perfil_s, width=W, height=H)),
                          codigo="por fecha: HH uint8 = (dB+30)*5 (255 sin dato), luego agua nueva % (255 sin dato)")
    return capas


def series_zona(zona):
    """% agua nueva por fecha (track de la serie) con banda de sensibilidad + 'remaining' y km de caminos."""
    t = ZONAS[zona]["serie"]
    pf = pd.read_csv(BASE / "metricas_por_fecha.csv")
    pf = pf[(pf.zona == zona) & (pf.track == t)].set_index("fecha")
    sb = pd.read_csv(BASE / "sensibilidad_por_fecha.csv")
    sb = sb[(sb.zona == zona) & (sb.track == t)].set_index("fecha")
    cp = pd.read_csv(IMP / "caminos_por_fecha.csv")
    cp = cp[cp.zona == zona].set_index("fecha")
    with rasterio.open(BASE / zona / t / "metricas" / "agua_nueva_por_fecha.tif") as r:
        pila, desc = r.read(), list(r.descriptions)
    ext, perfil_t = leer(BASE / zona / t / "metricas" / "extension_max.tif")
    ext = (ext == 1) & ~previa_en_grilla(zona, perfil_t)     # "remaining" = sólo agua de la tormenta
    out = []
    for fecha, r in pf.iterrows():
        m = pila[desc.index(fecha)]
        rem = round(100 * float(((m == 1) & ext).sum()) / max(int(ext.sum()), 1), 1) if pd.Timestamp(fecha) >= INICIO_LLUVIA else None
        out.append(dict(fecha=fecha, fase=r.fase, v=round(r.pct_agua_nueva, 2),
                        lo=round(float(sb.loc[fecha, "min"]), 2) if fecha in sb.index else None,
                        hi=round(float(sb.loc[fecha, "max"]), 2) if fecha in sb.index else None,
                        remaining=rem,
                        km=round(float(cp.loc[fecha, "km_bajo_agua"]), 1) if fecha in cp.index else None))
    return out


def tabla(path, zona=None, cols=None, n=None, orden=None):
    if not path.exists():
        return []
    df = pd.read_csv(path)
    if zona is not None and "zona" in df.columns:
        df = df[df.zona == zona]
    if orden:
        df = df.sort_values(orden, ascending=False)
    if cols:
        df = df[[c for c in cols if c in df.columns]]
    if n:
        df = df.head(n)
    return json.loads(df.to_json(orient="records", double_precision=3))


def resumen_zona(zona):
    res = pd.read_csv(IMP / "resumen.csv").set_index("zona").loc[zona]
    mr = pd.read_csv(BASE / "metricas_resumen.csv")
    t = ZONAS[zona]["serie"]
    fila_t = mr[(mr.zona == zona) & (mr.track == t)].iloc[0]
    sens = pd.read_csv(BASE / "sensibilidad_resumen.csv")
    s = sens[(sens.zona == zona) & (sens.track == t)].iloc[0]
    cr = pd.read_csv(BASE / "combinado_resumen.csv").set_index("zona")
    comb = cr.loc[zona] if zona in cr.index else None
    monte = pd.read_csv(BASE / "monte_ribereno_resumen.csv")
    monte = monte[monte.zona == zona]
    return dict(
        ha_inundada=round(float(res.ha_inundada)), ha_previa=round(float(res.ha_agua_previa)), fuente=res.fuente, ha_dia=round(float(res.ha_dia)),
        km_caminos=round(float(res.km_caminos_bajo_agua), 1), km_caminos_7d=round(float(res.km_caminos_mas_7_dias), 1),
        serie_track=t, serie_ha_ext=round(float(s["central"])), serie_pct_ext=round(float(fila_t.pct_extension_max), 2),
        serie_ha_lo=round(float(s["min"])), serie_ha_hi=round(float(s["max"])),
        persist_mid=None if comb is None else float(comb.persistencia_mediana_dias),
        persist_min=float(comb.persistencia_min_mediana if comb is not None else fila_t.persistencia_min_mediana),
        persist_max=float(comb.persistencia_max_mediana if comb is not None else fila_t.persistencia_max_mediana),
        pct_sigue=float(comb.pct_sigue_con_agua if comb is not None else fila_t.pct_sigue_con_agua),
        ha_max_una_obs=None if comb is None else round(float(comb.ha_extension_max)),
        obs_evento=None if comb is None else comb.obs_evento,
        tracks=[dict(track=r.track, ha=round(r.ha_extension_max), pct=round(r.pct_extension_max, 2))
                for r in mr[mr.zona == zona].itertuples()],
        monte=json.loads(monte.to_json(orient="records", double_precision=2)))


def validacion():
    v = dict(pares=tabla(BASE / "armonizacion_pares.csv"), s1=tabla(BASE / "validacion_s1.csv"))
    # cronología: fecha del máximo de agua nueva (serie) vs cresta reportada
    pf = pd.read_csv(BASE / "metricas_por_fecha.csv")
    cron = []
    for zona, (cresta, txt) in CRESTAS.items():
        g = pf[(pf.zona == zona) & (pf.track == ZONAS[zona]["serie"]) & (pf.fase != "base")]
        g = g[(g.fecha >= str(EVENTO[0].date())) & (g.fecha <= str(EVENTO[1].date()))]   # ventana del evento
        if g.empty:
            continue
        pk = g.loc[g.pct_agua_nueva.idxmax()]
        cron.append(dict(zona=zona, cresta=cresta, cresta_txt=txt, pico_nisar=pk.fecha,
                         pico_pct=round(float(pk.pct_agua_nueva), 2),
                         pasadas=[dict(fecha=r.fecha, v=round(r.pct_agua_nueva, 2)) for r in g.itertuples()]))
    v["cronologia"] = cron
    return v


def monte_mercedes():
    m = pd.read_csv(BASE / "monte_ribereno.csv")
    m = m[m.zona == "mercedes"]
    out = []
    for track, g in m.groupby("track"):
        series = {}
        for clase, gc in g.groupby("clase"):
            base = gc[gc.fase == "base"].hh_hv_db.mean()
            series[clase] = [dict(fecha=str(r.fecha)[:10], v=round(r.hh_hv_db - base, 2))
                             for r in gc.sort_values("fecha").itertuples() if np.isfinite(r.hh_hv_db)]
        out.append(dict(track=track, series=series))
    return out


def descargas():
    d = SAL / "descargas"
    d.mkdir(exist_ok=True)
    archivos = []
    for src, nombre, desc in [
        (BASE / "metricas_resumen.csv", "flood_metrics_by_track.csv", "Flood metrics per area and orbit track"),
        (BASE / "metricas_por_fecha.csv", "new_water_by_pass.csv", "New-water share on every NISAR pass"),
        (BASE / "combinado_resumen.csv", "flood_metrics_combined.csv", "All tracks combined (confirmed extent, persistence)"),
        (BASE / "sensibilidad_resumen.csv", "sensitivity_extent.csv", "Extent range across detector settings"),
        (IMP / "caminos.csv", "roads_under_water.csv", "Rural roads under water: km and days"),
        (IMP / "localidades.csv", "localities.csv", "Towns: flooded area inside and within 500 m"),
        (IMP / "subcuencas.csv", "sub_basins.csv", "Sub-basins (HydroBASINS L8): ha and hectare-days"),
        (IMP / "uso_suelo.csv", "land_cover.csv", "Flooded area by land cover (ESA WorldCover)"),
        (BASE / "armonizacion_pares.csv", "track_agreement.csv", "Agreement between tracks ≤1 day apart"),
        (BASE / "validacion_s1.csv", "validation_sentinel1.csv", "Comparison with Sentinel-1 (validation only)"),
        (IMP / "caminos.geojson", "roads_under_water.geojson", "Flooded road segments (GeoJSON)"),
    ]:
        if src.exists():
            if src.name == "localidades.csv":                      # columna con listas: fuera del CSV público
                pd.read_csv(src).drop(columns=["serie_500m"], errors="ignore").to_csv(d / nombre, index=False)
            else:
                shutil.copy(src, d / nombre)
            archivos.append(dict(archivo=f"data/descargas/{nombre}", desc=desc, kb=round((d / nombre).stat().st_size / 1024)))
    for zona in ZONAS:
        comb = BASE / zona / "combinado"
        src = comb if (comb / "extension_confirmada.tif").exists() else BASE / zona / ZONAS[zona]["serie"] / "metricas"
        e, p = leer(src / ("extension_confirmada.tif" if src == comb else "extension_max.tif"))
        pers, _ = leer(src / "persistencia_dias.tif")
        ret, _ = leer(src / "fecha_retiro.tif")
        pers = np.where(ret == 999, 255, np.clip(pers, 0, 254))
        pers = np.where(e == 1, pers, 0).astype("uint8")
        prof = p.copy()
        prof.update(driver="GTiff", count=2, dtype="uint8", compress="deflate", nodata=None, tiled=True,
                    blockxsize=256, blockysize=256)
        nombre = f"{zona}_flood_extent_persistence.tif"
        with rasterio.open(d / nombre, "w", **prof) as dst:
            dst.write(e.astype("uint8"), 1)
            dst.write(pers, 2)
            dst.set_band_description(1, "flooded (1) 10 Aug - 10 Sep 2026")
            dst.set_band_description(2, "days under water (midpoint); 255 = still wet on 20 Oct")
        archivos.append(dict(archivo=f"data/descargas/{nombre}", desc=f"{NOMBRES[zona][0]}: GeoTIFF, band 1 flooded, band 2 days under water",
                             kb=round((d / nombre).stat().st_size / 1024)))
    return archivos


def impacto_geo():
    d = SAL / "impacto"
    d.mkdir(exist_ok=True)
    for n in ("caminos", "localidades", "subcuencas"):
        if (IMP / f"{n}.geojson").exists():
            shutil.copy(IMP / f"{n}.geojson", d / f"{n}.geojson")


def cifras(zonas):
    """Cifras de portada, todas derivadas."""
    m = zonas["merin_arrozales"]
    rem = [s for s in m["fechas"] if s["remaining"] is not None]
    pico = max(rem, key=lambda s: s["remaining"])
    sep21 = next((s for s in rem if s["fecha"] >= "2026-09-20"), None)
    total_ha = sum(z["resumen"]["ha_inundada"] for z in zonas.values())
    total_km = sum(z["resumen"]["km_caminos"] for z in zonas.values())
    total_previa = sum(z["resumen"]["ha_previa"] for z in zonas.values())
    return dict(ha_total=total_ha, ha_previa=total_previa, km_total=round(total_km), merin_ha=m["resumen"]["ha_inundada"],
                merin_pico_fecha=pico["fecha"], merin_pico_pct=pico["remaining"],
                merin_sep_fecha=sep21["fecha"] if sep21 else None, merin_sep_pct=sep21["remaining"] if sep21 else None,
                merin_ha_lo=m["resumen"]["serie_ha_lo"], merin_ha_hi=m["resumen"]["serie_ha_hi"],
                desplazados=2229, desplazados_fecha="2026-08-22")


def main():
    if SAL.exists():
        shutil.rmtree(SAL)
    SAL.mkdir(parents=True)
    if not COUNTRIES.exists():
        bajar_countries(COUNTRIES)
    zonas = {}
    for zona in ZONAS:
        print(f"== {zona}")
        out = SAL / zona
        out.mkdir()
        zonas[zona] = dict(
            id=zona, nombre=NOMBRES[zona][0], rio=NOMBRES[zona][1], cuenca=CUENCA[zona],
            descripcion=DESCRIPCION[zona], capas=capas_zona(zona, out), fechas=series_zona(zona),
            resumen=resumen_zona(zona),
            caminos=tabla(IMP / "caminos.csv", zona, ["nombre", "donde", "clase", "km", "km_bajo_agua", "dias_mid",
                                                      "dias_min", "dias_max", "sigue", "lon", "lat"], 15, ["km_bajo_agua"]),
            localidades=tabla(IMP / "localidades.csv", zona, ["nombre", "place", "ha_area", "ha_inundada",
                                                              "ha_inundada_500m", "ha_dia_500m", "serie_500m"]),
            subcuencas=tabla(IMP / "subcuencas.csv", zona, ["nombre", "ha_area", "ha_inundada", "pct_inundada", "ha_dia",
                                                            "ha_dia_min", "ha_dia_max", "retiro_mediano"], None, ["ha_dia"]),
            uso_suelo=tabla(IMP / "uso_suelo.csv", zona, ["clase", "ha_clase", "ha_inundada", "pct_clase_inundada", "ha_dia"]),
        )
        for l in zonas[zona]["localidades"]:
            if isinstance(l.get("serie_500m"), str):
                l["serie_500m"] = json.loads(l["serie_500m"].replace("'", '"'))
    impacto_geo()
    manifest = dict(generado=str(date.today()), evento=dict(lluvia=["2026-08-15", "2026-08-19"], ventana=[str(EVENTO[0].date()), str(EVENTO[1].date())],
                                                         tormenta=[str(INICIO_LLUVIA.date()), str(EVENTO[1].date())],
                                                         hueco=["2026-07-27", "2026-08-10"]),
                    cifras=cifras(zonas), zonas=zonas, validacion=validacion(), monte_mercedes=monte_mercedes(),
                    contexto=contexto(COUNTRIES), descargas=descargas(),
                    leyendas=dict(persistencia=[dict(rango=f"{a}–{b}" if b < 9999 else f"{a}+", color="rgb(%d,%d,%d)" % c) for a, b, c in PERS_BINS],
                                  retiro=[dict(desde=a, hasta=b, color="rgb(%d,%d,%d)" % c) for a, b, c in RETIRO_BINS],
                                  sigue="rgb(%d,%d,%d)" % SIGUE, previa="rgb(%d,%d,%d)" % PREVIA))
    (SAL / "manifest.json").write_text(json.dumps(manifest, separators=(",", ":"), allow_nan=False, default=str))
    tam = sum(p.stat().st_size for p in SAL.rglob("*") if p.is_file()) / 1e6
    print(f"-> {SAL}  ({tam:.1f} MB)")


if __name__ == "__main__":
    main()
