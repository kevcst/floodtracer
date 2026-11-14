"""
Exporta capas livianas y datos para la POC web (poc/index.html).

  python scripts/exportar_poc.py            # baja los contornos de países si no están (world-atlas, Natural Earth)

Sale en poc/data/: por zona y fecha un JPEG de HH (gris) + PNG de agua (base/nueva), extensión máxima,
persistencia; y poc/data/poc.json con series para los gráficos y el mapa de contexto.
Sólo usa productos ya calculados por metricas_evento.py y monte_ribereno.py (correrlos antes).
"""
import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from PIL import Image

from metricas_evento import BASE, EVENTO, cargar_track
from zonas import ZONAS

RAIZ = Path(__file__).resolve().parents[1]
SAL = RAIZ / "poc" / "data"
COUNTRIES_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-50m.json"
COUNTRIES = RAIZ / "data_nisar" / "contexto" / "countries-50m.json"


def bajar_countries(destino):
    """Contornos Natural Earth 1:50m (TopoJSON). Usa certifi por si el Python del sistema no trae certificados."""
    import ssl
    import urllib.request

    import certifi

    destino.parent.mkdir(parents=True, exist_ok=True)
    ctx = ssl.create_default_context(cafile=certifi.where())
    destino.write_bytes(urllib.request.urlopen(COUNTRIES_URL, context=ctx, timeout=60).read())
    print(f"contornos -> {destino}")

# Visor de mapas: un track por zona (series consistentes, regla 2)
VISOR = [("merin_arrozales", "T53D_F105", 4, "Rice fields of the Cebollatí–Tacuarí (Laguna Merín basin)"),
         ("treinta_y_tres", "T154D_F105", 2, "Treinta y Tres city and the lower Olimar river")]
# Pulso por zona: el track con mejor cobertura del evento en cada una
PULSO = [("treinta_y_tres", "T154D_F105", "Treinta y Tres", "Olimar"),
         ("merin_arrozales", "T53D_F105", "Laguna Merín rice fields", "Cebollatí–Tacuarí"),
         ("rio_branco_jaguarao", "T53D_F105", "Río Branco / Jaguarão", "Yaguarón"),
         ("melo", "T31A_F161", "Melo", "Arroyo Conventos"),
         ("durazno", "T60A_F161", "Durazno", "Yí"),
         ("mercedes", "T10D_F105", "Mercedes", "Río Negro")]
NARANJA = (235, 104, 52)
AZUL = (42, 120, 214)
PERSIST = {12: (158, 197, 244), 24: (85, 152, 231), 36: (37, 106, 191), 48: (16, 66, 129)}
SIGUE = (13, 54, 107)


def leer(path):
    with rasterio.open(path) as r:
        return r.read(), r.profile, r.descriptions


def rgba(h, w):
    return np.zeros((h, w, 4), "uint8")


def exportar_visor(zona, track, f):
    tdir = BASE / zona / track
    fechas, hh, _, perfil = cargar_track(tdir)
    nueva, _, desc = leer(tdir / "metricas" / "agua_nueva_por_fecha.tif")
    base = leer(tdir / "metricas" / "agua_base.tif")[0][0][::f, ::f]
    ext = leer(tdir / "metricas" / "extension_max.tif")[0][0][::f, ::f]
    pers = leer(tdir / "metricas" / "persistencia_dias.tif")[0][0][::f, ::f]
    ret = leer(tdir / "metricas" / "fecha_retiro.tif")[0][0][::f, ::f]
    hh = hh[:, ::f, ::f]
    n, h, w = hh.shape
    clave = f"{zona}_{track}"
    capas = []
    ext_px = ext.astype(bool)
    for i, fe in enumerate(fechas):
        d = str(fe.date())
        g = np.clip((hh[i] + 22) / 20 * 255, 0, 255)
        g = np.where(np.isfinite(hh[i]), g, 0).astype("uint8")
        Image.fromarray(g).save(SAL / f"{clave}_{d}_hh.jpg", quality=78)
        m = nueva[desc.index(d)][::f, ::f]
        o = rgba(h, w)
        o[base == 1] = (*AZUL, 255)
        o[m == 1] = (*NARANJA, 255)
        Image.fromarray(o).save(SAL / f"{clave}_{d}_agua.png", optimize=True)
        capas.append(dict(fecha=d, pct_nueva=round(100 * float((m == 1).sum()) / max(int((m != 255).sum()), 1), 2),
                          remaining=round(100 * float(((m == 1) & ext_px).sum()) / max(int(ext_px.sum()), 1), 1)
                          if fe >= EVENTO[0] else None))
    o = rgba(h, w)
    o[ext == 1] = (*NARANJA, 255)
    Image.fromarray(o).save(SAL / f"{clave}_extension.png", optimize=True)
    o = rgba(h, w)
    for dias, c in PERSIST.items():
        o[(pers >= dias) & (pers < dias + 12) if dias < 48 else (pers >= 48)] = (*c, 255)
    o[ret == 999] = (*SIGUE, 255)
    Image.fromarray(o).save(SAL / f"{clave}_persistencia.png", optimize=True)

    px = abs(perfil["transform"].a) * f
    ha_px = (abs(perfil["transform"].a) ** 2) / 1e4
    ext_full = leer(tdir / "metricas" / "extension_max.tif")[0][0]
    pers_full = leer(tdir / "metricas" / "persistencia_dias.tif")[0][0]
    ret_full = leer(tdir / "metricas" / "fecha_retiro.tif")[0][0]
    tot = int((ext_full == 1).sum())
    hist = {str(k): round(100 * float(((pers_full >= k) & (pers_full < k + 12)).sum()) / tot, 1) for k in (12, 24, 36)}
    hist["48"] = round(100 * float((pers_full >= 48).sum()) / tot, 1)
    hist["still"] = round(100 * float((ret_full == 999).sum()) / tot, 1)
    return dict(clave=clave, zona=zona, track=track, ancho=w, alto=h, px_m=px, capas=capas,
                ha_extension=round(tot * ha_px), persistencia=hist)


