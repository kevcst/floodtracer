"""
¿La subida de HH−HV en el monte durante agosto es agua bajo los árboles o suelo húmedo en general?
Compara monte ribereño (fondo de valle) vs monte de altura (lomas) en cada zona/track.

  python scripts/monte_ribereno.py [--zona rocha_norte]

Contexto topográfico (NO entra en las series NISAR, sólo clasifica píxeles): Copernicus DEM GLO-30 (AWS, público).
  - El DEM es un DSM (incluye copas): suelo ≈ mínimo móvil de 500 m.
  - HAND (altura sobre el drenaje más cercano) = suelo − suelo del píxel de río/arroyo OSM más cercano
    (capas_contexto.py; ríos, arroyos, canales). Si la zona no tiene ríos OSM, cae al proxy viejo
    (suelo − mínimo del suelo en 3 km).
  - Monte = HH base > −7 dB y HV base > −14 dB (igual que metricas_evento.py).
  - Ribereño: monte con HAND < 4 m y a < 1 km de un cauce · De altura: monte con HAND > 12 m.
Si el agua está bajo el monte ribereño, HH−HV debe subir ahí y NO (o mucho menos) en el monte de altura.
El monte de altura también sube un poco (suelo y troncos mojados): ese componente general se RESTA.
  exceso ribereño(fecha) = [HH−HV ribereño − su base] − [HH−HV de altura − su base]
Mapa: veg_inundada_ribereno.tif = monte ribereño donde, en alguna pasada del evento, el píxel sube > 2 dB en HH−HV
por encima de lo que sube la mediana del monte de altura esa fecha, y HH sube > 1 dB (doble rebote).

Salida: .../T*/contexto/{dem,hand,dist_rio,clase_monte}.tif · .../T*/metricas/veg_inundada_ribereno.tif
        data_nisar/zonas/monte_ribereno.csv / .png · monte_ribereno_resumen.csv
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

from metricas_evento import BASE, Evento, cargar_track, guardar, tracks_zona
from zonas import ZONAS

warnings.filterwarnings("ignore", category=RuntimeWarning)
DEM_URL = "/vsis3/copernicus-dem-30m/Copernicus_DSM_COG_10_{t}_DEM/Copernicus_DSM_COG_10_{t}_DEM.tif"
H_RIB, H_ALT = 4.0, 12.0
DIST_RIB = 1000.0
EXCESO_PX_DB, DHH_PX_DB = 2.0, 1.0
CAPAS = BASE.parent / "contexto" / "capas"


def hand_osm(zona, perfil, suelo):
    """HAND con la red de drenaje OSM: suelo − suelo del cauce más cercano. None si no hay cauces."""
    import geopandas as gpd
    from rasterio.features import rasterize

    gpkg = CAPAS / f"{zona}.gpkg"
    if not gpkg.exists():
        return None, None
    rios = gpd.read_file(gpkg, layer="rios").to_crs(perfil["crs"])
    rios = rios[rios.waterway.isin(["river", "stream", "canal"])]
    if rios.empty:
        return None, None
    cauce = rasterize(((g, 1) for g in rios.geometry), out_shape=(perfil["height"], perfil["width"]),
                      transform=perfil["transform"], fill=0, dtype="uint8", all_touched=True).astype(bool)
    dist, (fi, ci) = ndi.distance_transform_edt(~cauce, return_indices=True)
    return suelo - suelo[fi, ci], dist * abs(perfil["transform"].a)


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
    ev = Evento(zona)
    es_base = ev.es_base(fechas, hh)
    es_evento = ev.es_evento(fechas)
    valid = np.all(np.isfinite(hh), axis=0)

    ctx = tdir / "contexto"
    ctx.mkdir(exist_ok=True)
    dem_en_grilla(zona, perfil, ctx / "dem.tif")
    with rasterio.open(ctx / "dem.tif") as r:
        dem = r.read(1).astype("float32")
    px = abs(perfil["transform"].a)
    suelo = ndi.minimum_filter(dem, size=max(3, int(500 / px)))
    hrel, dist = hand_osm(zona, perfil, suelo)
    metodo = "hand_osm"
    if hrel is None:
        hrel, dist, metodo = suelo - ndi.minimum_filter(suelo, size=int(3000 / px)), np.zeros_like(suelo), "proxy_3km"

    hh_base, hv_base = np.nanmean(hh[es_base], axis=0), np.nanmean(hv[es_base], axis=0)
    monte = valid & (hh_base > -7) & (hv_base > -14)
    rib, alt = monte & (hrel < H_RIB) & (dist < DIST_RIB), monte & (hrel > H_ALT)
    clase = np.where(rib, 1, np.where(alt, 2, np.where(monte, 3, 0)))
    guardar(ctx / "hand.tif", np.where(valid, hrel, np.nan), perfil, "float32", np.nan)
    guardar(ctx / "dist_rio.tif", np.where(valid, dist, np.nan), perfil, "float32", np.nan)
    guardar(ctx / "clase_monte.tif", clase, perfil, "uint8")

    # mapa de agua bajo monte ribereño, descontando el componente general de humedad (monte de altura)
    dif = hh - hv
    tiene_hv = np.array([np.isfinite(dif[i]).any() for i in range(len(fechas))])
    dif_base = np.nanmean(dif[es_base & tiene_hv], axis=0) if (es_base & tiene_hv).any() else None
    veg = np.zeros(valid.shape, bool)
    if dif_base is not None and alt.sum() >= 100:
        for i in np.where(es_evento & tiene_hv)[0]:
            ref = float(np.nanmedian((dif[i] - dif_base)[alt]))
            veg |= rib & ((dif[i] - dif_base) - ref > EXCESO_PX_DB) & (hh[i] - hh_base > DHH_PX_DB)
    guardar(tdir / "metricas" / "veg_inundada_ribereno.tif", veg, perfil, "uint8")
    ha_px = px * px / 1e4

    filas = []
    for nombre, m in [("ribereno", rib), ("altura", alt), ("no_monte", valid & ~monte)]:
        if m.sum() < 100:
            continue
        for i, f in enumerate(fechas):
            filas.append(dict(zona=zona, track=tdir.name, clase=nombre, n_px=int(m.sum()), fecha=f,
                              fase="base" if es_base[i] else ("evento" if es_evento[i] else "post"), metodo=metodo,
                              ha_veg_inundada=veg.sum() * ha_px, ha_ribereno=rib.sum() * ha_px,
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
            ax.plot(gc.fecha, gc.hh_hv_db - base, marker="o", ms=3, color=colores[c],
                    label={"ribereno": "riverside forest", "altura": "upland forest", "no_monte": "open land"}.get(c, c))
        ax.axvspan(*Evento(z).lluvia, color="tab:red", alpha=0.15)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_title(f"{z} {t}", fontsize=9)
        ax.tick_params(labelsize=7)
    axs[0, 0].set_ylabel("HH−HV minus baseline mean (dB)")
    axs[0, 0].legend(fontsize=7)
    fig.suptitle("Riverside vs upland forest: if water is under the trees, only the riverside forest rises", fontsize=10)
    plt.tight_layout()
    plt.savefig(path, dpi=100)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--zona", default="todas", choices=["todas", *ZONAS])
    a = ap.parse_args()
    dfs = [procesar(z, t) for z in (ZONAS if a.zona == "todas" else [a.zona]) for t in tracks_zona(z)]
    df = pd.concat([d for d in dfs if not d.empty])
    # resumen: exceso ribereño medio en las pasadas del evento (con HV)
    filas = []
    for (z, t), g in df.groupby(["zona", "track"]):
        piv = g.pivot_table(index=["fecha", "fase"], columns="clase", values="hh_hv_db").reset_index()
        if not {"ribereno", "altura"} <= set(piv.columns):
            continue
        b = piv[piv.fase == "base"][["ribereno", "altura"]].mean()
        ev = piv[piv.fase == "evento"].dropna(subset=["ribereno", "altura"])
        if ev.empty:
            continue
        exc = (ev.ribereno - b.ribereno) - (ev.altura - b.altura)
        filas.append(dict(zona=z, track=t, metodo=g.metodo.iloc[0], subida_ribereno_db=(ev.ribereno - b.ribereno).mean(),
                          subida_altura_db=(ev.altura - b.altura).mean(), exceso_ribereno_db=exc.mean(),
                          exceso_max_db=exc.max(), ha_ribereno=g.ha_ribereno.iloc[0],
                          ha_veg_inundada=g.ha_veg_inundada.iloc[0]))
    res = pd.DataFrame(filas).round(2)
    if a.zona == "todas":
        res.to_csv(BASE / "monte_ribereno_resumen.csv", index=False)
    print(res.to_string(index=False))
    sufijo = "" if a.zona == "todas" else f"_{a.zona}"   # el CSV global sólo con todas las zonas (lo usa exportar_app.py)
    df.round({"hh_db": 3, "hh_hv_db": 3}).to_csv(BASE / f"monte_ribereno{sufijo}.csv", index=False)
    grafico(df, BASE / f"monte_ribereno{sufijo}.png")
    print(f"-> {BASE / f'monte_ribereno{sufijo}.csv'}, {BASE / f'monte_ribereno{sufijo}.png'}")
