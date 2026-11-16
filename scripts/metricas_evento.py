"""
Métricas de la crecida de agosto 2026 por zona y track ("¿Cuánto tiempo se queda el agua?").

  python scripts/metricas_evento.py                       # todas las zonas/tracks
  python scripts/metricas_evento.py --zona rocha_norte    # una zona (no escribe los CSV globales)

Entrada : data_nisar/zonas/{zona}/T{track}{dir}_F{frame}/{fecha}_{HH|HV}.tif  (gamma0 lineal, misma grilla por track)
Salida  : .../T*/metricas/
            agua_base.tif         1 = agua "normal": HH < umbral en la mayoría de las pasadas base de CALMA
                                  (viento ERA5 < 3 m/s, clima.py; si no hay ninguna, todas las base)
            extension_max.tif     1 = agua nueva en alguna pasada de la tormenta (15/8–10/9) que no estaba antes
                                  (sin el agua previa de este track ni la del combinado: ver previa_en_grilla)
            agua_previa.tif       1 = agua nueva ya presente en las pasadas antes de la lluvia (10/8 al 15/8 09:29 UTC, previa_hasta; aparte)
            primera_fecha.tif     día del año de la primera pasada con agua nueva (0 = nunca)
            fecha_retiro.tif      día del año de la primera pasada seca después (0 = no aplica, 999 = sigue con agua)
            persistencia_dias.tif punto medio del intervalo de persistencia (días; -1 = no aplica)
            persistencia_min.tif  última pasada mojada − primera pasada mojada (cota inferior)
            persistencia_max.tif  primera pasada seca − pasada anterior a la primera detección (cota superior)
            delta_hh_db.tif       HH medio del evento − HH medio base (dB); sube con doble rebote (agua bajo vegetación)
            veg_inundada.tif      1 = candidato a agua bajo vegetación (delta > +3 dB, no agua abierta, HV base > −20 dB)
            mapas_agua.png        HH por fecha con agua base (azul) y agua nueva (rojo)
          data_nisar/zonas/metricas_resumen.csv   (una fila por zona/track)
          data_nisar/zonas/metricas_por_fecha.csv (% agua total / nueva por fecha)

Detector de agua NUEVA (por defecto, "cambio"): HH del día − mediana HH de la base del MISMO track < −3 dB
y HH < −14 dB, fuera del agua base, en manchas ≥ 10 píxeles (0,4 ha). Elegido con scripts/armonizar_tracks.py:
con pasadas de 1 día de diferencia de distinto track duplica la coincidencia (Jaccard 0,2–0,3 → 0,5–0,6) frente a
un umbral absoluto, porque compara cada píxel contra sí mismo y se cancelan geometría, ángulo y calibración del track.
El agua BASE (permanente) sigue saliendo del umbral absoluto calibrado por track.

Reglas (CLAUDE.md): sólo NISAR, un track por serie, sólo PROVISIONAL (ventana de zonas.py).
"""
import argparse
import json
import warnings
from collections import Counter

import numpy as np
import pandas as pd
import rasterio
from scipy import ndimage as ndi

from zonas import OUT, ZONAS

BASE = OUT / "zonas"
warnings.filterwarnings("ignore", category=RuntimeWarning)   # nanmean de píxeles sin datos
FIN_BASE = pd.Timestamp("2026-07-27")         # inicio del hueco global de datos: todo lo anterior es línea de base
EVENTO = (pd.Timestamp("2026-08-10"), pd.Timestamp("2026-09-10"))
VENTANA_SPECKLE = 5                            # media 5×5 en lineal (≈100 m)
UMBRAL_DEFECTO = -18.0
DELTA_VEG_DB = 3.0
# detector por cambio (ver armonizar_tracks.py)
CAMBIO_DB = -3.0          # caída mínima respecto de la mediana base del píxel
TECHO_DB = -14.0          # y además HH absoluto por debajo de esto (descarta caídas de campo a campo más liso)
MMU_PX = 10               # mancha mínima (píxeles de 20 m)
MAX_DESVIO_ESCENA_DB = 5.0   # pasada descartada si la mediana del recorte se aleja más que esto de la del track
INICIO_LLUVIA = pd.Timestamp("2026-08-15")   # el agua del evento no pudo llegar antes (cota de persistencia)

