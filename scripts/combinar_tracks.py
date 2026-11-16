"""
Persistencia del agua combinando tracks de una zona a nivel de MÁSCARA (regla 2 de CLAUDE.md):
cada track usa su propio umbral y su propia línea de base (metricas_evento.py); acá sólo se juntan
las máscaras de agua nueva 0/1 en una grilla común → revisita ~6 días en vez de 12.

  python scripts/metricas_evento.py      # primero: genera metricas/agua_nueva_por_fecha.tif
  python scripts/combinar_tracks.py [--zona treinta_y_tres]

Reglas por píxel sobre la secuencia de observaciones (todas las pasadas, todos los tracks, por fecha):
  - agua previa = mojada en alguna obs. antes de la lluvia (10/8 al 15/8 09:29 UTC, Evento.previa_hasta): aparte, fuera de todo lo que sigue
  - primera  = primera observación de la tormenta (15/8–10/9) con agua nueva
  - retiro   = primera observación seca posterior que es seguida por OTRA observación seca (o es la última):
               evita que una sola pasada de otra geometría que "no ve" el agua cuente como retiro
  - persistencia = intervalo [última obs mojada − primera, retiro − obs previa (≥ 15/8)]; se guarda el punto medio
                 y las cotas (persistencia_min/max.tif); "sigue" si nunca se cumple el retiro.
                 Las medianas del CSV se calculan sobre extension_confirmada (≥ 2 obs.), no sobre extension_max
Grilla común: la del track con más fechas (vecino más cercano).

Salida: data_nisar/zonas/{zona}/combinado/{extension_max,extension_confirmada,n_mojado,persistencia_min,persistencia_max,primera_fecha,fecha_retiro,persistencia_dias,n_obs}.tif
        data_nisar/zonas/combinado_resumen.csv · combinado_por_fecha.csv · combinado_persistencia.png
"""
import argparse
import warnings

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import Resampling, reproject

from metricas_evento import BASE, Evento, guardar, intervalos_persistencia, tracks_zona
from zonas import ZONAS

warnings.filterwarnings("ignore", category=RuntimeWarning)


def leer_pila(path):
    with rasterio.open(path) as r:
        return r.read(), [pd.Timestamp(d) for d in r.descriptions], r.profile