def pulso():
    pf = pd.read_csv(BASE / "metricas_por_fecha.csv")
    out = []
    for zona, track, nombre, rio in PULSO:
        g = pf[(pf.zona == zona) & (pf.track == track)].sort_values("fecha")
        out.append(dict(zona=zona, track=track, nombre=nombre, rio=rio,
                        serie=[dict(fecha=r.fecha, v=round(r.pct_agua_nueva, 2)) for r in g.itertuples()
                               if np.isfinite(r.pct_agua_nueva)]))
    return out


def monte():
    m = pd.read_csv(BASE / "monte_ribereno.csv")
    m = m[m.zona == "mercedes"]
    out = []
    for track, g in m.groupby("track"):
        series = {}
        for clase, gc in g.groupby("clase"):
            base = gc[gc.fase == "base"].hh_hv_db.mean()
            # escenas SHSH no tienen HV -> HH−HV es NaN: se descartan (NaN no es JSON válido)
            series[clase] = [dict(fecha=str(r.fecha)[:10], v=round(r.hh_hv_db - base, 2))
                             for r in gc.sort_values("fecha").itertuples() if np.isfinite(r.hh_hv_db)]
        out.append(dict(track=track, series=series))
    return out


def resumen_zonas():
    r = pd.read_csv(BASE / "metricas_resumen.csv")
    c = pd.read_csv(BASE / "combinado_resumen.csv")
    return dict(tracks=r[["zona", "track", "pct_extension_max", "ha_extension_max", "delta_hh_bosque_db"]].round(2).to_dict("records"),
                combinado=c[["zona", "ha_extension_max", "pct_extension_max"]].round(1).to_dict("records"))


def contexto(countries):
    """Contornos de Uruguay y vecinos (Natural Earth vía world-atlas) + rectángulos de las zonas."""
    topo = json.load(open(countries))
    sc, tr = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = []
    for a in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in a:
            x += dx
            y += dy
            pts.append((round(x * sc[0] + tr[0], 3), round(y * sc[1] + tr[1], 3)))
        arcs.append(pts)

    def anillo(idx):
        pts = []
        for i in idx:
            seg = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts += seg[1:] if pts else seg
        return pts

    paises = {}
    for g in topo["objects"]["countries"]["geometries"]:
        if g.get("id") not in ("858", "076", "032"):
            continue
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        anillos = [anillo(r) for p in polys for r in p]
        bb = (-59.5, -35.2, -52.5, -29.8)
        anillos = [a for a in anillos if any(bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3] for x, y in a)]
        paises[{"858": "UY", "076": "BR", "032": "AR"}[g["id"]]] = anillos
    zonas = {}
    for z, d in ZONAS.items():
        nums = [float(v) for v in re.findall(r"-?\d+\.?\d*", d["wkt"])]
        xs, ys = nums[0::2], nums[1::2]
        zonas[z] = [min(xs), min(ys), max(xs), max(ys)]
    return dict(paises=paises, zonas=zonas)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--countries", type=Path, default=COUNTRIES, help="world-atlas countries-50m.json")
    a = ap.parse_args()
    if not a.countries.exists():
        bajar_countries(a.countries)
    SAL.mkdir(parents=True, exist_ok=True)
    data = dict(visor=[dict(exportar_visor(z, t, f), titulo=tt) for z, t, f, tt in VISOR],
                pulso=pulso(), monte=monte(), resumen=resumen_zonas(), contexto=contexto(a.countries))
    (SAL / "poc.json").write_text(json.dumps(data, separators=(",", ":"), allow_nan=False))
    tam = sum(p.stat().st_size for p in SAL.iterdir()) / 1e6
    print(f"-> {SAL}  ({len(list(SAL.iterdir()))} archivos, {tam:.1f} MB)")
