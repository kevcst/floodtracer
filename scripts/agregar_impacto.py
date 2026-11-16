"""
Impacto agregado por camino, localidad, subcuenca, departamento y uso del suelo (B2 del plan).

  python scripts/agregar_impacto.py          # requiere combinar_tracks.py y capas_contexto.py

Rasters de entrada por zona: el COMBINADO de todos los tracks (zonas/{zona}/combinado/) para extensión y
persistencia; si la zona tiene un solo track se usan las métricas de ese track. Para la evolución por
fecha (km de camino bajo agua, % urbano con agua) se usa el track de la serie principal (`serie` en zonas.py),
para respetar la regla 2.

Definiciones
  extensión      = extension_confirmada (agua nueva en ≥ 2 observaciones del 15/8 al 10/9; con un solo track:
                   extension_max de ese track). Excluye el agua previa (ya mojada el 10–14/8, antes de la lluvia),
                   que se reporta aparte como ha_agua_previa.
  ha·día         = Σ píxeles inundados × persistencia (días) × ha/píxel. Rango con persistencia_min / _max.
                   Píxeles que siguen con agua al final de la serie: persistencia = última fecha − primera (cota inf.)
  camino cortado = puntos cada 20 m sobre el eje; un tramo está "bajo agua" si el píxel está en la extensión.
                   días de corte = persistencia máxima sobre el tramo (punto medio; rango min–max).
                   "sigue" = todavía con agua en la última pasada (20/10): días es cota inferior.
                   Vías con nombre se agrupan por nombre; sin nombre, cada way de OSM es una fila.
                   Ojo: los caminos suelen ir en terraplén; 20 m de píxel mezcla camino y banquina inundada.
  localidad      = mancha urbana OSM (landuse=residential) o, si no hay, círculo de 300 m en el punto `place`;
                   se mide dentro y en un anillo de 500 m alrededor.

Salida: data_nisar/zonas/impacto/{caminos,caminos_por_fecha,localidades,subcuencas,departamentos,uso_suelo}.csv
        y GeoJSON livianos (WGS84) para la app: caminos.geojson, localidades.geojson, subcuencas.geojson
"""
import warnings

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask

from metricas_evento import BASE
from zonas import ZONAS

warnings.filterwarnings("ignore")
CAPAS = BASE.parent / "contexto" / "capas"
SAL = BASE / "impacto"
WORLDCOVER = {10: "Tree cover", 20: "Shrubland", 30: "Grassland", 40: "Cropland (rice)", 50: "Built-up",
              60: "Bare", 80: "Water", 90: "Herbaceous wetland", 95: "Mangroves", 100: "Moss"}


def leer(p):
    with rasterio.open(p) as r:
        return r.read(1), r.profile


def productos(zona):
    comb = BASE / zona / "combinado"
    if (comb / "extension_confirmada.tif").exists():
        d, fuente = comb, "combined"
        ext, perfil = leer(d / "extension_confirmada.tif")
        ref = pd.read_csv(BASE / "combinado_resumen.csv").set_index("zona").loc[zona, "grilla_ref"]
    else:
        ref = ZONAS[zona]["serie"]
        d, fuente = BASE / zona / ref / "metricas", "single track"
        ext, perfil = leer(d / "extension_max.tif")
    p = {k: leer(d / f"{k}.tif")[0] for k in ("persistencia_dias", "persistencia_min", "persistencia_max",
                                               "fecha_retiro", "primera_fecha")}
    ext = ext == 1
    sigue = ext & (p["fecha_retiro"] == 999)
    fin = max(pd.Timestamp(f.name[:10]) for f in (BASE / zona).glob("T*_F*/*_HH.tif"))   # última pasada de la zona
    cota = np.where(sigue, fin.day_of_year - p["primera_fecha"], 0)
    pers = {k: np.where(sigue, cota, np.maximum(p[f"persistencia_{k}" if k != "mid" else "persistencia_dias"], 0))
            for k in ("mid", "min", "max")}
    for k in pers:
        pers[k] = np.where(ext, pers[k], 0)
    previa = leer(d / "agua_previa.tif")[0] == 1 if (d / "agua_previa.tif").exists() else np.zeros(ext.shape, bool)
    wc_path = BASE / zona / ref / "contexto" / "worldcover.tif"
    wc = leer(wc_path)[0] if wc_path.exists() else None
    return dict(ext=ext, pers=pers, sigue=sigue, retiro=np.where(ext & ~sigue, p["fecha_retiro"], 0),
                perfil=perfil, fuente=fuente, ref=ref, wc=wc, previa=previa)