# Eventos: cada zona declara el suyo en zonas.py (clave "evento", por defecto "agosto").
#   ventana  = pasadas que cuentan para la extensión (≥ 2 obs. en combinar_tracks.py)
#   inicio   = el agua del evento no pudo llegar antes: las pasadas de la ventana anteriores son "agua previa"
#   fin_base = la línea de base son las pasadas anteriores
#   previa_hasta = hora UTC hasta la que una pasada todavía es "agua previa" (por defecto = inicio). En agosto la 31A del
#              15/8 pasa a las 09:29 UTC y la lluvia empieza en la madrugada del 16/8 en las 6 zonas del este (ERA5,
#              _clima/{zona}.json; ≤ 0,7 mm antes de la pasada): esa pasada es previa aunque caiga el día 0.
#   cultivo_sin_dato_desde = desde esa fecha los cultivos (WorldCover 40) son "sin dato": en octubre empieza el laboreo
#              y la inundación de los arrozales, que el detector confunde con agua que no se fue
EVENTOS = {
    "agosto": dict(nombre="August storm", lluvia=("2026-08-15", "2026-08-19"), ventana=("2026-08-10", "2026-09-10"),
                   inicio="2026-08-15", previa_hasta="2026-08-16T00:00", fin_base="2026-07-27",
                   cultivo_sin_dato_desde="2026-10-01"),
}
WC_CULTIVO = 40
# Océano: no aporta nada a la pregunta y genera falsa "agua nueva" con mar calmo (en T53D sólo el 72 % del mar de
# Rocha norte quedaba como agua permanente: estaba justo en el umbral). Se marca sin dato en cargar_track.
# mar = cuerpos de agua de WorldCover (80) que tocan el polígono `mar_wkt` de la zona (zonas.py, dibujado del lado del
# mar), recortados a ese polígono + MAR_BUFFER_M (para no seguir un arroyo hasta una laguna) y dilatados MAR_DILATAR_PX
# (píxeles mixtos de la rompiente). Es contexto, no validación (regla 1).
MAR_BUFFER_M = 1500
MAR_DILATAR_PX = 2


class Evento:
    def __init__(self, zona):
        z = ZONAS[zona]
        self.clave = z.get("evento", "agosto")
        e = EVENTOS[self.clave]
        self.nombre, self.lluvia = e["nombre"], tuple(pd.Timestamp(x) for x in e["lluvia"])
        self.ventana = tuple(pd.Timestamp(x) for x in e["ventana"])
        self.inicio = pd.Timestamp(e["inicio"])
        self.previa_hasta = pd.Timestamp(e.get("previa_hasta", e["inicio"]))
        self.cultivo_sin_dato_desde = pd.Timestamp(e["cultivo_sin_dato_desde"]) if e.get("cultivo_sin_dato_desde") else None
        self.zona = zona
        self.fin_base = pd.Timestamp(z.get("fin_base", e["fin_base"]))

    def es_evento(self, fechas):
        return np.asarray((fechas >= self.ventana[0]) & (fechas <= self.ventana[1]))

    def es_previa(self, fechas, tracks=None):
        """Pasadas de la ventana anteriores a la lluvia. Con `tracks` (uno o uno por fecha) compara la HORA de la pasada
        (clima_pasadas.csv) contra previa_hasta; sin hora conocida, la fecha contra inicio (regla anterior)."""
        fechas = pd.DatetimeIndex(fechas)
        previa = np.asarray(fechas < self.inicio)
        if tracks is not None and self.previa_hasta > self.inicio:
            ts = horas_pasadas(self.zona, [tracks] * len(fechas) if isinstance(tracks, str) else tracks, fechas)
            previa = previa | np.asarray([pd.notna(t) and t < self.previa_hasta for t in ts])
        return self.es_evento(fechas) & previa

    def es_base(self, fechas, hh=None):
        """Pasadas de la línea de base: todas las anteriores a fin_base (hh se acepta por compatibilidad de llamadas)."""
        return np.asarray(fechas < self.fin_base)


def tracks_zona(zona, todos=False):
    """Carpetas de track de la zona. Sin `todos`, sin los de ZONAS[zona]["excluir_tracks"] (diagnóstico solamente:
    no entran al combinado, la validación ni la app)."""
    ex = set() if todos else set(ZONAS[zona].get("excluir_tracks", []))
    return [t for t in sorted((BASE / zona).glob("T*_F*")) if t.is_dir() and t.name not in ex]


def excluido(zona, track):
    return track in ZONAS[zona].get("excluir_tracks", [])


def horas_pasadas(zona, tracks, fechas):
    """Fecha y hora UTC de cada pasada (clima_pasadas.csv de clima.py); NaT si no se conoce."""
    f = BASE / zona / "clima_pasadas.csv"
    d = {}
    if f.exists():
        c = pd.read_csv(f)
        d = {(r.track, r.fecha): pd.Timestamp(f"{r.fecha}T{r.hora_utc}") for r in c.itertuples()}
    return [d.get((t, str(pd.Timestamp(x).date())), pd.NaT) for t, x in zip(tracks, fechas)]


