"""
Incertidumbre por elección de parámetros del detector de agua nueva (A3 del plan).

  python scripts/sensibilidad.py

Para cada zona/track recalcula el % de agua nueva por fecha y la extensión máxima del evento barriendo
  caída ΔHH ∈ {−2, −2,5, −3, −3,5, −4} dB  ×  techo HH ∈ {−13, −14, −15} dB
(el central es −3 / −14, el de metricas_evento.py). El rango min–max es la banda que muestra la app:
no es un intervalo estadístico, es "cuánto cambia la cifra si el detector fuera razonablemente otro".

Salida: data_nisar/zonas/sensibilidad_por_fecha.csv · sensibilidad_resumen.csv
"""
import itertools

import numpy as np
import pandas as pd

from metricas_evento import (BASE, CAMBIO_DB, Evento, TECHO_DB, agua_permanente, calibrar_umbral, cargar_track,
                             detectar_nueva, es_validado, pasadas_calma, previa_en_grilla, sin_dato_por_fecha, tracks_zona)
from zonas import ZONAS

CAMBIOS = [-2.0, -2.5, -3.0, -3.5, -4.0]
TECHOS = [-13.0, -14.0, -15.0]


def procesar(zona, tdir):
    fechas, hh, _, perfil = cargar_track(tdir)
    fechas = pd.DatetimeIndex(fechas)
    ev = Evento(zona)
    es_base = ev.es_base(fechas, hh)
    es_ev = ev.es_evento(fechas)
    es_previa = ev.es_previa(fechas, tdir.name)                   # antes de la lluvia: agua previa, fuera de la extensión
    sin_dato = sin_dato_por_fecha(zona, perfil, fechas)           # cultivos desde octubre (laboreo), como metricas_evento
    val = es_validado(fechas)
    valid = np.all(np.isfinite(hh), axis=0)
    umbral, _, _ = calibrar_umbral(hh[es_base], valid)
    agua_base = agua_permanente(hh, pasadas_calma(zona, tdir.name, fechas, es_base)[0], umbral, valid)
    med = np.nanmedian(hh[es_base], axis=0)
    nv = valid.sum()
    ha_px = abs(perfil["transform"].a * perfil["transform"].e) / 1e4
    por_fecha, resumen = [], []
    for c, t in itertools.product(CAMBIOS, TECHOS):
        ext = np.zeros(valid.shape, bool)
        previa = np.zeros(valid.shape, bool)
        for i, f in enumerate(fechas):
            m = detectar_nueva(hh[i], med, agua_base, cambio=c, techo=t, validado=val[i]) & valid & ~sin_dato[i]
            por_fecha.append(dict(zona=zona, track=tdir.name, fecha=f.date(), cambio=c, techo=t,
                                  pct_agua_nueva=100 * m.sum() / max((valid & ~sin_dato[i]).sum(), 1)))
            if es_previa[i]:
                previa |= m
            elif es_ev[i]:
                ext |= m
        ext &= ~previa_en_grilla(zona, perfil, previa)   # incluye la previa vista por otros tracks
        resumen.append(dict(zona=zona, track=tdir.name, cambio=c, techo=t, ha_extension_max=ext.sum() * ha_px,
                            pct_extension_max=100 * ext.sum() / nv))
    print(f"== {zona}/{tdir.name}")
    return por_fecha, resumen


def bandas(df, valor, claves):
    central = df[(df.cambio == CAMBIO_DB) & (df.techo == TECHO_DB)].set_index(claves)[valor].rename("central")
    g = df.groupby(claves)[valor]
    return pd.concat([g.min().rename("min"), central, g.max().rename("max")], axis=1).reset_index()


if __name__ == "__main__":
    pf, rs = [], []
    for zona in ZONAS:
        for tdir in tracks_zona(zona):
            a, b = procesar(zona, tdir)
            pf += a
            rs += b
    pf, rs = pd.DataFrame(pf), pd.DataFrame(rs)
    bf = bandas(pf, "pct_agua_nueva", ["zona", "track", "fecha"]).round(2)
    br = bandas(rs, "ha_extension_max", ["zona", "track"]).round(0)
    bf.to_csv(BASE / "sensibilidad_por_fecha.csv", index=False)
    br.to_csv(BASE / "sensibilidad_resumen.csv", index=False)
    print(br.to_string(index=False))
    print(f"-> {BASE / 'sensibilidad_por_fecha.csv'}, {BASE / 'sensibilidad_resumen.csv'}")
