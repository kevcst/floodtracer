"""
Paso 3: ¿un criterio GLOBAL (mismo umbral en todos los tracks) con normalización por ángulo supera al actual
(umbral calibrado por track)? Experimento: NO cambia el pipeline ni la app.
  python scripts/angulo_incidencia.py && python scripts/clima_pasadas.py     # antes
  python scripts/comparar_global.py

Normalización a θ_ref = 40° con las pendientes medidas en diagnostico_tracks.py (HH baja con el ángulo):
  tierra : HH_40 = HH + 0,10·(θ − 40)            (pradera/cultivo −0,10…−0,15 dB/°; monte ~0)
  dos    : 0,25 dB/° donde la base del píxel es oscura (< −15 dB, agua abierta), 0,10 en el resto. La clase sale del
           propio HH (no de WorldCover) y es fija por píxel → no afecta la detección por cambio, sólo los umbrales.
Variantes
  actual        agua base = HH < umbral calibrado por track en la mayoría de la base; agua nueva = cambio + techo −14
  global        sin normalizar, umbral único −18 dB (cuánto pierde un umbral global sin corregir el ángulo)
  global_tierra normalización "tierra" + umbral único −18 dB (agua base) y techo −14 dB (agua nueva) sobre HH_40
  global_dos    normalización "dos" + los mismos umbrales
  *_calma       la misma variante, pero el agua base se decide con las pasadas base de viento ERA5 < 3 m/s (si hay
                ≥ 1; si no, todas). El clima sólo ELIGE pasadas (contexto, regla 1), no corrige valores.
Métricas
  agua base : F1 / precisión / exhaustividad vs JRC Global Surface Water (ocurrencia ≥ 75 %, 1984–2021; sólo valida)
              y Jaccard entre tracks de la misma grilla
  agua nueva: Jaccard entre tracks a ≤ 1 día y F1 vs Sentinel-1 (mismas pasadas y máscara S1 que validar_s1.py)
Salida: data_nisar/zonas/comparacion_global/{base.csv, base_pares.csv, nueva_pares.csv, nueva_s1.csv, resumen.txt}
"""
import itertools
import os
import warnings

import certifi
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import Resampling, reproject

import validar_s1 as vs
from armonizar_tracks import pares
from metricas_evento import (BASE, Evento, calibrar_umbral, cargar_track, detectar_nueva, es_validado, filtrar_mmu)
from zonas import ZONAS

warnings.filterwarnings("ignore")
os.environ.setdefault("CURL_CA_BUNDLE", certifi.where())
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
OUT = BASE / "comparacion_global"
JRC = "/vsicurl/https://storage.googleapis.com/global-surface-water/downloads2021/occurrence/occurrence_60W_30Sv1_4_2021.tif"
JRC_PERMANENTE = 75
THETA_REF = 40.0
K_TIERRA, K_AGUA, OSCURO_DB = 0.10, 0.25, -15.0
U_GLOBAL, TECHO = -18.0, -14.0
CALMA_MS = 3.0
VARIANTES = ["actual", "actual_calma", "global", "global_tierra", "global_tierra_calma", "global_dos", "global_dos_calma"]


def jrc_en_grilla(tdir, perfil):
    f = tdir / "contexto" / "jrc_ocurrencia.tif"
    if not f.exists():
        out = np.zeros((perfil["height"], perfil["width"]), "uint8")
        with rasterio.open(JRC) as src:
            reproject(rasterio.band(src, 1), out, dst_transform=perfil["transform"], dst_crs=perfil["crs"],
                      resampling=Resampling.average)
        p = perfil.copy()
        p.update(driver="GTiff", dtype="uint8", count=1, nodata=None, compress="deflate")
        for k in ("blockxsize", "blockysize", "tiled", "interleave"):
            p.pop(k, None)
        with rasterio.open(f, "w", **p) as dst:
            dst.write(out, 1)
    with rasterio.open(f) as r:
        x = r.read(1)
    return np.where(x <= 100, x, 0)          # 0–100 % de ocurrencia; > 100 = sin dato


def preparar(zona, tdir, viento):
    fi = tdir / "contexto" / "incidencia.tif"
    if not fi.exists():
        return None
    fechas, hh, _, perfil = cargar_track(tdir)
    fechas = pd.DatetimeIndex(fechas)
    ev = Evento(zona)
    es_base = ev.es_base(fechas, hh)
    with rasterio.open(fi) as r:
        inc = r.read(1)
    valid = np.all(np.isfinite(hh), axis=0) & np.isfinite(inc)
    med = np.nanmedian(hh[es_base], axis=0)
    k = {"tierra": np.full(inc.shape, K_TIERRA, "float32"),
         "dos": np.where(med < OSCURO_DB, K_AGUA, K_TIERRA).astype("float32")}
    v = np.array([viento.get((zona, tdir.name, str(f.date())), np.nan) for f in fechas])
    umbral, _, _ = calibrar_umbral(hh[es_base], valid)
    return dict(fechas=fechas, hh=hh, perfil=perfil, es_base=es_base, inc=inc, valid=valid, k=k, viento=v,
                umbral=umbral, jrc=jrc_en_grilla(tdir, perfil), ev=ev, val=es_validado(fechas))


