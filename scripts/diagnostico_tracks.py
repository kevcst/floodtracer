"""
Diagnóstico entre tracks (paso 1): ¿cuánto del desacuerdo entre tracks explica el ángulo de incidencia?
  python scripts/angulo_incidencia.py      # primero: contexto/incidencia.tif por track
  python scripts/diagnostico_tracks.py

Todos los pares casi simultáneos (≤ 1 día, los de armonizar_tracks.py) son ascendente vs. descendente: ángulo, hora
(~06:30 vs ~18:30) y dirección de observación van juntos. Se separan así: dentro de un par, Δθ = θa − θb VARÍA a lo
ancho de la escena (un track mira al este y el otro al oeste), mientras que hora/rocío/calibración son ~parejos en
toda la escena → un corrimiento constante por par. Viento sobre el agua: puede variar en el espacio (queda en el resto).

Partes
  A. Dentro de cada escena: σ° base (mediana jun–jul) vs θ por cobertura → pendiente dB/° por clase y track.
  B. Pares casi simultáneos: ΔHH (y ΔHV) = a − b por píxel, por clase. Desvío del resto con modelos crecientes:
       M0 crudo · M1 corrimiento por par y clase (calibración, hora, rocío/viento parejos en la escena) ·
       M2 = M1 + k_clase·Δθ (pendiente común por clase, estimada dentro de los pares)
     Si M2 baja mucho respecto de M1, el ángulo explica el desacuerdo y un criterio global con normalización por
     ángulo es viable. Si no, domina lo que cambia entre pasadas (hora, viento, dirección).
Coberturas: ESA WorldCover SÓLO para estratificar el diagnóstico (contexto, regla 1); no entra en ninguna serie.
Salida: data_nisar/zonas/diagnostico_tracks/{intra_escena.csv, pares.csv, modelos.csv, *.png}
"""
import warnings

import numpy as np
import pandas as pd
import rasterio

from armonizar_tracks import pares
from metricas_evento import BASE, Evento, cargar_track
from zonas import ZONAS

warnings.filterwarnings("ignore", category=RuntimeWarning)
OUT = BASE / "diagnostico_tracks"
CLASES = {80: "agua", 10: "monte", 30: "pradera", 40: "cultivo", 90: "humedal"}
N_MUESTRA = 40_000
RNG = np.random.default_rng(0)


def leer1(path):
    with rasterio.open(path) as r:
        return r.read(1)


def preparar(zona, tdir):
    fi = tdir / "contexto" / "incidencia.tif"
    fw = tdir / "contexto" / "worldcover.tif"
    if not (fi.exists() and fw.exists()):
        return None
    fechas, hh, hv, perfil = cargar_track(tdir)
    fechas = pd.DatetimeIndex(fechas)
    es_base = Evento(zona).es_base(fechas, hh)
    return dict(fechas=fechas, hh=hh, hv=hv, perfil=perfil, es_base=es_base, inc=leer1(fi), wc=leer1(fw),
                hh_base=np.nanmedian(hh[es_base], axis=0), hv_base=np.nanmedian(hv[es_base], axis=0))


def intra_escena(zona, nombre, D):
    filas = []
    for cod, clase in CLASES.items():
        m = (D["wc"] == cod) & np.isfinite(D["hh_base"]) & np.isfinite(D["inc"])
        if m.sum() < 2000:
            continue
        th, h, v = D["inc"][m], D["hh_base"][m], D["hv_base"][m]
        k_hh = np.polyfit(th, h, 1)[0]
        ok = np.isfinite(v)
        k_hv = np.polyfit(th[ok], v[ok], 1)[0] if ok.sum() > 2000 else np.nan
        filas.append(dict(zona=zona, track=nombre, clase=clase, n=int(m.sum()), theta_min=float(np.percentile(th, 2)),
                          theta_max=float(np.percentile(th, 98)), hh_med=float(np.median(h)),
                          k_hh_db_por_grado=float(k_hh), k_hv_db_por_grado=float(k_hv)))
    return filas


def muestra_par(zona, ta, i, tb, j, A, B):
    v = (np.isfinite(A["hh"][i]) & np.isfinite(B["hh"][j]) & np.isfinite(A["inc"]) & np.isfinite(B["inc"]))
    filas = []
    for cod, clase in CLASES.items():
        idx = np.flatnonzero(v & (A["wc"] == cod))
        if idx.size < 500:
            continue
        idx = RNG.choice(idx, min(N_MUESTRA, idx.size), replace=False)
        filas.append(pd.DataFrame(dict(
            zona=zona, par=f"{zona}|{ta}|{A['fechas'][i].date()}|{tb}|{B['fechas'][j].date()}",
            fase="base" if A["es_base"][i] else "evento/post", clase=clase,
            dtheta=A["inc"].ravel()[idx] - B["inc"].ravel()[idx],
            dhh=A["hh"][i].ravel()[idx] - B["hh"][j].ravel()[idx],
            dhv=A["hv"][i].ravel()[idx] - B["hv"][j].ravel()[idx])))
    return filas