def mascara_mar(zona, perfil):
    """1 = océano en la grilla `perfil` (ver MAR_*). Ceros si la zona no declara mar_wkt."""
    from rasterio.features import geometry_mask
    from rasterio.warp import transform_geom
    from shapely import wkt as shp_wkt
    from shapely.geometry import mapping, shape

    H, W = perfil["height"], perfil["width"]
    z = ZONAS.get(zona, {})
    if not z.get("mar_wkt"):
        return np.zeros((H, W), bool)
    g = shape(transform_geom("EPSG:4326", perfil["crs"], mapping(shp_wkt.loads(z["mar_wkt"]))))
    dentro = lambda geom: ~geometry_mask([mapping(geom)], (H, W), perfil["transform"])
    nucleo, cerca = dentro(g), dentro(g.buffer(MAR_BUFFER_M))
    agua = mascara_wc(zona, perfil, 80)
    lab, _ = ndi.label(agua)
    ids = np.unique(lab[nucleo & agua])
    mar = np.isin(lab, ids[ids > 0]) & cerca
    return ndi.binary_dilation(mar, iterations=MAR_DILATAR_PX) & cerca | (nucleo & agua)


def mascara_wc(zona, perfil, clase):
    """Clase de ESA WorldCover en la grilla `perfil` (cualquier track de la zona; capas_contexto.py)."""
    from rasterio.warp import Resampling, reproject

    H, W = perfil["height"], perfil["width"]
    archivos = sorted((BASE / zona).glob("T*_F*/contexto/worldcover.tif"))
    if not archivos:
        return np.zeros((H, W), bool)
    for f in archivos:                           # misma grilla: se lee tal cual
        with rasterio.open(f) as r:
            if r.shape == (H, W) and r.transform == perfil["transform"] and r.crs == perfil["crs"]:
                return r.read(1) == clase
    with rasterio.open(archivos[0]) as r:        # si no, se reproyecta el primero (vecino más cercano)
        src, ps = r.read(1), r.profile
    out = np.zeros((H, W), "uint8")
    reproject(src, out, src_transform=ps["transform"], src_crs=ps["crs"], dst_transform=perfil["transform"],
              dst_crs=perfil["crs"], resampling=Resampling.nearest)
    return out == clase


def sin_dato_por_fecha(zona, perfil, fechas):
    """(n_fechas, H, W) True = la pasada no informa sobre ese píxel aunque haya señal: cultivos desde
    Evento.cultivo_sin_dato_desde (laboreo/arroz en octubre). Lo usan metricas_evento (retiro, pila) y, vía la pila
    (255), combinar_tracks y exportar_app."""
    H, W = perfil["height"], perfil["width"]
    ev = Evento(zona)
    out = np.zeros((len(fechas), H, W), bool)
    if ev.cultivo_sin_dato_desde is None:
        return out
    tarde = np.asarray(pd.DatetimeIndex(fechas) >= ev.cultivo_sin_dato_desde)
    if tarde.any():
        out[tarde] = mascara_wc(zona, perfil, WC_CULTIVO)
    return out


def es_validado(fechas):
    """Pasadas VALIDATED (regla 3): el detector las normaliza por escena también en el techo absoluto."""
    from zonas import INICIO_VALIDATED
    return np.asarray(pd.DatetimeIndex(fechas) >= pd.Timestamp(INICIO_VALIDATED))


def filtrar_mmu(m, mmu=MMU_PX):
    if mmu <= 1 or not m.any():
        return m
    lab, n = ndi.label(m)
    tam = ndi.sum(m, lab, np.arange(1, n + 1))
    return np.r_[False, tam >= mmu][lab]


def detectar_nueva(hh, hh_base_med, agua_base, metodo="cambio", umbral=UMBRAL_DEFECTO,
                   cambio=CAMBIO_DB, techo=TECHO_DB, mmu=MMU_PX, normalizar=True, validado=False):
    """Máscara de agua nueva para una pasada (hh en dB, 2D)."""
    if metodo == "umbral":
        return (hh < umbral) & ~agua_base
    d = hh - hh_base_med
    # normalización por escena: corrige corrimientos de toda la pasada (calibración, suelo más seco/húmedo).
    # La mediana es robusta mientras el agua nueva ocupe < 50 % del recorte.
    tierra = np.isfinite(d) & ~agua_base
    off = float(np.nanmedian(d[tierra])) if normalizar and tierra.any() else 0.0
    # VALIDATED: el salto de calibración (~−1,7 dB en tierra) también corre el techo absoluto → se le resta el mismo off
    m = (d - off < cambio) & ((hh - off if validado else hh) < techo) & ~agua_base
    return filtrar_mmu(m, mmu)


