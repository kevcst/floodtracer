"""
Validación independiente con Sentinel-1 (A4 del plan). Regla 1: S1 SÓLO valida, nunca entra en las series ni en los
umbrales de NISAR.

  python scripts/validar_s1.py                   # baja recortes S1 RTC (Planetary Computer, anónimo) y compara
  python scripts/validar_s1.py --zona treinta_y_tres

Qué hace
  1. Para cada zona/track NISAR y cada pasada entre el 10/8 y el 22/9 busca una escena Sentinel-1 RTC (banda C, VV,
     gamma0 RTC 10 m) a ≤ 2 días que cubra ≥ 20 % del AOI. Prefiere la de menor desfase.
  2. Línea de base S1: escenas de la MISMA órbita relativa antes del fin de base de la zona (jun–jul).
  3. Recorta S1 directo sobre la grilla del track NISAR (promedio 10 → 20 m, lectura parcial del COG) y lo cachea en
     data_nisar/validacion/s1/{zona}/{track}/.
  4. Agua nueva S1 con un detector análogo pero con parámetros propios de banda C:
     ΔVV < −3 dB respecto de la mediana base S1, VV < −15 dB, fuera del agua base S1 (VV < −18 en la mayoría de la base).
     Referencia "laxa": la misma caída con VV < −12 dB (agua somera o parcial en el píxel de 20 m).
  5. Compara contra la máscara NISAR (detector por cambio, y el viejo por umbral para referencia):
     acuerdo (Jaccard), precisión y exhaustividad tomando S1 como referencia, y % de agua de cada uno.

Advertencia física: banda C (5,6 cm) satura antes en vegetación; el arroz con rastrojo o pasto emergente inundado
se ve más brillante en C que en L, así que S1 tiende a VER MENOS agua somera con vegetación. Precisión NISAR baja
frente a S1 no es necesariamente error NISAR.

Salida: data_nisar/zonas/validacion_s1.csv · validacion_s1.png (mapas lado a lado de los mejores pares)
"""
import argparse
import json
import os
import ssl
import time
import urllib.request
import warnings

import certifi
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from shapely import wkt as shp_wkt
from shapely.geometry import shape

from metricas_evento import (BASE, Evento, es_validado, OUT, calibrar_umbral, cargar_track, detectar_nueva, filtrar_mmu, guardar,
                             media_nan, agua_permanente, pasadas_calma)
from zonas import ZONAS

warnings.filterwarnings("ignore", category=RuntimeWarning)
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-1-rtc"
CTX = ssl.create_default_context(cafile=certifi.where())
CACHE = OUT / "validacion" / "s1"
MAX_DT = 2
VAL_EXTRA = pd.Timedelta(days=12)   # ventana de validación = ventana del evento + 12 días
S1_CAMBIO, S1_TECHO, S1_AGUA = -3.0, -15.0, -18.0
S1_TECHO_LAXO = -12.0      # referencia "laxa": misma caída pero sin exigir VV tan oscuro (agua somera / parcial)
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CURL_CA_BUNDLE", certifi.where())
_token = {"t": None, "exp": 0}


def token():
    if time.time() > _token["exp"]:
        _token["t"] = json.load(urllib.request.urlopen(SAS, context=CTX, timeout=60))["token"]
        _token["exp"] = time.time() + 40 * 60
    return _token["t"]


