"""
Capas vectoriales y de uso del suelo para agregar el impacto (B1 del plan). Sólo CONTEXTO (regla 1).

  python scripts/capas_contexto.py            # baja lo que falte y recorta por zona

Fuentes (todas abiertas):
  - OpenStreetMap, extracto Uruguay de Geofabrik (ODbL): localidades (place), áreas urbanas (landuse=residential),
    caminos (highway), ríos y cañadas (waterway), departamentos (admin_level=4).
    Se lee el .osm.pbf con el driver OSM de GDAL (Overpass no respondía).
  - HydroBASINS nivel 8 (HydroSHEDS, WWF): subcuencas.
  - ESA WorldCover 10 m 2021 v200 (AWS público): uso/cobertura del suelo, reproyectado a la grilla de cada track
    por moda. Clases: 10 árboles · 20 arbustal · 30 pradera · 40 cultivo · 50 urbano · 60 suelo desnudo ·
    80 agua · 90 humedal herbáceo. En la cuenca de la Merín "cultivo" es casi todo arroz.

Salida: data_nisar/contexto/capas/{zona}.gpkg (EPSG:32721): localidades, areas_urbanas, caminos, rios,
        departamentos, subcuencas · data_nisar/zonas/{zona}/T*/contexto/worldcover.tif
"""
import re
import ssl
import subprocess
import urllib.request
import zipfile
from pathlib import Path

import certifi
import geopandas as gpd
import pandas as pd
from shapely import wkt as shp_wkt
from shapely.geometry import box

from metricas_evento import BASE, OUT
from zonas import ZONAS

CTX_DIR = OUT / "contexto"
PBF = CTX_DIR / "osm" / "uruguay-latest.osm.pbf"
PBF_URL = "https://download.geofabrik.de/south-america/uruguay-latest.osm.pbf"
HYBAS = CTX_DIR / "hybas_sa_lev08_v1c.zip"
HYBAS_URL = "https://data.hydrosheds.org/file/hydrobasins/standard/hybas_sa_lev08_v1c.zip"
WORLDCOVER = [f"/vsis3/esa-worldcover/v200/2021/map/ESA_WorldCover_10m_2021_v200_{t}_Map.tif"
              for t in ("S36W060", "S36W057", "S33W057", "S36W054", "S33W054")]
CRS = "EPSG:32721"
SAL = CTX_DIR / "capas"
CTX = ssl.create_default_context(cafile=certifi.where())

# jerarquía vial: lo que importa para "caminos cortados"
VIAS = {"motorway": "national", "trunk": "national", "primary": "national", "secondary": "departmental",
        "tertiary": "departmental", "unclassified": "rural", "track": "rural", "residential": "urban",
        "living_street": "urban", "service": None}
LOCALIDADES = ("city", "town", "village", "hamlet", "suburb", "neighbourhood")
RIOS = ("river", "stream", "canal", "drain", "ditch")


def bajar(url, destino):
    if destino.exists():
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    print(f"bajando {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research script)"})
    with urllib.request.urlopen(req, context=CTX, timeout=900) as r, open(destino, "wb") as f:
        while b := r.read(1 << 20):
            f.write(b)


def bbox_todas(buffer=0.05):
    xs, ys = [], []
    for d in ZONAS.values():
        b = shp_wkt.loads(d["wkt"]).bounds
        xs += [b[0], b[2]]
        ys += [b[1], b[3]]
    return min(xs) - buffer, min(ys) - buffer, max(xs) + buffer, max(ys) + buffer