def falsa_alarma_base(hh, es_base, agua_base, valid, validado):
    """Piso de ruido del detector: % del recorte marcado como agua nueva en cada pasada BASE comparada contra la mediana
    de las OTRAS pasadas base (dejar-una-afuera; sin agua real esperable). Se devuelve la mediana entre pasadas, que no
    se infla si una pasada base tuvo agua de verdad (p. ej. 22–23/7). NaN con < 2 pasadas base (no se puede estimar)."""
    idx = np.where(es_base)[0]
    if len(idx) < 2 or not valid.any():
        return np.nan
    pcts = []
    for i in idx:
        med = np.nanmedian(hh[idx[idx != i]], axis=0)
        m = detectar_nueva(hh[i], med, agua_base, validado=validado[i]) & valid
        pcts.append(100 * m.sum() / valid.sum())
    return float(np.median(pcts))


def previa_en_grilla(zona, perfil, propia=None):
    """Agua previa (mojada antes de la lluvia: 10/8 al 15/8 09:29 UTC) llevada a la grilla de un track. Usa la del COMBINADO si existe, porque un
    track sin pasada antes del 15/8 (p. ej. 53D) no puede separarla solo. Si no, la propia del track."""
    from rasterio.warp import Resampling, reproject

    f = BASE / zona / "combinado" / "agua_previa.tif"
    if not f.exists():
        return propia if propia is not None else np.zeros((perfil["height"], perfil["width"]), bool)
    with rasterio.open(f) as r:
        src, ps = r.read(1), r.profile
    out = np.zeros((perfil["height"], perfil["width"]), "uint8")
    reproject(src, out, src_transform=ps["transform"], src_crs=ps["crs"], dst_transform=perfil["transform"],
              dst_crs=perfil["crs"], resampling=Resampling.nearest)
    out = out == 1
    return out | propia if propia is not None else out


def intervalos_persistencia(fechas, nueva, ok, ext_max, es_evento, retiro_i, primera_i, inicio=INICIO_LLUVIA):
    """Persistencia como intervalo a partir de la secuencia de observaciones.
    min = última obs mojada antes del retiro − primera obs mojada
    max = obs de retiro − max(obs anterior a la primera detección, inicio de la lluvia)
    retiro_i = índice de la obs que marca el retiro (-1 = sigue)."""
    t = np.asarray(fechas.values.astype("datetime64[D]").astype("int64"))
    H, W = ext_max.shape
    ultima = np.full((H, W), -1, "int64")
    for i in range(len(fechas)):
        upd = ext_max & ok[i] & nueva[i] & ((retiro_i < 0) | (i < retiro_i)) & (primera_i >= 0) & (i >= primera_i)
        ultima[upd] = i
    prev = np.full((H, W), -1, "int64")                    # última obs con dato antes de la primera detección
    for i in range(len(fechas)):
        upd = ext_max & ok[i] & (i < primera_i)
        prev[upd] = i
    t_ini = np.where(prev >= 0, t[np.maximum(prev, 0)], t[np.maximum(primera_i, 0)])
    t_lluvia = np.datetime64(inicio.date(), "D").astype("int64")
    t_ini = np.where(t[np.maximum(primera_i, 0)] >= t_lluvia, np.maximum(t_ini, t_lluvia), t_ini)
    hecho = ext_max & (retiro_i >= 0)
    pmin = np.where(hecho, t[np.maximum(ultima, 0)] - t[np.maximum(primera_i, 0)], -1)
    pmax = np.where(hecho, t[np.maximum(retiro_i, 0)] - t_ini, -1)
    pmid = np.where(hecho, (pmin + pmax) / 2, -1)
    return pmin.astype("int16"), pmax.astype("int16"), np.round(pmid).astype("int16")


def media_nan(x, w=VENTANA_SPECKLE):
    """Media móvil que ignora NaN (para no comerse los bordes del recorte)."""
    ok = np.isfinite(x)
    s = ndi.uniform_filter(np.where(ok, x, 0), w)
    n = ndi.uniform_filter(ok.astype("float32"), w)
    with np.errstate(invalid="ignore", divide="ignore"):
        m = s / n
    m[~ok] = np.nan
    return m


def leer(path):
    with rasterio.open(path) as r:
        x = r.read(1).astype("float32")
        perfil = r.profile
    # < −50 dB no es señal: relleno fuera del swath que algunos frames traen como ~1e-14 en vez de 0/NaN
    x[(x < 1e-5) | ~np.isfinite(x)] = np.nan
    return x, perfil