def serie(zona):
    """Pila de agua nueva por fecha del track de la serie principal."""
    t = ZONAS[zona]["serie"]
    with rasterio.open(BASE / zona / t / "metricas" / "agua_nueva_por_fecha.tif") as r:
        return r.read(), list(r.descriptions), r.profile, t


def muestrear(geoms, perfil, paso=20.0):
    """Puntos cada `paso` m sobre cada línea → índices fila/col válidos (por geometría)."""
    inv = ~perfil["transform"]
    H, W = perfil["height"], perfil["width"]
    out = []
    for g in geoms:
        n = max(int(g.length // paso), 1)
        pts = [g.interpolate(i * paso) for i in range(n + 1)]
        cols, filas = zip(*[inv * (q.x, q.y) for q in pts])
        f, c = np.floor(filas).astype(int), np.floor(cols).astype(int)
        ok = (f >= 0) & (f < H) & (c >= 0) & (c < W)
        out.append((f[ok], c[ok]))
    return out


def doy_a_fecha(d):
    return (pd.Timestamp("2025-12-31") + pd.Timedelta(days=int(d))).date() if d and d < 999 else None


RUMBOS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def referencia(geom, lugares):
    """'4 km NE of Cebollatí' respecto de la localidad OSM más cercana (lugares en la misma proyección métrica)."""
    if lugares is None or lugares.empty:
        return ""
    c = geom.centroid
    d = lugares.distance(c)
    i = d.idxmin()
    lu = lugares.loc[i]
    km = d[i] / 1000
    if km < 1:
        return f"in {lu['name']}"
    ang = (np.degrees(np.arctan2(c.x - lu.geometry.x, c.y - lu.geometry.y)) + 360) % 360
    return f"{km:.0f} km {RUMBOS[int((ang + 22.5) // 45) % 8]} of {lu['name']}"


def lugares_zona(zona, crs):
    try:
        lu = gpd.read_file(CAPAS / f"{zona}.gpkg", layer="localidades").to_crs(crs)
        lu = lu[lu["name"].notna() & lu.place.isin(["city", "town", "village", "hamlet"])]
        return lu.reset_index(drop=True)
    except Exception:
        return None


def caminos(zona, P, S):
    g = gpd.read_file(CAPAS / f"{zona}.gpkg", layer="caminos")
    g = g[g.clase != "urban"].to_crs(P["perfil"]["crs"])
    if g.empty:
        return pd.DataFrame(), pd.DataFrame(), g
    ha = abs(P["perfil"]["transform"].a) / 1000                      # km por píxel muestreado (paso = 20 m)
    idx = muestrear(g.geometry, P["perfil"])
    filas = []
    for (f, c), (_, r) in zip(idx, g.iterrows()):
        m = P["ext"][f, c]
        filas.append(dict(km_bajo_agua=m.sum() * ha, dias_mid=int(P["pers"]["mid"][f, c].max()) if m.any() else 0,
                          dias_min=int(P["pers"]["min"][f, c].max()) if m.any() else 0,
                          dias_max=int(P["pers"]["max"][f, c].max()) if m.any() else 0,
                          sigue=bool(P["sigue"][f, c].any()),
                          retiro=doy_a_fecha(int(P["retiro"][f, c].max())) if m.any() else None))
    g = pd.concat([g.reset_index(drop=True), pd.DataFrame(filas)], axis=1)
    g["zona"] = zona
    g["nombre"] = g["name"].fillna(g["ref"].map(lambda x: f"Route {x}" if isinstance(x, str) else None))
    # vías con nombre: se agrupan por nombre; sin nombre: cada way de OSM por separado (si no, todo el campo
    # sería un único "camino rural sin nombre")
    g["clave"] = np.where(g.nombre.notna(), g.nombre, "osm:" + g.osm_id.astype(str))
    g["nombre"] = g.nombre.fillna(g.clase.map({"rural": "Unnamed rural road", "departmental": "Unnamed road",
                                               "national": "Unnamed route"}))
    c = g.to_crs("EPSG:4326").geometry.centroid
    g["lon"], g["lat"] = c.x, c.y
    agg = (g.groupby(["zona", "clave", "nombre", "clase"])
           .agg(km=("km", "sum"), km_bajo_agua=("km_bajo_agua", "sum"), dias_mid=("dias_mid", "max"),
                dias_min=("dias_min", "max"), dias_max=("dias_max", "max"), sigue=("sigue", "any"),
                lon=("lon", "mean"), lat=("lat", "mean"))
           .reset_index())
    agg = agg[agg.km_bajo_agua > 0].sort_values(["dias_mid", "km_bajo_agua"], ascending=False)
    lugares = lugares_zona(zona, P["perfil"]["crs"])
    geo_clave = g.dissolve(by="clave").geometry
    agg["donde"] = [referencia(geo_clave[k], lugares) for k in agg.clave]

    # km bajo agua por fecha (serie principal, su propia grilla)
    pila, fechas, perfil_s, t = S
    g_s = g.to_crs(perfil_s["crs"])
    idx_s = muestrear(g_s.geometry, perfil_s)
    f_all = np.concatenate([f for f, _ in idx_s]) if idx_s else np.array([], int)
    c_all = np.concatenate([c for _, c in idx_s]) if idx_s else np.array([], int)
    km_px = abs(perfil_s["transform"].a) / 1000
    por_fecha = [dict(zona=zona, track=t, fecha=d,
                      km_bajo_agua=float((pila[i][f_all, c_all] == 1).sum() * km_px),
                      km_rural_bajo_agua=float((pila[i][f_all, c_all] == 1)[
                          np.concatenate([np.full(len(f), cl == "rural") for (f, _), cl in zip(idx_s, g.clase)])
                      ].sum() * km_px) if idx_s else 0.0,
                      km_con_dato=float((pila[i][f_all, c_all] != 255).sum() * km_px))
                 for i, d in enumerate(fechas)]
    return agg, pd.DataFrame(por_fecha), g[g.km_bajo_agua > 0]


def poligonos(zona, P, gdf, nombre_col, ha_px):
    """Estadísticas zonales: ha de extensión, ha·día (rango) y fecha de retiro mediana."""
    filas = []
    for _, r in gdf.iterrows():
        m = geometry_mask([r.geometry], out_shape=P["ext"].shape, transform=P["perfil"]["transform"], invert=True)
        e = m & P["ext"]
        ret = P["retiro"][e & (P["retiro"] > 0)]
        filas.append(dict(zona=zona, nombre=r[nombre_col], ha_area=m.sum() * ha_px, ha_inundada=e.sum() * ha_px,
                          pct_inundada=100 * e.sum() / max(m.sum(), 1),
                          ha_dia=float(P["pers"]["mid"][e].sum() * ha_px),
                          ha_dia_min=float(P["pers"]["min"][e].sum() * ha_px),
                          ha_dia_max=float(P["pers"]["max"][e].sum() * ha_px),
                          ha_sigue=float((P["sigue"] & m).sum() * ha_px),
                          retiro_mediano=doy_a_fecha(int(np.median(ret))) if ret.size else None))
    return pd.DataFrame(filas)


def nombres_subcuencas(zona, sc, crs):
    """Nombre legible: el curso de agua con nombre más largo dentro de la subcuenca + localidad de referencia."""
    rios = gpd.read_file(CAPAS / f"{zona}.gpkg", layer="rios").to_crs(crs)
    rios = rios[rios["name"].notna()]
    lugares = lugares_zona(zona, crs)
    out = []
    for _, r in sc.iterrows():
        nombre = None
        if len(rios):
            dentro = gpd.clip(rios, r.geometry)
            if len(dentro):
                largo = dentro.assign(l=dentro.length).groupby("name").l.sum()
                nombre = largo.idxmax()
        ref = referencia(r.geometry, lugares)
        out.append(f"{nombre} ({ref})" if nombre and ref else nombre or (f"Basin {ref}" if ref else f"HYBAS {r.HYBAS_ID}"))
    # nombres repetidos: se desambiguan con el id
    s = pd.Series(out)
    dup = s.duplicated(keep=False)
    s[dup] = [f"{n} · {h}" for n, h in zip(s[dup], sc.HYBAS_ID.astype(str).str[-4:][dup.values])]
    return s.values


def localidades(zona, P, S):
    crs = P["perfil"]["crs"]
    urb = gpd.read_file(CAPAS / f"{zona}.gpkg", layer="areas_urbanas").to_crs(crs)
    pts = gpd.read_file(CAPAS / f"{zona}.gpkg", layer="localidades").to_crs(crs)
    pts = pts[pts.place.isin(["city", "town", "village"])]
    # unir manchas urbanas tocadas por el mismo punto; si no hay mancha, círculo de 300 m
    filas = []
    for _, p in pts.iterrows():
        cerca = urb[urb.distance(p.geometry) < 300]
        geom = cerca.union_all() if len(cerca) else p.geometry.buffer(300)
        filas.append(dict(nombre=p["name"], place=p.place, geometry=geom))
    if not filas:
        return pd.DataFrame(), gpd.GeoDataFrame()
    loc = gpd.GeoDataFrame(filas, crs=crs).dissolve(by="nombre", aggfunc="first").reset_index()
    ha_px = abs(P["perfil"]["transform"].a * P["perfil"]["transform"].e) / 1e4
    dentro = poligonos(zona, P, loc, "nombre", ha_px)
    anillo = loc.copy()
    anillo["geometry"] = loc.buffer(500).difference(loc.geometry)
    fuera = poligonos(zona, P, anillo, "nombre", ha_px)[["nombre", "ha_inundada", "ha_dia"]]
    fuera.columns = ["nombre", "ha_inundada_500m", "ha_dia_500m"]
    df = dentro.merge(fuera, on="nombre")
    df["place"] = loc.place.values
    # % urbano con agua por fecha (serie principal)
    pila, fechas, perfil_s, t = S
    loc_s = loc.to_crs(perfil_s["crs"])
    serie_loc = {}
    for _, r in loc_s.iterrows():
        m = geometry_mask([r.geometry.buffer(500)], out_shape=pila.shape[1:], transform=perfil_s["transform"],
                          invert=True)
        serie_loc[r.nombre] = [dict(fecha=d, ha=float((pila[i][m] == 1).sum() * ha_px)) for i, d in enumerate(fechas)]
    df["serie_500m"] = df.nombre.map(serie_loc)
    return df, loc.assign(zona=zona)


def uso_suelo(zona, P):
    if P["wc"] is None:
        return pd.DataFrame()
    ha_px = abs(P["perfil"]["transform"].a * P["perfil"]["transform"].e) / 1e4
    wc = P["wc"]
    if wc.shape != P["ext"].shape:
        return pd.DataFrame()
    filas = []
    for k, nombre in WORLDCOVER.items():
        m = wc == k
        if m.sum() == 0:
            continue
        e = m & P["ext"]
        filas.append(dict(zona=zona, clase=nombre, ha_clase=m.sum() * ha_px, ha_inundada=e.sum() * ha_px,
                          pct_clase_inundada=100 * e.sum() / m.sum(), ha_dia=float(P["pers"]["mid"][e].sum() * ha_px)))
    return pd.DataFrame(filas)


def main():
    SAL.mkdir(exist_ok=True)
    out = {k: [] for k in ("caminos", "caminos_por_fecha", "localidades", "subcuencas", "departamentos", "uso_suelo")}
    geo = {k: [] for k in ("caminos", "localidades", "subcuencas")}
    resumen = []
    for zona in ZONAS:
        P = productos(zona)
        S = serie(zona)
        ha_px = abs(P["perfil"]["transform"].a * P["perfil"]["transform"].e) / 1e4
        print(f"== {zona} ({P['fuente']}, grilla {P['ref']}): extensión {P['ext'].sum() * ha_px:,.0f} ha")
        a, pf, gseg = caminos(zona, P, S)
        out["caminos"].append(a)
        out["caminos_por_fecha"].append(pf)
        if len(gseg):
            geo["caminos"].append(gseg[["zona", "nombre", "clase", "km_bajo_agua", "dias_mid", "dias_min", "dias_max",
                                        "sigue", "geometry"]].to_crs("EPSG:4326"))
        loc, gloc = localidades(zona, P, S)
        out["localidades"].append(loc)
        if len(gloc):
            geo["localidades"].append(gloc[["zona", "nombre", "place", "geometry"]].to_crs("EPSG:4326"))
        sc = gpd.read_file(CAPAS / f"{zona}.gpkg", layer="subcuencas").to_crs(P["perfil"]["crs"])
        sc["nombre"] = nombres_subcuencas(zona, sc, P["perfil"]["crs"])
        s = poligonos(zona, P, sc, "nombre", ha_px)
        s["hybas_id"] = sc.HYBAS_ID.astype(str).values
        out["subcuencas"].append(s)
        geo["subcuencas"].append(sc.assign(zona=zona)[["zona", "nombre", "geometry"]].to_crs("EPSG:4326"))
        dp = gpd.read_file(CAPAS / f"{zona}.gpkg", layer="departamentos").to_crs(P["perfil"]["crs"])
        out["departamentos"].append(poligonos(zona, P, dp, "name", ha_px))
        out["uso_suelo"].append(uso_suelo(zona, P))
        km = a.km_bajo_agua.sum() if len(a) else 0
        resumen.append(dict(zona=zona, fuente=P["fuente"], ha_inundada=P["ext"].sum() * ha_px,
                            ha_agua_previa=P["previa"].sum() * ha_px,
                            ha_dia=float(P["pers"]["mid"].sum() * ha_px), km_caminos_bajo_agua=km,
                            km_caminos_mas_7_dias=a[a.dias_mid > 7].km_bajo_agua.sum() if len(a) else 0))
        print(f"   caminos: {km:.1f} km bajo agua · {len(a)} vías afectadas · localidades: {len(loc)}")

    for k, v in out.items():
        v = [x for x in v if len(x)]
        if v:
            pd.concat(v).round(2).to_csv(SAL / f"{k}.csv", index=False)
    pd.DataFrame(resumen).round(1).to_csv(SAL / "resumen.csv", index=False)
    for k, v in geo.items():
        if v:
            g = pd.concat(v)
            g["geometry"] = g.geometry.simplify(0.0002 if k != "caminos" else 0.00005)
            g.to_file(SAL / f"{k}.geojson", driver="GeoJSON", COORDINATE_PRECISION=5)
    print(pd.DataFrame(resumen).round(0).to_string(index=False))
    print(f"-> {SAL}")


if __name__ == "__main__":
    main()
