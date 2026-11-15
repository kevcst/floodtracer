"""
Diagnóstico entre tracks (paso 1): ¿cuánto del desacuerdo entre tracks explica el ángulo de incidencia?
  python scripts/angulo_incidencia.py      # primero: contexto/incidencia.tif por track
  python scripts/diagnostico_tracks.py

Dentro de cada zona el ángulo varía sólo 1–4° (recortes de ~40 km); entre tracks de la misma zona, hasta ~12°
(34° vs 47°). Por eso el ángulo se estudia ENTRE tracks:

  A. Mismos píxeles, distinto track. Por zona y cobertura: mediana de la base (jun–jul) de HH y HV de cada track sobre
     los píxeles válidos en TODOS los tracks de la zona, contra el ángulo medio del track. Pendiente dB/° con efecto
     fijo por zona (sólo se usa la variación entre tracks de una misma zona).
  B. Pares casi simultáneos (≤ 1 día, todos asc/desc): ΔHH = a − b por cobertura. Calibración y hora corren a todas
     las coberturas por igual; el ángulo pega mucho más en el agua que en la tierra. El CONTRASTE
     (ΔHH agua − ΔHH tierra) contra Δθ aísla el ángulo; lo que sobra es viento (agua) y rocío (vegetación), por pasada.

Coberturas: ESA WorldCover SÓLO para estratificar el diagnóstico (contexto, regla 1); no entra en ninguna serie.
Salida: data_nisar/zonas/diagnostico_tracks/{entre_tracks.csv, pares.csv, resumen.txt, *.png}
"""
import warnings

import numpy as np
import pandas as pd
import rasterio

from armonizar_tracks import pares
from metricas_evento import BASE, Evento, cargar_track
from zonas import ZONAS

warnings.filterwarnings("ignore")
OUT = BASE / "diagnostico_tracks"
CLASES = {80: "agua", 10: "monte", 30: "pradera", 40: "cultivo", 90: "humedal"}
TIERRA = ("pradera", "cultivo")
MIN_PX = 2000
MAX_DTIERRA_DB = 5.0


def leer1(path):
    with rasterio.open(path) as r:
        return r.read(1)


def preparar(zona, tdir):
    fi, fw = tdir / "contexto" / "incidencia.tif", tdir / "contexto" / "worldcover.tif"
    if not (fi.exists() and fw.exists()):
        return None
    fechas, hh, hv, perfil = cargar_track(tdir)
    fechas = pd.DatetimeIndex(fechas)
    es_base = Evento(zona).es_base(fechas, hh)
    return dict(fechas=fechas, hh=hh, hv=hv, perfil=perfil, es_base=es_base, inc=leer1(fi), wc=leer1(fw),
                dir=tdir.name.split("_")[0][-1], hh_base=np.nanmedian(hh[es_base], axis=0),
                hv_base=np.nanmedian(hv[es_base & np.array([np.isfinite(x).any() for x in hv])], axis=0))


def misma_grilla(datos):
    """Grupos de tracks de la zona con la misma grilla (los de armonizar_tracks)."""
    grupos = {}
    for n, D in datos.items():
        grupos.setdefault((D["hh"].shape[1:], tuple(D["perfil"]["transform"])[:6]), []).append(n)
    return [g for g in grupos.values() if len(g) >= 2]


def entre_tracks(zona, datos):
    filas = []
    for grupo in misma_grilla(datos):
        ref = datos[grupo[0]]
        comun = np.ones(ref["hh_base"].shape, bool)
        for n in grupo:
            comun &= np.isfinite(datos[n]["hh_base"]) & np.isfinite(datos[n]["inc"])
        for cod, clase in CLASES.items():
            m = comun & (ref["wc"] == cod)
            if m.sum() < MIN_PX:
                continue
            for n in grupo:
                D = datos[n]
                filas.append(dict(zona=zona, track=n, dir=D["dir"], clase=clase, n_px=int(m.sum()),
                                  theta=float(np.mean(D["inc"][m])), hh_base=float(np.median(D["hh_base"][m])),
                                  hv_base=float(np.nanmedian(D["hv_base"][m]))))
    return filas