def cargar_track(tdir):
    """Devuelve fechas, stacks HH/HV suavizados en dB y el perfil raster. Descarta fechas con otra grilla."""
    archivos = sorted(tdir.glob("*_HH.tif"))
    grillas = {}
    for f in archivos:
        with rasterio.open(f) as r:
            grillas[f] = (r.shape, tuple(round(v, 3) for v in r.transform[:6]))
    modal = Counter(grillas.values()).most_common(1)[0][0]
    descartadas = [f.name[:10] for f in archivos if grillas[f] != modal]
    if descartadas:
        print(f"   ! fechas con otra grilla, descartadas: {descartadas}")
    archivos = [f for f in archivos if grillas[f] == modal]

    fechas, hh, hv, perfil = [], [], [], None
    for f in archivos:
        x, perfil = leer(f)
        hh.append(10 * np.log10(np.maximum(media_nan(x), 1e-6)))
        fv = f.with_name(f.name.replace("_HH", "_HV"))
        if fv.exists():
            y, _ = leer(fv)
            hv.append(10 * np.log10(np.maximum(media_nan(y), 1e-6)))
        else:                                   # escenas SHSH: no hay HV
            hv.append(np.full_like(x, np.nan))
        fechas.append(pd.Timestamp(f.name[:10]))
    hh, hv = np.stack(hh), np.stack(hv)
    hh[~np.isfinite(hh)] = np.nan
    # pasadas que cubren sólo un borde del recorte (frame parcial): como el resto exige dato en TODAS las fechas,
    # una sola achica el área válida de toda la serie → se descartan si cubren < 80 % de la mediana del track
    n = np.isfinite(hh).sum(axis=(1, 2))
    ok = n >= 0.8 * np.median(n)
    if not ok.all():
        print(f"   ! pasadas parciales descartadas: {[str(f.date()) for f, o in zip(fechas, ok) if not o]}")
        fechas = [f for f, o in zip(fechas, ok) if o]
        hh, hv = hh[ok], hv[ok]
    # pasadas con calibración rota: la mediana de TODO el recorte se aleja > 5 dB de la del track (p. ej. T60A_F162
    # 2026-06-18: +24 dB; otra escena 2026-07-12: −15 dB). Ni una crecida ni el salto VALIDATED (~−1,7 dB) mueven tanto
    # la mediana de un recorte entero. Sin este filtro una escena "brillante" entraba como la base más seca.
    med = np.array([np.nanmedian(x) for x in hh])
    ok = np.abs(med - np.nanmedian(med)) <= MAX_DESVIO_ESCENA_DB
    if not ok.all():
        print(f"   ! pasadas con calibración rota descartadas: "
              f"{[f'{f.date()} ({m - np.nanmedian(med):+.0f} dB)' for f, m, o in zip(fechas, med, ok) if not o]}")
        fechas = [f for f, o in zip(fechas, ok) if o]
        hh, hv = hh[ok], hv[ok]
    if tdir.parent.name in ZONAS:                # océano = sin dato (ver MAR_*)
        mar = mascara_mar(tdir.parent.name, perfil)
        hh[:, mar] = np.nan
        hv[:, mar] = np.nan
    return fechas, hh, hv, perfil


def pasadas_calma(zona, track, fechas, es_base):
    """Pasadas base con viento ERA5 < clima.CALMA_MS a la hora del paso (clima.py). Si el track no tiene ninguna,
    o no hay clima, devuelve todas las pasadas base (comportamiento anterior)."""
    from clima import CALMA_MS, viento_pasadas

    v = viento_pasadas(zona, track, fechas)
    calma = es_base & (v < CALMA_MS)
    return (calma if calma.any() else es_base), v


def agua_permanente(hh, sel, umbral, valid):
    """Agua base = HH < umbral del track en la MAYORÍA de las pasadas `sel` (las base de calma, ver pasadas_calma).
    Con viento el agua abierta se riza y sube a −16/−17 dB (laguna Merín en 53D): con todas las pasadas base sólo
    llegaba a mayoría el 5–11 % de la laguna; con las de calma, ~90 % (F1 vs JRC 0,37 → 0,50)."""
    return ((hh[sel] < umbral) & valid).mean(axis=0) > 0.5


