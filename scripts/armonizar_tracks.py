"""
Armonización entre tracks: ¿qué detector de agua nueva da la misma respuesta en dos tracks que pasan con 1 día de diferencia?

  python scripts/armonizar_tracks.py              # evalúa detectores sobre todos los pares casi simultáneos
  python scripts/armonizar_tracks.py --barrido    # además barre parámetros del detector por cambio (lento)

Idea: dos pasadas de tracks distintos separadas por ≤ 1 día ven (casi) la misma agua. Si un detector da máscaras muy
distintas, la diferencia es del detector (geometría, ángulo de incidencia, calibración del track, viento), no del agua.
Medimos la coincidencia con Jaccard = |A∩B| / |A∪B| sobre píxeles válidos en ambos y fuera del agua base de ambos.

Hallazgo (2026-11-14): con umbral absoluto (HH < −17,5 dB) el Jaccard en el pico es 0,2–0,3 y los tracks
descendentes (~21:40 UTC = ~18:30 hora local, atardecer) ven 2–3× más agua que los ascendentes (~09:40 UTC =
~06:30, amanecer). Horarios verificados en los nombres de las escenas. La causa está abierta (ángulo/dirección de
observación de cada track, rocío matinal sobre la vegetación…); el viento no lo explica. Con detección por CAMBIO respecto de la base del mismo píxel y track
(ΔHH < −3 dB y HH < −14 dB, mancha ≥ 10 px) sube a 0,5–0,7: es el detector por defecto de metricas_evento.py.

Salida: data_nisar/zonas/armonizacion_pares.csv · armonizacion_pares.png · (con --barrido) armonizacion_barrido.csv
"""
import argparse
import itertools

import numpy as np
import pandas as pd

from metricas_evento import (BASE, CAMBIO_DB, FIN_BASE, MMU_PX, TECHO_DB, calibrar_umbral, cargar_track,
                             detectar_nueva)
from zonas import ZONAS

MAX_DIAS = 1


def preparar(zona, tdir):
    fechas, hh, _, perfil = cargar_track(tdir)
    fechas = pd.DatetimeIndex(fechas)
    fin_base = pd.Timestamp(ZONAS[zona].get("fin_base", FIN_BASE))
    es_base = np.asarray(fechas < fin_base)
    valid = np.all(np.isfinite(hh), axis=0)
    umbral, _, _ = calibrar_umbral(hh[es_base], valid)
    agua_base = ((hh[es_base] < umbral) & valid).mean(axis=0) > 0.5
    return dict(fechas=fechas, hh=hh, perfil=perfil, umbral=umbral, agua_base=agua_base,
                base_med=np.nanmedian(hh[es_base], axis=0), es_base=es_base)


def pares(datos):
    """Pares (track_a, i, track_b, j) con |Δt| ≤ MAX_DIAS y misma grilla."""
    out = []
    for ta, tb in itertools.combinations(sorted(datos), 2):
        A, B = datos[ta], datos[tb]
        if A["hh"].shape[1:] != B["hh"].shape[1:] or A["perfil"]["transform"] != B["perfil"]["transform"]:
            print(f"   ! {ta} y {tb} no comparten grilla, se saltean")
            continue
        for i, fa in enumerate(A["fechas"]):
            for j, fb in enumerate(B["fechas"]):
                if abs((fa - fb).days) <= MAX_DIAS:
                    out.append((ta, i, tb, j))
    return out


def jaccard(A, B, i, j, **kw):
    v = np.isfinite(A["hh"][i]) & np.isfinite(B["hh"][j]) & ~A["agua_base"] & ~B["agua_base"]
    wa = detectar_nueva(A["hh"][i], A["base_med"], A["agua_base"], umbral=A["umbral"], **kw) & v
    wb = detectar_nueva(B["hh"][j], B["base_med"], B["agua_base"], umbral=B["umbral"], **kw) & v
    union = (wa | wb).sum()
    return ((wa & wb).sum() / union if union else np.nan), 100 * wa[v].mean(), 100 * wb[v].mean()


METODOS = {"umbral": dict(metodo="umbral"),
           "cambio_sin_norm": dict(metodo="cambio", cambio=CAMBIO_DB, techo=TECHO_DB, mmu=MMU_PX, normalizar=False),
           "cambio": dict(metodo="cambio", cambio=CAMBIO_DB, techo=TECHO_DB, mmu=MMU_PX)}