def pares_resumen(zona, datos):
    filas = []
    for ta, i, tb, j in pares(datos):
        if datos[ta]["dir"] == "D" and datos[tb]["dir"] == "A":     # siempre a = ascendente (~06:30), b = descendente
            ta, i, tb, j = tb, j, ta, i
        A, B = datos[ta], datos[tb]
        v = np.isfinite(A["hh"][i]) & np.isfinite(B["hh"][j]) & np.isfinite(A["inc"]) & np.isfinite(B["inc"])
        fila = dict(zona=zona, track_a=ta, fecha_a=A["fechas"][i].date(), track_b=tb, fecha_b=B["fechas"][j].date(),
                    dir_a=A["dir"], fase="base" if A["es_base"][i] else "evento/post")
        for cod, clase in CLASES.items():
            m = v & (A["wc"] == cod)
            if m.sum() < MIN_PX:
                continue
            fila[f"dtheta_{clase}"] = float(np.mean(A["inc"][m] - B["inc"][m]))
            fila[f"dhh_{clase}"] = float(np.median(A["hh"][i][m] - B["hh"][j][m]))
            dv = A["hv"][i][m] - B["hv"][j][m]
            fila[f"dhv_{clase}"] = float(np.nanmedian(dv)) if np.isfinite(dv).any() else np.nan
        filas.append(fila)
    return filas


def pendiente_fe(df, y, x="theta", grupo="zona"):
    """Pendiente con efecto fijo por grupo: y y x centrados por grupo."""
    d = df[[y, x, grupo]].dropna()
    d = d[d.groupby(grupo)[x].transform("count") >= 2]
    yc = d[y] - d.groupby(grupo)[y].transform("mean")
    xc = d[x] - d.groupby(grupo)[x].transform("mean")
    if len(d) < 4 or (xc ** 2).sum() == 0:
        return np.nan, np.nan, len(d)
    k = float((xc * yc).sum() / (xc ** 2).sum())
    r2 = float(1 - ((yc - k * xc) ** 2).sum() / (yc ** 2).sum()) if (yc ** 2).sum() else np.nan
    return k, r2, len(d)


