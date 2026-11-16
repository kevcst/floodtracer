"""
Exporta lo que necesita la app web (app/: index.html, explorer.html, method.html) a app/data/.

  python scripts/exportar_app.py          # después: python scripts/exportar_metodo.py (agrega la entrada "metodo")

Requiere el resto del pipeline (README §4). Borra y regenera app/data/ salvo app/data/metodo/ (exportar_metodo.py).

Sale en app/data/:
  manifest.json                 todo número que muestra la app (nada escrito a mano en el HTML ni en los JS)
  {zona}/hh_{fecha}.webp        HH en gris (WebP con alfa) del track de la serie, una imagen por pasada
  {zona}/agua_{fecha}.png       agua permanente (azul), agua nueva (naranja) y agua previa a la lluvia (cian) de esa pasada
  {zona}/extension.png          extensión confirmada (combinado) con el agua previa · monte.png: agua bajo monte ribereño
  {zona}/sonda.bin              HH y agua por fecha a ~200 m para el clic en el mapa de la historia (ver capas.sonda)
  impacto/caminos.geojson       caminos OSM con días bajo agua (WGS84)
  secado.geojson                celdas de HEAT_M con días bajo agua para el heatmap "dónde se quedó más tiempo el agua"
  contexto/*.webp               escenas de la historia (óptico, S1 vs NISAR, monte, ejemplo de secado)
Las imágenes llevan las 4 esquinas en lon/lat para un "image source" de MapLibre.

Campos del manifest que usa la app, además de capas/fechas/resumen por zona:
  zonas[z].resumen.dia_mitad_seca · dia_90_seco    primera pasada (después de la más mojada) con ≤ 50 % / ≤ 10 % de la
                                  huella del evento todavía mojada ("remaining" de la serie)
  zonas[z].fechas[].viento_ms / confianza   viento ERA5 a la hora de la pasada y "baja" si ≥ VIENTO_BAJA_CONF m/s
  zonas[CASO].validacion          Sentinel-1 (+ medias), pares de tracks a ≤ 1 día (+ Jaccard medio) y agua_conocida (JRC,
                                  con la columna excluido de zonas.excluir_tracks); JRC y S1 sólo validan (regla 1)
  cifras.revisita_dias            mediana del intervalo entre pasadas de las series
  contexto.zonas                  bbox de cada zona · contexto.caso / prensa_caso (regla 4: preliminar, con fuentes)
  contexto.optico · s1_vs_nisar · monte_caso · secado_ejemplo   escenas de la historia
  secado.dias[zona]               días mínimo y máximo de las celdas del heatmap (leyenda)
  leyendas.persistencia · previa  rangos de días (escala de caminos) y color del agua previa
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

from shapely import wkt as shp_wkt
from metricas_evento import BASE, EVENTOS, Evento, cargar_track, previa_en_grilla, tracks_zona
from zonas import ZONAS

warnings.filterwarnings("ignore")
RAIZ = BASE.parents[1]
APP = RAIZ / "app"
SAL = APP / "data"
IMP = BASE / "impacto"

NOMBRES = {"treinta_y_tres": "Treinta y Tres", "merin_arrozales": "Laguna Merín rice fields",
           "rio_branco_jaguarao": "Río Branco / Jaguarão", "rocha_norte": "Northern Rocha"}
NARANJA, AZUL = (235, 104, 52), (42, 120, 214)
# persistencia (días): rangos de la escala de caminos de la app
PERS_BINS = [(0, 7, (198, 219, 245)), (8, 14, (138, 182, 238)), (15, 28, (74, 140, 222)), (29, 42, (36, 98, 176)),
             (43, 9999, (18, 64, 124))]
MONTE = (27, 175, 122)
PREVIA = (60, 200, 230)           # inundación presente antes de la tormenta (lluvias de julio y principios de agosto;
                                  # última pasada antes de la lluvia = 15/8 09:29 UTC): celeste, fuera de la tormenta. Antes gris, que se
                                  # confundía con el radar
MAX_LADO = 2200
SONDA_M = 200.0
FACTOR_RUIDO = 2.0   # zona concluyente si lo inundado (≥ 2 obs.) es al menos 2× el piso de ruido del detector


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
    previa_s = previa_en_grilla(zona, perfil_s)[::f, ::f]   # agua ya mojada antes de la lluvia: celeste también por fecha
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
        if fe >= Evento(zona).ventana[0]:                    # en la base no aplica
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
    fe_ = factor(perfil_e)
    sl = (slice(None, None, fe_), slice(None, None, fe_))
    ext = ext[sl] == 1
    previa = (leer(d_e / "agua_previa.tif")[0][sl] == 1) if (d_e / "agua_previa.tif").exists() else np.zeros(ext.shape, bool)
    o = rgba(ext.shape)
    o[previa] = (*PREVIA, 255)
    o[ext] = (*NARANJA, 255)
    png(out / "extension.png", o)
    # agua bajo monte ribereño: unión de los tracks llevada a la grilla del evento
    veg = np.zeros((perfil_e["height"], perfil_e["width"]), "uint8")
    for t in [d / "metricas" / "veg_inundada_ribereno.tif" for d in tracks_zona(zona) if (d / "metricas" / "veg_inundada_ribereno.tif").exists()]:
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
    ev = Evento(zona)
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
    previa_f = dict(zip(desc, ev.es_previa(pd.DatetimeIndex(desc), t)))
    out = []
    for fecha, r in pf.iterrows():
        m = pila[desc.index(fecha)]
        # denominador = la huella con dato en esa pasada (255 = sin dato: cultivos desde octubre, metricas_evento)
        con_dato = ext & (m != 255)
        rem = (round(100 * float(((m == 1) & con_dato).sum()) / max(int(con_dato.sum()), 1), 1)
               if pd.Timestamp(fecha) >= ev.inicio and not previa_f[fecha] else None)
        out.append(dict(fecha=fecha, fase=r.fase, v=round(r.pct_agua_nueva, 2), dia=(pd.Timestamp(fecha) - ev.inicio).days,
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
    if "excluido" in mr:                                   # tracks sólo de diagnóstico (zonas.excluir_tracks)
        mr = mr[~mr.excluido.astype(bool)]
    t = ZONAS[zona]["serie"]
    fila_t = mr[(mr.zona == zona) & (mr.track == t)].iloc[0]
    sens = pd.read_csv(BASE / "sensibilidad_resumen.csv")
    s = sens[(sens.zona == zona) & (sens.track == t)].iloc[0]
    cr = pd.read_csv(BASE / "combinado_resumen.csv").set_index("zona")
    comb = cr.loc[zona] if zona in cr.index else None
    monte = pd.read_csv(BASE / "monte_ribereno_resumen.csv")
    monte = monte[monte.zona == zona]
    # piso de ruido: falsa alarma del detector en las pasadas base (dejar-una-afuera, metricas_evento.falsa_alarma_base),
    # mediana entre los tracks de la zona. Sin estimación (< 2 pasadas base en todos los tracks) = no concluyente.
    ruido = mr[mr.zona == zona].ha_ruido_base.dropna()
    ha_ruido = float(ruido.median()) if len(ruido) else None
    if ha_ruido is None:
        motivo = "una_base"
    elif float(res.ha_inundada) < FACTOR_RUIDO * ha_ruido:
        motivo = "bajo_ruido"
    else:
        motivo = None
    return dict(
        concluyente=motivo is None, motivo_no_concluyente=motivo,
        ha_ruido=None if ha_ruido is None else round(ha_ruido), factor_ruido=FACTOR_RUIDO,
        # el track de la serie no encontró agua permanente oscura para calibrar (calibrar_umbral): la detección de agua
        # abierta es menos confiable y "poca agua" pesa menos
        sin_agua_permanente=bool(pd.isna(fila_t.agua_perm_db)),
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
        tracks=[dict(track=r.track, ha=round(r.ha_extension_max), pct=round(r.pct_extension_max, 2),
                     pct_falsa_alarma=None if pd.isna(r.pct_falsa_alarma_base) else round(r.pct_falsa_alarma_base, 2))
                for r in mr[mr.zona == zona].itertuples()],
        monte=json.loads(monte.to_json(orient="records", double_precision=2)))


def impacto_geo():
    d = SAL / "impacto"
    d.mkdir(exist_ok=True)
    shutil.copy(IMP / "caminos.geojson", d / "caminos.geojson")


def evento_json(zona):
    ev = Evento(zona)
    d = lambda t: str(t.date())
    return dict(clave=ev.clave, nombre=ev.nombre, lluvia=[d(ev.lluvia[0]), d(ev.lluvia[1])], ventana=[d(ev.ventana[0]), d(ev.ventana[1])],
                tormenta=[d(ev.inicio), d(ev.ventana[1])], hueco=["2026-07-27", "2026-08-10"])


HEAT_M = 400.0      # celda del heatmap de secado


def secado_heatmap(zonas):
    """Puntos (centro de celda ~400 m) con días bajo agua, para el heatmap "dónde tarda más en secarse".
    Peso = días medios bajo agua de los píxeles inundados × fracción inundada de la celda (≈ ha·día por ha).
    Las celdas que siguen mojadas en la última pasada usan la cota (última pasada − primera detección).
    Se escribe app/data/secado.geojson; el manifest guarda el máximo para normalizar en la app."""
    from agregar_impacto import productos
    feats, wmax = [], 0.0
    for zona in zonas:
        p = productos(zona)
        ext, pers, perfil = p["ext"], p["pers"]["mid"], p["perfil"]
        k = max(1, int(round(HEAT_M / abs(perfil["transform"].a))))
        H, W = (ext.shape[0] // k) * k, (ext.shape[1] // k) * k
        e = ext[:H, :W].reshape(H // k, k, W // k, k)
        d = np.where(ext, pers, 0)[:H, :W].reshape(H // k, k, W // k, k).astype("float32")
        s = p["sigue"][:H, :W].reshape(H // k, k, W // k, k)
        n = e.sum(axis=(1, 3))
        frac = n / (k * k)
        dias = np.where(n > 0, d.sum(axis=(1, 3)) / np.maximum(n, 1), 0)
        sig = s.sum(axis=(1, 3)) / np.maximum(n, 1)
        ii, jj = np.where(frac >= 0.05)
        t = perfil["transform"]
        xs = t.c + (jj * k + k / 2) * t.a
        ys = t.f + (ii * k + k / 2) * t.e
        lon, lat = warp_transform(perfil["crs"], "EPSG:4326", list(xs), list(ys))
        for a, b, i, j in zip(lon, lat, ii, jj):
            w = float(dias[i, j] * frac[i, j])
            wmax = max(wmax, w)
            feats.append(dict(type="Feature", geometry=dict(type="Point", coordinates=[round(a, 5), round(b, 5)]),
                              properties=dict(z=zona, d=int(round(dias[i, j])), f=round(float(frac[i, j]), 2),
                                              w=round(w, 2), s=round(float(sig[i, j]), 2))))
    (SAL / "secado.geojson").write_text(json.dumps(dict(type="FeatureCollection", features=feats), separators=(",", ":")))
    print(f"   heatmap secado: {len(feats)} celdas")
    dias = {}
    for f in feats:
        z, dd = f["properties"]["z"], f["properties"]["d"]
        lo, hi = dias.get(z, (dd, dd))
        dias[z] = (min(lo, dd), max(hi, dd))
    return dict(archivo="data/secado.geojson", celda_m=HEAT_M, w_max=round(wmax, 2), n=len(feats),
                dias={z: dict(min=lo, max=hi) for z, (lo, hi) in dias.items()})


CASO = "rocha_norte"        # zona del caso de estudio de la historia
VENTANA_S1 = 600            # lado (px de 20 m) del recorte S1 vs NISAR de la historia
# equivalencias humanas de la historia (escena 2). Superficie del departamento de Montevideo: 530 km² (INE).
def gris_db(x):
    """dB → gris (misma escala que hh_*.webp) y alfa (sin dato transparente)."""
    g = np.where(np.isfinite(x), np.clip((x + 22) / 20 * 255, 0, 255), 0).astype("uint8")
    return np.dstack([g, g, g, np.where(np.isfinite(x), 255, 0).astype("uint8")])


def pintar(img, mascara, color):
    img[mascara] = (*color, 255)
    return img


def ventana_max(m, n):
    """(fila, columna) de la ventana n×n con más píxeles True (suma acumulada, paso n/6)."""
    H, W = m.shape
    cs = np.pad(m.astype("int32").cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    mejor, rc = -1, (0, 0)
    for r0 in range(0, max(1, H - n + 1), max(1, n // 6)):
        for c0 in range(0, max(1, W - n + 1), max(1, n // 6)):
            s = cs[min(H, r0 + n), min(W, c0 + n)] - cs[r0, min(W, c0 + n)] - cs[min(H, r0 + n), c0] + cs[r0, c0]
            if s > mejor:
                mejor, rc = s, (r0, c0)
    return rc


def esquinas_ventana(perfil, r0, c0, h, w):
    from rasterio.windows import Window, transform as win_transform
    return esquinas(dict(perfil, width=w, height=h, transform=win_transform(Window(c0, r0, w, h), perfil["transform"])))


def optico_ctx():
    """Escena 1: recorte óptico (scripts/exportar_optico.py, caché) + el mismo recorte de la pasada NISAR."""
    out = {}
    d = SAL / "contexto"
    for mp in sorted((BASE.parent / "contexto" / "optico").glob("*.json")):
        meta = json.loads(mp.read_text())
        zona, (c0, r0, w, h) = meta["zona"], meta["ventana"]
        tdir = BASE / zona / meta["track"]
        fechas, hh, _, perfil = cargar_track(tdir)
        i = [str(f.date()) for f in fechas].index(meta["fecha_nisar"])
        with rasterio.open(tdir / "metricas" / "agua_nueva_por_fecha.tif") as r:
            m = r.read(list(r.descriptions).index(meta["fecha_nisar"]) + 1) == 1
        base = leer(tdir / "metricas" / "agua_base.tif")[0] == 1
        previa = previa_en_grilla(zona, perfil)
        sl = (slice(r0, r0 + h), slice(c0, c0 + w))
        d.mkdir(exist_ok=True)
        img = gris_db(hh[i][sl])
        pintar(img, base[sl], AZUL); pintar(img, m[sl], NARANJA); pintar(img, m[sl] & previa[sl], PREVIA)
        Image.fromarray(img, "RGBA").save(d / f"nisar_{zona}_{meta['fecha_nisar']}.webp", quality=82)
        tif = mp.with_suffix(".tif")
        opt = None
        if tif.exists():
            with rasterio.open(tif) as r:
                Image.fromarray(np.moveaxis(r.read(), 0, -1)).save(d / f"optico_{zona}.webp", quality=82)
            opt = f"data/contexto/optico_{zona}.webp"
        out[zona] = dict({k: meta[k] for k in ("track", "fecha_nisar", "fecha_s2", "nubes", "catalogo", "fuente", "escena", "buscado")},
                         optico=opt, nisar=f"data/contexto/nisar_{zona}_{meta['fecha_nisar']}.webp",
                         esquinas=esquinas_ventana(perfil, r0, c0, h, w), lado_km=round(w * abs(perfil["transform"].a) / 1000, 1))
    return out


def s1_par(zonas, zona=None):
    """Escena 5: par NISAR / Sentinel-1 de la zona del caso de estudio (CASO): el de menor desfase en días; entre esos,
    la pasada NISAR en calma (viento ERA5 < VIENTO_BAJA_CONF: el viento aclara el agua para los dos radares) y después
    donde NISAR ve más agua que S1. Sin el desempate por calma, al sacar el mar (15/11) ganaba una pasada con viento. S1 se rearma desde la caché de validar_s1.py con su mismo detector (sólo
    valida, regla 1)."""
    from validar_s1 import CACHE, S1_AGUA, S1_CAMBIO, S1_TECHO, db
    from metricas_evento import filtrar_mmu
    p = BASE / "validacion_s1.csv"
    if not p.exists():
        return None
    s1 = pd.read_csv(p)
    c = s1[s1.zona == (zona or CASO)].copy()
    if c.empty:
        return None
    c["adt"], c["dif"] = c.dt_dias.abs(), c.pct_nisar_cambio - c.pct_s1
    from clima import viento_pasadas
    c["ventoso"] = [bool(v >= VIENTO_BAJA_CONF) for v in
                    (viento_pasadas(z, t, [f])[0] for z, t, f in zip(c.zona, c.track, c.fecha_nisar))]
    r = c.sort_values(["adt", "ventoso", "dif"], ascending=[True, True, False]).iloc[0]
    tdir = BASE / r.zona / r.track
    fechas, hh, _, perfil = cargar_track(tdir)
    i = [str(f.date()) for f in fechas].index(r.fecha_nisar)
    with rasterio.open(tdir / "metricas" / "agua_nueva_por_fecha.tif") as src:
        nis = src.read(list(src.descriptions).index(r.fecha_nisar) + 1) == 1
    base = leer(tdir / "metricas" / "agua_base.tif")[0] == 1
    previa = previa_en_grilla(r.zona, perfil)
    cache, orb, fin_base = CACHE / r.zona / r.track, int(r.orbita_s1), Evento(r.zona).fin_base
    bases = [f for f in sorted(cache.glob(f"*_o{orb}_VV.tif")) if pd.Timestamp(f.name[:10]) < fin_base]
    lee = lambda f: db(leer(f)[0])
    pila = np.stack([lee(f) for f in bases])
    vv_med, s1_base = np.nanmedian(pila, axis=0), (pila < S1_AGUA).mean(axis=0) > 0.5
    vv = lee(cache / f"{r.fecha_s1}_o{orb}_VV.tif")
    dd = vv - vv_med
    okv = np.isfinite(dd)
    off = float(np.nanmedian(dd[okv & ~s1_base]))
    s1n = filtrar_mmu((dd - off < S1_CAMBIO) & (vv < S1_TECHO) & ~s1_base & okv)
    valid = okv & np.isfinite(hh[i])
    nis_sp = nis & ~previa
    # agua que ve NISAR y S1 no, fuera del agua permanente de los dos (si no, la ventana cae en el borde de las lagunas)
    r0, c0 = ventana_max(nis_sp & ~s1n & valid & ~base & ~s1_base, VENTANA_S1)
    h, w = min(VENTANA_S1, nis.shape[0] - r0), min(VENTANA_S1, nis.shape[1] - c0)
    sl = (slice(r0, r0 + h), slice(c0, c0 + w))
    d = SAL / "contexto"
    d.mkdir(exist_ok=True)
    a = gris_db(np.where(valid, hh[i], np.nan)[sl])
    pintar(a, base[sl], AZUL); pintar(a, nis_sp[sl] & valid[sl], NARANJA); pintar(a, (nis & previa)[sl], PREVIA)
    b = gris_db(np.where(valid, vv, np.nan)[sl])
    pintar(b, (s1_base & valid)[sl], AZUL); pintar(b, (s1n & valid)[sl], NARANJA)
    fn = f"{r.zona}_{r.fecha_nisar}"
    Image.fromarray(a, "RGBA").save(d / f"nisar_vs_s1_{fn}.webp", quality=82)
    Image.fromarray(b, "RGBA").save(d / f"s1_vs_nisar_{fn}.webp", quality=82)
    v = valid[sl]
    return dict(zona=r.zona, track=r.track, fecha_nisar=r.fecha_nisar, fecha_s1=r.fecha_s1, orbita_s1=orb,
                nisar=f"data/contexto/nisar_vs_s1_{fn}.webp", s1=f"data/contexto/s1_vs_nisar_{fn}.webp",
                esquinas=esquinas_ventana(perfil, r0, c0, h, w), lado_km=round(w * abs(perfil["transform"].a) / 1000, 1),
                pct_nisar=round(float(r.pct_nisar_cambio), 2), pct_s1=round(float(r.pct_s1), 2),
                pct_nisar_ventana=round(100 * float((nis_sp[sl] & v).sum()) / max(int(v.sum()), 1), 1),
                pct_s1_ventana=round(100 * float((s1n[sl] & v).sum()) / max(int(v.sum()), 1), 1),
                recall=round(float(r.recall_cambio), 3), oscurece=round(float(r.solo_nisar_s1_oscurece_cambio), 3))


VENTANA_MONTE = 160         # lado (px de 20 m) del recorte del monte ribereño de la historia (3,2 km)
RATIO_DB = (2.0, 12.0)      # escala de gris del cociente HH−HV en dB (negro → blanco)


def monte_caso(zona=None):
    """Escena "agua bajo el monte": recorte donde más se concentra el monte ribereño con agua debajo (track de la
    serie), con el cociente HH−HV en gris (más claro = más doble rebote agua–tronco) en la base (mediana de las pasadas
    base) y en la pasada del evento con la señal ribereña más alta. Sólo visualiza productos existentes."""
    zona = zona or CASO
    tdir = BASE / zona / ZONAS[zona]["serie"]
    p = tdir / "metricas" / "veg_inundada_ribereno.tif"
    if not p.exists():
        return None
    vr = leer(p)[0] == 1
    fechas, hh, hv, perfil = cargar_track(tdir)
    fechas = pd.DatetimeIndex(fechas)
    ev = Evento(zona)
    es_base = ev.es_base(fechas, hh)
    ratio = hh - hv
    # ventana sobre monte de verdad: la señal ribereña cae también en bañado herbáceo (WorldCover 90); se centra en la que
    # además es cobertura arbórea (WorldCover 10). El agua permanente se pinta de azul: con viento el agua abierta sube su
    # HH−HV y, en gris, una laguna "se aclara" como si fuera monte inundado.
    wc_p = tdir / "contexto" / "worldcover.tif"
    arbol = (leer(wc_p)[0] == 10) if wc_p.exists() else np.ones_like(vr)
    agua_base = leer(tdir / "metricas" / "agua_base.tif")[0] == 1
    r0, c0 = ventana_max(vr & arbol, VENTANA_MONTE)
    h, w = min(VENTANA_MONTE, vr.shape[0] - r0), min(VENTANA_MONTE, vr.shape[1] - c0)
    sl = (slice(r0, r0 + h), slice(c0, c0 + w))
    base = np.nanmedian(ratio[es_base][(slice(None),) + sl], axis=0)
    cand = [i for i in np.where(ev.es_evento(fechas) | (fechas > ev.ventana[1]))[0] if np.isfinite(ratio[i][sl]).mean() > 0.9]
    if not cand:
        return None
    i_post = max(cand, key=lambda i: np.nanmean(ratio[i][sl][vr[sl]]))
    from scipy import ndimage as ndi
    zona_m = ndi.binary_closing((vr & arbol)[sl], iterations=2)
    borde = ndi.binary_dilation(zona_m, iterations=2) & ~zona_m          # contorno verde del monte con agua debajo
    gris = lambda x: pintar(pintar(gris_db(np.where(np.isfinite(x), (x - RATIO_DB[0]) / (RATIO_DB[1] - RATIO_DB[0]) * 20 - 22, np.nan)),
                                   agua_base[sl], AZUL), borde, MONTE)
    d = SAL / "contexto"
    d.mkdir(exist_ok=True)
    f_post = str(fechas[i_post].date())
    Image.fromarray(gris(base), "RGBA").save(d / f"monte_base_{zona}.webp", quality=85)
    Image.fromarray(gris(ratio[i_post][sl]), "RGBA").save(d / f"monte_post_{zona}.webp", quality=85)
    sube = float(np.nanmedian((ratio[i_post][sl] - base)[(vr & arbol)[sl]]))
    return dict(track=tdir.name, fecha_post=f_post, base=f"data/contexto/monte_base_{zona}.webp", post=f"data/contexto/monte_post_{zona}.webp",
                esquinas=esquinas_ventana(perfil, r0, c0, h, w), lado_km=round(w * abs(perfil["transform"].a) / 1000, 1),
                n_base=int(es_base.sum()), ha_ventana=round(float((vr & arbol)[sl].sum()) * abs(perfil["transform"].a * perfil["transform"].e) / 1e4),
                sube_db=round(sube, 2))


VENTANA_SECADO = 150        # lado (px de 20 m) del ejemplo "cómo surge el heatmap" (3 km)
SECADO_N_PASADAS = 4        # pasadas del evento que se muestran en el ejemplo
DIAS_COLORES = [(0, (254, 224, 144)), (7, (253, 174, 97)), (14, (244, 109, 67)), (28, (215, 48, 39)), (42, (103, 0, 31))]   # = celdas del heatmap


def secado_ejemplo(zona=None):
    """Escena del heatmap: recorte de la serie donde el agua duró más, con el radar + agua en las primeras pasadas del
    evento y los días bajo agua que resultan (misma rampa que las celdas del heatmap)."""
    zona = zona or CASO
    tdir = BASE / zona / ZONAS[zona]["serie"]
    m = tdir / "metricas"
    if not (m / "persistencia_dias.tif").exists():
        return None
    pers, perfil = leer(m / "persistencia_dias.tif")
    ext = leer(m / "extension_max.tif")[0] == 1
    base = leer(m / "agua_base.tif")[0] == 1
    previa = previa_en_grilla(zona, perfil)
    largo = ext & ~previa & (pers >= DIAS_COLORES[3][0])
    r0, c0 = ventana_max(largo, VENTANA_SECADO)
    h, w = min(VENTANA_SECADO, pers.shape[0] - r0), min(VENTANA_SECADO, pers.shape[1] - c0)
    sl = (slice(r0, r0 + h), slice(c0, c0 + w))
    fechas, hh, _, _ = cargar_track(tdir)
    ev = Evento(zona)
    fs = [str(f.date()) for f in fechas]
    with rasterio.open(m / "agua_nueva_por_fecha.tif") as r:
        pila, desc = r.read(), list(r.descriptions)
    idx = [i for i, f in enumerate(fechas) if f >= ev.inicio and fs[i] in desc][:SECADO_N_PASADAS]
    d = SAL / "contexto"
    d.mkdir(exist_ok=True)
    out = []
    for i in idx:
        n = pila[desc.index(fs[i])][sl] == 1
        im = gris_db(hh[i][sl])
        pintar(im, base[sl], AZUL); pintar(im, n & ~previa[sl], NARANJA); pintar(im, n & previa[sl], PREVIA)
        Image.fromarray(im, "RGBA").save(d / f"secado_{zona}_{fs[i]}.webp", quality=82)
        out.append(dict(fecha=fs[i], img=f"data/contexto/secado_{zona}_{fs[i]}.webp"))
    dias = np.zeros((h, w, 4), "uint8")
    zona_ok = (ext & ~previa)[sl]
    for k, (desde, col) in enumerate(DIAS_COLORES):
        hasta = DIAS_COLORES[k + 1][0] if k + 1 < len(DIAS_COLORES) else 1e9
        dias[zona_ok & (pers[sl] >= desde) & (pers[sl] < hasta)] = (*col, 255)
    gris = gris_db(hh[idx[0]][sl]) if idx else dias
    gris[..., 3] = 255
    gris[dias[..., 3] > 0] = dias[dias[..., 3] > 0]
    pintar(gris, base[sl], AZUL)
    Image.fromarray(gris, "RGBA").save(d / f"secado_{zona}_dias.webp", quality=85)
    return dict(track=tdir.name, pasadas=out, dias=f"data/contexto/secado_{zona}_dias.webp",
                esquinas=esquinas_ventana(perfil, r0, c0, h, w), lado_km=round(w * abs(perfil["transform"].a) / 1000, 1),
                dias_mediana=int(np.median(pers[sl][zona_ok])) if zona_ok.any() else None,
                colores=[dict(desde=a, color="rgb(%d,%d,%d)" % c) for a, c in DIAS_COLORES])


VIENTO_BAJA_CONF = 3.0      # m/s: pasada con viento ≥ esto = "baja confianza" (el mismo corte que define las pasadas de calma)
# prensa del caso de estudio (regla 4: preliminar). Fuentes en docs/event_context_aug2026.md
PRENSA_CASO = dict(zona="rocha_norte", ha_min=5000, ha_max=6000, vacunos=15000, fecha="2026-08-19",
                   lugar="18 de Julio", fuentes=["APU 20/8", "La R 21/8", "InfoUruguay 19/8", "Agrolatam 24/8"], preliminar=True)


def viento_fechas(zona, fechas):
    """Agrega viento_ms (ERA5 a la hora de la pasada, clima_pasadas.csv) y confianza a cada fecha de la serie."""
    p = BASE / zona / "clima_pasadas.csv"
    c = pd.read_csv(p) if p.exists() else pd.DataFrame(columns=["track", "fecha", "viento"])
    c = c[c.track == ZONAS[zona]["serie"]].set_index("fecha")
    for f in fechas:
        v = float(c.loc[f["fecha"], "viento"]) if f["fecha"] in c.index and pd.notna(c.loc[f["fecha"], "viento"]) else None
        f["viento_ms"] = None if v is None else round(v, 1)
        f["confianza"] = None if v is None else ("baja" if v >= VIENTO_BAJA_CONF else "normal")


def validacion_zona(zona):
    """Validación de una zona: Sentinel-1 (validacion_s1.csv) y acuerdo entre tracks a ≤ 1 día (armonizacion_pares.csv)."""
    s1 = pd.read_csv(BASE / "validacion_s1.csv")
    s1 = s1[s1.zona == zona]
    ar = pd.read_csv(BASE / "armonizacion_pares.csv")
    ar = ar[ar.zona == zona]
    ev = ar[ar.fase != "base"]
    # sin los pares que cruzan el inicio de la lluvia (una pasada previa y la otra no): comparan estados distintos
    e = Evento(zona)
    cruza = [bool(e.es_previa(pd.DatetimeIndex([r.fecha_a]), r.track_a)[0]) != bool(e.es_previa(pd.DatetimeIndex([r.fecha_b]), r.track_b)[0])
             for r in ev.itertuples()]
    ev = ev[[not c for c in cruza]]
    cols_s1 = ["track", "fecha_nisar", "fecha_s1", "dt_dias", "pct_s1", "pct_nisar_cambio", "precision_cambio", "recall_cambio",
               "f1_cambio", "f1_cambio_laxa"]
    return dict(s1=json.loads(s1[cols_s1].to_json(orient="records", double_precision=3)),
                s1_medias=dict(n=int(len(s1)), f1=round(float(s1.f1_cambio.mean()), 3), f1_laxa=round(float(s1.f1_cambio_laxa.mean()), 3),
                               recall=round(float(s1.recall_cambio.mean()), 3), precision=round(float(s1.precision_cambio.mean()), 3)),
                tracks=json.loads(ar[["track_a", "fecha_a", "track_b", "fecha_b", "fase", "jaccard_cambio", "pct_a_cambio",
                                      "pct_b_cambio"]].to_json(orient="records", double_precision=3)),
                jaccard_evento=round(float(ev.jaccard_cambio.mean()), 3) if len(ev) else None, n_pares_evento=int(len(ev)),
                agua_conocida=agua_conocida(zona))


def agua_conocida(zona):
    p = BASE / "agua_conocida.csv"
    if not p.exists():
        return []
    a = pd.read_csv(p)
    return json.loads(a[a.zona == zona].drop(columns="zona").to_json(orient="records", double_precision=2))


def secado_umbral(fechas, share):
    """Primera pasada después de la más mojada con 'remaining' ≤ share (igual que index.html, tabla 'Half dry by')."""
    pts = [p for p in fechas if p["remaining"] is not None and p["dia"] >= 0]
    if not pts:
        return None, None, None
    k = max(range(len(pts)), key=lambda i: (pts[i]["remaining"], -i))
    hit = next((p for p in pts[k + 1:] if p["remaining"] <= share), None)
    return (hit["dia"], hit["fecha"], None) if hit else (None, None, pts[-1]["dia"])


def cifras(zonas):
    """Cifras derivadas que usa la app."""
    return dict(revisita_dias=int(np.median([d for z in zonas.values()
                                             for d in pd.to_datetime(pd.Series(z["capas"]["serie"]["fechas"])).diff().dt.days.dropna()])))


def zonas_bbox():
    return {z: [round(v, 4) for v in shp_wkt.loads(d["wkt"]).bounds] for z, d in ZONAS.items()}


def main():
    # se borra lo que genera este script; se conserva app/data/metodo/ (scripts/exportar_metodo.py)
    conservar = {SAL / "metodo"}
    if SAL.exists():
        for p in sorted(SAL.rglob("*"), reverse=True):
            if any(p == c or c in p.parents for c in conservar) or any(p in c.parents for c in conservar):
                continue
            p.unlink() if p.is_file() else p.rmdir()
    SAL.mkdir(parents=True, exist_ok=True)
    zonas = {}
    for zona in ZONAS:
        print(f"== {zona}")
        out = SAL / zona
        out.mkdir()
        zonas[zona] = dict(
            id=zona, nombre=NOMBRES[zona], evento=evento_json(zona),
            capas=capas_zona(zona, out), fechas=series_zona(zona),
            resumen=resumen_zona(zona),
            uso_suelo=tabla(IMP / "uso_suelo.csv", zona, ["clase", "ha_clase", "ha_inundada", "pct_clase_inundada", "ha_dia"]),
        )
        r = zonas[zona]["resumen"]
        r["dia_mitad_seca"], r["fecha_mitad_seca"], r["mitad_seca_despues_de"] = secado_umbral(zonas[zona]["fechas"], 50)
        r["dia_90_seco"], r["fecha_90_seco"], r["seco_90_despues_de"] = secado_umbral(zonas[zona]["fechas"], 10)
        viento_fechas(zona, zonas[zona]["fechas"])
        if zona == CASO:
            zonas[zona]["validacion"] = validacion_zona(zona)
    impacto_geo()
    manifest = dict(generado=str(date.today()), evento=evento_json("treinta_y_tres"),
                    eventos={k: evento_json(next(z for z in ZONAS if ZONAS[z].get("evento", "agosto") == k)) for k in EVENTOS
                             if any(ZONAS[z].get("evento", "agosto") == k for z in ZONAS)},   # sólo los eventos de las zonas
                    secado=secado_heatmap(zonas),
                    cifras=cifras(zonas), zonas=zonas,
                    contexto=dict(zonas=zonas_bbox(), optico=optico_ctx(), s1_vs_nisar=s1_par(zonas), monte_caso=monte_caso(),
                                  secado_ejemplo=secado_ejemplo(), caso=CASO, prensa_caso=PRENSA_CASO),
                    leyendas=dict(persistencia=[dict(rango=f"{a}–{b}" if b < 9999 else f"{a}+", color="rgb(%d,%d,%d)" % c) for a, b, c in PERS_BINS],
                                  previa="rgb(%d,%d,%d)" % PREVIA))
    (SAL / "manifest.json").write_text(json.dumps(manifest, separators=(",", ":"), allow_nan=False, default=str))
    tam = sum(p.stat().st_size for p in SAL.rglob("*") if p.is_file()) / 1e6
    print(f"-> {SAL}  ({tam:.1f} MB)")


if __name__ == "__main__":
    main()