def main(barrido):
    filas, barr = [], []
    for zona in ZONAS:
        tdirs = sorted((BASE / zona).glob("T*_F*"))
        if len(tdirs) < 2:
            continue
        print(f"== {zona}")
        datos = {t.name: preparar(zona, t) for t in tdirs}
        ps = pares(datos)
        for ta, i, tb, j in ps:
            A, B = datos[ta], datos[tb]
            fila = dict(zona=zona, track_a=ta, fecha_a=A["fechas"][i].date(), track_b=tb, fecha_b=B["fechas"][j].date(),
                        fase="base" if A["es_base"][i] else "evento/post")
            for nombre, kw in METODOS.items():
                jj, pa, pb = jaccard(A, B, i, j, **kw)
                fila |= {f"jaccard_{nombre}": jj, f"pct_a_{nombre}": pa, f"pct_b_{nombre}": pb}
            filas.append(fila)
            print(f"   {fila['fecha_a']} {ta} vs {fila['fecha_b']} {tb}: "
                  f"umbral J={fila['jaccard_umbral']:.2f} ({fila['pct_a_umbral']:.1f}/{fila['pct_b_umbral']:.1f} %) · "
                  f"sin norm J={fila['jaccard_cambio_sin_norm']:.2f} · cambio J={fila['jaccard_cambio']:.2f} ({fila['pct_a_cambio']:.1f}/{fila['pct_b_cambio']:.1f} %)")
        if barrido:
            ev = [(ta, i, tb, j) for ta, i, tb, j in ps if not datos[ta]["es_base"][i]]
            for c, t, m in itertools.product([-2, -2.5, -3, -3.5, -4], [-13, -14, -15, -16], [1, 10, 25]):
                js = [jaccard(datos[ta], datos[tb], i, j, metodo="cambio", cambio=c, techo=t, mmu=m)[0]
                      for ta, i, tb, j in ev]
                barr.append(dict(zona=zona, cambio=c, techo=t, mmu=m, jaccard_medio=np.nanmean(js)))

    df = pd.DataFrame(filas).round(3)
    df.to_csv(BASE / "armonizacion_pares.csv", index=False)
    ev = df[df.fase != "base"]
    # con muy poca agua (< 0,5 % en ambos) el Jaccard es ruido: se reporta aparte
    con_agua = ev[(ev[["pct_a_cambio", "pct_b_cambio"]].max(axis=1) >= 0.5)]
    print("\nJaccard medio en pares del evento/post con agua:")
    print(con_agua.groupby("zona")[["jaccard_umbral", "jaccard_cambio_sin_norm", "jaccard_cambio"]].mean().round(2).to_string())
    grafico(con_agua, BASE / "armonizacion_pares.png")
    if barr:
        b = pd.DataFrame(barr)
        b.round(3).to_csv(BASE / "armonizacion_barrido.csv", index=False)
        print(b.groupby(["cambio", "techo", "mmu"]).jaccard_medio.mean().sort_values(ascending=False).head(8))
    print(f"-> {BASE / 'armonizacion_pares.csv'}")


def grafico(df, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    df = df.sort_values(["zona", "fecha_a"]).reset_index(drop=True)
    etiquetas = [f"{r.zona[:10]}\n{str(r.fecha_a)[5:]}/{str(r.fecha_b)[5:]}" for r in df.itertuples()]
    x = np.arange(len(df))
    fig, ax = plt.subplots(figsize=(max(8, 0.55 * len(df)), 3.6))
    ax.bar(x - 0.2, df.jaccard_umbral, 0.38, color="#c9c9c9", label="absolute threshold (HH < −17.5 dB)")
    ax.bar(x + 0.2, df.jaccard_cambio, 0.38, color="#2a78d6", label="change vs. own baseline (ΔHH < −3 dB)")
    ax.set_xticks(x, etiquetas, fontsize=6, rotation=90)
    ax.set_ylabel("Jaccard (same-water agreement)")
    ax.set_ylim(0, 1)
    ax.axhline(0.6, color="k", lw=0.5, ls=":")
    ax.legend(fontsize=7, frameon=False)
    ax.set_title("Two tracks, ≤ 1 day apart: do they see the same new water?", fontsize=9)
    plt.tight_layout()
    plt.savefig(path, dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--barrido", action="store_true")
    main(ap.parse_args().barrido)