def leer_osm():
    from pyogrio import read_dataframe

    bb = bbox_todas()
    print("leyendo OSM (puede tardar ~1 min)…")
    pts = read_dataframe(PBF, layer="points", bbox=bb, columns=["name", "place"],
                         where="place IN ('" + "','".join(LOCALIDADES) + "')")
    lin = read_dataframe(PBF, layer="lines", bbox=bb, columns=["osm_id", "name", "highway", "waterway", "other_tags"],
                         where="highway IS NOT NULL OR waterway IS NOT NULL")
    # dos lecturas: con el driver OSM un WHERE con OR entre landuse y boundary pierde las relaciones administrativas
    urb = read_dataframe(PBF, layer="multipolygons", columns=["name", "landuse"], bbox=bb, where="landuse = 'residential'")
    dep = read_dataframe(PBF, layer="multipolygons", columns=["name", "boundary", "admin_level"],
                         where="boundary = 'administrative' AND admin_level = '4'")
    dep["geometry"] = dep.geometry.make_valid()
    ref = lin.other_tags.fillna("").str.extract(r'"ref"=>"([^"]+)"')[0]
    lin = lin.assign(ref=ref).drop(columns="other_tags")
    return pts, lin, urb, dep


def main():
    bajar(PBF_URL, PBF)
    bajar(HYBAS_URL, HYBAS)
    SAL.mkdir(parents=True, exist_ok=True)
    pts, lin, urb, deptos = leer_osm()
    with zipfile.ZipFile(HYBAS) as z:
        shp = [n for n in z.namelist() if n.endswith(".shp")][0]
    bb = bbox_todas()
    cuencas = gpd.read_file(f"zip://{HYBAS}!{shp}", bbox=bb)[["HYBAS_ID", "NEXT_DOWN", "SUB_AREA", "UP_AREA",
                                                                "geometry"]]
    deptos = deptos[["name", "geometry"]]
    urb = urb[["name", "geometry"]]
    caminos = lin[lin.highway.notna()].copy()
    caminos["clase"] = caminos.highway.map(VIAS)
    caminos = caminos[caminos.clase.notna()][["osm_id", "name", "ref", "highway", "clase", "geometry"]]
    rios = lin[lin.waterway.isin(RIOS)][["name", "waterway", "geometry"]]

    for zona, d in ZONAS.items():
        aoi = shp_wkt.loads(d["wkt"])
        recorte = gpd.GeoDataFrame(geometry=[aoi], crs="EPSG:4326")
        gpkg = SAL / f"{zona}.gpkg"
        gpkg.unlink(missing_ok=True)
        capas = dict(localidades=pts, areas_urbanas=urb, caminos=caminos, rios=rios, departamentos=deptos,
                     subcuencas=cuencas)
        for nombre, g in capas.items():
            g = g.set_crs("EPSG:4326", allow_override=True) if g.crs is None else g
            sub = gpd.clip(g, recorte).to_crs(CRS)
            sub = sub[~sub.geometry.is_empty]
            if nombre == "caminos":
                sub = sub.explode(index_parts=False)
                sub["km"] = sub.length / 1000
            sub.to_file(gpkg, layer=nombre, driver="GPKG")
            print(f"  {zona}/{nombre}: {len(sub)}")
        for tdir in sorted((BASE / zona).glob("T*_F*")):
            worldcover(tdir)


def worldcover(tdir):
    import rasterio

    destino = tdir / "contexto" / "worldcover.tif"
    if destino.exists():
        return
    ref = sorted(tdir.glob("*_HH.tif"))[0]
    with rasterio.open(ref) as r:
        b, crs, (w, h) = r.bounds, r.crs.to_string(), (r.width, r.height)
    destino.parent.mkdir(exist_ok=True)
    subprocess.run(["gdalwarp", "-q", "-overwrite", "-t_srs", crs, "-te", str(b.left), str(b.bottom), str(b.right),
                    str(b.top), "-ts", str(w), str(h), "-r", "mode", "-ot", "Byte", "-co", "COMPRESS=DEFLATE",
                    "--config", "AWS_NO_SIGN_REQUEST", "YES", *WORLDCOVER, str(destino)], check=True)
    print(f"  worldcover -> {destino.relative_to(OUT)}")


if __name__ == "__main__":
    main()
