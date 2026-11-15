"""
Descarga recortes NISAR GCOV (HH, HV) por zona para la idea "¿Cuánto tiempo se queda el agua?".

  python scripts/descargar_zonas.py listar                       # qué escenas hay por zona/track (sin login)
  python scripts/descargar_zonas.py descargar --zona treinta_y_tres
  python scripts/descargar_zonas.py descargar --zona todas --workers 4
  python scripts/descargar_zonas.py resumen                      # % agua por fecha, zona y track -> CSV + PNG

Salida: data_nisar/zonas/{zona}/T{track}{dir}_F{frame}/{fecha}_{HH|HV}.tif  (gamma0 lineal, proyección nativa)
Zonas y tracks: scripts/zonas.py. Requiere ~/.netrc (Earthdata) y GDAL CLI.
"""
import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import asf_search as asf
import pandas as pd

from nisar_eda_uruguay import OUT, POLS, gdal_prefijo
from zonas import FECHA_FIN, FECHA_FIN_VALIDATED, FECHA_INI, ZONAS

BASE = OUT / "zonas"
UMBRAL_AGUA_DB = -18.0  # ver docs/eda_T53D_F105.md (Otsu global no sirve)

CFG = ["--config", "GDAL_HTTP_NETRC", "YES",
       "--config", "GDAL_HTTP_COOKIEFILE", "/tmp/gdal_cookies.txt",
       "--config", "GDAL_HTTP_COOKIEJAR", "/tmp/gdal_cookies.txt",
       "--config", "GDAL_DISABLE_READDIR_ON_OPEN", "TRUE",
       "--config", "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES", "YES",
       "--config", "CPL_VSIL_CURL_CHUNK_SIZE", "2097152"]


def escenas(zona, madurez):
    z = ZONAS[zona]
    filas = []
    for m in madurez:
        # PROVISIONAL hasta FECHA_FIN; VALIDATED sólo después (nunca la misma fecha en las dos madureces).
        # Las fechas VALIDATED se reconocen por fecha (>= zonas.INICIO_VALIDATED) y se normalizan al detectar.
        ini, fin = (FECHA_INI, FECHA_FIN) if m == "PROVISIONAL" else (FECHA_FIN, FECHA_FIN_VALIDATED)
        res = asf.search(dataset="NISAR", processingLevel="GCOV", dataMaturity=m,
                         intersectsWith=z["wkt"], start=ini, end=fin + "T23:59:59Z",
                         maxResults=2000)
        for g in res:
            p = g.properties
            k = (p.get("pathNumber"), p.get("flightDirection", "")[:1], p.get("frameNumber"))
            if k not in z["tracks"]:
                continue
            if m == "VALIDATED" and p["startTime"][:10] <= FECHA_FIN:
                continue
            filas.append(dict(zona=zona, madurez=m, fecha=p["startTime"][:10], track=k[0], dir=k[1],
                              frame=k[2], escena=p["sceneName"], url=g.get_urls()[0]))
    if not filas:
        return pd.DataFrame()
    df = pd.DataFrame(filas)
    # Si hay varias escenas en la misma fecha, preferir modo principal 20 MHz ("_2005_..._M_") y frame
    # completo ("_N_F_") sobre parciales/auxiliares ("4005_..._A_..._P_", 10 m, cubren parte del AOI);
    # a igualdad, la versión más nueva (_002 > _001).
    df["prioridad"] = (df.escena.str.contains("_2005_").astype(int) * 4
                       + df.escena.str.contains(r"_M_\d{8}T").astype(int) * 2
                       + df.escena.str.contains("_N_F_").astype(int))
    df = df.sort_values(["track", "dir", "frame", "fecha", "prioridad", "escena"])
    return df.drop_duplicates(["track", "dir", "frame", "fecha"], keep="last").drop(columns="prioridad")


def zonas_sel(nombre):
    return list(ZONAS) if nombre == "todas" else [nombre]


def listar(a):
    tablas = []
    for zona in zonas_sel(a.zona):
        df = escenas(zona, a.madurez)
        if df.empty:
            print(f"{zona}: sin escenas"); continue
        tablas.append(df)
        print(f"\n== {zona}: {ZONAS[zona]['descripcion']}")
        for (t, d, f), g in df.groupby(["track", "dir", "frame"]):
            print(f"   T{t}{d}_F{f}: {len(g)} fechas -> {', '.join(x[5:] for x in g.fecha)}")
    if tablas:
        BASE.mkdir(parents=True, exist_ok=True)
        pd.concat(tablas).to_csv(BASE / "inventario_zonas.csv", index=False)
        n = sum(len(t) for t in tablas) * len(POLS)
        print(f"\nTotal recortes a bajar: {n}  ->  {BASE/'inventario_zonas.csv'}")


