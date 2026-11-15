"""Zonas de estudio para la idea "¿Cuánto tiempo se queda el agua?" (crecida 15–19 ago 2026).

Cobertura verificada con asf_search el 2026-11-14 (cov = % del AOI cubierto por el frame).
Fechas de evento = pasadas entre 10/8 y 10/9.
"""

ZONAS = {
    # --- Núcleo: cuenca Laguna Merín -------------------------------------------------
    "treinta_y_tres": dict(
        serie="T154D_F105",              # track de la serie temporal principal (regla 2: un track por serie)
        descripcion="Ciudad de Treinta y Tres + bajo Olimar (pico ~19–20/8, ~1.600 desplazados)",
        wkt="POLYGON((-54.55 -33.40,-54.15 -33.40,-54.15 -33.10,-54.55 -33.10,-54.55 -33.40))",
        tracks=[(132, "A", 161),   # cov 100 %  ago-sep: 08-10, 08-22, 09-03
                (154, "D", 105)],  # cov 100 %  ago-sep: 08-11, 08-23, 09-04
    ),
    "merin_arrozales": dict(
        serie="T53D_F105",              # track de la serie temporal principal (regla 2: un track por serie)
        descripcion="Arrozales Cebollatí–Tacuarí + borde Laguna Merín (53D ya bajado como T53D_F105)",
        wkt="POLYGON((-54.10 -33.75,-53.60 -33.75,-53.60 -33.00,-54.10 -33.00,-54.10 -33.75))",
        tracks=[(53, "D", 105),    # cov 100 %  08-16, 08-28, 09-09
                (132, "A", 161),   # cov 100 %  08-10, 08-22, 09-03
                (154, "D", 105)],  # cov 100 %  08-11, 08-23, 09-04
    ),
    "melo": dict(
        serie="T31A_F161",              # track de la serie temporal principal (regla 2: un track por serie)
        descripcion="Melo – arroyo Conventos (cuenca Tacuarí → Merín)",
        wkt="POLYGON((-54.26 -32.43,-54.08 -32.43,-54.08 -32.30,-54.26 -32.30,-54.26 -32.43))",
        tracks=[(31, "A", 161),    # cov 98 %   08-15 (durante el evento), 08-27, 09-08
                (154, "D", 105)],  # cov 100 %  08-11, 08-23, 09-04
    ),
    "rio_branco_jaguarao": dict(
        serie="T53D_F105",              # track de la serie temporal principal (regla 2: un track por serie)
        descripcion="Río Branco (UY) + Jaguarão (BR) – río Yaguarón, frontera",
        wkt="POLYGON((-53.46 -32.66,-53.30 -32.66,-53.30 -32.50,-53.46 -32.50,-53.46 -32.66))",
        tracks=[(53, "D", 105),    # cov 100 %  08-16, 08-28, 09-09
                (31, "A", 161)],   # cov 100 %  08-15, 08-27, 09-08
    ),
    # --- Contexto país: cuenca río Negro ----------------------------------------------
    "durazno": dict(
        serie="T60A_F161",              # track de la serie temporal principal (regla 2: un track por serie)
        descripcion="Durazno – río Yí (crecida jul ~23/7 y pico 9,75 m el 22/8)",
        wkt="POLYGON((-56.62 -33.45,-56.40 -33.45,-56.40 -33.30,-56.62 -33.30,-56.62 -33.45))",
        tracks=[(60, "A", 161)],   # cov 100 %  07-12, 07-24, 08-17, 08-29, 09-10
        fin_base="2026-07-20",     # la pasada 07-24 ya tiene la crecida de julio del Yí (~23/7): no es línea de base
    ),
    "mercedes": dict(
        serie="T10D_F105",              # track de la serie temporal principal (regla 2: un track por serie)
        descripcion="Mercedes – río Negro (Soriano), aguas abajo del Yí",
        wkt="POLYGON((-58.12 -33.32,-57.93 -33.32,-57.93 -33.20,-58.12 -33.20,-58.12 -33.32))",
        tracks=[(10, "D", 105),    # cov 100 %  08-13, 08-25, 09-06
                (161, "A", 161),   # cov 100 %  08-24, 09-05
                (60, "A", 161)],   # cov 100 %  08-17, 08-29, 09-10
    ),
    # --- Agosto, este: campos bajos de Rocha (ganado trasladado, emergencia agropecuaria) ---------
    "rocha_norte": dict(
        serie="T53D_F105",
        evento="agosto",
        descripcion="Norte de Rocha – 18 de Julio, San Miguel (5–6 mil ha de campos anegados, ~15.000 vacunos trasladados)",
        wkt="POLYGON((-53.60 -34.00,-53.35 -34.00,-53.35 -33.50,-53.60 -33.50,-53.60 -34.00))",  # al este de merin_arrozales, sin solape
        tracks=[(53, "D", 105),    # cov 100 %  08-16, 08-28, 09-09
                (132, "A", 161),   # cov 100 %  08-10, 08-22, 09-03
                (31, "A", 161)],   # cov 100 %  08-15, 08-27, 09-08
    ),
    "castillos": dict(
        serie="T53D_F106",
        evento="agosto",
        descripcion="Castillos – bañados de la laguna de Castillos (puente cubierto 19/8, Camino Guardia del Monte)",
        wkt="POLYGON((-54.00 -34.32,-53.70 -34.32,-53.70 -34.10,-54.00 -34.10,-54.00 -34.32))",
        tracks=[(53, "D", 106),    # cov 100 %
                (132, "A", 160),   # cov 100 %
                (154, "D", 105)],  # cov 94 %
    ),
    # --- Octubre, litoral oeste: creciente del río Uruguay y del Cuareim ---------------------------
    "salto": dict(
        serie="T10D_F104",
        evento="octubre",
        descripcion="Salto – río Uruguay aguas abajo de Salto Grande (~12 m el 10–11/10, costanera cortada)",
        wkt="POLYGON((-58.03 -31.45,-57.88 -31.45,-57.88 -31.33,-58.03 -31.33,-58.03 -31.45))",
        tracks=[(10, "D", 104),    # cov 100 %  10-12
                (60, "A", 162)],   # cov 100 %  10-04, 10-16
        # 82D-104 y 161A-162: el catálogo dice 62–69 % pero el recorte trae dato sólo en una franja del borde (resto ~−135 dB)
    ),
    "paysandu": dict(
        serie="T10D_F105",
        evento="octubre",
        descripcion="Paysandú – río Uruguay (pico 6,32 m ~12–16/10, 108 desplazados)",
        wkt="POLYGON((-58.13 -32.38,-57.98 -32.38,-57.98 -32.26,-58.13 -32.26,-58.13 -32.38))",
        tracks=[(10, "D", 105),    # cov 100 %  10-12
                (161, "A", 161),   # cov 100 %  10-11
                (60, "A", 161)],   # cov 100 %  10-04, 10-16
    ),
    "artigas": dict(
        serie="T60A_F162",
        evento="octubre",
        descripcion="Artigas – río Cuareim (> 11,5 m el 1/10, ~120 personas)",
        wkt="POLYGON((-56.55 -30.45,-56.40 -30.45,-56.40 -30.36,-56.55 -30.36,-56.55 -30.45))",
        tracks=[(60, "A", 162),    # cov 100 %  10-04, 10-16
                (82, "D", 104),    # cov 100 %  10-05, 10-17
                (132, "A", 162)],  # cov 100 %  10-09, 10-21
    ),

}

# Ventana por defecto: línea de base jun–jul, evento ago, retiro sep–oct.
# Sólo PROVISIONAL (hasta ~2026-10-20) para no mezclar calibraciones (ver docs/eda_T53D_F105.md).
FECHA_INI = "2026-06-15"
FECHA_FIN = "2026-10-20"
# Litoral (evento de octubre): el retiro cae en VALIDATED. Se baja después de FECHA_FIN con --madurez PROVISIONAL VALIDATED
# y el detector normaliza esas pasadas por escena (regla 3: salto ~−1,7 dB HH en tierra).
INICIO_VALIDATED = "2026-10-21"
FECHA_FIN_VALIDATED = "2026-11-15"