def calibrar_umbral(hh_base, valid):
    """Umbral por track: 30 % del camino entre agua permanente y tierra (≈ −18 dB en 53D).
    Si no hay suficiente agua permanente en el recorte, usa el umbral por defecto."""
    agua = valid & np.all(hh_base < -20, axis=0)
    tierra = valid & np.all(hh_base > -14, axis=0)
    if agua.sum() < 200 or tierra.sum() < 200:
        return UMBRAL_DEFECTO, None, None
    w, t = float(np.median(hh_base[:, agua])), float(np.median(hh_base[:, tierra]))
    # tope −17,5 dB: con −16 entran potreros lisos/mojados (una zona de prueba oscilaba 6–18 % según la lluvia del día)
    return float(np.clip(w + 0.3 * (t - w), -20, -17.5)), w, t


def guardar(path, arr, perfil, dtype, nodata=None):
    p = perfil.copy()
    p.update(driver="GTiff", dtype=dtype, count=1, compress="deflate", nodata=nodata)
    for k in ("blockxsize", "blockysize", "tiled", "interleave"):
        p.pop(k, None)
    with rasterio.open(path, "w", **p) as dst:
        dst.write(arr.astype(dtype), 1)


def procesar(zona, tdir, umbral_forzado=None, metodo="cambio"):
    print(f"== {zona}/{tdir.name}")
    fechas, hh, hv, perfil = cargar_track(tdir)
    fechas = pd.DatetimeIndex(fechas)
    ev = Evento(zona)
    es_base = ev.es_base(fechas, hh)
    es_evento = ev.es_evento(fechas)
    if es_base.sum() == 0 or es_evento.sum() == 0:
        print("   ! sin fechas de base o de evento, se saltea")
        return None, []
    valid = np.all(np.isfinite(hh), axis=0)

    if umbral_forzado is not None:
        umbral, w, t = umbral_forzado, None, None
    else:
        umbral, w, t = calibrar_umbral(hh[es_base], valid)
    W_abs = (hh < umbral) & valid                               # agua abierta por fecha (umbral absoluto)
    calma, viento = pasadas_calma(zona, tdir.name, fechas, es_base)
    agua_base = agua_permanente(hh, calma, umbral, valid)       # agua "normal": mayoría de las pasadas base de calma
    hh_base_med = np.nanmedian(hh[es_base], axis=0)
    sin_dato = sin_dato_por_fecha(zona, perfil, fechas)
    ok = np.isfinite(hh) & ~sin_dato
    val = es_validado(fechas)
    nueva = np.stack([detectar_nueva(hh[i], hh_base_med, agua_base, metodo, umbral, validado=val[i]) & ok[i] & valid
                      for i in range(len(fechas))])            # agua nueva por fecha
    W = (W_abs & agua_base) | nueva                             # agua total = base + nueva

    # agua previa: agua nueva en pasadas de la ventana ANTERIORES a la lluvia (10/8 al 15/8 09:29 UTC, previa_hasta; después del hueco de datos).
    # Venía de las lluvias de julio y del hueco; no se le puede atribuir a la tormenta ni fechar su llegada,
    # así que se reporta aparte (agua_previa.tif) y queda FUERA de la extensión y la persistencia del evento.
    es_previa = ev.es_previa(fechas, tdir.name)
    agua_previa = nueva[es_previa].any(axis=0) if es_previa.any() else np.zeros(valid.shape, bool)
    es_tormenta = es_evento & ~es_previa
    if not es_tormenta.any():
        print(f"   ! sin pasadas después de {ev.inicio.date()} en la ventana, se saltea")
        return None, []
    # también el agua previa vista por OTROS tracks: uno sin pasada antes de la lluvia (53D) no puede separarla solo y
    # la contaría como tormenta. Requiere combinado/agua_previa.tif (combinar_tracks.py, que sólo lee las pilas por
    # fecha y no depende de esto); en una corrida desde cero hay que volver a correr este script después de combinar.
    ext_max = nueva[es_tormenta].any(axis=0) & ~previa_en_grilla(zona, perfil, agua_previa)
    doy = np.asarray(fechas.day_of_year)
    idx_ev = np.where(es_tormenta)[0]

    # primera pasada del evento con agua nueva y primera pasada seca posterior (cualquier fecha hasta el final)
    primera_i = np.full(valid.shape, -1, "int16")
    for i in idx_ev[::-1]:
        primera_i[nueva[i]] = i
    retiro_i = np.full(valid.shape, -1, "int16")               # -1 = sigue con agua al final de la serie
    pendiente = ext_max.copy()
    for i in range(idx_ev[0] + 1, len(fechas)):
        seco = pendiente & ok[i] & ~nueva[i] & (primera_i < i)
        retiro_i[seco] = i
        pendiente &= ~seco
    sigue = ext_max & (retiro_i < 0)

    primera = np.where(ext_max, doy[np.maximum(primera_i, 0)], 0)
    retiro = np.where(ext_max & ~sigue, doy[np.maximum(retiro_i, 0)], 0)
    retiro[sigue] = 999
    pmin, pmax, persist = intervalos_persistencia(fechas, nueva, ok, ext_max, es_evento, retiro_i, primera_i, ev.inicio)

    # agua bajo vegetación: HH sube (doble rebote) sin pasar a agua abierta, en zonas con vegetación (HV alto)
    delta = np.nanmean(hh[es_evento], axis=0) - np.nanmean(hh[es_base], axis=0)
    hv_base = np.nanmean(hv[es_base], axis=0) if np.isfinite(hv[es_base]).any() else np.full(valid.shape, np.nan)
    veg = valid & (delta > DELTA_VEG_DB) & ~W[es_evento].any(axis=0) & ~agua_base & (hv_base > -20)

    out = tdir / "metricas"
    out.mkdir(exist_ok=True)
    guardar(out / "agua_base.tif", agua_base, perfil, "uint8")
    guardar(out / "extension_max.tif", ext_max, perfil, "uint8")
    guardar(out / "agua_previa.tif", agua_previa, perfil, "uint8")
    guardar(out / "primera_fecha.tif", primera, perfil, "int16", 0)
    guardar(out / "fecha_retiro.tif", retiro, perfil, "int16", 0)
    guardar(out / "persistencia_dias.tif", persist, perfil, "int16", -1)
    guardar(out / "persistencia_min.tif", pmin, perfil, "int16", -1)
    guardar(out / "persistencia_max.tif", pmax, perfil, "int16", -1)
    guardar(out / "delta_hh_db.tif", np.where(valid, delta, np.nan), perfil, "float32", np.nan)
    guardar(out / "veg_inundada.tif", veg, perfil, "uint8")
    # pila de agua nueva por fecha (0/1, 255 = sin dato) para combinar tracks a nivel de máscara (combinar_tracks.py).
    # El agua permanente también es 255: ahí este track no puede ver agua nueva, así que no "vota seco" contra otro
    # track que sí la ve. Ídem los cultivos tardíos (sin_dato_por_fecha).
    p = perfil.copy()
    p.update(driver="GTiff", dtype="uint8", count=len(fechas), compress="deflate", nodata=255)
    for k in ("blockxsize", "blockysize", "tiled", "interleave"):
        p.pop(k, None)
    with rasterio.open(out / "agua_nueva_por_fecha.tif", "w", **p) as dst:
        for i, f in enumerate(fechas):
            dst.write(np.where(ok[i] & ~agua_base, nueva[i], 255).astype("uint8"), i + 1)
            dst.set_band_description(i + 1, str(f.date()))

    nv = valid.sum()
    ha_px = abs(perfil["transform"].a * perfil["transform"].e) / 1e4
    far = falsa_alarma_base(hh, es_base, agua_base, valid, val)
    # monte / monte ribereño: dispersión de volumen alta en la base. Si se inunda, HH y HH−HV suben (doble rebote).
    hh_base = np.nanmean(hh[es_base], axis=0)
    bosque = valid & (hh_base > -7) & (hv_base > -14)
    def fase(f, b, e):
        return "base" if b else ("evento" if e else ("pre" if f < ev.ventana[0] else "post"))
    por_fecha = [dict(zona=zona, track=tdir.name, fecha=f.date(), fase=fase(f, b, e),
                      pct_agua=100 * W[i].sum() / max((valid & ok[i]).sum(), 1),
                      pct_agua_nueva=100 * nueva[i].sum() / max((valid & ok[i]).sum(), 1),
                      hh_bosque_db=float(np.median(hh[i][bosque])) if bosque.any() else np.nan,
                      hh_hv_bosque_db=float(np.nanmedian((hh[i] - hv[i])[bosque])) if bosque.any() else np.nan)
                 for i, (f, b, e) in enumerate(zip(fechas, es_base, es_evento))]
    pers_validos = persist[ext_max & ~sigue]
    fila = dict(zona=zona, track=tdir.name, excluido=excluido(zona, tdir.name), evento=ev.clave, metodo=metodo, n_fechas=len(fechas), n_base=int(es_base.sum()),
                fechas_base=" ".join(str(f.date())[5:] for f in fechas[es_base]),
                fechas_base_calma=" ".join(str(f.date())[5:] for f in fechas[calma]),
                viento_base=" ".join(f"{x:.1f}" for x in viento[es_base]),
                fechas_evento=" ".join(str(f.date())[5:] for f in fechas[es_evento]),
                umbral_db=round(umbral, 2), agua_perm_db=w and round(w, 1), tierra_db=t and round(t, 1),
                pct_agua_base=100 * agua_base.sum() / nv, pct_extension_max=100 * ext_max.sum() / nv,
                ha_extension_max=ext_max.sum() * ha_px,
                ha_agua_previa=agua_previa.sum() * ha_px,
                ha_valida=nv * ha_px,
                pct_falsa_alarma_base=far, ha_ruido_base=far * nv * ha_px / 100,
                persistencia_mediana_dias=float(np.median(pers_validos)) if pers_validos.size else np.nan,
                persistencia_min_mediana=float(np.median(pmin[ext_max & ~sigue])) if pers_validos.size else np.nan,
                persistencia_max_mediana=float(np.median(pmax[ext_max & ~sigue])) if pers_validos.size else np.nan,
                pct_sigue_con_agua=100 * sigue.sum() / max(ext_max.sum(), 1),
                pct_veg_inundada=100 * veg.sum() / nv, pct_bosque=100 * bosque.sum() / nv,
                delta_hh_bosque_db=float(np.median(delta[bosque])) if bosque.any() else np.nan)
    print("   " + json.dumps({k: (round(v, 2) if isinstance(v, float) else v) for k, v in fila.items()
                              if k not in ("zona", "track")}, ensure_ascii=False))
    panel(out / "mapas_agua.png", f"{zona} {tdir.name}: {metodo} detector, permanent water < {umbral:.1f} dB", fechas, hh, W, agua_base, es_base,
          es_evento, ext_max, persist)
    return fila, por_fecha


