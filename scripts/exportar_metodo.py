"""
Insumos de la página "How we did it" (app/method.html) con datos reales del caso de estudio.
Sólo LEE data_nisar/ y escribe app/data/metodo/ + la entrada "metodo" de app/data/manifest.json. No cambia métricas.

  python scripts/exportar_metodo.py            # zona por defecto: el caso de estudio (exportar_app.CASO)

Correr DESPUÉS de exportar_app.py (que regenera el manifest y conserva app/data/metodo/).

Paneles (WebP, sin texto incrustado: la página los rotula en EN/ES), todos del track de la serie salvo indicación:
  1 speckle      m1_crudo · m1_filtrado            HH de una pasada sin filtrar vs media móvil 5×5 (recorte chico)
  2 detector     m2_base · m2_pico · m2_cambio · m2_nueva · m2_umbral
                 mediana base · pasada del pico · cambio normalizado (azul claro→azul = más oscuro, rojo = más brillante; el agua
                 permanente en gris oscuro: no entra al detector) ·
                 agua nueva (detector por cambio) · detector viejo por umbral absoluto
  3 píxeles      JSON (no imagen): historia HH de 4 píxeles reales (agua permanente, se seca rápido, se seca tarde, seco)
  4 combinado    m4_{track} · m4_confirmada        máscaras de los 3 tracks en la grilla del combinado (pasadas del pico)
                                                    → extensión confirmada (≥ 2 obs.) con el agua previa en celeste (inundación presente antes de la tormenta)
  5 permanente   m5_todas · m5_calma               agua permanente con todas las pasadas base vs sólo las de calma, en la zona
                                                    de la app donde más difieren (permanente.zona; hoy la Laguna Merín)
  6 S1           referencia a contexto.s1_vs_nisar (exportar_app.py)
  7 monte        serie HH−HV ribereño / altura / sin monte (JSON) + m7_monte (agua bajo monte sobre HH)
  9 secado       m7_pixel · m7_celdas · m7_heat     días por píxel → promedio por celda de HEAT_M → heatmap de la historia
Además: fechas por track (línea de tiempo de las pasadas) y el hueco global de datos.
"""
import argparse
import json

import numpy as np
import pandas as pd
import rasterio
from PIL import Image
from rasterio.warp import Resampling, reproject

from exportar_app import AZUL, CASO, MONTE, NARANJA, PREVIA, SAL, esquinas_ventana, gris_db, leer, pintar, ventana_max
from metricas_evento import (BASE, CAMBIO_DB, TECHO_DB, VENTANA_SPECKLE, Evento, agua_permanente, calibrar_umbral, cargar_track, detectar_nueva,
                             pasadas_calma, previa_en_grilla, tracks_zona)
from zonas import ZONAS

OUT = SAL / "metodo"
LADO = 500          # px de los recortes (20 m → 10 km)
LADO_SPECKLE = 160  # recorte chico para que se vea el grano
Q = 82


def guardar(nombre, rgba):
    Image.fromarray(rgba, "RGBA").save(OUT / f"{nombre}.webp", quality=Q)
    return f"data/metodo/{nombre}.webp"


def recorte(a, r0, c0, n):
    return a[r0:r0 + n, c0:c0 + n]


def cambio_rgba(d):
    """Cambio en dB → divergente: azul = más oscuro (posible agua), blanco = igual, rojo = más brillante."""
    ok = np.isfinite(d)
    x = np.clip(np.where(ok, d, 0) / 6, -1, 1)          # ±6 dB = color pleno
    neg = x < 0
    r = np.where(neg, 255 * (1 + x), 255)
    g = 255 * (1 - np.abs(x))
    b = np.where(neg, 255, 255 * (1 - x))
    return np.dstack([r, g, b, np.where(ok, 255, 0)]).astype("uint8")


# rampa de días de la historia (story.js: círculos "cells" y HEAT_RAMP del heatmap)
RAMPA_DIAS = [(0, (254, 224, 144)), (7, (253, 174, 97)), (14, (244, 109, 67)), (28, (215, 48, 39)), (42, (103, 0, 31))]
RAMPA_HEAT = [(0.0, (255, 237, 160, 0)), (0.15, (255, 237, 160, 153)), (0.35, (253, 174, 97, 255)), (0.55, (244, 109, 67, 255)),
              (0.75, (215, 48, 39, 255)), (1.0, (103, 0, 31, 255))]