def ajustar(df, y):
    """Desvío del resto por clase con los modelos M0–M3 (pendiente común por clase, corrimientos por par)."""
    filas = []
    for (fase, clase), g in df.groupby(["fase", "clase"]):
        g = g[np.isfinite(g[y]) & np.isfinite(g.dtheta)]
        if len(g) < 5000:
            continue
        yv, x = g[y].to_numpy(), g.dtheta.to_numpy()
        r0 = yv
        r1 = yv - g.groupby("par")[y].transform("mean").to_numpy()
        xc = x - g.groupby("par").dtheta.transform("mean").to_numpy()
        k = float(np.sum(xc * r1) / np.sum(xc * xc))          # pendiente común dentro de pares (efectos fijos)
        r2 = r1 - k * xc
        filas.append(dict(variable=y, fase=fase, clase=clase, n=len(g), pares=g.par.nunique(),
                          k_db_por_grado=k, rango_dtheta=float(np.percentile(x, 98) - np.percentile(x, 2)),
                          sd_M0_crudo=float(np.std(r0)), sd_M1_offset_par=float(np.std(r1)),
                          sd_M2_offset_mas_angulo=float(np.std(r2)),
                          var_explicada_angulo_pct=float(100 * (1 - np.var(r2) / np.var(r1)))))
    return filas


def grafico_intra(df, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(1, 2, figsize=(11, 3.8))
    for ax, col, t in ((axs[0], "k_hh_db_por_grado", "HH"), (axs[1], "k_hv_db_por_grado", "HV")):
        for x, (clase, g) in enumerate(df.groupby("clase")):
            ax.scatter(np.full(len(g), x) + RNG.uniform(-0.15, 0.15, len(g)), g[col], s=14, alpha=0.7)
            ax.hlines(g[col].median(), x - 0.3, x + 0.3, color="k")
        ax.set_xticks(range(df.clase.nunique()), sorted(df.clase.unique()))
        ax.axhline(0, color="0.6", lw=0.6)
        ax.set_title(f"Within-scene slope of baseline {t} vs incidence (one dot = one track)", fontsize=9)
        ax.set_ylabel("dB per degree")
    plt.tight_layout()
    plt.savefig(path, dpi=110)
    plt.close(fig)


def grafico_pares(df, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    clases = [c for c in CLASES.values() if c in set(df.clase)]
    fig, axs = plt.subplots(1, len(clases), figsize=(3.4 * len(clases), 3.4), sharey=True)
    for ax, clase in zip(np.atleast_1d(axs), clases):
        g = df[(df.clase == clase) & (df.fase == "base")]
        g = g.assign(r=g.dhh - g.groupby("par").dhh.transform("mean"))
        b = pd.cut(g.dtheta, np.arange(-20, 21, 1))
        s = g.groupby(b, observed=True).r.agg(["median", lambda x: x.quantile(.25), lambda x: x.quantile(.75)])
        xc = [iv.mid for iv in s.index]
        ax.fill_between(xc, s.iloc[:, 1], s.iloc[:, 2], alpha=0.3)
        ax.plot(xc, s["median"])
        ax.axhline(0, color="0.6", lw=0.6)
        ax.set_title(f"{clase} (base pairs)", fontsize=9)
        ax.set_xlabel("Δθ = θ_a − θ_b (deg)")
    np.atleast_1d(axs)[0].set_ylabel("ΔHH − pair mean (dB)")
    fig.suptitle("Near-simultaneous asc/desc pairs: does the HH difference follow the angle difference?", fontsize=10)
    plt.tight_layout()
    plt.savefig(path, dpi=110)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    intra, muestras = [], []
    for zona in ZONAS:
        tdirs = sorted((BASE / zona).glob("T*_F*"))
        if not tdirs:
            continue
        print(f"== {zona}")
        datos = {}
        for t in tdirs:
            D = preparar(zona, t)
            if D is None:
                print(f"   ! {t.name}: falta incidencia.tif o worldcover.tif")
                continue
            datos[t.name] = D
            intra += intra_escena(zona, t.name, D)
        for ta, i, tb, j in pares(datos):
            muestras += muestra_par(zona, ta, i, tb, j, datos[ta], datos[tb])
    di = pd.DataFrame(intra)
    di.round(3).to_csv(OUT / "intra_escena.csv", index=False)
    dp = pd.concat(muestras, ignore_index=True)
    resumen_pares = dp.groupby(["par", "fase", "clase"]).agg(
        n=("dhh", "size"), dhh_media=("dhh", "mean"), dhh_sd=("dhh", "std"), dhv_media=("dhv", "mean"),
        dtheta_media=("dtheta", "mean"), dtheta_rango=("dtheta", lambda x: x.quantile(.98) - x.quantile(.02)))
    resumen_pares.round(3).to_csv(OUT / "pares.csv")
    dm = pd.DataFrame(ajustar(dp, "dhh") + ajustar(dp, "dhv"))
    dm.round(3).to_csv(OUT / "modelos.csv", index=False)
    grafico_intra(di, OUT / "intra_escena.png")
    grafico_pares(dp, OUT / "pares_dhh_vs_dtheta.png")
    pd.set_option("display.width", 200)
    print("\nA. Pendiente dentro de la escena (mediana entre tracks, dB/°):")
    print(di.groupby("clase")[["k_hh_db_por_grado", "k_hv_db_por_grado", "hh_med"]].median().round(3).to_string())
    print("\nB. Pares casi simultáneos — desvío del resto (dB) y % explicado por el ángulo:")
    print(dm.round(3).to_string(index=False))
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