def panel(path, titulo, fechas, hh, W, agua_base, es_base, es_evento, ext_max, persist):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = len(fechas) + 2
    cols = min(n, 5)
    filas = int(np.ceil(n / cols))
    h, w = hh.shape[1:]
    fig, axs = plt.subplots(filas, cols, figsize=(3.2 * cols, 3.2 * filas * h / w + 0.4 * filas), squeeze=False)
    for ax in axs.flat:
        ax.axis("off")
    for i, f in enumerate(fechas):
        ax = axs.flat[i]
        g = np.clip((hh[i] + 22) / 20, 0, 1)
        rgb = np.dstack([g, g, g])
        rgb[W[i] & agua_base] = [0.1, 0.3, 0.9]
        rgb[W[i] & ~agua_base] = [0.95, 0.15, 0.1]
        ax.imshow(rgb, interpolation="nearest")
        fase = "baseline" if es_base[i] else ("EVENT" if es_evento[i] else "after")
        ax.set_title(f"{f.date()} ({fase})\nnew water {100 * (W[i] & ~agua_base).mean():.1f}%", fontsize=8)
    ax = axs.flat[len(fechas)]
    ax.imshow(np.where(ext_max, 1, np.nan), cmap="Reds", vmin=0, vmax=1.2, interpolation="nearest")
    ax.imshow(np.where(agua_base, 1, np.nan), cmap="Blues", vmin=0, vmax=1.2, interpolation="nearest")
    ax.set_title("max. extent (red) / permanent water (blue)", fontsize=8)
    ax = axs.flat[len(fechas) + 1]
    im = ax.imshow(np.where(persist >= 0, persist, np.nan), cmap="viridis", vmin=0, vmax=48, interpolation="nearest")
    ax.set_title("days under water", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.suptitle(f"{titulo}   blue = permanent water · red = new water", fontsize=10)
    plt.tight_layout()
    plt.savefig(path, dpi=90)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--zona", default="todas", choices=["todas", *ZONAS])
    ap.add_argument("--umbral", type=float, help="umbral fijo HH (dB) en vez de calibrar por track")
    ap.add_argument("--metodo", default="cambio", choices=["cambio", "umbral"], help="detector de agua nueva")
    a = ap.parse_args()
    filas, fechas = [], []
    for zona in (ZONAS if a.zona == "todas" else [a.zona]):
        for tdir in tracks_zona(zona, todos=True):        # los excluidos también: quedan marcados (excluido=True)
            fila, pf = procesar(zona, tdir, a.umbral, a.metodo)
            if fila:
                filas.append(fila)
                fechas += pf
    if filas and a.zona == "todas":
        pd.DataFrame(filas).round(2).to_csv(BASE / "metricas_resumen.csv", index=False)
        pd.DataFrame(fechas).round(2).to_csv(BASE / "metricas_por_fecha.csv", index=False)
        print(f"-> {BASE / 'metricas_resumen.csv'}, {BASE / 'metricas_por_fecha.csv'}")