def rampa(v, paradas):
    """Interpola colores (RGB o RGBA) en paradas [(valor, color)] para un array de valores."""
    xs = np.array([p for p, _ in paradas], "float32")
    cs = np.array([c for _, c in paradas], "float32")
    return np.stack([np.interp(v, xs, cs[:, k]) for k in range(cs.shape[1])], axis=-1)


def secado_paneles(zona, hh_fondo):
    """Tres imágenes de toda la zona: días bajo agua por píxel → promedio por celda → heatmap (pesos días × fracción)."""
    from scipy import ndimage as ndi

    from agregar_impacto import productos
    from exportar_app import HEAT_M
    p = productos(zona)
    ext, pers, perfil = p["ext"], p["pers"]["mid"], p["perfil"]
    fondo = gris_db(hh_fondo) if hh_fondo.shape == ext.shape else np.dstack([np.full(ext.shape, 60, "uint8")] * 3 + [np.full(ext.shape, 255, "uint8")])
    fondo[..., :3] = (fondo[..., :3] * 0.55 + 255 * 0.45).astype("uint8")       # radar aclarado: sólo contexto
    fondo[..., 3] = np.where(np.isfinite(hh_fondo), 255, 0) if hh_fondo.shape == ext.shape else 255
    # a) días por píxel
    a = fondo.copy()
    col = rampa(np.where(ext, pers, 0).astype("float32"), RAMPA_DIAS).astype("uint8")
    a[ext, :3] = col[ext]; a[ext, 3] = 255
    # b) celdas de HEAT_M
    k = max(1, int(round(HEAT_M / abs(perfil["transform"].a))))
    H, W = (ext.shape[0] // k) * k, (ext.shape[1] // k) * k
    e = ext[:H, :W].reshape(H // k, k, W // k, k)
    n = e.sum(axis=(1, 3)); frac = n / (k * k)
    dias = np.where(n > 0, np.where(ext, pers, 0)[:H, :W].reshape(H // k, k, W // k, k).sum(axis=(1, 3)) / np.maximum(n, 1), 0)
    celda = frac >= 0.05
    big = lambda x: np.repeat(np.repeat(x, k, axis=0), k, axis=1)
    b = fondo.copy()
    cc = rampa(dias.astype("float32"), RAMPA_DIAS).astype("uint8")
    mask = big(celda)
    b[:H, :W][mask, :3] = big(cc)[mask]; b[:H, :W][mask, 3] = 255
    # c) heatmap: peso = días × fracción, suavizado como el heatmap de MapLibre
    w = np.where(celda, dias * frac, 0).astype("float32")
    ws = ndi.gaussian_filter(big(w), sigma=k * 0.9)
    dens = np.clip(ws / max(float(ws.max()), 1e-6), 0, 1)
    hc = rampa(dens, RAMPA_HEAT)
    c = fondo.copy().astype("float32")
    al = hc[..., 3:4] / 255
    c[:H, :W, :3] = c[:H, :W, :3] * (1 - al) + hc[..., :3] * al
    c = c.astype("uint8")
    return dict(pixel=guardar("m7_pixel", a), celdas=guardar("m7_celdas", b), heat=guardar("m7_heat", c),
                celda_m=int(HEAT_M), dias_min=int(round(float(dias[celda].min()))) if celda.any() else None,
                dias_max=int(round(float(dias[celda].max()))) if celda.any() else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zona", default=CASO)
    zona = ap.parse_args().zona
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.webp"):
        f.unlink()
    ev = Evento(zona)
    serie = ZONAS[zona]["serie"]
    tdir = BASE / zona / serie
    fechas, hh, hv, perfil = cargar_track(tdir)
    fechas = pd.DatetimeIndex(fechas)
    fs = [str(f.date()) for f in fechas]
    es_base = ev.es_base(fechas, hh)
    valid = np.all(np.isfinite(hh), axis=0)
    umbral, _, _ = calibrar_umbral(hh[es_base], valid)
    agua_base = leer(tdir / "metricas" / "agua_base.tif")[0] == 1
    med = np.nanmedian(hh[es_base], axis=0)
    with rasterio.open(tdir / "metricas" / "agua_nueva_por_fecha.tif") as r:
        pila, desc = r.read(), list(r.descriptions)
    previa = previa_en_grilla(zona, perfil)
    ext = (leer(tdir / "metricas" / "extension_max.tif")[0] == 1)
    pers = leer(tdir / "metricas" / "persistencia_dias.tif")[0]
    retiro = leer(tdir / "metricas" / "fecha_retiro.tif")[0]
    m = {"zona": zona, "track": serie, "resolucion_m": round(abs(perfil["transform"].a))}

    # pasada del pico: la de más agua nueva dentro de la tormenta (serie del manifest: misma regla que remaining)
    tormenta = ev.es_evento(fechas) & ~ev.es_previa(fechas, serie)
    i_pico = max(np.where(tormenta)[0], key=lambda i: (pila[desc.index(fs[i])] == 1).sum())
    m["fecha_pico"] = fs[i_pico]
    r0, c0 = ventana_max(ext & ~previa, LADO)
    m["ventana"] = dict(esquinas=esquinas_ventana(perfil, r0, c0, LADO, LADO), lado_km=round(LADO * abs(perfil["transform"].a) / 1000, 1))

    # 1 speckle: HH crudo (sin media móvil) vs filtrado, recorte chico centrado en la ventana
    raw = leer(tdir / f"{fs[i_pico]}_HH.tif")[0].astype("float64")
    raw_db = 10 * np.log10(np.where(raw > 0, raw, np.nan))
    s0, s1 = r0 + (LADO - LADO_SPECKLE) // 2, c0 + (LADO - LADO_SPECKLE) // 2
    m["speckle"] = dict(crudo=guardar("m1_crudo", gris_db(recorte(raw_db, s0, s1, LADO_SPECKLE))),
                        filtrado=guardar("m1_filtrado", gris_db(recorte(hh[i_pico], s0, s1, LADO_SPECKLE))),
                        ventana_px=VENTANA_SPECKLE, lado_km=round(LADO_SPECKLE * abs(perfil["transform"].a) / 1000, 1))

    # 2 detector
    sl = (slice(r0, r0 + LADO), slice(c0, c0 + LADO))
    nueva = pila[desc.index(fs[i_pico])] == 1
    d = hh[i_pico] - med
    tierra = valid & ~agua_base & np.isfinite(d)
    off = float(np.nanmedian(d[tierra]))
    umb = detectar_nueva(hh[i_pico], med, agua_base, metodo="umbral", umbral=umbral) & valid
    img_nueva = gris_db(hh[i_pico][sl])
    pintar(img_nueva, agua_base[sl], AZUL); pintar(img_nueva, (nueva & ~previa)[sl], NARANJA); pintar(img_nueva, (nueva & previa)[sl], PREVIA)
    img_umb = gris_db(hh[i_pico][sl])
    pintar(img_umb, agua_base[sl], AZUL); pintar(img_umb, umb[sl], NARANJA)
    v = valid[sl]
    m["detector"] = dict(base=guardar("m2_base", gris_db(med[sl])), pico=guardar("m2_pico", gris_db(hh[i_pico][sl])),
                         cambio=guardar("m2_cambio", pintar(cambio_rgba((d - off)[sl]), agua_base[sl], (70, 70, 70))), nueva=guardar("m2_nueva", img_nueva),
                         umbral=guardar("m2_umbral", img_umb),
                         pct_nueva=round(100 * float((nueva & ~previa)[sl][v].mean()), 1), pct_umbral=round(100 * float(umb[sl][v].mean()), 1),
                         n_base=int(es_base.sum()), caida_db=CAMBIO_DB, techo_db=TECHO_DB, umbral_db=round(umbral, 1))

    # 3 historias de píxeles (JSON): agua permanente, se seca rápido, se seca tarde, seco
    rng = np.random.default_rng(0)
    # sin cultivos y con dato en todas las pasadas: desde octubre los cultivos son "sin dato" (metricas_evento.sin_dato_por_fecha)
    # y un punto sin dato se leía como "seco" en el gráfico
    from metricas_evento import mascara_wc
    con_dato = ((pila != 255).all(axis=0)) & ~mascara_wc(zona, perfil, 40)
    i_desp = [desc.index(f) for f in fs if f in desc and pd.Timestamp(f) >= ev.inicio]
    mojado_desp = (pila[i_desp] == 1).sum(axis=0)
    # "inundado poco tiempo": agua en la primera pasada después de la lluvia, bien oscuro (≤ −16 dB), y seco en todas las siguientes
    hh_desp = hh[[fs.index(desc[i]) for i in i_desp]]
    seco_rapido = (ext & ~previa & valid & con_dato & (pila[i_desp[0]] == 1) & (mojado_desp == 1)
                   & (hh_desp[0] <= -16) & np.all(hh_desp[1:] > TECHO_DB + 1, axis=0))   # y después claramente por encima del techo
    seco_tarde = ext & ~previa & ((retiro == 999) | (pers >= 30)) & (mojado_desp >= 3) & valid & con_dato
    nunca = valid & ~ext & ~agua_base & ~previa & (pila == 1).sum(axis=0).astype(bool).__invert__()
    perm = agua_base & valid & (np.nanmax(hh, axis=0) < umbral)
    tipos = {"permanente": perm, "rapido": seco_rapido, "tarde": seco_tarde, "seco": nunca}
    pix = []
    t = perfil["transform"]
    from rasterio.warp import transform as wt
    for k, msk in tipos.items():
        rr, cc = np.where(msk[sl])
        if not len(rr):
            continue
        j = rng.integers(len(rr))
        r, c = rr[j] + r0, cc[j] + c0
        lon, lat = wt(perfil["crs"], "EPSG:4326", [t.c + (c + .5) * t.a], [t.f + (r + .5) * t.e])
        pix.append(dict(tipo=k, lon=round(lon[0], 5), lat=round(lat[0], 5), base_db=round(float(med[r, c]), 2),
                        serie=[dict(fecha=f, hh_db=None if not np.isfinite(hh[i, r, c]) else round(float(hh[i, r, c]), 2),
                                    nueva=bool(pila[desc.index(f), r, c] == 1) if f in desc else None,
                                    sin_dato=bool(pila[desc.index(f), r, c] == 255 and not agua_base[r, c]) if f in desc else True)
                                for i, f in enumerate(fs)]))
    m["pixeles"] = pix

    # 4 combinado: los tracks en la grilla del combinado, en las pasadas de cada uno más cercanas al pico
    ce, pe = leer(BASE / zona / "combinado" / "extension_confirmada.tif")
    cp = leer(BASE / zona / "combinado" / "agua_previa.tif")[0] == 1
    q0, p0 = ventana_max((ce == 1), LADO)
    slc = (slice(q0, q0 + LADO), slice(p0, p0 + LADO))
    tracks = []
    for td in tracks_zona(zona):
        if not (td / "metricas" / "agua_nueva_por_fecha.tif").exists():
            continue
        with rasterio.open(td / "metricas" / "agua_nueva_por_fecha.tif") as r:
            dsc, prof = list(r.descriptions), r.profile
            cerca = min(dsc, key=lambda f: abs((pd.Timestamp(f) - fechas[i_pico]).days))
            band = r.read(dsc.index(cerca) + 1)
        out = np.zeros((pe["height"], pe["width"]), "uint8")
        reproject((band == 1).astype("uint8"), out, src_transform=prof["transform"], src_crs=prof["crs"], dst_transform=pe["transform"],
                  dst_crs=pe["crs"], resampling=Resampling.nearest)
        img = np.zeros((LADO, LADO, 4), "uint8"); img[..., 3] = 255; img[..., :3] = 40
        pintar(img, (out[slc] == 1) & ~cp[slc], NARANJA); pintar(img, (out[slc] == 1) & cp[slc], PREVIA)   # como m2_nueva
        tracks.append(dict(track=td.name, fecha=cerca, img=guardar(f"m4_{td.name}", img)))
    img = np.zeros((LADO, LADO, 4), "uint8"); img[..., 3] = 255; img[..., :3] = 40
    pintar(img, cp[slc], PREVIA); pintar(img, ce[slc] == 1, NARANJA)
    m["combinado"] = dict(tracks=tracks, confirmada=guardar("m4_confirmada", img), min_obs=2)

    # 5 agua permanente: todas las pasadas base vs sólo las de calma. Con el punto de viento sobre agua de tierra adentro
    # (clima.py, 15/11) las 4 pasadas base de T53D en Rocha norte son de calma y el panel quedaba igual a los dos lados:
    # el ejemplo sale de la zona/track de la app donde más difieren (hoy la Laguna Merín, T53D). Ver permanente.zona.
    mejor = None
    for zz in ZONAS:
        td = BASE / zz / ZONAS[zz]["serie"]
        if not (td / "metricas" / "agua_base.tif").exists():
            continue
        f_z, hh_z, _, perf_z = (cargar_track(td) if zz != zona else (fechas, hh, hv, perfil))
        f_z = pd.DatetimeIndex(f_z)
        eb = Evento(zz).es_base(f_z, hh_z)
        vz = np.all(np.isfinite(hh_z), axis=0)
        uz, _, _ = calibrar_umbral(hh_z[eb], vz)
        cz, wz = pasadas_calma(zz, ZONAS[zz]["serie"], f_z, eb)
        tz, sz = agua_permanente(hh_z, eb, uz, vz), agua_permanente(hh_z, cz, uz, vz)
        dif = int((tz ^ sz).sum())
        if mejor is None or dif > mejor[0]:
            mejor = (dif, zz, f_z, hh_z, perf_z, eb, cz, wz, tz, sz)
    _, zp, f_p, hh_p, perf_p, eb_p, calma, viento, todas, solo_calma = mejor
    fs_p = [str(f.date()) for f in f_p]
    a0, b0 = ventana_max(solo_calma ^ todas, LADO)
    slp = (slice(a0, a0 + LADO), slice(b0, b0 + LADO))
    i_calma = int(np.where(calma)[0][0])
    im_t = gris_db(hh_p[i_calma][slp]); pintar(im_t, todas[slp], AZUL)
    im_c = gris_db(hh_p[i_calma][slp]); pintar(im_c, solo_calma[slp], AZUL)
    ha_p = abs(perf_p["transform"].a * perf_p["transform"].e) / 1e4
    m["permanente"] = dict(zona=zp, track=ZONAS[zp]["serie"], todas=guardar("m5_todas", im_t), calma=guardar("m5_calma", im_c),
                           n_base=int(eb_p.sum()), n_calma=int(calma.sum()),
                           viento_base=[dict(fecha=f, viento_ms=None if not np.isfinite(w) else round(float(w), 1), calma=bool(c))
                                        for f, w, c, b in zip(fs_p, viento, calma, eb_p) if b],
                           ha_todas=round(float(todas.sum()) * ha_p), ha_calma=round(float(solo_calma.sum()) * ha_p))

    # 7 monte: serie HH−HV relativa a la base por clase + mapa
    mr = pd.read_csv(BASE / "monte_ribereno.csv")
    mr = mr[(mr.zona == zona) & (mr.track == serie)]
    series = {}
    for clase, g in mr.groupby("clase"):
        b = g[g.fase == "base"].hh_hv_db.mean()
        series[clase] = [dict(fecha=str(r.fecha)[:10], v=round(r.hh_hv_db - b, 2)) for r in g.sort_values("fecha").itertuples() if np.isfinite(r.hh_hv_db)]
    vr = leer(tdir / "metricas" / "veg_inundada_ribereno.tif")[0] == 1
    m0, n0 = ventana_max(vr, LADO)
    slm = (slice(m0, m0 + LADO), slice(n0, n0 + LADO))
    im = gris_db(hh[i_pico][slm]); pintar(im, vr[slm], MONTE)
    m["monte"] = dict(series=series, mapa=guardar("m7_monte", im))

    # 2 datos: pasadas por track (línea de tiempo) y hueco global
    m["pasadas"] = {}
    for td in tracks_zona(zona):
        if (td / "metricas").exists():
            f2, *_ = cargar_track(td)
            m["pasadas"][td.name] = [str(x.date()) for x in f2]
    m["hueco"] = ["2026-07-27", "2026-08-10"]
    m["lluvia"] = [str(ev.lluvia[0].date()), str(ev.lluvia[1].date())]
    # 7 secado: del píxel al heatmap de la historia ("dónde se quedó más tiempo el agua"), con la misma regla que
    # exportar_app.secado_heatmap: días medios de los píxeles inundados por celda de HEAT_M × fracción inundada.
    m["secado"] = secado_paneles(zona, hh[i_pico])


    p = SAL / "manifest.json"
    man = json.loads(p.read_text())
    man["metodo"] = m
    p.write_text(json.dumps(man, separators=(",", ":"), allow_nan=False, default=str))
    tam = sum(f.stat().st_size for f in OUT.glob("*")) / 1e6
    print(f"-> {OUT} ({tam:.1f} MB) · pico {m['fecha_pico']} · {len(pix)} píxeles · tracks {[x['track'] for x in tracks]}")


if __name__ == "__main__":
    main()
