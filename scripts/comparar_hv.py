"""
¿Sumar HV como condición extra mejora el detector de agua nueva? (experimento; NO cambia el detector de la app)
  python scripts/comparar_hv.py                # todas las zonas (usa la caché S1 de validar_s1.py)
  python scripts/comparar_hv.py --zona treinta_y_tres
  python scripts/comparar_hv.py --figuras      # + data_nisar/zonas/comparacion_hv/*.png (una por zona + resumen)

Variantes (todas = detector por cambio de HH de metricas_evento.py + una condición sobre HV; sin HV → sólo HH):
  hh            ΔHH < −3 dB y HH < −14 dB (el de la app)
  hv_cae15      + ΔHV < −1,5 dB (HV también baja respecto de su base)
  hv_cae3       + ΔHV < −3 dB
  hv_oscuro     + HV < −22 dB (HV absoluto oscuro)
Métricas, en las mismas pasadas que armonizar_tracks.py y validar_s1.py:
  - Jaccard entre tracks a ≤ 1 día (pares del evento/post con ≥ 0,5 % de agua)
  - F1 / precisión / exhaustividad contra Sentinel-1 (referencia estricta), ventana del evento + 12 días
Salida: data_nisar/zonas/comparacion_hv_pares.csv · comparacion_hv_s1.csv (no pisa los CSV del pipeline)
"""
import argparse
import warnings

import numpy as np
import pandas as pd

import validar_s1 as vs
from armonizar_tracks import pares
from metricas_evento import (BASE, Evento, calibrar_umbral, cargar_track, detectar_nueva, es_validado, filtrar_mmu)
from zonas import ZONAS

warnings.filterwarnings("ignore", category=RuntimeWarning)
FIG = BASE / "comparacion_hv"
VARIANTES = {"hh": {}, "hv_cae15": dict(hv_cambio=-1.5), "hv_cae3": dict(hv_cambio=-3.0),
             "hv_oscuro": dict(hv_techo=-22.0)}


def preparar(zona, tdir):
    fechas, hh, hv, perfil = cargar_track(tdir)
    fechas = pd.DatetimeIndex(fechas)
    ev = Evento(zona)
    es_base = ev.es_base(fechas, hh)
    valid = np.all(np.isfinite(hh), axis=0)
    umbral, _, _ = calibrar_umbral(hh[es_base], valid)
    tiene_hv = np.array([np.isfinite(hv[i]).any() for i in range(len(fechas))])
    bh = es_base & tiene_hv
    return dict(fechas=fechas, hh=hh, hv=hv, perfil=perfil, valid=valid, ev=ev, es_base=es_base,
                agua_base=((hh[es_base] < umbral) & valid).mean(axis=0) > 0.5, tiene_hv=tiene_hv,
                base_med=np.nanmedian(hh[es_base], axis=0),
                hv_med=np.nanmedian(hv[bh], axis=0) if bh.any() else None)


def mascara(D, i, var):
    return detectar_nueva(D["hh"][i], D["base_med"], D["agua_base"], validado=es_validado([D["fechas"][i]])[0],
                          hv=D["hv"][i], hv_base_med=D["hv_med"], **VARIANTES[var])


def jaccards(zona, datos):
    filas = []
    for ta, i, tb, j in pares(datos):
        A, B = datos[ta], datos[tb]
        if A["es_base"][i]:
            continue
        v = np.isfinite(A["hh"][i]) & np.isfinite(B["hh"][j]) & ~A["agua_base"] & ~B["agua_base"]
        fila = dict(zona=zona, track_a=ta, fecha_a=A["fechas"][i].date(), track_b=tb, fecha_b=B["fechas"][j].date(),
                    hv_ambos=bool(A["tiene_hv"][i] and B["tiene_hv"][j]))
        for var in VARIANTES:
            wa, wb = mascara(A, i, var) & v, mascara(B, j, var) & v
            u = (wa | wb).sum()
            fila |= {f"jaccard_{var}": (wa & wb).sum() / u if u else np.nan,
                     f"pct_{var}": 100 * max(wa[v].mean(), wb[v].mean())}
        filas.append(fila)
    return filas


