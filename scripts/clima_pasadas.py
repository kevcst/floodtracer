"""
¿El residuo por pasada sobre el agua es viento? (paso 2 del diagnóstico entre tracks). Sólo CONTEXTO (regla 1):
el clima explica/marca pasadas, no corrige valores de NISAR.
  python scripts/clima_pasadas.py

Para cada zona/track/pasada:
  - HH del día − HH típico del track (mediana entre pasadas) sobre agua permanente (WorldCover 80, ≥ 2000 px) y sobre
    tierra (pradera + cultivo). Al restar la mediana del MISMO track se cancela el ángulo: queda lo que cambia por día.
  - Clima ERA5 / ERA5-Land vía Open-Meteo (archivo histórico, sin clave) a la hora UTC de la escena (nombre de la
    escena en ASF): viento 10 m y ráfaga, lluvia de las 24/72 h previas, T − Td (rocío si ~0), humedad del suelo 0–7 cm.
    Punto del viento: centroide del agua de la zona (si hay) o del AOI; la celda de ERA5 es ~10–25 km.
Salida: data_nisar/zonas/diagnostico_tracks/clima_pasadas.csv · clima.png · clima_resumen.txt
"""
import json
import ssl
import urllib.request
import warnings

import certifi
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform as warp_transform
from shapely import wkt as shp_wkt

from descargar_zonas import escenas
from metricas_evento import BASE, Evento, cargar_track
from zonas import ZONAS

warnings.filterwarnings("ignore")
OUT = BASE / "diagnostico_tracks"
CACHE = BASE / "_clima"
API = "https://archive-api.open-meteo.com/v1/archive"
VARS = "wind_speed_10m,wind_direction_10m,wind_gusts_10m,precipitation,temperature_2m,dew_point_2m,soil_moisture_0_to_7cm"
INI, FIN = "2026-06-01", "2026-11-10"
MIN_PX = 2000
CTX = ssl.create_default_context(cafile=certifi.where())


def clima(lat, lon, nombre):
    f = CACHE / f"{nombre}.json"
    if not f.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        u = (f"{API}?latitude={lat:.4f}&longitude={lon:.4f}&start_date={INI}&end_date={FIN}&hourly={VARS}"
             f"&wind_speed_unit=ms&timezone=GMT")
        f.write_text(urllib.request.urlopen(u, context=CTX, timeout=120).read().decode())
    h = json.loads(f.read_text())["hourly"]
    df = pd.DataFrame(h)
    df["time"] = pd.to_datetime(df.time)
    df = df.set_index("time")
    df["lluvia_24h"] = df.precipitation.rolling(24, min_periods=1).sum()
    df["lluvia_72h"] = df.precipitation.rolling(72, min_periods=1).sum()
    df["t_menos_td"] = df.temperature_2m - df.dew_point_2m
    return df


def horas_paso(zona):
    """(track_dir, fecha) → hora UTC de la escena (del nombre: ..._YYYYMMDDTHHMMSS_...)."""
    df = escenas(zona, ["PROVISIONAL", "VALIDATED"])
    out = {}
    for r in df.itertuples():
        t = pd.Timestamp(r.escena.split("_")[-7][:15])        # inicio de adquisición (…_M_20260617T213500_…)
        out[(f"T{r.track}{r.dir}_F{r.frame}", r.fecha)] = t
    return out


def centroide_agua(tdir):
    wc_f = tdir / "contexto" / "worldcover.tif"
    if not wc_f.exists():
        return None
    with rasterio.open(wc_f) as r:
        wc, tr, crs = r.read(1), r.transform, r.crs
    fil, col = np.nonzero(wc == 80)
    if fil.size < MIN_PX:
        return None
    x, y = rasterio.transform.xy(tr, [int(np.median(fil))], [int(np.median(col))])
    lon, lat = warp_transform(crs, "EPSG:4326", x, y)
    return lat[0], lon[0]


