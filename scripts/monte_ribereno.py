"""
¿La subida de HH−HV en el monte durante agosto es agua bajo los árboles o suelo húmedo en general?
Compara monte ribereño (fondo de valle) vs monte de altura (lomas) en cada zona/track.

  python scripts/monte_ribereno.py [--zona durazno]

Contexto topográfico (NO entra en las series NISAR, sólo clasifica píxeles): Copernicus DEM GLO-30 (AWS, público).
  - El DEM es un DSM (incluye copas): suelo ≈ mínimo móvil de 500 m.
  - Altura relativa (proxy de HAND) = suelo − mínimo del suelo en 3 km.
  - Monte = HH base > −7 dB y HV base > −14 dB (igual que metricas_evento.py).
  - Ribereño: monte con altura relativa < 4 m · De altura: monte con altura relativa > 12 m.
Si el agua está bajo el monte ribereño, HH−HV debe subir ahí y NO (o mucho menos) en el monte de altura.

Salida: .../T*/contexto/{dem,altura_rel,clase_monte}.tif ; data_nisar/zonas/monte_ribereno.csv / .png
  clase_monte: 1 = ribereño, 2 = de altura, 3 = otro monte, 0 = no monte
"""
import argparse
import math
import subprocess
import warnings

import numpy as np
import pandas as pd
import rasterio
from scipy import ndimage as ndi

from metricas_evento import BASE, EVENTO, FIN_BASE, cargar_track, guardar
from zonas import ZONAS

warnings.filterwarnings("ignore", category=RuntimeWarning)
DEM_URL = "/vsis3/copernicus-dem-30m/Copernicus_DSM_COG_10_{t}_DEM/Copernicus_DSM_COG_10_{t}_DEM.tif"
H_RIB, H_ALT = 4.0, 12.0


def tiles(wkt):
    nums = [float(v) for v in wkt.replace("POLYGON((", "").replace("))", "").replace(",", " ").split()]
    lons, lats = nums[0::2], nums[1::2]
    out = []
    for la in range(math.floor(min(lats)), math.floor(max(lats)) + 1):
        for lo in range(math.floor(min(lons)), math.floor(max(lons)) + 1):
            out.append(f"{'S' if la < 0 else 'N'}{abs(la):02d}_00_{'W' if lo < 0 else 'E'}{abs(lo):03d}_00")
    return out


def dem_en_grilla(zona, perfil, destino):
    """Reproyecta el DEM a la grilla exacta del track (bilineal)."""
    if destino.exists():
        return
    t = perfil["transform"]
    xmin, ymax = t.c, t.f
    xmax, ymin = xmin + t.a * perfil["width"], ymax + t.e * perfil["height"]
    fuentes = [DEM_URL.format(t=x) for x in tiles(ZONAS[zona]["wkt"])]
    cmd = ["gdalwarp", "-q", "-overwrite", "-r", "bilinear", "-t_srs", perfil["crs"].to_wkt(),
           "-te", str(xmin), str(ymin), str(xmax), str(ymax), "-ts", str(perfil["width"]), str(perfil["height"]),
           "-ot", "Float32", "-co", "COMPRESS=DEFLATE", *fuentes, str(destino),
           "--config", "AWS_NO_SIGN_REQUEST", "YES"]
    subprocess.run(cmd, check=True)


