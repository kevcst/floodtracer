"""
Imagen óptica de contexto para la historia (app/story.html, escena 1 "The day satellites went blind").
Regla 1: Sentinel-2 es SÓLO contexto visual (mostrar que el óptico no veía por las nubes); nunca entra en el análisis.

  python scripts/exportar_optico.py                      # zona por defecto: merin_arrozales
  python scripts/exportar_optico.py --zona treinta_y_tres

Qué hace
  1. Toma la primera pasada NISAR de la serie de la zona después del inicio de la lluvia y elige una ventana de
     VENTANA_PX × VENTANA_PX píxeles (grilla del track de la serie, 20 m) centrada donde esa pasada ve más agua nueva.
  2. Busca en Planetary Computer (STAC anónimo, colección sentinel-2-l2a) las escenas entre el inicio de la lluvia y
     DIAS_DESPUES días después que tocan la ventana, con su % de nubes del catálogo (eo:cloud_cover).
  3. Elige la fecha más cercana a la pasada NISAR cuya imagen no sea blanco puro (si todas lo son, la más cercana) y mosaica el asset "visual" (color verdadero, 10 m) sobre la ventana
     NISAR (promedio a 20 m). Si ninguna escena cubre la ventana, deja sólo el catálogo de nubes (la app muestra un
     aviso honesto en lugar de la imagen).

Salida (caché, no se versiona): data_nisar/contexto/optico/{zona}.tif (RGB uint8, grilla de la ventana) + {zona}.json
exportar_app.py lo copia a app/data/contexto/ y lo describe en manifest.contexto.optico.
"""
import argparse
import json
import os
import ssl
import time
import urllib.request

import certifi
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds
from rasterio.windows import Window
from rasterio.windows import transform as win_transform
from shapely.geometry import box, shape

from metricas_evento import BASE, OUT, Evento, cargar_track
from zonas import ZONAS

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-2-l2a"
CTX = ssl.create_default_context(cafile=certifi.where())
SAL = OUT / "contexto" / "optico"
VENTANA_PX = 600        # 600 px × 20 m = 12 km de lado
DIAS_DESPUES = 7        # ventana de búsqueda óptica: lluvia[0] … lluvia[0] + 7 días (15–22/8 en agosto)
SATURADO = 250          # las 3 bandas ≥ 250 = blanco puro (nube espesa saturada en el color verdadero)
MAX_SATURADO = 0.99     # imagen "toda blanca": se prueba la fecha siguiente
FUENTE = "Sentinel-2 L2A (ESA Copernicus), via Microsoft Planetary Computer"
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CURL_CA_BUNDLE", certifi.where())


def token():
    return json.load(urllib.request.urlopen(SAS, context=CTX, timeout=60))["token"]


