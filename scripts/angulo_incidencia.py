"""
Ángulo de incidencia por track (diagnóstico entre tracks, paso 1). Sólo geometría del propio NISAR (regla 1 OK).
  python scripts/angulo_incidencia.py                  # una escena por track (la geometría se repite entre pasadas)
  python scripts/angulo_incidencia.py --verificar      # además baja una 2.ª fecha por track y compara

Fuente: GCOV /science/LSAR/GCOV/metadata/radarGrid/incidenceAngle, cubo de 21 alturas (−1000…9000 m, cada 500 m)
en una grilla de 500 m en la MISMA proyección que las imágenes (x/yCoordinates). Se usa el nivel 0 m (banda 3):
la cuenca está entre 0 y ~300 m y el ángulo cambia muy poco con la altura a esas cotas.
Salida: data_nisar/zonas/{zona}/T*/contexto/incidencia.tif (grados, grilla del track, bilineal)
        data_nisar/zonas/{zona}/T*/contexto/incidencia_{fecha}_500m.tif (cubo nivel 0 m, sin remuestrear)
"""
import argparse
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

from descargar_zonas import BASE, escenas
from zonas import ZONAS

RG = "//science/LSAR/GCOV/metadata/radarGrid"
BANDA_0M = 3
ENV = dict(os.environ, GDAL_HTTP_NETRC="YES", GDAL_HTTP_COOKIEFILE="/tmp/gdal_cookies.txt",
           GDAL_HTTP_COOKIEJAR="/tmp/gdal_cookies.txt", GDAL_DISABLE_READDIR_ON_OPEN="TRUE",
           GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES")


def leer_hdf5(url, ruta, banda=1):
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "x.tif"
        r = subprocess.run(["gdal_translate", "-q", "-b", str(banda), f'HDF5:"/vsicurl/{url}":{ruta}', str(out)],
                           env=ENV, capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr.strip()[-300:])
        with rasterio.open(out) as src:
            return src.read(1).astype("float64")


def cubo_0m(url, crs, destino):
    """Nivel 0 m del cubo de incidencia como GeoTIFF georreferenciado (500 m)."""
    if destino.exists():
        return destino
    inc = leer_hdf5(url, f"{RG}/incidenceAngle", BANDA_0M).astype("float32")
    x = leer_hdf5(url, f"{RG}/xCoordinates").ravel()
    y = leer_hdf5(url, f"{RG}/yCoordinates").ravel()
    dx, dy = x[1] - x[0], y[1] - y[0]
    if dy > 0:                       # filas de sur a norte → dar vuelta
        inc, y, dy = inc[::-1], y[::-1], -dy
    perfil = dict(driver="GTiff", dtype="float32", count=1, width=inc.shape[1], height=inc.shape[0], crs=crs,
                  transform=from_origin(x[0] - dx / 2, y[0] - dy / 2, dx, -dy), nodata=np.nan, compress="deflate")
    destino.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(destino, "w", **perfil) as dst:
        dst.write(inc, 1)
    return destino


def a_grilla(cubo, ref_tif, destino):
    with rasterio.open(ref_tif) as ref, rasterio.open(cubo) as src:
        out = np.full((ref.height, ref.width), np.nan, "float32")
        reproject(src.read(1), out, src_transform=src.transform, src_crs=src.crs, dst_transform=ref.transform,
                  dst_crs=ref.crs, resampling=Resampling.bilinear, src_nodata=np.nan, dst_nodata=np.nan)
        p = ref.profile.copy()
    p.update(dtype="float32", count=1, nodata=np.nan, compress="deflate")
    for k in ("blockxsize", "blockysize", "tiled", "interleave"):
        p.pop(k, None)
    with rasterio.open(destino, "w", **p) as dst:
        dst.write(out, 1)
    return out


def main(verificar):
    for zona in ZONAS:
        tdirs = {t.name: t for t in sorted((BASE / zona).glob("T*_F*"))}
        if not tdirs:
            continue
        df = escenas(zona, ["PROVISIONAL"])
        for nombre, tdir in tdirs.items():
            fechas_locales = sorted(f.name[:10] for f in tdir.glob("*_HH.tif") if ".part" not in f.name)
            g = df[(df.apply(lambda r: f"T{r.track}{r.dir}_F{r.frame}", axis=1) == nombre)
                   & df.fecha.isin(fechas_locales)].sort_values("fecha")
            if g.empty:
                print(f"   ! {zona}/{nombre}: sin escena PROVISIONAL que coincida con los recortes")
                continue
            ref = tdir / f"{g.iloc[0].fecha}_HH.tif"
            with rasterio.open(ref) as r:
                crs = r.crs
            usar = [g.iloc[0]] + ([g.iloc[len(g) // 2]] if verificar and len(g) > 1 else [])
            capas = []
            for fila in usar:
                cubo = cubo_0m(fila.url, crs, tdir / "contexto" / f"incidencia_{fila.fecha}_500m.tif")
                destino = tdir / "contexto" / ("incidencia.tif" if fila is usar[0] else f"incidencia_{fila.fecha}.tif")
                capas.append(a_grilla(cubo, ref, destino))
            a = capas[0]
            msg = f"{zona}/{nombre}: {np.nanmin(a):.1f}–{np.nanmax(a):.1f}° (cobertura {100 * np.isfinite(a).mean():.0f} %)"
            if len(capas) > 1:
                msg += f" · {usar[1].fecha} vs {usar[0].fecha}: |Δ| máx {np.nanmax(np.abs(capas[1] - a)):.3f}°"
            print(msg)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verificar", action="store_true")
    main(ap.parse_args().verificar)