def procesar(zona, tdir):
    fechas, hh, hv, perfil = cargar_track(tdir)
    fechas = pd.DatetimeIndex(fechas)
    fin_base = pd.Timestamp(ZONAS[zona].get("fin_base", FIN_BASE))
    es_base = np.asarray(fechas < fin_base)
    es_evento = np.asarray((fechas >= EVENTO[0]) & (fechas <= EVENTO[1]))
    valid = np.all(np.isfinite(hh), axis=0)

    ctx = tdir / "contexto"
    ctx.mkdir(exist_ok=True)
    dem_en_grilla(zona, perfil, ctx / "dem.tif")
    with rasterio.open(ctx / "dem.tif") as r:
        dem = r.read(1).astype("float32")
    px = abs(perfil["transform"].a)
    suelo = ndi.minimum_filter(dem, size=max(3, int(500 / px)))
    hrel = suelo - ndi.minimum_filter(suelo, size=int(3000 / px))

    hh_base, hv_base = np.nanmean(hh[es_base], axis=0), np.nanmean(hv[es_base], axis=0)
    monte = valid & (hh_base > -7) & (hv_base > -14)
    rib, alt = monte & (hrel < H_RIB), monte & (hrel > H_ALT)
    clase = np.where(rib, 1, np.where(alt, 2, np.where(monte, 3, 0)))
    guardar(ctx / "altura_rel.tif", np.where(valid, hrel, np.nan), perfil, "float32", np.nan)
    guardar(ctx / "clase_monte.tif", clase, perfil, "uint8")

    filas = []
    dif = hh - hv
    for nombre, m in [("ribereno", rib), ("altura", alt), ("no_monte", valid & ~monte)]:
        if m.sum() < 100:
            continue
        for i, f in enumerate(fechas):
            filas.append(dict(zona=zona, track=tdir.name, clase=nombre, n_px=int(m.sum()), fecha=f,
                              fase="base" if es_base[i] else ("evento" if es_evento[i] else "post"),
                              hh_db=float(np.nanmedian(hh[i][m])), hh_hv_db=float(np.nanmedian(dif[i][m]))))
    df = pd.DataFrame(filas)
    if df.empty:
        return df
    d = df.groupby(["clase", "fase"]).hh_hv_db.mean().unstack()
    txt = " | ".join(f"{c}: Δ(HH−HV) evento−base {d.loc[c, 'evento'] - d.loc[c, 'base']:+.2f} dB"
                     for c in d.index if {"base", "evento"} <= set(d.columns))
    print(f"== {zona}/{tdir.name}  ribereño {100 * rib.sum() / valid.sum():.1f} %  altura "
          f"{100 * alt.sum() / valid.sum():.1f} %\n   {txt}")
    return df


def grafico(df, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    grupos = list(df.groupby(["zona", "track"]))
    cols = 3
    filas = math.ceil(len(grupos) / cols)
    fig, axs = plt.subplots(filas, cols, figsize=(5 * cols, 3 * filas), sharey=True, squeeze=False)
    colores = {"ribereno": "tab:blue", "altura": "tab:green", "no_monte": "tab:gray"}
    for ax in axs.flat:
        ax.axis("off")
    for ax, ((z, t), g) in zip(axs.flat, grupos):
        ax.axis("on")
        for c, gc in g.groupby("clase"):
            base = gc[gc.fase == "base"].hh_hv_db.mean()
            ax.plot(gc.fecha, gc.hh_hv_db - base, marker="o", ms=3, color=colores[c], label=c)
        ax.axvspan(pd.Timestamp("2026-08-15"), pd.Timestamp("2026-08-19"), color="tab:red", alpha=0.15)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_title(f"{z} {t}", fontsize=9)
        ax.tick_params(labelsize=7)
    axs[0, 0].set_ylabel("HH−HV − media base (dB)")
    axs[0, 0].legend(fontsize=7)
    fig.suptitle("Monte ribereño vs de altura: si el agua está bajo los árboles, sólo sube el ribereño", fontsize=10)
    plt.tight_layout()
    plt.savefig(path, dpi=100)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--zona", default="todas", choices=["todas", *ZONAS])
    a = ap.parse_args()
    dfs = [procesar(z, t) for z in (ZONAS if a.zona == "todas" else [a.zona]) for t in sorted((BASE / z).glob("T*_F*"))]
    df = pd.concat([d for d in dfs if not d.empty])
    sufijo = "" if a.zona == "todas" else f"_{a.zona}"   # el CSV global sólo con todas las zonas (lo usa exportar_poc.py)
    df.round({"hh_db": 3, "hh_hv_db": 3}).to_csv(BASE / f"monte_ribereno{sufijo}.csv", index=False)
    grafico(df, BASE / f"monte_ribereno{sufijo}.png")
    print(f"-> {BASE / f'monte_ribereno{sufijo}.csv'}, {BASE / f'monte_ribereno{sufijo}.png'}")