def ols(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = np.asarray(x)[ok], np.asarray(y)[ok]
    if len(x) < 4:
        return np.nan, np.nan, np.nan, len(x)
    k, c = np.polyfit(x, y, 1)
    r2 = 1 - np.var(y - (k * x + c)) / np.var(y)
    return float(k), float(c), float(r2), len(x)


def graficos(de, dp, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(1, 3, figsize=(15, 4.2))
    colores = {"agua": "#2a78d6", "pradera": "#7fb069", "cultivo": "#e0a458", "monte": "#2d6a4f", "humedal": "#8e7dbe"}
    for clase, g in de.groupby("clase"):
        yc = g.hh_base - g.groupby("zona").hh_base.transform("mean")
        xc = g.theta - g.groupby("zona").theta.transform("mean")
        axs[0].scatter(xc, yc, s=18, color=colores.get(clase), label=clase, alpha=0.8)
    axs[0].set_xlabel("θ of track − zone mean (deg)")
    axs[0].set_ylabel("baseline HH − zone mean (dB)")
    axs[0].set_title("A. Same pixels, different tracks (baseline HH)", fontsize=9)
    axs[0].legend(fontsize=7, frameon=False)
    agua = de[de.clase == "agua"]
    for z, g in agua.groupby("zona"):
        g = g.sort_values("theta")
        axs[1].plot(g.theta, g.hh_base, marker="o", label=z)
        for r in g.itertuples():
            axs[1].annotate(r.track.split("_")[0], (r.theta, r.hh_base), fontsize=6, xytext=(3, 3),
                            textcoords="offset points")
    axs[1].set_xlabel("mean incidence angle of track (deg)")
    axs[1].set_ylabel("baseline HH over water (dB)")
    axs[1].set_title("A. Water: baseline HH vs angle, per zone", fontsize=9)
    axs[1].legend(fontsize=6, frameon=False)
    d = dp.dropna(subset=["contraste", "dtheta_agua"])
    for fase, mk in (("base", "o"), ("evento/post", "^")):
        g = d[d.fase == fase]
        axs[2].scatter(g.dtheta_agua, g.contraste, marker=mk, s=22, label=fase, alpha=0.8)
    k, c, r2, n = ols(d.dtheta_agua, d.contraste)
    if np.isfinite(k):
        xs = np.linspace(d.dtheta_agua.min(), d.dtheta_agua.max(), 10)
        axs[2].plot(xs, k * xs + c, color="k", lw=1)
    axs[2].axhline(0, color="0.6", lw=0.6)
    axs[2].set_xlabel("Δθ = θ_a − θ_b over water (deg)")
    axs[2].set_ylabel("ΔHH water − ΔHH land (dB)")
    axs[2].set_title(f"B. Near-simultaneous pairs: k={k:.2f} dB/°, R²={r2:.2f}, n={n}", fontsize=9)
    axs[2].legend(fontsize=7, frameon=False)
    plt.tight_layout()
    plt.savefig(path, dpi=110)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    fe, fp = [], []
    for zona in ZONAS:
        tdirs = sorted((BASE / zona).glob("T*_F*"))
        if len(tdirs) < 2:
            continue
        print(f"== {zona}")
        datos = {t.name: D for t in tdirs if (D := preparar(zona, t)) is not None}
        fe += entre_tracks(zona, datos)
        fp += pares_resumen(zona, datos)
    de, dp = pd.DataFrame(fe), pd.DataFrame(fp)
    tierra = dp[[f"dhh_{c}" for c in TIERRA if f"dhh_{c}" in dp]].mean(axis=1)
    dp["contraste"] = dp.get("dhh_agua") - tierra
    dp["contraste_hv"] = dp.get("dhv_agua") - dp[[f"dhv_{c}" for c in TIERRA if f"dhv_{c}" in dp]].mean(axis=1)
    # pasadas con calibración rota (p. ej. T60A_F162 2026-06-18: +24 dB en todo el recorte): fuera del ajuste
    dp["calibracion_rota"] = tierra.abs() > MAX_DTIERRA_DB
    de.round(3).to_csv(OUT / "entre_tracks.csv", index=False)
    dp.round(3).to_csv(OUT / "pares.csv", index=False)
    rotas = dp[dp.calibracion_rota]
    dp = dp[~dp.calibracion_rota & tierra.notna()]
    graficos(de, dp, OUT / "diagnostico.png")

    lineas = ["A. Mismos píxeles, distinto track (efecto fijo por zona): pendiente de la base vs ángulo del track"]
    for clase, g in de.groupby("clase"):
        k, r2, n = pendiente_fe(g, "hh_base")
        kv, r2v, _ = pendiente_fe(g, "hv_base")
        lineas.append(f"   {clase:8s} HH {k:+.2f} dB/° (R² {r2:.2f}) · HV {kv:+.2f} dB/° (R² {r2v:.2f}) · n={n} tracks")
    lineas.append(f"\nB. Pares casi simultáneos (a = asc ~06:30, b = desc ~18:30): ΔHH por cobertura vs Δθ. "
                  f"Excluidos por calibración rota (|ΔHH tierra| > {MAX_DTIERRA_DB} dB): "
                  + (", ".join(f"{r.zona} {r.fecha_a}/{r.fecha_b}" for r in rotas.itertuples()) or "ninguno"))
    for clase in CLASES.values():
        if f"dhh_{clase}" in dp:
            k, c, r2, n = ols(dp[f"dtheta_{clase}"], dp[f"dhh_{clase}"])
            sd = dp[f"dhh_{clase}"].std()
            sd_zona = dp.groupby("zona")[f"dhh_{clase}"].std().median()
            lineas.append(f"   {clase:8s} k {k:+.2f} dB/° · intercepto (asc−desc a Δθ=0) {c:+.2f} dB · R² {r2:.2f} · "
                          f"sd ΔHH {sd:.2f} dB · sd entre pasadas de una zona (mismo Δθ) {sd_zona:.2f} dB · n={n}")
    for fase in ("todas", "base", "evento/post"):
        g = dp if fase == "todas" else dp[dp.fase == fase]
        k, c, r2, n = ols(g.dtheta_agua, g.contraste)
        kv, _, r2v, _ = ols(g.dtheta_agua, g.contraste_hv)
        lineas.append(f"   contraste agua−tierra [{fase}]: HH k {k:+.2f} dB/° R² {r2:.2f} · "
                      f"HV k {kv:+.2f} dB/° R² {r2v:.2f} · sd {g.contraste.std():.2f} dB · n={n}")
    txt = "\n".join(lineas)
    (OUT / "resumen.txt").write_text(txt + "\n")
    print("\n" + txt)
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