def main():
    filas = []
    for zona in ZONAS:
        tdirs = sorted((BASE / zona).glob("T*_F*"))
        if not tdirs:
            continue
        print(f"== {zona}")
        horas = horas_paso(zona)
        c = shp_wkt.loads(ZONAS[zona]["wkt"]).centroid
        punto = next((p for t in tdirs if (p := centroide_agua(t))), (c.y, c.x))
        met = clima(*punto, zona)
        ev = Evento(zona)
        for tdir in tdirs:
            wc_f = tdir / "contexto" / "worldcover.tif"
            if not wc_f.exists():
                continue
            with rasterio.open(wc_f) as r:
                wc = r.read(1)
            fechas, hh, hv, _ = cargar_track(tdir)
            fechas = pd.DatetimeIndex(fechas)
            es_base, es_evento = ev.es_base(fechas, hh), ev.es_evento(fechas)
            valid = np.all(np.isfinite(hh), axis=0)
            agua, tierra = valid & (wc == 80), valid & np.isin(wc, (30, 40))
            hay_agua = agua.sum() >= MIN_PX
            m_agua = np.array([np.median(x[agua]) for x in hh]) if hay_agua else np.full(len(fechas), np.nan)
            m_tierra = np.array([np.median(x[tierra]) for x in hh])
            for i, f in enumerate(fechas):
                t = horas.get((tdir.name, str(f.date())))
                if t is None:
                    continue
                w = met.iloc[met.index.get_indexer([t.round("h")], method="nearest")[0]]
                filas.append(dict(zona=zona, track=tdir.name, dir=tdir.name.split("_")[0][-1], fecha=f.date(),
                                  hora_utc=t.strftime("%H:%M"), fase="base" if es_base[i] else
                                  ("evento" if es_evento[i] else "otra"), px_agua=int(agua.sum()) if hay_agua else 0,
                                  hh_agua=m_agua[i], dev_agua=m_agua[i] - np.nanmedian(m_agua),
                                  hh_tierra=m_tierra[i], dev_tierra=m_tierra[i] - np.median(m_tierra),
                                  viento=w.wind_speed_10m, rafaga=w.wind_gusts_10m, dir_viento=w.wind_direction_10m,
                                  lluvia_24h=w.lluvia_24h, lluvia_72h=w.lluvia_72h, t_menos_td=w.t_menos_td,
                                  humedad_suelo=w.soil_moisture_0_to_7cm))
    df = pd.DataFrame(filas)
    OUT.mkdir(exist_ok=True)
    df.round(3).to_csv(OUT / "clima_pasadas.csv", index=False)
    resumen(df)
    grafico(df, OUT / "clima.png")


def ajuste(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 8:
        return np.nan, np.nan, int(ok.sum())
    k, c = np.polyfit(x[ok], y[ok], 1)
    return float(k), float(np.corrcoef(x[ok], y[ok])[0, 1] ** 2), int(ok.sum())


def resumen(df):
    a = df[df.px_agua > 0]
    grandes = a[a.px_agua >= 50_000]          # lagunas y ríos anchos: los ríos angostos son píxeles mezclados
    lineas = ["Desvío del HH de la pasada respecto de la mediana de su track (ángulo cancelado) vs clima a la hora del paso"]
    for nombre, g in (("agua (toda)", a), ("agua grande ≥ 50.000 px", grandes)):
        for var in ("viento", "rafaga"):
            k, r2, n = ajuste(g[var].to_numpy(), g.dev_agua.to_numpy())
            lineas.append(f"   {nombre:24s} vs {var:7s}: {k:+.2f} dB por m/s · R² {r2:.2f} · n={n} pasadas")
        lineas.append(f"   {nombre:24s} sd del desvío {g.dev_agua.std():.2f} dB · viento medio asc {g[g.dir == 'A'].viento.mean():.1f} "
                      f"m/s vs desc {g[g.dir == 'D'].viento.mean():.1f} m/s")
    b = df[df.fase == "base"]
    for var in ("lluvia_72h", "humedad_suelo", "t_menos_td", "viento"):
        k, r2, n = ajuste(b[var].to_numpy(), b.dev_tierra.to_numpy())
        lineas.append(f"   tierra (pasadas base) vs {var:13s}: pendiente {k:+.3f} · R² {r2:.2f} · n={n}")
    lineas.append(f"   tierra (pasadas base) sd del desvío {b.dev_tierra.std():.2f} dB")
    txt = "\n".join(lineas)
    (OUT / "clima_resumen.txt").write_text(txt + "\n")
    print("\n" + txt)


def grafico(df, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(1, 2, figsize=(12, 4.2))
    a = df[df.px_agua >= 50_000]
    for z, g in a.groupby("zona"):
        axs[0].scatter(g.viento, g.dev_agua, s=20, label=z, alpha=0.8)
    k, r2, n = ajuste(a.viento.to_numpy(), a.dev_agua.to_numpy())
    if np.isfinite(k):
        xs = np.linspace(0, a.viento.max(), 10)
        axs[0].plot(xs, k * (xs - a.viento.mean()) + a.dev_agua.mean(), color="k", lw=1)
    axs[0].axhline(0, color="0.6", lw=0.6)
    axs[0].set_xlabel("ERA5 10 m wind at pass time (m/s)")
    axs[0].set_ylabel("water HH − track median (dB)")
    axs[0].set_title(f"Large water bodies: {k:+.2f} dB per m/s, R²={r2:.2f}, n={n}", fontsize=9)
    axs[0].legend(fontsize=7, frameon=False)
    b = df[df.fase == "base"]
    sc = axs[1].scatter(b.humedad_suelo, b.dev_tierra, c=b.lluvia_72h, cmap="Blues", s=20, edgecolor="0.5", lw=0.3)
    fig.colorbar(sc, ax=axs[1], label="rain previous 72 h (mm)")
    axs[1].axhline(0, color="0.6", lw=0.6)
    axs[1].set_xlabel("ERA5-Land soil moisture 0–7 cm (m³/m³)")
    axs[1].set_ylabel("land HH − track median (dB)")
    axs[1].set_title("Grass/crop, baseline passes", fontsize=9)
    plt.tight_layout()
    plt.savefig(path, dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    main()
