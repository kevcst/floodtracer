# EDA — NISAR GCOV track 53 D, frame 105 (2026-06-17 → 2026-10-27)

Recorte: arrozales Cebollatí–Tacuarí + borde Laguna Merín (UTM 22S, 20 m). 11 fechas (10 PROVISIONAL + 1 VALIDATED).
Figuras: `figs/eda_T53D_F105_serie.png`, `figs/eda_T53D_F105_mapas.png`. Código: `scripts/eda_extra_T53D.py`.

## Hallazgos

1. **NISAR capturó una crecida completa (16–19 ago 2026).** INUMET emitió aviso por 70–100 mm/día y acumulados >250 mm en Treinta y Tres/Rocha (16–19/8); Olimar y Yerbal desbordados, evacuados en Treinta y Tres.
   - Agua abierta (HH < −18 dB): ~4–5 % (jun–jul) → 10 % (08-16) → **14 % (08-28, pico)** → 8 % (09-09) → 5 % (09-21).
   - 6,1 % del recorte fue agua *nueva* en agosto; 85 % de eso ya se había retirado el 21/9.
   - Mucha del agua nueva está en **lotes rectangulares** (arrozales en barbecho con taipas reteniendo lluvia) y en bajos del sur del recorte.
2. **La inundación de arroz todavía no empezó** al 27/10: sólo 0,36 % de agua nueva. Consistente con el calendario (nov–dic). Los datos que la muestran son las próximas pasadas VALIDATED (~08/11, 20/11, 02/12 en este track).
3. **Salto de calibración PROVISIONAL → VALIDATED.** El 27/10 (VALIDATED, CRID P05036) todo el terreno baja ~1,7 dB en HH y ~2,2 dB en HV, y los dispersores persistentes (estructuras) bajan ~2,2 dB, mientras el agua abierta queda igual (piso de ruido ~−22,5 dB). Probablemente es calibración, no un cambio real. **No mezclar madurezes sin normalizar** (p. ej. offset con dispersores persistentes) — el +6,5 % de "agua" del 27/10 en `serie_resumen.csv` es mayormente este artefacto.
4. **Otsu global no sirve**: el histograma de la escena no es bimodal (el agua es ~5 %), Otsu corta en ~−11 dB y separa tipos de tierra. Usar umbral fijo calibrado con agua permanente (Laguna Merín ~−22,5 dB → umbral −18/−19 dB) u Otsu por *tiles* que pasen un test de bimodalidad.
5. **Doble rebote (bañados/monte ribereño)**: el corredor del Cebollatí se ve brillante en HH (doble rebote). Con una máscara gruesa (HH > −6 dB y HH−HV > 9 dB, 3,5 % del área) la relación HH−HV baja ~1 dB durante jul–ago y se recupera en setiembre. Señal interesante pero no concluyente; requiere zonas de interés bien elegidas.

## Implicancias para las ideas
- **Idea 2 (lluvia → inundación) pasa a ser la más sólida hoy**: evento completo (subida, pico, retroceso) con validación independiente (avisos INUMET, noticias). Falta: lluvia diaria INUMET/IMERG para el análisis de desfase.
- **Idea 4 (arroz) sigue en pie pero depende de datos de nov–dic.** Gran giro narrativo: los *mismos lotes* aparecen con agua "mala" en agosto y tendrán agua "buena" en diciembre.
- **Idea 3 (bañados)**: secundaria; elegir ROIs manuales (India Muerta, bañados del Cebollatí) antes de concluir.

## Pendientes
- Repetir con track 132 A 161 (otra geometría) para confirmar el evento de agosto y el salto de calibración (su VALIDATED arranca después del 21/10).
- Normalización entre madurezes con dispersores persistentes.
- Mapa de fecha de máximo y de retroceso por píxel/lote para el evento de agosto.
- Bajar nuevas fechas VALIDATED a medida que salgan.