def norm(D, x, var):
    var = var.removesuffix("_calma")
    if var in ("actual", "global"):
        return x
    k = D["k"]["tierra" if var == "global_tierra" else "dos"]
    return x + k * (D["inc"] - THETA_REF)


def agua_base(D, var):
    if (key := ("_ab", var)) in D:
        return D[key]
    hb = norm(D, D["hh"][D["es_base"]], var)
    u = D["umbral"] if var.startswith("actual") else U_GLOBAL
    sel = np.ones(hb.shape[0], bool)
    if var.endswith("_calma"):
        calma = D["viento"][D["es_base"]] < CALMA_MS
        if calma.any():
            sel = calma
    D[key] = ((hb[sel] < u).mean(axis=0) > 0.5) & D["valid"]
    return D[key]


def nueva(D, i, var):
    ab = agua_base(D, var)
    hhN = norm(D, D["hh"][i], var)
    medN = norm(D, np.nanmedian(D["hh"][D["es_base"]], axis=0), var)
    return detectar_nueva(hhN, medN, ab, techo=TECHO, validado=D["val"][i]) & D["valid"]


def metricas(pred, ref, v):
    p, r = pred & v, ref & v
    tp, fp, fn = (p & r).sum(), (p & ~r).sum(), (~p & r).sum()
    return dict(f1=2 * tp / max(2 * tp + fp + fn, 1), precision=tp / max(tp + fp, 1), recall=tp / max(tp + fn, 1))


def contra_s1(zona, tdir, D, s1):
    ev, perfil = D["ev"], D["perfil"]
    cache = vs.CACHE / zona / tdir.name
    s1 = s1[s1.cov_fecha >= 0.2]
    filas, bases = [], {}
    for i, f in enumerate(D["fechas"]):
        if not (ev.ventana[0] <= f <= ev.ventana[1] + vs.VAL_EXTRA):
            continue
        cand = s1[(s1.fecha - f).abs().dt.days <= vs.MAX_DT].copy()
        if cand.empty:
            continue
        cand = cand.assign(adt=(cand.fecha - f).dt.days.abs()).sort_values(["adt", "cov_fecha"], ascending=[True, False])
        fe, orb = cand.iloc[0].fecha, cand.iloc[0].orbita
        if orb not in bases:
            bs = s1[(s1.orbita == orb) & (s1.fecha < ev.fin_base)]
            if bs.fecha.nunique() < 2:
                bases[orb] = None
            else:
                pila = np.stack([vs.db(vs.recorte(g, perfil, cache / f"{d.date()}_o{orb}_VV.tif"))
                                 for d, g in bs.groupby("fecha")])
                bases[orb] = (np.nanmedian(pila, axis=0), (pila < vs.S1_AGUA).mean(axis=0) > 0.5)
        if bases[orb] is None:
            continue
        vv_med, s1_base = bases[orb]
        vv = vs.db(vs.recorte(s1[(s1.fecha == fe) & (s1.orbita == orb)], perfil, cache / f"{fe.date()}_o{orb}_VV.tif"))
        d = vv - vv_med
        ok = np.isfinite(d)
        off = float(np.nanmedian(d[ok & ~s1_base])) if ok.any() else 0.0
        s = filtrar_mmu((d - off < vs.S1_CAMBIO) & (vv < vs.S1_TECHO) & ~s1_base & ok)
        fila = dict(zona=zona, track=tdir.name, fecha=f.date(), fecha_s1=fe.date())
        for var in VARIANTES:
            v = D["valid"] & ok & ~agua_base(D, var) & ~s1_base
            m = metricas(nueva(D, i, var), s, v)
            fila |= {f"{k}_{var}": x for k, x in m.items()}
            fila[f"pct_{var}"] = 100 * (nueva(D, i, var) & v).sum() / max(v.sum(), 1)
        filas.append(fila)
    return filas


def misma_grilla(datos):
    grupos = {}
    for n, D in datos.items():
        grupos.setdefault((D["hh"].shape[1:], tuple(D["perfil"]["transform"])[:6]), []).append(n)
    return [g for g in grupos.values() if len(g) >= 2]