def contra_s1(zona, tdir, D, s1, mapas=None):
    """Misma selección de pasada S1 y misma máscara S1 que validar_s1.validar_track (lee su caché)."""
    ev, fechas, perfil = D["ev"], D["fechas"], D["perfil"]
    cache = vs.CACHE / zona / tdir.name
    s1 = s1[s1.cov_fecha >= 0.2]
    filas, bases = [], {}
    for i, f in enumerate(fechas):
        if not (ev.ventana[0] <= f <= ev.ventana[1] + vs.VAL_EXTRA):
            continue
        cand = s1[(s1.fecha - f).abs().dt.days <= vs.MAX_DT].copy()
        if cand.empty:
            continue
        cand = cand.assign(adt=(cand.fecha - f).dt.days.abs()).sort_values(["adt", "cov_fecha"], ascending=[True, False])
        fe, orb = cand.iloc[0].fecha, cand.iloc[0].orbita
        if orb not in bases:
            bs = s1[(s1.orbita == orb) & (s1.fecha < ev.fin_base)]
            if bs.fecha.nunique() < 2:
                bases[orb] = None
            else:
                pila = np.stack([vs.db(vs.recorte(g, perfil, cache / f"{d.date()}_o{orb}_VV.tif"))
                                 for d, g in bs.groupby("fecha")])
                bases[orb] = (np.nanmedian(pila, axis=0), (pila < vs.S1_AGUA).mean(axis=0) > 0.5)
        if bases[orb] is None:
            continue
        vv_med, s1_base = bases[orb]
        vv = vs.db(vs.recorte(s1[(s1.fecha == fe) & (s1.orbita == orb)], perfil, cache / f"{fe.date()}_o{orb}_VV.tif"))
        d = vv - vv_med
        ok = np.isfinite(d)
        off = float(np.nanmedian(d[ok & ~s1_base])) if ok.any() else 0.0
        s = filtrar_mmu((d - off < vs.S1_CAMBIO) & (vv < vs.S1_TECHO) & ~s1_base & ok)
        v = D["valid"] & ok & np.isfinite(D["hh"][i]) & ~D["agua_base"] & ~s1_base
        s &= v
        fila = dict(zona=zona, track=tdir.name, fecha_nisar=f.date(), fecha_s1=fe.date(), hv=bool(D["tiene_hv"][i]),
                    pct_s1=100 * s[v].mean())
        for var in VARIANTES:
            n = mascara(D, i, var) & v
            tp, fp, fn = (n & s).sum(), (n & ~s).sum(), (~n & s).sum()
            fila |= {f"pct_{var}": 100 * n[v].mean(), f"f1_{var}": 2 * tp / max(2 * tp + fp + fn, 1),
                     f"precision_{var}": tp / max(tp + fp, 1), f"recall_{var}": tp / max(tp + fn, 1)}
        filas.append(fila)
        if mapas is not None and fila["hv"]:
            mapas.append(dict(fila=fila, hh=D["hh"][i], hv=D["hv"][i], dhh=D["hh"][i] - D["base_med"],
                              dhv=D["hv"][i] - D["hv_med"] if D["hv_med"] is not None else None, vv=vv, s1=s,
                              base=D["agua_base"] | s1_base, masks={var: mascara(D, i, var) & v for var in VARIANTES}))
    return filas


VENTANA_FIG = 600   # px de 20 m = 12 km
ETIQUETAS = {"hh": "HH only (current)", "hv_cae15": "+ ΔHV < −1.5 dB", "hv_cae3": "+ ΔHV < −3 dB",
             "hv_oscuro": "+ HV < −22 dB"}


