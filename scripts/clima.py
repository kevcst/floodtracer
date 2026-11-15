"""
Clima a la hora de cada pasada NISAR (etapa del pipeline, antes de metricas_evento.py).
  python scripts/clima.py                 # todas las zonas
  python scripts/clima.py --zona merin_arrozales

Para qué: el viento riza el agua abierta y la vuelve brillante en HH. Con viento ERA5 < 3 m/s a la hora del paso el
agua de las lagunas se ve en promedio 1,4 dB más oscura (hasta 4–6 dB); desde ~3 m/s queda estable
(diagnóstico en clima_pasadas.py). metricas_evento.py decide el agua PERMANENTE con las pasadas base de calma
(regla 1: NISAR es la fuente principal; ERA5 sólo elige pasadas, no corrige valores).

Fuentes
  - Hora UTC de cada escena: nombre de la escena en ASF (…_M_20260617T213500_…), vía descargar_zonas.escenas().
  - ERA5 / ERA5-Land horario por la API de archivo de Open-Meteo (sin clave). Punto: centroide del agua WorldCover
    del primer track con ≥ 2000 px de agua (contexto/worldcover.tif, capas_contexto.py) o, si no hay, centroide del AOI.
    Celda ERA5 ~10–25 km: el viento es representativo de la zona, no del píxel.
Salida: data_nisar/zonas/{zona}/clima_pasadas.csv  (track, fecha, hora_utc, viento, rafaga, dir_viento, lluvia_24h,
        lluvia_72h, t_menos_td, humedad_suelo) · caché de la serie horaria en data_nisar/zonas/_clima/{zona}.json
"""
import argparse
import json
import ssl
import urllib.request
from pathlib import Path

import certifi
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform as warp_transform
from shapely import wkt as shp_wkt

from nisar_eda_uruguay import OUT
from zonas import ZONAS

BASE = OUT / "zonas"
CACHE = BASE / "_clima"
API = "https://archive-api.open-meteo.com/v1/archive"
VARS = "wind_speed_10m,wind_direction_10m,wind_gusts_10m,precipitation,temperature_2m,dew_point_2m,soil_moisture_0_to_7cm"
INI, FIN = "2026-06-01", "2026-11-10"
MIN_PX_AGUA = 2000
CALMA_MS = 3.0          # viento ERA5 a 10 m por debajo del cual la pasada cuenta como "calma" para el agua abierta
CTX = ssl.create_default_context(cafile=certifi.where())


def serie_horaria(lat, lon, nombre):
    f = CACHE / f"{nombre}.json"
    if not f.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        u = (f"{API}?latitude={lat:.4f}&longitude={lon:.4f}&start_date={INI}&end_date={FIN}&hourly={VARS}"
             f"&wind_speed_unit=ms&timezone=GMT")
        f.write_text(urllib.request.urlopen(u, context=CTX, timeout=120).read().decode())
    df = pd.DataFrame(json.loads(f.read_text())["hourly"])
    df["time"] = pd.to_datetime(df.time)
    df = df.set_index("time")
    df["lluvia_24h"] = df.precipitation.rolling(24, min_periods=1).sum()
    df["lluvia_72h"] = df.precipitation.rolling(72, min_periods=1).sum()
    df["t_menos_td"] = df.temperature_2m - df.dew_point_2m
    return df


def horas_paso(zona):
    """{(track, 'YYYY-MM-DD'): hora UTC de inicio de la escena}."""
    from descargar_zonas import escenas

    df = escenas(zona, ["PROVISIONAL", "VALIDATED"])
    return {(f"T{r.track}{r.dir}_F{r.frame}", r.fecha): pd.Timestamp(r.escena.split("_")[-7][:15])
            for r in df.itertuples()}


def centroide_agua(tdir):
    f = tdir / "contexto" / "worldcover.tif"
    if not f.exists():
        return None
    with rasterio.open(f) as r:
        wc, tr, crs = r.read(1), r.transform, r.crs
    fil, col = np.nonzero(wc == 80)
    if fil.size < MIN_PX_AGUA:
        return None
    x, y = rasterio.transform.xy(tr, [int(np.median(fil))], [int(np.median(col))])
    lon, lat = warp_transform(crs, "EPSG:4326", x, y)
    return lat[0], lon[0]


def punto_zona(zona):
    for t in sorted((BASE / zona).glob("T*_F*")):
        if (p := centroide_agua(t)) is not None:
            return p, "agua WorldCover"
    c = shp_wkt.loads(ZONAS[zona]["wkt"]).centroid
    return (c.y, c.x), "centroide AOI"


def procesar(zona):
    tdirs = sorted((BASE / zona).glob("T*_F*"))
    if not tdirs:
        return None
    horas = horas_paso(zona)
    (lat, lon), origen = punto_zona(zona)
    met = serie_horaria(lat, lon, zona)
    filas = []
    for t in tdirs:
        for f in sorted(t.glob("*_HH.tif")):
            if ".part" in f.name:
                continue
            fecha = f.name[:10]
            h = horas.get((t.name, fecha))
            if h is None:
                continue
            w = met.iloc[met.index.get_indexer([h.round("h")], method="nearest")[0]]
            filas.append(dict(track=t.name, fecha=fecha, hora_utc=h.strftime("%H:%M"), lat=round(lat, 4),
                              lon=round(lon, 4), punto=origen, viento=w.wind_speed_10m, rafaga=w.wind_gusts_10m,
                              dir_viento=w.wind_direction_10m, lluvia_24h=w.lluvia_24h, lluvia_72h=w.lluvia_72h,
                              t_menos_td=w.t_menos_td, humedad_suelo=w.soil_moisture_0_to_7cm))
    df = pd.DataFrame(filas).round(3)
    df.to_csv(BASE / zona / "clima_pasadas.csv", index=False)
    calma = (df.viento < CALMA_MS).mean() * 100 if len(df) else 0
    print(f"== {zona}: {len(df)} pasadas, punto {origen} ({lat:.3f}, {lon:.3f}), {calma:.0f} % con viento < {CALMA_MS} m/s")
    return df


def viento_pasadas(zona, track, fechas):
    """Viento ERA5 (m/s) a la hora de cada pasada, NaN si falta. Lee el CSV de esta etapa (no usa la red)."""
    f = BASE / zona / "clima_pasadas.csv"
    if not f.exists():
        return np.full(len(fechas), np.nan)
    df = pd.read_csv(f)
    d = {(r.track, r.fecha): r.viento for r in df.itertuples()}
    return np.array([d.get((track, str(pd.Timestamp(x).date())), np.nan) for x in fechas], dtype=float)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--zona", default="todas", choices=["todas", *ZONAS])
    a = ap.parse_args()
    for z in (ZONAS if a.zona == "todas" else [a.zona]):
        procesar(z)
