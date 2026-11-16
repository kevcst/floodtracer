"""
Chequeos del caso de estudio Rocha norte. Sólo analiza: no cambia el pipeline ni escribe en data_nisar/ ni en app/.

  python scripts/caso_rocha_norte.py            # zona por defecto: rocha_norte
  python scripts/caso_rocha_norte.py --zona merin_arrozales

a. Base de julio mojada: extensión de agua nueva por track con la mediana base de TODAS las pasadas base (pipeline)
   vs sólo las de junio (las secas). Mismo detector (metricas_evento.detectar_nueva), mismo agua permanente
   (agua_base.tif del pipeline), sin el agua previa (agua_previa.tif del track + la del combinado).
   Se reporta "≥ 1 obs." (= extension_max del track) y "≥ 2 obs." (como la extensión confirmada, pero de un track solo).
b. Viento en las pasadas del evento (clima_pasadas.csv, ERA5 a la hora de la pasada).
e. Validación de la zona: Sentinel-1 (validacion_s1.csv) y acuerdo entre tracks a ≤ 1 día (armonizacion_pares.csv).
"""
import argparse

import numpy as np
import pandas as pd
import rasterio

from metricas_evento import BASE, Evento, cargar_track, detectar_nueva, es_validado, previa_en_grilla, tracks_zona

VIENTO_BAJA_CONF = 3.0      # m/s, el mismo corte que define las pasadas "de calma" del agua permanente


def leer(p):
    with rasterio.open(p) as r:
        return r.read(1), r.profile


def base_junio(zona):
    filas = []
    ev = Evento(zona)
    for tdir in tracks_zona(zona):
        if not (tdir / "metricas" / "agua_base.tif").exists():
            continue
        fechas, hh, _, perfil = cargar_track(tdir)
        fechas = pd.DatetimeIndex(fechas)
        es_base = ev.es_base(fechas, hh)
        junio = es_base & (fechas.month == 6)
        tormenta = ev.es_evento(fechas) & ~ev.es_previa(fechas, tdir.name)
        agua_base = leer(tdir / "metricas" / "agua_base.tif")[0] == 1
        previa_t = leer(tdir / "metricas" / "agua_previa.tif")[0] == 1
        previa = previa_en_grilla(zona, perfil, previa_t)
        valid = np.all(np.isfinite(hh), axis=0)
        ok = np.isfinite(hh)
        val = es_validado(fechas)
        ha_px = abs(perfil["transform"].a * perfil["transform"].e) / 1e4
        res = dict(zona=zona, track=tdir.name, n_base=int(es_base.sum()), n_junio=int(junio.sum()),
                   base=",".join(str(f.date()) for f in fechas[es_base]))
        for nombre, sel in (("todas", es_base), ("junio", junio)):
            if not sel.any():
                res |= {f"ha1_{nombre}": None, f"ha2_{nombre}": None}
                continue
            med = np.nanmedian(hh[sel], axis=0)
            n = np.stack([detectar_nueva(hh[i], med, agua_base, validado=val[i]) & ok[i] & valid for i in np.where(tormenta)[0]])
            cuenta = (n & ~previa).sum(axis=0)
            res[f"ha1_{nombre}"] = round(float((cuenta >= 1).sum() * ha_px))
            res[f"ha2_{nombre}"] = round(float((cuenta >= 2).sum() * ha_px))
            res[f"pct_base_{nombre}"] = round(float(100 * np.nanmean(
                [detectar_nueva(hh[i], med, agua_base, validado=val[i])[valid].mean() for i in np.where(es_base)[0]])), 2)
        if res.get("ha2_junio") is not None and res["ha2_todas"]:
            res["cambio_ha2_pct"] = round(100 * (res["ha2_junio"] - res["ha2_todas"]) / res["ha2_todas"], 1)
        filas.append(res)
    return pd.DataFrame(filas)


def viento(zona):
    c = pd.read_csv(BASE / zona / "clima_pasadas.csv")
    ev = Evento(zona)
    c["fase"] = np.where(pd.to_datetime(c.fecha) < ev.fin_base, "base",
                         np.where(pd.to_datetime(c.fecha) < ev.inicio, "previa", "evento/post"))
    c["confianza"] = np.where(c.viento >= VIENTO_BAJA_CONF, "baja", "normal")
    return c[["track", "fecha", "hora_utc", "fase", "viento", "rafaga", "lluvia_72h", "confianza"]]


def validacion(zona):
    s1 = pd.read_csv(BASE / "validacion_s1.csv")
    s1 = s1[s1.zona == zona][["track", "fecha_nisar", "fecha_s1", "dt_dias", "pct_s1", "pct_nisar_cambio", "precision_cambio",
                              "recall_cambio", "f1_cambio", "f1_cambio_laxa"]]
    ar = pd.read_csv(BASE / "armonizacion_pares.csv")
    ar = ar[ar.zona == zona][["track_a", "fecha_a", "track_b", "fecha_b", "fase", "jaccard_cambio", "pct_a_cambio", "pct_b_cambio"]]
    return s1, ar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zona", default="rocha_norte")
    zona = ap.parse_args().zona
    pd.set_option("display.width", 200)
    print("== a. base: todas las pasadas vs sólo junio (ha de agua nueva de la tormenta, sin agua previa)")
    print(base_junio(zona).to_string(index=False))
    print("\n== b. viento en las pasadas (ERA5, m/s)")
    print(viento(zona).to_string(index=False))
    s1, ar = validacion(zona)
    print("\n== e. Sentinel-1")
    print(s1.to_string(index=False))
    print(f"   medias: F1 {s1.f1_cambio.mean():.2f} · F1 laxa {s1.f1_cambio_laxa.mean():.2f} · "
          f"exhaustividad {s1.recall_cambio.mean():.2f} · precisión {s1.precision_cambio.mean():.2f}")
    print("\n== e. acuerdo entre tracks (≤ 1 día)")
    print(ar.to_string(index=False))
    ev = ar[ar.fase != "base"]
    print(f"   Jaccard medio (evento/post): {ev.jaccard_cambio.mean():.2f}")


if __name__ == "__main__":
    main()
