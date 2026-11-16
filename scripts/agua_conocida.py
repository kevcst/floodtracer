"""
Chequeo de calibración con agua conocida. Sólo lee: no cambia métricas.

Pregunta: ¿el radar ve como agua permanente (metricas/agua_base.tif) el agua que sabemos que existe?
Referencia: JRC Global Surface Water, ocurrencia ≥ 75 % (1984–2021). Es fuente de VALIDACIÓN (regla 1): no entra al
cálculo, así que el chequeo es independiente (WorldCover, en cambio, ya se usa en el pipeline).
El océano queda afuera (sin dato desde el 15/11, metricas_evento.mascara_mar): no se evalúa.

Por track:
  ha_jrc              agua conocida dentro del área válida
  pct_detectada       % de esa agua marcada como agua permanente por NISAR
  pct_nucleo          ídem a > 60 m de la orilla (3 px erosionados: sin píxeles mixtos)
  pct_tierra_agua     % de la tierra firme (JRC 0 %, también erosionada) marcada como agua permanente (falsa alarma)

  python scripts/agua_conocida.py            # todas las zonas → data_nisar/zonas/agua_conocida.csv
  python scripts/agua_conocida.py --zona rocha_norte
"""
import argparse
import os

import certifi

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import Resampling, reproject
from scipy import ndimage as ndi

from metricas_evento import BASE, cargar_track, excluido, tracks_zona
from zonas import ZONAS

EROSION_PX = 3
os.environ.setdefault("CURL_CA_BUNDLE", certifi.where())
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
# JRC Global Surface Water, ocurrencia 1984–2021 (tile 60W_30S); se cachea por track en contexto/jrc_ocurrencia.tif
JRC = "/vsicurl/https://storage.googleapis.com/global-surface-water/downloads2021/occurrence/occurrence_60W_30Sv1_4_2021.tif"
JRC_PERMANENTE = 75


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

MIN_HA = 20          # con menos agua conocida el porcentaje no dice nada


def procesar(zona):
    filas = []
    for tdir in tracks_zona(zona, todos=True):            # también los excluidos: muestra por qué se sacaron
        f = tdir / "metricas" / "agua_base.tif"
        if not f.exists():
            continue
        _, hh, _, perfil = cargar_track(tdir)              # aplica la máscara de mar → valid sin océano
        valid = np.all(np.isfinite(hh), axis=0)
        with rasterio.open(f) as r:
            base = r.read(1) == 1
        jrc = jrc_en_grilla(tdir, perfil)
        agua = (jrc >= JRC_PERMANENTE) & valid
        tierra = ndi.binary_erosion((jrc == 0) & valid, iterations=EROSION_PX)
        nucleo = ndi.binary_erosion(agua, iterations=EROSION_PX)
        ha_px = abs(perfil["transform"].a * perfil["transform"].e) / 1e4
        pct = lambda m: round(100 * float(base[m].mean()), 1) if m.any() else None
        filas.append(dict(zona=zona, track=tdir.name, serie=tdir.name == ZONAS[zona]["serie"], excluido=excluido(zona, tdir.name),
                          ha_jrc=round(float(agua.sum() * ha_px)), pct_detectada=pct(agua), pct_nucleo=pct(nucleo),
                          pct_tierra_agua=round(100 * float(base[tierra].mean()), 2) if tierra.any() else None))
    return filas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zona", default="todas", choices=["todas", *ZONAS])
    a = ap.parse_args()
    filas = [f for z in (ZONAS if a.zona == "todas" else [a.zona]) for f in procesar(z)]
    df = pd.DataFrame(filas)
    df.loc[df.ha_jrc < MIN_HA, ["pct_detectada", "pct_nucleo"]] = None
    pd.set_option("display.width", 200)
    print(df.to_string(index=False))
    out = BASE / "agua_conocida.csv"
    if a.zona != "todas" and out.exists():          # una sola zona: se reemplazan sus filas
        viejo = pd.read_csv(out)
        df = pd.concat([viejo[viejo.zona != a.zona], df])
    df.to_csv(out, index=False)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