def jac(a, b, v):
    u = ((a | b) & v).sum()
    return (a & b & v).sum() / u if u else np.nan


def main():
    OUT.mkdir(exist_ok=True)
    cl = pd.read_csv(BASE / "diagnostico_tracks" / "clima_pasadas.csv")
    viento = {(r.zona, r.track, str(r.fecha)): r.viento for r in cl.itertuples()}
    fb, fbp, fnp, fns = [], [], [], []
    for zona in ZONAS:
        tdirs = sorted((BASE / zona).glob("T*_F*"))
        if not tdirs:
            continue
        print(f"== {zona}")
        datos = {t.name: D for t in tdirs if (D := preparar(zona, t, viento)) is not None}
        for n, D in datos.items():
            ref = D["jrc"] >= JRC_PERMANENTE
            fila = dict(zona=zona, track=n, ha_jrc=round(float((ref & D["valid"]).sum()) * 0.04, 1))
            for var in VARIANTES:
                fila |= {f"{k}_{var}": x for k, x in metricas(agua_base(D, var), ref, D["valid"]).items()}
            fb.append(fila)
        for grupo in misma_grilla(datos):
            for a, b in itertools.combinations(grupo, 2):
                v = datos[a]["valid"] & datos[b]["valid"]
                fbp.append(dict(zona=zona, track_a=a, track_b=b,
                                **{f"jaccard_{var}": jac(agua_base(datos[a], var), agua_base(datos[b], var), v)
                                   for var in VARIANTES}))
        for ta, i, tb, j in pares(datos):
            A, B = datos[ta], datos[tb]
            if A["es_base"][i]:
                continue
            fila = dict(zona=zona, track_a=ta, fecha_a=A["fechas"][i].date(), track_b=tb, fecha_b=B["fechas"][j].date())
            for var in VARIANTES:
                v = A["valid"] & B["valid"] & ~agua_base(A, var) & ~agua_base(B, var)
                wa, wb = nueva(A, i, var) & v, nueva(B, j, var) & v
                fila[f"jaccard_{var}"] = jac(wa, wb, v)
                fila[f"pct_{var}"] = 100 * max(wa.sum(), wb.sum()) / max(v.sum(), 1)
            fnp.append(fila)
        s1 = vs.buscar(ZONAS[zona]["wkt"])
        for n, D in datos.items():
            fns += contra_s1(zona, BASE / zona / n, D, s1)
    db_, dbp, dnp, dns = (pd.DataFrame(x) for x in (fb, fbp, fnp, fns))
    for df, nombre in ((db_, "base"), (dbp, "base_pares"), (dnp, "nueva_pares"), (dns, "nueva_s1")):
        df.round(3).to_csv(OUT / f"{nombre}.csv", index=False)
    resumen(db_, dbp, dnp, dns)


def resumen(db_, dbp, dnp, dns):
    pd.set_option("display.width", 220)
    t = pd.DataFrame({var: {
        "base F1 vs JRC": db_[f"f1_{var}"].mean(),
        "base precisión vs JRC": db_[f"precision_{var}"].mean(),
        "base exhaustividad vs JRC": db_[f"recall_{var}"].mean(),
        "base Jaccard entre tracks": dbp[f"jaccard_{var}"].mean(),
        "nueva Jaccard entre tracks": dnp[dnp.pct_actual >= 0.5][f"jaccard_{var}"].mean(),
        "nueva F1 vs S1": dns[f"f1_{var}"].mean(),
        "nueva precisión vs S1": dns[f"precision_{var}"].mean(),
        "nueva exhaustividad vs S1": dns[f"recall_{var}"].mean(),
        "nueva % de la escena": dns[f"pct_{var}"].mean()} for var in VARIANTES})
    lagunas = db_[db_.ha_jrc >= 2000]
    txt = ["Media sobre zonas/tracks/pasadas (ver CSV para el detalle por zona)", t.round(3).to_string(), "",
           f"Agua base en tracks con ≥ 2.000 ha de agua permanente JRC (lagunas; n={len(lagunas)}) — exhaustividad:",
           lagunas[["zona", "track", "ha_jrc"] + [f"recall_{v}" for v in VARIANTES]].round(2).to_string(index=False),
           "", "Agua base por zona — F1 vs JRC:",
           db_.groupby("zona")[[f"f1_{v}" for v in VARIANTES]].mean().round(2).to_string(),
           "", "Agua nueva por zona — F1 vs S1:",
           dns.groupby("zona")[[f"f1_{v}" for v in VARIANTES]].mean().round(2).to_string()]
    txt = "\n".join(txt)
    (OUT / "resumen.txt").write_text(txt + "\n")
    print("\n" + txt)


if __name__ == "__main__":
    main()