def buscar(wkt):
    g = shp_wkt.loads(wkt)
    body = {"collections": ["sentinel-1-rtc"], "intersects": g.__geo_interface__,
            "datetime": "2026-06-01/2026-11-15", "limit": 500}
    req = urllib.request.Request(STAC, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    feats = json.load(urllib.request.urlopen(req, context=CTX, timeout=120))["features"]
    filas = []
    for f in feats:
        cov = shape(f["geometry"]).intersection(g).area / g.area
        p = f["properties"]
        filas.append(dict(id=f["id"], fecha=pd.Timestamp(p["datetime"][:10]), orbita=p.get("sat:relative_orbit"),
                          cov=cov, href=f["assets"]["vv"]["href"]))
    df = pd.DataFrame(filas)
    # cobertura de la fecha = unión de las escenas contiguas de esa órbita (se aproxima con la suma, tope 1)
    cob = df.groupby(["fecha", "orbita"])["cov"].sum().clip(upper=1).rename("cov_fecha")
    return df.join(cob, on=["fecha", "orbita"])


def recorte(escenas, perfil, destino):
    """Mosaico de las escenas S1 de una fecha/órbita sobre la grilla NISAR (gamma0 lineal, NaN = sin dato)."""
    if destino.exists():
        with rasterio.open(destino) as r:
            return r.read(1)
    out = np.full((perfil["height"], perfil["width"]), np.nan, "float32")
    for href in escenas.href:
        for intento in range(3):
            try:
                with rasterio.open(f"{href}?{token()}") as src, WarpedVRT(
                        src, crs=perfil["crs"], transform=perfil["transform"], width=perfil["width"],
                        height=perfil["height"], resampling=Resampling.average, src_nodata=src.nodata,
                        nodata=np.nan, dtype="float32") as vrt:
                    x = vrt.read(1)
                break
            except rasterio.errors.RasterioIOError as e:
                print(f"     reintento {intento + 1}: {e}")
                _token["exp"] = 0
                time.sleep(3)
        else:
            continue
        x[(x <= 0) | ~np.isfinite(x)] = np.nan
        out = np.where(np.isnan(out), x, out)
    destino.parent.mkdir(parents=True, exist_ok=True)
    guardar(destino, out, perfil, "float32", np.nan)
    return out


def db(x):
    return 10 * np.log10(np.maximum(media_nan(x), 1e-6))


def validar_track(zona, tdir, s1):
    fechas, hh, _, perfil = cargar_track(tdir)
    fechas = pd.DatetimeIndex(fechas)
    ev = Evento(zona)
    fin_base = ev.fin_base
    es_base = ev.es_base(fechas, hh)
    val = es_validado(fechas)
    valid = np.all(np.isfinite(hh), axis=0)
    umbral, _, _ = calibrar_umbral(hh[es_base], valid)
    agua_base = agua_permanente(hh, pasadas_calma(zona, tdir.name, fechas, es_base)[0], umbral, valid)
    med = np.nanmedian(hh[es_base], axis=0)
    cache = CACHE / zona / tdir.name
    s1 = s1[s1.cov_fecha >= 0.2]
    filas, mapas = [], []
    bases = {}
    for i, f in enumerate(fechas):
        if not (ev.ventana[0] <= f <= ev.ventana[1] + VAL_EXTRA):
            continue
        cand = s1[(s1.fecha - f).abs().dt.days <= MAX_DT].copy()
        if cand.empty:
            continue
        cand["desfase"] = (cand.fecha - f).dt.days
        cand = cand.assign(adt=cand.desfase.abs()).sort_values(["adt", "cov_fecha"], ascending=[True, False])
        fe, orb, dt = cand.iloc[0].fecha, cand.iloc[0].orbita, int(cand.iloc[0].desfase)
        if orb not in bases:
            bs = s1[(s1.orbita == orb) & (s1.fecha < fin_base)]
            if bs.fecha.nunique() < 2:
                print(f"   ! órbita {orb}: menos de 2 fechas base S1, se saltea")
                bases[orb] = None
            else:
                pila = np.stack([db(recorte(g, perfil, cache / f"{d.date()}_o{orb}_VV.tif"))
                                 for d, g in bs.groupby("fecha")])
                bases[orb] = (np.nanmedian(pila, axis=0), (pila < S1_AGUA).mean(axis=0) > 0.5, bs.fecha.nunique())
        if bases[orb] is None:
            continue
        vv_med, s1_agua_base, nb = bases[orb]
        vv = db(recorte(s1[(s1.fecha == fe) & (s1.orbita == orb)], perfil, cache / f"{fe.date()}_o{orb}_VV.tif"))
        d = vv - vv_med
        ok_s1 = np.isfinite(d)
        off = float(np.nanmedian(d[ok_s1 & ~s1_agua_base])) if ok_s1.any() else 0.0
        s1_nueva = filtrar_mmu((d - off < S1_CAMBIO) & (vv < S1_TECHO) & ~s1_agua_base & ok_s1)
        s1_laxa = filtrar_mmu((d - off < S1_CAMBIO) & (vv < S1_TECHO_LAXO) & ~s1_agua_base & ok_s1)
        v = valid & ok_s1 & np.isfinite(hh[i]) & ~agua_base & ~s1_agua_base
        fila = dict(zona=zona, track=tdir.name, fecha_nisar=f.date(), fecha_s1=fe.date(), dt_dias=dt, orbita_s1=orb,
                    n_base_s1=nb, pct_valido=round(100 * v.mean(), 1), pct_s1=100 * s1_nueva[v].mean(),
                    pct_s1_laxa=100 * s1_laxa[v].mean())
        for nombre, kw in (("cambio", dict(validado=val[i])), ("umbral", dict(metodo="umbral", umbral=umbral))):
            n = detectar_nueva(hh[i], med, agua_base, **kw) & v
            fila[f"pct_nisar_{nombre}"] = 100 * n[v].mean()
            for ref, sm in (("", s1_nueva), ("_laxa", s1_laxa)):
                s = sm & v
                tp, fp, fn = (n & s).sum(), (n & ~s).sum(), (~n & s).sum()
                fila |= {f"jaccard_{nombre}{ref}": tp / max(tp + fp + fn, 1),
                         f"precision_{nombre}{ref}": tp / max(tp + fp, 1), f"recall_{nombre}{ref}": tp / max(tp + fn, 1),
                         f"f1_{nombre}{ref}": 2 * tp / max(2 * tp + fp + fn, 1)}
            # de lo que sólo ve NISAR, ¿cuánto también se oscurece en S1 (ΔVV < −2 dB)?
            solo = n & ~s1_nueva & v
            fila[f"solo_nisar_s1_oscurece_{nombre}"] = float(((d - off) < -2)[solo].mean()) if solo.any() else np.nan
        filas.append(fila)
        mapas.append((fila, hh[i], vv, detectar_nueva(hh[i], med, agua_base, validado=val[i]) & v, s1_nueva & v, agua_base | s1_agua_base))
        print(f"   NISAR {f.date()} vs S1 {fe.date()} (Δ{dt:+d} d, órb {orb}): S1 {fila['pct_s1']:.1f} % · "
              f"NISAR cambio {fila['pct_nisar_cambio']:.1f} % F1={fila['f1_cambio']:.2f} (laxa {fila['f1_cambio_laxa']:.2f}) · "
              f"umbral {fila['pct_nisar_umbral']:.1f} % F1={fila['f1_umbral']:.2f}")
    return filas, mapas


def grafico(mapas, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(len(mapas), 3, figsize=(11, 3.6 * len(mapas)), squeeze=False)
    for (a1, a2, a3), (fila, hh, vv, n, s, base) in zip(axs, mapas):
        for ax in (a1, a2, a3):
            ax.axis("off")
        a1.imshow(np.clip((hh + 22) / 20, 0, 1), cmap="gray", interpolation="nearest")
        a1.set_title(f"NISAR L-band HH {fila['fecha_nisar']}", fontsize=8)
        a2.imshow(np.clip((vv + 22) / 20, 0, 1), cmap="gray", interpolation="nearest")
        a2.set_title(f"Sentinel-1 C-band VV {fila['fecha_s1']}", fontsize=8)
        rgb = np.ones(n.shape + (3,))
        rgb[base] = (0.75, 0.82, 0.92)
        rgb[n & s] = (0.10, 0.35, 0.75)
        rgb[n & ~s] = (0.92, 0.41, 0.20)
        rgb[~n & s] = (0.10, 0.69, 0.48)
        a3.imshow(rgb, interpolation="nearest")
        a3.set_title(f"{fila['zona']} {fila['track']}: blue both · orange NISAR only · green S1 only\n"
                     f"F1 {fila['f1_cambio']:.2f} (old threshold {fila['f1_umbral']:.2f})", fontsize=8)
    plt.tight_layout()
    plt.savefig(path, dpi=90)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--zona", default="todas", choices=["todas", *ZONAS])
    a = ap.parse_args()
    filas, mapas = [], []
    for zona in (ZONAS if a.zona == "todas" else [a.zona]):
        print(f"== {zona}")
        s1 = buscar(ZONAS[zona]["wkt"])
        for tdir in sorted((BASE / zona).glob("T*_F*")):
            print(f"  {tdir.name}")
            fl, mp = validar_track(zona, tdir, s1)
            filas += fl
            mapas += mp
    df = pd.DataFrame(filas).round(3)
    if a.zona == "todas":
        df.to_csv(BASE / "validacion_s1.csv", index=False)
        # mapas: el par con más agua S1 de cada zona, con desfase mínimo
        sel = [m for m in mapas if m[0]["pct_s1"] >= 1]
        sel = sorted(sel, key=lambda m: (m[0]["zona"], abs(m[0]["dt_dias"]), -m[0]["pct_s1"]))
        vistos, elegidos = set(), []
        for m in sel:
            if m[0]["zona"] not in vistos:
                vistos.add(m[0]["zona"])
                elegidos.append(m)
        if elegidos:
            grafico(elegidos, BASE / "validacion_s1.png")
    print(df.groupby("zona")[["f1_cambio", "f1_umbral", "f1_cambio_laxa", "f1_umbral_laxa", "precision_cambio",
                              "recall_cambio", "solo_nisar_s1_oscurece_cambio"]].mean().round(2).to_string())
