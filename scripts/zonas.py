"""Zonas de estudio para la idea "¿Cuánto tiempo se queda el agua?" (crecida 15–19 ago 2026).

2026-11-15: sólo las 4 zonas de la app (Treinta y Tres, Laguna Merín, Río Branco, Rocha norte). Melo, Durazno, Mercedes,
Castillos y el litoral (Salto, Paysandú, Artigas, evento de octubre) se sacaron; su definición está en el historial de git
(commit 42b9ec8) y sus recortes siguen en data_nisar/zonas/.

Cobertura verificada con asf_search el 2026-11-14 (cov = % del AOI cubierto por el frame).
Fechas de evento = pasadas entre 10/8 y 10/9.
"""
import re
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data_nisar"   # datos descargados y productos intermedios (no versionado)
POLS = {"HH": "HHHH", "HV": "HVHV"}                          # términos diagonales de la covarianza GCOV = potencia gamma0 (lineal)


def gdal_prefijo():
    """Prefijo de ruta para leer HDF5 remotos con GDAL: vacío desde GDAL 3.13, "NETCDF:" en versiones anteriores."""
    v = subprocess.run(["gdalinfo", "--version"], capture_output=True, text=True).stdout
    m = re.search(r"GDAL (\d+)\.(\d+)", v)
    return "" if m and (int(m[1]), int(m[2])) >= (3, 13) else "NETCDF:"



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
    "rio_branco_jaguarao": dict(
        serie="T53D_F105",              # track de la serie temporal principal (regla 2: un track por serie)
        descripcion="Río Branco (UY) + Jaguarão (BR) – río Yaguarón, frontera",
        wkt="POLYGON((-53.46 -32.66,-53.30 -32.66,-53.30 -32.50,-53.46 -32.50,-53.46 -32.66))",
        tracks=[(53, "D", 105),    # cov 100 %  08-16, 08-28, 09-09
                (31, "A", 161)],   # cov 100 %  08-15, 08-27, 09-08
    ),
    # --- Agosto, este: campos bajos de Rocha (ganado trasladado, emergencia agropecuaria) ---------
    "rocha_norte": dict(
        serie="T53D_F105",
        evento="agosto",
        descripcion="Norte de Rocha – 18 de Julio, San Miguel (5–6 mil ha de campos anegados, ~15.000 vacunos trasladados)",
        wkt="POLYGON((-53.60 -34.00,-53.35 -34.00,-53.35 -33.50,-53.60 -33.50,-53.60 -34.00))",  # al este de merin_arrozales, sin solape
        # océano (esquina SE): núcleo dibujado del lado del mar, ~300 m afuera de la costa (ver MAR_* en metricas_evento)
        mar_wkt="POLYGON((-53.33 -33.735,-53.37 -33.755,-53.41 -33.785,-53.45 -33.82,-53.48 -33.855,-53.50 -33.89,"
                "-53.51 -33.92,-53.525 -33.96,-53.535 -33.99,-53.535 -34.01,-53.33 -34.01,-53.33 -33.735))",
        tracks=[(53, "D", 105),    # cov 100 %  08-16, 08-28, 09-09
                (132, "A", 161),   # cov 100 %  08-10, 08-22, 09-03
                (31, "A", 161)],   # cov 100 %  08-15, 08-27, 09-08
        # T132A: agua permanente de 1 sola pasada de calma (umbral en el tope −20 dB), ve el 57 % del agua de JRC y marca
        # agua previa que los otros no ven (10/8). Se sigue descargando y procesando para diagnóstico, pero no entra al
        # combinado ni a la app.
        excluir_tracks=["T132A_F161"],
    ),

}

# Ventana por defecto: línea de base jun–jul, evento ago, retiro sep–oct.
# Sólo PROVISIONAL (hasta ~2026-10-20) para no mezclar calibraciones (el 27/10, primera pasada VALIDATED, muestra un salto de calibración, no agua real).
FECHA_INI = "2026-06-15"
FECHA_FIN = "2026-10-20"
# Pasadas VALIDATED (desde INICIO_VALIDATED): se bajan sólo con --madurez PROVISIONAL VALIDATED y el detector las normaliza
# por escena (regla 3: salto ~−1,7 dB HH en tierra). Las 4 zonas actuales usan sólo PROVISIONAL.
INICIO_VALIDATED = "2026-10-21"
FECHA_FIN_VALIDATED = "2026-11-15"