def elegir_ventana(zona):
    """Pasada NISAR (serie) tras el inicio de la lluvia y ventana con más agua nueva."""
    tdir = BASE / zona / ZONAS[zona]["serie"]
    ev = Evento(zona)
    fechas, _, _, perfil = cargar_track(tdir)
    fecha = next(f for f in pd.DatetimeIndex(fechas) if f >= ev.lluvia[0])
    with rasterio.open(tdir / "metricas" / "agua_nueva_por_fecha.tif") as r:
        m = r.read(list(r.descriptions).index(str(fecha.date())) + 1) == 1
    n, paso = VENTANA_PX, VENTANA_PX // 6
    H, W = m.shape
    cs = np.pad(m.astype("int32").cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    mejor, rc = -1, (0, 0)
    for r0 in range(0, max(1, H - n + 1), paso):
        for c0 in range(0, max(1, W - n + 1), paso):
            s = cs[r0 + n, c0 + n] - cs[r0, c0 + n] - cs[r0 + n, c0] + cs[r0, c0]
            if s > mejor:
                mejor, rc = s, (r0, c0)
    win = Window(rc[1], rc[0], min(n, W), min(n, H))
    perfil_w = dict(perfil, width=int(win.width), height=int(win.height), transform=win_transform(win, perfil["transform"]))
    return tdir.name, fecha, win, perfil_w


def buscar(perfil_w, desde, hasta):
    b = transform_bounds(perfil_w["crs"], "EPSG:4326", *rasterio.transform.array_bounds(perfil_w["height"], perfil_w["width"], perfil_w["transform"]))
    g = box(*b)
    body = {"collections": ["sentinel-2-l2a"], "intersects": g.__geo_interface__,
            "datetime": f"{desde.date()}/{hasta.date()}T23:59:59Z", "limit": 200}
    req = urllib.request.Request(STAC, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    feats = json.load(urllib.request.urlopen(req, context=CTX, timeout=120))["features"]
    filas = [dict(id=f["id"], fecha=f["properties"]["datetime"][:10], nubes=float(f["properties"].get("eo:cloud_cover", np.nan)),
                  cob=shape(f["geometry"]).intersection(g).area / g.area, href=f["assets"]["visual"]["href"])
             for f in feats if "visual" in f["assets"]]
    return pd.DataFrame(filas)


def mosaico(hrefs, perfil_w):
    out = np.zeros((3, perfil_w["height"], perfil_w["width"]), "uint8")
    tk = token()
    for href in hrefs:
        for intento in range(3):
            try:
                with rasterio.open(f"{href}?{tk}") as src, WarpedVRT(src, crs=perfil_w["crs"], transform=perfil_w["transform"],
                                                                     width=perfil_w["width"], height=perfil_w["height"],
                                                                     resampling=Resampling.average, src_nodata=0, nodata=0) as vrt:
                    x = vrt.read()
                break
            except rasterio.errors.RasterioIOError as e:
                print(f"   reintento {intento + 1}: {e}")
                tk = token()
                time.sleep(3)
        else:
            continue
        vacio = out.sum(0) == 0
        out[:, vacio] = x[:, vacio]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zona", default="merin_arrozales")
    a = ap.parse_args()
    zona = a.zona
    ev = Evento(zona)
    track, fecha, win, perfil_w = elegir_ventana(zona)
    print(f"{zona}: pasada NISAR {fecha.date()} ({track}), ventana {win}")
    desde, hasta = ev.lluvia[0], ev.lluvia[0] + pd.Timedelta(days=DIAS_DESPUES)
    df = buscar(perfil_w, desde, hasta)
    SAL.mkdir(parents=True, exist_ok=True)
    meta = dict(zona=zona, track=track, fecha_nisar=str(fecha.date()), ventana=[int(win.col_off), int(win.row_off), int(win.width), int(win.height)],
                buscado=[str(desde.date()), str(hasta.date())], fuente=FUENTE, escena=None, fecha_s2=None, nubes=None,
                catalogo=[])
    if not df.empty:
        cat = df[df.cob > 0].groupby("fecha").apply(lambda g: pd.Series(dict(nubes=float(np.average(g.nubes, weights=g.cob)),
                                                                              cob=float(min(1.0, g.cob.sum())))), include_groups=False)
        meta["catalogo"] = [dict(fecha=f, nubes=round(r.nubes, 1), cobertura=round(r.cob, 2)) for f, r in cat.iterrows()]
        ok = cat[cat.cob >= 0.9]
        # fechas por cercanía a la pasada NISAR; se usa la primera cuya imagen no esté saturada por completo (nube
        # espesa = blanco puro en el color verdadero, que en pantalla parece una imagen rota). Si todas lo están, la más cercana.
        orden = sorted(ok.index, key=lambda f: abs((pd.Timestamp(f) - fecha).days))
        elegida = None
        for f2 in orden:
            g = df[(df.fecha == f2) & (df.cob > 0)].sort_values("cob", ascending=False)
            rgb = mosaico(list(g.href), perfil_w)
            if (rgb.sum(0) > 0).mean() <= 0.9:
                continue
            sat = float((rgb.min(0) >= SATURADO).mean())
            print(f"   {f2}: {100 * sat:.0f} % de píxeles saturados (blancos)")
            if elegida is None or sat < MAX_SATURADO:
                elegida = (f2, g, rgb, sat)
            if sat < MAX_SATURADO:
                break
        if elegida:
            f2, g, rgb, sat = elegida
            p = dict(perfil_w, driver="GTiff", count=3, dtype="uint8", nodata=0, compress="deflate")
            with rasterio.open(SAL / f"{zona}.tif", "w", **p) as w:
                w.write(rgb)
            meta.update(escena=list(g.id), fecha_s2=f2, nubes=round(float(cat.loc[f2, "nubes"]), 1))
    (SAL / f"{zona}.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in meta.items() if k != "catalogo"}, ensure_ascii=False))
    print("catálogo:", meta["catalogo"])


if __name__ == "__main__":
    main()