def ventana(m):
    """Recorte de VENTANA_FIG px centrado donde más difieren las variantes (y hay agua S1)."""
    from scipy import ndimage as ndi

    dif = np.zeros(m["s1"].shape, "float32")
    for var in VARIANTES:
        dif += m["masks"][var] != m["masks"]["hh"]
    dif += 0.3 * (m["s1"] | m["masks"]["hh"])
    w = min(VENTANA_FIG, *dif.shape)
    sc = ndi.uniform_filter(dif, w)
    r, c = np.unravel_index(np.argmax(sc), sc.shape)
    r0 = int(np.clip(r - w // 2, 0, dif.shape[0] - w))
    c0 = int(np.clip(c - w // 2, 0, dif.shape[1] - w))
    return np.s_[r0:r0 + w, c0:c0 + w]


def figura(m, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    f, sl = m["fila"], ventana(m)
    fig, axs = plt.subplots(2, 5, figsize=(17, 8))
    for ax in axs.flat:
        ax.axis("off")
    gris = dict(cmap="gray", vmin=-25, vmax=-3, interpolation="nearest")
    dif = dict(cmap="RdBu", vmin=-8, vmax=8, interpolation="nearest")
    axs[0, 0].imshow(m["hh"][sl], **gris)
    axs[0, 0].set_title(f"NISAR HH {f['fecha_nisar']} (dB)", fontsize=9)
    axs[0, 1].imshow(m["hv"][sl], cmap="gray", vmin=-32, vmax=-10, interpolation="nearest")
    axs[0, 1].set_title("NISAR HV (dB)", fontsize=9)
    im = axs[0, 2].imshow(m["dhh"][sl], **dif)
    axs[0, 2].set_title("ΔHH vs own baseline (red = drop)", fontsize=9)
    if m["dhv"] is not None:
        axs[0, 3].imshow(m["dhv"][sl], **dif)
    axs[0, 3].set_title("ΔHV vs own baseline", fontsize=9)
    axs[0, 4].imshow(m["vv"][sl], **gris)
    axs[0, 4].set_title(f"Sentinel-1 VV {f['fecha_s1']} (reference)", fontsize=9)
    cax = axs[1, 4].inset_axes([0.05, 0.3, 0.85, 0.05])
    fig.colorbar(im, cax=cax, orientation="horizontal", label="ΔHH / ΔHV (dB)")
    s = m["s1"][sl]
    for ax, var in zip(axs[1, :4], VARIANTES):
        n = m["masks"][var][sl]
        rgb = np.ones(n.shape + (3,))
        rgb[m["base"][sl]] = (0.80, 0.85, 0.92)
        rgb[n & s] = (0.10, 0.35, 0.75)
        rgb[n & ~s] = (0.92, 0.41, 0.20)
        rgb[~n & s] = (0.10, 0.69, 0.48)
        ax.imshow(rgb, interpolation="nearest")
        ax.set_title(f"{ETIQUETAS[var]}\nF1 {f[f'f1_{var}']:.2f} · prec {f[f'precision_{var}']:.2f} · "
                     f"recall {f[f'recall_{var}']:.2f} · {f[f'pct_{var}']:.1f} % (whole scene)", fontsize=8)
    leyenda = axs[1, 4]
    for k, (col, txt) in enumerate([((0.10, 0.35, 0.75), "NISAR and S1"), ((0.92, 0.41, 0.20), "NISAR only"),
                                    ((0.10, 0.69, 0.48), "S1 only"), ((0.80, 0.85, 0.92), "permanent water")]):
        leyenda.add_patch(plt.Rectangle((0.05, 0.8 - 0.15 * k), 0.12, 0.1, color=col, transform=leyenda.transAxes))
        leyenda.text(0.22, 0.85 - 0.15 * k, txt, transform=leyenda.transAxes, va="center", fontsize=9)
    leyenda.text(0.05, 0.12, f"Window 12 × 12 km where the variants\ndiffer most. S1 new water: "
                 f"{f['pct_s1']:.1f} % of scene.", transform=leyenda.transAxes, fontsize=8, color="0.3")
    fig.suptitle(f"{f['zona']} · {f['track']} · does adding HV improve new-water detection?", fontsize=11)
    plt.tight_layout()
    plt.savefig(path, dpi=100)
    plt.close(fig)


def resumen(ds, dj, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cols = list(VARIANTES)
    met = {"Jaccard between tracks": [dj[dj.pct_hh >= 0.5][f"jaccard_{v}"].mean() for v in cols],
           "F1 vs S1": [ds[f"f1_{v}"].mean() for v in cols],
           "Precision vs S1": [ds[f"precision_{v}"].mean() for v in cols],
           "Recall vs S1": [ds[f"recall_{v}"].mean() for v in cols]}
    fig, axs = plt.subplots(1, 4, figsize=(14, 3.4), sharey=True)
    colores = ["#2a78d6", "#9bbbe0", "#c9c9c9", "#7a7a7a"]
    for ax, (t, vals) in zip(axs, met.items()):
        ax.bar(range(len(cols)), vals, color=colores)
        for x, y in enumerate(vals):
            ax.text(x, y + 0.01, f"{y:.2f}", ha="center", fontsize=8)
        ax.set_xticks(range(len(cols)), [ETIQUETAS[v] for v in cols], rotation=30, ha="right", fontsize=8)
        ax.set_title(t, fontsize=9)
        ax.set_ylim(0, 0.8)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("HV as an extra condition: mean over all areas and passes", fontsize=10)
    plt.tight_layout()
    plt.savefig(path, dpi=110)
    plt.close(fig)


def main(zona_arg, figuras=False):
    fj, fs = [], []
    for zona in (ZONAS if zona_arg == "todas" else [zona_arg]):
        tdirs = sorted((BASE / zona).glob("T*_F*"))
        if not tdirs:
            continue
        print(f"== {zona}")
        datos = {t.name: preparar(zona, t) for t in tdirs}
        fj += jaccards(zona, datos)
        s1 = vs.buscar(ZONAS[zona]["wkt"])
        mapas = [] if figuras else None
        for t in tdirs:
            fs += contra_s1(zona, t, datos[t.name], s1, mapas)
        if mapas:
            m = max(mapas, key=lambda x: x["fila"]["pct_s1"])
            if m["fila"]["pct_s1"] >= 0.5:
                FIG.mkdir(exist_ok=True)
                figura(m, FIG / f"{zona}_{m['fila']['track']}_{m['fila']['fecha_nisar']}.png")
    sufijo = "" if zona_arg == "todas" else f"_{zona_arg}"
    dj, ds = pd.DataFrame(fj).round(3), pd.DataFrame(fs).round(3)
    dj.to_csv(BASE / f"comparacion_hv_pares{sufijo}.csv", index=False)
    ds.to_csv(BASE / f"comparacion_hv_s1{sufijo}.csv", index=False)
    cols = list(VARIANTES)
    con_agua = dj[dj.pct_hh >= 0.5]
    print("\nJaccard medio entre tracks (pares del evento/post con agua):")
    print(con_agua.groupby("zona")[[f"jaccard_{v}" for v in cols]].mean().round(2).to_string())
    print(con_agua[[f"jaccard_{v}" for v in cols]].mean().round(3).to_string())
    print("\nContra Sentinel-1 (media por pasada):")
    print(ds.groupby("zona")[[f"f1_{v}" for v in cols]].mean().round(2).to_string())
    for k in ("f1", "precision", "recall", "pct"):
        print(k, ds[[f"{k}_{v}" for v in cols]].mean().round(3).to_dict())
    if figuras:
        FIG.mkdir(exist_ok=True)
        resumen(ds, dj, FIG / f"resumen{sufijo}.png")
        print(f"-> {FIG}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--zona", default="todas", choices=["todas", *ZONAS])
    ap.add_argument("--figuras", action="store_true", help="un PNG por zona (pasada con más agua S1) + resumen")
    a = ap.parse_args()
    main(a.zona, a.figuras)
