"""
NISAR GCOV - descarga para análisis exploratorio (Laguna Merín, Uruguay)

Pasos:
  python nisar_eda_uruguay.py inventario          # lista qué hay (no requiere login)
  python nisar_eda_uruguay.py descargar --track 53 --dir D --frame 105
  python nisar_eda_uruguay.py explorar  --track 53 --dir D --frame 105

Requisitos:
  pip install asf_search pandas rasterio numpy matplotlib
  GDAL CLI (brew install gdal). Si `gdal --version` < 3.13 se usa el prefijo NETCDF: automáticamente.
  ~/.netrc con credenciales de Earthdata Login (urs.earthdata.nasa.gov).
"""
import argparse
import re
import subprocess
from pathlib import Path

import asf_search as asf
import pandas as pd

# Zona de búsqueda: Treinta y Tres / Rocha (arrozales del Cebollatí-Tacuarí + Bañados del Este + ciudad de Treinta y Tres)
AOI_BUSQUEDA = "POLYGON((-54.5 -33.9,-53.3 -33.9,-53.3 -32.5,-54.5 -32.5,-54.5 -33.9))"
# Recorte más chico para bajar (arrozales + bañados). Ajustar a gusto copiando el WKT desde Vertex.
AOI_RECORTE = "POLYGON((-54.1 -33.75,-53.6 -33.75,-53.6 -33.0,-54.1 -33.0,-54.1 -33.75))"

POLS = {"HH": "HHHH", "HV": "HVHV"}  # términos diagonales de la covarianza = potencia gamma0 (lineal)
OUT = Path(__file__).resolve().parent.parent / "data_nisar"  # raíz del repo/data_nisar


def buscar():
    filas = []
    for madurez in ["BETA", "PROVISIONAL", "VALIDATED"]:
        res = asf.search(dataset="NISAR", processingLevel="GCOV", dataMaturity=madurez,
                         intersectsWith=AOI_BUSQUEDA, maxResults=2000)
        for g in res:
            p = g.properties
            filas.append(dict(
                madurez=madurez,
                fecha=p["startTime"][:10],
                track=p.get("pathNumber"),
                dir=p.get("flightDirection", "")[:1],
                frame=p.get("frameNumber"),
                escena=p["sceneName"],
                url=g.get_urls()[0],
            ))
    df = pd.DataFrame(filas).drop_duplicates("escena").sort_values(["track", "dir", "frame", "fecha"])
    # Si una misma fecha/track/frame aparece dos veces (reprocesos), quedarse con la última versión
    df = df.drop_duplicates(["track", "dir", "frame", "fecha"], keep="last")
    return df


def inventario(_):
    df = buscar()
    OUT.mkdir(exist_ok=True)
    df.to_csv(OUT / "inventario.csv", index=False)
    resumen = (df.groupby(["track", "dir", "frame", "madurez"])
                 .fecha.agg(["count", "min", "max"]).reset_index())
    print(resumen.to_string(index=False))
    print(f"\nTotal escenas: {len(df)}  ->  {OUT/'inventario.csv'}")
    print("Elegí UN track+dir+frame (misma geometría) para la serie temporal.")


def gdal_prefijo():
    v = subprocess.run(["gdalinfo", "--version"], capture_output=True, text=True).stdout
    m = re.search(r"GDAL (\d+)\.(\d+)", v)
    return "" if m and (int(m[1]), int(m[2])) >= (3, 13) else "NETCDF:"


def descargar(a):
    df = pd.read_csv(OUT / "inventario.csv")
    sel = df[(df.track == a.track) & (df.dir == a.dir) & (df.frame == a.frame)]
    if sel.empty:
        raise SystemExit("No hay escenas para esa combinación. Corré 'inventario' primero.")
    pref = gdal_prefijo()
    dest = OUT / f"T{a.track}{a.dir}_F{a.frame}"
    dest.mkdir(parents=True, exist_ok=True)
    cfg = ["--config", "GDAL_HTTP_NETRC", "YES",
           "--config", "GDAL_HTTP_COOKIEFILE", "/tmp/gdal_cookies.txt",
           "--config", "GDAL_HTTP_COOKIEJAR", "/tmp/gdal_cookies.txt",
           "--config", "GDAL_DISABLE_READDIR_ON_OPEN", "TRUE",
           "--config", "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES", "YES",
           "--config", "CPL_VSIL_CURL_CHUNK_SIZE", "2097152"]
    for _, r in sel.iterrows():
        for nombre, var in POLS.items():
            salida = dest / f"{r.fecha}_{nombre}.tif"
            if salida.exists():
                continue
            ruta = f"//science/LSAR/GCOV/grids/frequencyA/{var}"
            # GDAL >= 3.13: driver HDF5 nativo. Más viejo: driver netCDF con el nombre entre comillas.
            # (sin prefijo de driver GDAL toma "url.h5://science/..." como una sola URL -> 404)
            src = f'NETCDF:"/vsicurl/{r.url}":{ruta}' if pref else f'HDF5:"/vsicurl/{r.url}":{ruta}'
            # Se mantiene la proyección nativa del frame (misma grilla en todas las fechas de un track)
            cmd = ["gdalwarp", "-of", "COG", "-cutline", AOI_RECORTE, "-cutline_srs", "WGS84",
                   "-crop_to_cutline", src, str(salida)] + cfg
            print(f"{r.fecha} {nombre} ({r.madurez}) ...")
            subprocess.run(cmd, check=False)
    print(f"Listo -> {dest}")


def explorar(a):
    import matplotlib.pyplot as plt
    import numpy as np
    import rasterio

    dest = OUT / f"T{a.track}{a.dir}_F{a.frame}"
    fechas = sorted({p.name[:10] for p in dest.glob("*_HH.tif")})
    filas = []
    for f in fechas:
        fila = {"fecha": pd.Timestamp(f)}
        for pol in POLS:
            with rasterio.open(dest / f"{f}_{pol}.tif") as src:
                x = src.read(1).astype("float32")
            x[(x <= 0) | ~np.isfinite(x)] = np.nan
            db = 10 * np.log10(x)
            fila[f"{pol}_mediana_dB"] = np.nanmedian(db)
            if pol == "HH":
                # % de píxeles muy oscuros = proxy grosero de agua abierta (ajustar umbral con un histograma / Otsu)
                fila["pct_agua_HH<-18dB"] = 100 * np.nanmean(db < -18)
        filas.append(fila)
    ts = pd.DataFrame(filas).set_index("fecha")
    ts.to_csv(dest / "serie_resumen.csv")
    print(ts.round(2).to_string())

    fig, ax = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    ts[["HH_mediana_dB", "HV_mediana_dB"]].plot(ax=ax[0], marker="o", title="Retrodispersión mediana (gamma0 dB)")
    ts["pct_agua_HH<-18dB"].plot(ax=ax[1], marker="o", color="tab:blue", title="% área oscura (proxy de agua)")
    plt.tight_layout()
    plt.savefig(dest / "serie_resumen.png", dpi=120)
    print(f"Gráfico -> {dest/'serie_resumen.png'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("inventario").set_defaults(fn=inventario)
    for nombre, fn in [("descargar", descargar), ("explorar", explorar)]:
        p = sp.add_parser(nombre)
        p.add_argument("--track", type=int, required=True)
        p.add_argument("--dir", choices=["A", "D"], required=True)
        p.add_argument("--frame", type=int, required=True)
        p.set_defaults(fn=fn)
    args = ap.parse_args()
    args.fn(args)