def procesar(zona):
    pilas = [t / "metricas" / "agua_nueva_por_fecha.tif" for t in tracks_zona(zona) if (t / "metricas" / "agua_nueva_por_fecha.tif").exists()]
    if len(pilas) < 2:
        print(f"== {zona}: {len(pilas)} track(s), no hay nada que combinar")
        return None, None
    datos = {p.parents[1].name: leer_pila(p) for p in pilas}
    ref = max(datos, key=lambda k: len(datos[k][1]))
    perfil = datos[ref][2]
    H, W_ = perfil["height"], perfil["width"]

    obs = []                                                   # (fecha, track, máscara en grilla ref)
    for track, (arr, fechas, prof) in datos.items():
        for i, f in enumerate(fechas):
            dst = np.full((H, W_), 255, "uint8")
            reproject(arr[i], dst, src_transform=prof["transform"], src_crs=prof["crs"], src_nodata=255,
                      dst_transform=perfil["transform"], dst_crs=perfil["crs"], dst_nodata=255,
                      resampling=Resampling.nearest)
            obs.append((f, track, dst))
    obs.sort(key=lambda o: (o[0], o[1]))
    fechas = pd.DatetimeIndex([o[0] for o in obs])
    M = np.stack([o[2] for o in obs])                          # 0 seco, 1 agua nueva, 255 sin dato
    ok = M != 255
    agua = M == 1
    ev = Evento(zona)
    es_evento = ev.es_evento(fechas)
    doy = np.asarray(fechas.day_of_year)

    # agua previa: mojada en alguna observación antes de la lluvia (por hora de pasada) → aparte, fuera del evento
    es_previa = ev.es_previa(fechas, [o[1] for o in obs])      # por hora de pasada (31A del 15/8 = antes de la lluvia)
    agua_previa = (agua & es_previa[:, None, None]).any(axis=0)
    es_evento = es_evento & ~es_previa                          # desde acá, "evento" = tormenta (15/8–10/9)
    ext_max = (agua & es_evento[:, None, None]).any(axis=0) & ~agua_previa
    # extensión confirmada: agua nueva en ≥ 2 observaciones (de cualquier track) entre el 15/8 y el 10/9.
    # Descarta lo que sólo ve una pasada (charco efímero o falsa alarma de un track).
    n_mojado = (agua & ok)[:, :, :].sum(axis=0)
    ext_conf = ext_max & ((agua & es_evento[:, None, None]).sum(axis=0) >= 2)
    primera_i = np.full((H, W_), -1, "int16")
    for i in np.where(es_evento)[0][::-1]:
        primera_i[agua[i]] = i

    # retiro: primera obs seca (con dato) posterior a la primera detección, confirmada por la siguiente obs con dato
    retiro_i = np.full((H, W_), -1, "int16")
    candidato = np.full((H, W_), -1, "int16")                  # obs seca pendiente de confirmar
    pendiente = ext_max.copy()
    for i in range(len(obs)):
        despues = pendiente & ok[i] & (primera_i >= 0) & (primera_i < i)
        seco = despues & ~agua[i]
        mojado = despues & agua[i]
        confirmar = seco & (candidato >= 0)
        retiro_i[confirmar] = candidato[confirmar]
        pendiente &= ~confirmar
        nuevo = seco & (candidato < 0)
        candidato[nuevo] = i
        candidato[mojado] = -1                                  # volvió a verse agua: se descarta el candidato
    ultimo = pendiente & (candidato >= 0)                      # seco en la última obs con dato: se acepta
    retiro_i[ultimo] = candidato[ultimo]
    sigue = ext_max & (retiro_i < 0)

    primera = np.where(ext_max, doy[np.maximum(primera_i, 0)], 0)
    retiro = np.where(ext_max & ~sigue, doy[np.maximum(retiro_i, 0)], 0)
    retiro[sigue] = 999
    pmin, pmax, persist = intervalos_persistencia(fechas, agua, ok, ext_max, es_evento, retiro_i, primera_i, ev.inicio)
    n_obs = ok.sum(axis=0)

    out = BASE / zona / "combinado"
    out.mkdir(exist_ok=True)
    guardar(out / "extension_max.tif", ext_max, perfil, "uint8")
    guardar(out / "primera_fecha.tif", primera, perfil, "int16", 0)
    guardar(out / "fecha_retiro.tif", retiro, perfil, "int16", 0)
    guardar(out / "persistencia_dias.tif", persist, perfil, "int16", -1)
    guardar(out / "persistencia_min.tif", pmin, perfil, "int16", -1)
    guardar(out / "persistencia_max.tif", pmax, perfil, "int16", -1)
    guardar(out / "n_obs.tif", n_obs, perfil, "uint8")
    guardar(out / "extension_confirmada.tif", ext_conf, perfil, "uint8")
    guardar(out / "agua_previa.tif", agua_previa, perfil, "uint8")
    guardar(out / "n_mojado.tif", np.minimum(n_mojado, 254), perfil, "uint8")

    cubierto = ok.any(axis=0)
    nv = cubierto.sum()
    # estadísticas sobre la extensión CONFIRMADA (la cifra principal): los píxeles vistos mojados una sola vez tienen
    # persistencia_min = 0 por construcción y empujaban la mediana a "media revisita" (rasters: siguen sobre ext_max)
    pv = persist[ext_conf & ~sigue]
    fila = dict(zona=zona, evento=ev.clave, tracks=" ".join(datos), grilla_ref=ref, n_obs=len(obs),
                obs_evento=" ".join(f"{f.strftime('%m-%d')}({t[1:5]})" for f, t, _ in obs if ev.ventana[0] <= f <= ev.ventana[1]),
                pct_extension_max=100 * ext_max.sum() / nv,
                ha_extension_max=ext_max.sum() * abs(perfil["transform"].a * perfil["transform"].e) / 1e4,
                ha_agua_previa=agua_previa.sum() * abs(perfil["transform"].a * perfil["transform"].e) / 1e4,
                ha_extension_confirmada=ext_conf.sum() * abs(perfil["transform"].a * perfil["transform"].e) / 1e4,
                pct_extension_confirmada=100 * ext_conf.sum() / nv,
                persistencia_mediana_dias=float(np.median(pv)) if pv.size else np.nan,
                persistencia_min_mediana=float(np.median(pmin[ext_conf & ~sigue])) if pv.size else np.nan,
                persistencia_max_mediana=float(np.median(pmax[ext_conf & ~sigue])) if pv.size else np.nan,
                persistencia_p90_dias=float(np.percentile(pv, 90)) if pv.size else np.nan,
                pct_sigue_con_agua=100 * (sigue & ext_conf).sum() / max(ext_conf.sum(), 1))
    print(f"== {zona}: " + ", ".join(f"{k}={round(v, 1) if isinstance(v, float) else v}"
                                     for k, v in fila.items() if k != "zona"))
    por_fecha = pd.DataFrame([dict(zona=zona, fecha=f.date(), track=t,
                                   pct_agua_nueva=100 * agua[i][ok[i]].mean() if ok[i].any() else np.nan)
                              for i, (f, t, _) in enumerate(obs)])
    hist = pd.Series(pv).value_counts().sort_index()
    return fila, (por_fecha, hist)


def grafico(extra, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(len(extra), 2, figsize=(13, 2.6 * len(extra)), squeeze=False)
    for (ax1, ax2), (zona, (pf, hist)) in zip(axs, extra.items()):
        for t, g in pf.groupby("track"):
            ax1.plot(pd.to_datetime(g.fecha), g.pct_agua_nueva, "o", ms=4, label=t)
        g = pf.sort_values("fecha")
        ax1.plot(pd.to_datetime(g.fecha), g.pct_agua_nueva, "-", color="k", lw=0.6)
        ax1.axvspan(*Evento(zona).lluvia, color="tab:red", alpha=0.15)
        ax1.set_title(f"{zona}: % new water per pass (all tracks)", fontsize=9)
        ax1.legend(fontsize=7)
        ax2.bar(hist.index, 100 * hist.values / hist.sum(), width=1.5)
        ax2.set_title(f"{zona}: days under water of the new water", fontsize=9)
        ax2.set_ylabel("% of the flooded area", fontsize=8)
        ax2.set_xlabel("days under water", fontsize=8)
    plt.tight_layout()
    plt.savefig(path, dpi=100)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--zona", default="todas", choices=["todas", *ZONAS])
    a = ap.parse_args()
    filas, extra = [], {}
    for z in (ZONAS if a.zona == "todas" else [a.zona]):
        fila, ex = procesar(z)
        if fila:
            filas.append(fila)
            extra[z] = ex
    if filas and a.zona == "todas":           # los CSV globales sólo con todas las zonas (los usa exportar_app.py)
        pd.DataFrame(filas).round(2).to_csv(BASE / "combinado_resumen.csv", index=False)
        pd.concat([e[0] for e in extra.values()]).round(2).to_csv(BASE / "combinado_por_fecha.csv", index=False)
        grafico(extra, BASE / "combinado_persistencia.png")
        print(f"-> {BASE / 'combinado_resumen.csv'}, {BASE / 'combinado_persistencia.png'}")
