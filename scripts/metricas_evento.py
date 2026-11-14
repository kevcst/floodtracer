"""
Métricas de la crecida de agosto 2026 por zona y track ("¿Cuánto tiempo se queda el agua?").

  python scripts/metricas_evento.py                       # todas las zonas/tracks
  python scripts/metricas_evento.py --zona durazno
  python scripts/metricas_evento.py --zona mercedes --umbral -18   # forzar umbral fijo (agua base)
  python scripts/metricas_evento.py --metodo umbral              # detector viejo (HH < umbral), sólo para comparar

Entrada : data_nisar/zonas/{zona}/T{track}{dir}_F{frame}/{fecha}_{HH|HV}.tif  (gamma0 lineal, misma grilla por track)
Salida  : .../T*/metricas/
            agua_base.tif         1 = agua "normal" (mayoría de fechas jun–jul)
            extension_max.tif     1 = agua nueva en alguna pasada del evento (10/8–10/9)
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
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from scipy import ndimage as ndi

from nisar_eda_uruguay import OUT
from zonas import ZONAS

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
INICIO_LLUVIA = pd.Timestamp("2026-08-15")   # el agua del evento no pudo llegar antes (cota de persistencia)


def filtrar_mmu(m, mmu=MMU_PX):
    if mmu <= 1 or not m.any():
        return m
    lab, n = ndi.label(m)
    tam = ndi.sum(m, lab, np.arange(1, n + 1))
    return np.r_[False, tam >= mmu][lab]


def detectar_nueva(hh, hh_base_med, agua_base, metodo="cambio", umbral=UMBRAL_DEFECTO,
                   cambio=CAMBIO_DB, techo=TECHO_DB, mmu=MMU_PX, normalizar=True):
    """Máscara de agua nueva para una pasada (hh en dB, 2D)."""
    if metodo == "umbral":
        return (hh < umbral) & ~agua_base
    d = hh - hh_base_med
    # normalización por escena: corrige corrimientos de toda la pasada (calibración, suelo más seco/húmedo).
    # La mediana es robusta mientras el agua nueva ocupe < 50 % del recorte.
    tierra = np.isfinite(d) & ~agua_base
    off = float(np.nanmedian(d[tierra])) if normalizar and tierra.any() else 0.0
    m = (d - off < cambio) & (hh < techo) & ~agua_base
    return filtrar_mmu(m, mmu)


def intervalos_persistencia(fechas, nueva, ok, ext_max, es_evento, retiro_i, primera_i):
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
    t_lluvia = np.datetime64(INICIO_LLUVIA.date(), "D").astype("int64")
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
    x[(x <= 0) | ~np.isfinite(x)] = np.nan
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
    return fechas, hh, hv, perfil


def calibrar_umbral(hh_base, valid):
    """Umbral por track: 30 % del camino entre agua permanente y tierra (≈ −18 dB en 53D).
    Si no hay suficiente agua permanente en el recorte, usa el umbral por defecto."""
    agua = valid & np.all(hh_base < -20, axis=0)
    tierra = valid & np.all(hh_base > -14, axis=0)
    if agua.sum() < 200 or tierra.sum() < 200:
        return UMBRAL_DEFECTO, None, None
    w, t = float(np.median(hh_base[:, agua])), float(np.median(hh_base[:, tierra]))
    # tope −17,5 dB: con −16 entran potreros lisos/mojados (Mercedes oscilaba 6–18 % según la lluvia del día)
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
    fin_base = pd.Timestamp(ZONAS[zona].get("fin_base", FIN_BASE))
    es_base = np.asarray(fechas < fin_base)
    es_evento = np.asarray((fechas >= EVENTO[0]) & (fechas <= EVENTO[1]))
    if es_base.sum() == 0 or es_evento.sum() == 0:
        print("   ! sin fechas de base o de evento, se saltea")
        return None, []
    valid = np.all(np.isfinite(hh), axis=0)

    if umbral_forzado is not None:
        umbral, w, t = umbral_forzado, None, None
    else:
        umbral, w, t = calibrar_umbral(hh[es_base], valid)
    W_abs = (hh < umbral) & valid                               # agua abierta por fecha (umbral absoluto)
    agua_base = W_abs[es_base].mean(axis=0) > 0.5               # agua "normal": mayoría de las fechas base
    hh_base_med = np.nanmedian(hh[es_base], axis=0)
    ok = np.isfinite(hh)
    nueva = np.stack([detectar_nueva(hh[i], hh_base_med, agua_base, metodo, umbral) & ok[i] & valid
                      for i in range(len(fechas))])            # agua nueva por fecha
    W = (W_abs & agua_base) | nueva                             # agua total = base + nueva

    ext_max = nueva[es_evento].any(axis=0)
    doy = np.asarray(fechas.day_of_year)
    idx_ev = np.where(es_evento)[0]

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
    pmin, pmax, persist = intervalos_persistencia(fechas, nueva, ok, ext_max, es_evento, retiro_i, primera_i)

    # agua bajo vegetación: HH sube (doble rebote) sin pasar a agua abierta, en zonas con vegetación (HV alto)
    delta = np.nanmean(hh[es_evento], axis=0) - np.nanmean(hh[es_base], axis=0)
    hv_base = np.nanmean(hv[es_base], axis=0) if np.isfinite(hv[es_base]).any() else np.full(valid.shape, np.nan)
    veg = valid & (delta > DELTA_VEG_DB) & ~W[es_evento].any(axis=0) & ~agua_base & (hv_base > -20)

    out = tdir / "metricas"
    out.mkdir(exist_ok=True)
    guardar(out / "agua_base.tif", agua_base, perfil, "uint8")
    guardar(out / "extension_max.tif", ext_max, perfil, "uint8")
    guardar(out / "primera_fecha.tif", primera, perfil, "int16", 0)
    guardar(out / "fecha_retiro.tif", retiro, perfil, "int16", 0)
    guardar(out / "persistencia_dias.tif", persist, perfil, "int16", -1)
    guardar(out / "persistencia_min.tif", pmin, perfil, "int16", -1)
    guardar(out / "persistencia_max.tif", pmax, perfil, "int16", -1)
    guardar(out / "delta_hh_db.tif", np.where(valid, delta, np.nan), perfil, "float32", np.nan)
    guardar(out / "veg_inundada.tif", veg, perfil, "uint8")
    # pila de agua nueva por fecha (0/1, 255 = sin dato) para combinar tracks a nivel de máscara (combinar_tracks.py)
    p = perfil.copy()
    p.update(driver="GTiff", dtype="uint8", count=len(fechas), compress="deflate", nodata=255)
    for k in ("blockxsize", "blockysize", "tiled", "interleave"):
        p.pop(k, None)
    with rasterio.open(out / "agua_nueva_por_fecha.tif", "w", **p) as dst:
        for i, f in enumerate(fechas):
            dst.write(np.where(np.isfinite(hh[i]), nueva[i], 255).astype("uint8"), i + 1)
            dst.set_band_description(i + 1, str(f.date()))

    nv = valid.sum()
    # monte / monte ribereño: dispersión de volumen alta en la base. Si se inunda, HH y HH−HV suben (doble rebote).
    hh_base = np.nanmean(hh[es_base], axis=0)
    bosque = valid & (hh_base > -7) & (hv_base > -14)
    por_fecha = [dict(zona=zona, track=tdir.name, fecha=f.date(), fase="base" if b else ("evento" if e else "post"),
                      pct_agua=100 * W[i].sum() / nv, pct_agua_nueva=100 * nueva[i].sum() / nv,
                      hh_bosque_db=float(np.median(hh[i][bosque])) if bosque.any() else np.nan,
                      hh_hv_bosque_db=float(np.nanmedian((hh[i] - hv[i])[bosque])) if bosque.any() else np.nan)
                 for i, (f, b, e) in enumerate(zip(fechas, es_base, es_evento))]
    pers_validos = persist[ext_max & ~sigue]
    fila = dict(zona=zona, track=tdir.name, metodo=metodo, n_fechas=len(fechas), n_base=int(es_base.sum()),
                fechas_evento=" ".join(str(f.date())[5:] for f in fechas[es_evento]),
                umbral_db=round(umbral, 2), agua_perm_db=w and round(w, 1), tierra_db=t and round(t, 1),
                pct_agua_base=100 * agua_base.sum() / nv, pct_extension_max=100 * ext_max.sum() / nv,
                ha_extension_max=ext_max.sum() * abs(perfil["transform"].a * perfil["transform"].e) / 1e4,
                persistencia_mediana_dias=float(np.median(pers_validos)) if pers_validos.size else np.nan,
                persistencia_min_mediana=float(np.median(pmin[ext_max & ~sigue])) if pers_validos.size else np.nan,
                persistencia_max_mediana=float(np.median(pmax[ext_max & ~sigue])) if pers_validos.size else np.nan,
                pct_sigue_con_agua=100 * sigue.sum() / max(ext_max.sum(), 1),
                pct_veg_inundada=100 * veg.sum() / nv, pct_bosque=100 * bosque.sum() / nv,
                delta_hh_bosque_db=float(np.median(delta[bosque])) if bosque.any() else np.nan)
    print("   " + json.dumps({k: (round(v, 2) if isinstance(v, float) else v) for k, v in fila.items()
                              if k not in ("zona", "track")}, ensure_ascii=False))
    panel(out / "mapas_agua.png", f"{zona} {tdir.name} — {metodo}, agua base < {umbral:.1f} dB", fechas, hh, W, agua_base, es_base,
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
        fase = "base" if es_base[i] else ("EVENTO" if es_evento[i] else "post")
        ax.set_title(f"{f.date()} ({fase})\nnueva {100 * (W[i] & ~agua_base).mean():.1f} %", fontsize=8)
    ax = axs.flat[len(fechas)]
    ax.imshow(np.where(ext_max, 1, np.nan), cmap="Reds", vmin=0, vmax=1.2, interpolation="nearest")
    ax.imshow(np.where(agua_base, 1, np.nan), cmap="Blues", vmin=0, vmax=1.2, interpolation="nearest")
    ax.set_title("extensión máx. (rojo) / base (azul)", fontsize=8)
    ax = axs.flat[len(fechas) + 1]
    im = ax.imshow(np.where(persist >= 0, persist, np.nan), cmap="viridis", vmin=0, vmax=48, interpolation="nearest")
    ax.set_title("persistencia (días)", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.suptitle(f"{titulo}   azul = agua base · rojo = agua nueva", fontsize=10)
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
        for tdir in sorted((BASE / zona).glob("T*_F*")):
            fila, pf = procesar(zona, tdir, a.umbral, a.metodo)
            if fila:
                filas.append(fila)
                fechas += pf
    if filas and a.zona == "todas":
        pd.DataFrame(filas).round(2).to_csv(BASE / "metricas_resumen.csv", index=False)
        pd.DataFrame(fechas).round(2).to_csv(BASE / "metricas_por_fecha.csv", index=False)
        print(f"-> {BASE / 'metricas_resumen.csv'}, {BASE / 'metricas_por_fecha.csv'}")