def _bajar(job):
    src, salida, etiqueta, wkt = job
    if salida.exists():
        return f"ya existe  {etiqueta}"
    tmp = salida.with_suffix(".part.tif")
    r = subprocess.run(["gdalwarp", "-q", "-of", "COG", "-cutline", wkt, "-cutline_srs", "WGS84",
                        "-crop_to_cutline", src, str(tmp)] + CFG, capture_output=True, text=True)
    if r.returncode == 0 and tmp.exists():
        tmp.rename(salida)
        return f"ok         {etiqueta}"
    tmp.unlink(missing_ok=True)
    return f"ERROR      {etiqueta}: {r.stderr.strip()[-300:]}"


def descargar(a):
    pref = gdal_prefijo()
    jobs = []
    for zona in zonas_sel(a.zona):
        df = escenas(zona, a.madurez)
        for _, r in df.iterrows():
            dest = BASE / zona / f"T{r.track}{r.dir}_F{r.frame}"
            dest.mkdir(parents=True, exist_ok=True)
            for nombre, var in POLS.items():
                ruta = f"//science/LSAR/GCOV/grids/frequencyA/{var}"
                src = f'NETCDF:"/vsicurl/{r.url}":{ruta}' if pref else f'HDF5:"/vsicurl/{r.url}":{ruta}'
                etiqueta = f"{zona}/T{r.track}{r.dir}_F{r.frame}/{r.fecha}_{nombre} ({r.madurez})"
                jobs.append((src, dest / f"{r.fecha}_{nombre}.tif", etiqueta, ZONAS[zona]["wkt"]))
    print(f"{len(jobs)} recortes en cola (workers={a.workers})")
    with ThreadPoolExecutor(a.workers) as ex:
        for msg in ex.map(_bajar, jobs):
            print(msg)


def resumen(a):
    import matplotlib.pyplot as plt
    import numpy as np
    import rasterio

    filas = []
    for zona in zonas_sel(a.zona):
        for tdir in sorted((BASE / zona).glob("T*_F*")):
            for hh in sorted(tdir.glob("*_HH.tif")):
                with rasterio.open(hh) as s:
                    x = s.read(1).astype("float32")
                x[(x <= 0) | ~np.isfinite(x)] = np.nan
                db = 10 * np.log10(x)
                valid = np.isfinite(db)
                if valid.sum() == 0:
                    continue
                filas.append(dict(zona=zona, track=tdir.name, fecha=pd.Timestamp(hh.name[:10]),
                                  pct_agua=100 * np.mean(db[valid] < UMBRAL_AGUA_DB),
                                  HH_mediana_dB=float(np.nanmedian(db))))
    if not filas:
        raise SystemExit("No hay recortes descargados.")
    ts = pd.DataFrame(filas).sort_values(["zona", "track", "fecha"])
    ts.to_csv(BASE / "resumen_agua.csv", index=False)
    print(ts.round(2).to_string(index=False))

    zs = ts.zona.unique()
    fig, axs = plt.subplots(len(zs), 1, figsize=(10, 2.6 * len(zs)), sharex=True, squeeze=False)
    for ax, z in zip(axs[:, 0], zs):
        for t, g in ts[ts.zona == z].groupby("track"):
            ax.plot(g.fecha, g.pct_agua, marker="o", label=t)
        ax.axvspan(pd.Timestamp("2026-08-15"), pd.Timestamp("2026-08-19"), color="tab:red", alpha=0.15)
        ax.axvspan(pd.Timestamp("2026-07-27"), pd.Timestamp("2026-08-10"), color="grey", alpha=0.15)
        ax.set_title(f"{z} — % área con HH < {UMBRAL_AGUA_DB} dB"); ax.legend(fontsize=7)
    axs[-1, 0].set_xlabel("rojo = lluvia 15–19/8 · gris = hueco de datos NISAR")
    plt.tight_layout(); plt.savefig(BASE / "resumen_agua.png", dpi=110)
    print(f"-> {BASE/'resumen_agua.csv'}, {BASE/'resumen_agua.png'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    for nombre, fn in [("listar", listar), ("descargar", descargar), ("resumen", resumen)]:
        p = sp.add_parser(nombre)
        p.add_argument("--zona", default="todas", choices=["todas", *ZONAS])
        p.add_argument("--madurez", nargs="+", default=["PROVISIONAL"],
                       choices=["PROVISIONAL", "VALIDATED"], help="no mezclar sin normalizar")
        p.add_argument("--workers", type=int, default=3)
        p.set_defaults(fn=fn)
    a = ap.parse_args()
    a.fn(a)
