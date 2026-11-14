# Contexto nacional — inundaciones jun–oct 2026 (ventana NISAR)

Recopilado 2026-11-14 de prensa y reportes SINAE/CECOED. Cifras preliminares: verificar con SINAE (gub.uy/sistema-nacional-emergencias) antes de publicarlas como definitivas.

## Eventos en la ventana NISAR

| Fecha | Lugar / cuenca | Qué pasó | Fuente |
|---|---|---|---|
| ~23 jul | Durazno – río Yí (cuenca río Negro) | Yí ~8,95 m; 57 personas desplazadas (19 familias) | Durazno Digital 23/7 |
| 15–19 ago | Este y noreste (Treinta y Tres, Cerro Largo, Rocha, Lavalleja, Maldonado) | Aviso INUMET: 70–100 mm/día, >250 mm acumulados. Laguna Merín 317 mm (máx. del país), Plácido Rosas 273, Bañado Medina 252, Río Branco 230, Melo 228 | InfoRocha 15/8; APU 20/8 |
| 18–21 ago | Treinta y Tres – río Olimar (cuenca Laguna Merín) | Olimar ~8,60 m; 21/8 bajando en 8,30 m; ~1.600 desplazados en la ciudad | APU 20/8; Intendencia TyT 21/8; La R 21/8 |
| 17–20 ago | Cerro Largo – arroyo Conventos (Melo) y río Yaguarón (Río Branco) | Desbordes, ~120 desplazados, rescates; Ruta 44 comprometida | APU 20/8; La R 21/8 |
| 18–19 ago | Jaguarão (Brasil) – río Yaguarón | Emergencia desde 15/8; el prefeito atribuye la crecida a aguas de Bagé/Piratini **y al nivel alto de la Lagoa Mirim** | A Hora do Sul 18/8 |
| ~19 ago | Rocha | 5.000–6.000 ha de campos bajos anegados; ~15.000 vacunos trasladados (zona 18 de Julio) | APU 20/8; La R 21/8 |
| 19–25 ago | Durazno – río Yí | Sube ~3 cm/h; **pico 9,75 m el sáb. 22/8 ~22 h** (supera la crecida de julio); 25/8 en 9,01 m bajando | Durazno Digital 19–25/8 |
| ~21 ago | Soriano – río Negro | Evacuación de paradores ante posible 6 m | La R 21/8 |
| 22–23 ago | País (SINAE) | Sáb. 22: **2.229 desplazados**, 565 viviendas (TyT 1.811, Durazno 205, Cerro Largo 104; también Soriano, Artigas, Paysandú, Rocha, Tacuarembó). Dom. 23: 989 total, **TyT baja a 418 y Durazno sube a 416** | Subrayado 23/8 (x2) |
| 21 ago | Contexto climático | SINAE: El Niño activo, >50 % de probabilidad de afectar más de la mitad del territorio, se extendería al menos hasta mayo 2027; antecedentes 2015-16 y 2023-24 | La R 21/8 |

**Corrección**: la nota "565 desplazados (San José, Durazno…)" citada antes como julio 2026 es de **septiembre 2017**. Descartada.

## "Una inundación afecta a otra" — hipótesis a mostrar
1. **Misma lluvia, dos vertientes, dos tiempos.** La Cuchilla Grande separa la vertiente atlántica (Olimar/Cebollatí/Tacuarí → Laguna Merín) de la del río Negro (Yí → Negro → Uruguay). El Olimar picó ~19–20/8 (cuenca corta, respuesta rápida); el Yí en Durazno recién el 22/8 (~3 días después); el río Negro en Soriano amenazaba después. Los desplazados lo muestran: el 23/8 Treinta y Tres baja y Durazno sube.
2. **Efecto remanso de la Laguna Merín.** La laguna recibió la mayor lluvia del país y todos los ríos del este desaguan en ella. Con la laguna alta, el Olimar/Cebollatí/Yaguarón drenan más lento → el agua se queda más tiempo en los campos. Coincide con lo que NISAR ve: agua en campos 16/8 → pico 28/8 → retiro recién al 21/9.
3. **Suelos saturados por eventos previos** (julio en el Yí) → la lluvia de agosto escurre más.
4. **Frontera**: la misma crecida afecta Río Branco (UY) y Jaguarão (BR) — NISAR no ve fronteras.

## Cobertura NISAR del evento (GCOV, fechas jul–sep 2026)
| Lugar | Track (fechas clave) |
|---|---|
| Treinta y Tres (ciudad, Olimar) | 132A-161: 08-10, **08-22**, 09-03 · 154D-105: 08-11, **08-23**, 09-04 |
| Arrozales Cebollatí (ya bajado) | 53D-105: 08-16, **08-28**, 09-09, 09-21 |
| Melo / Río Branco | 31A-161: **08-15**, 08-27 · 154D-105: 08-11, **08-23** · 53D-105 (Río Branco): 08-16, 08-28 |
| Durazno (Yí) | 60A-161: 07-12, **07-24** (evento julio), 08-17 (subiendo), **08-29** (post-pico) |
| Sarandí del Yí / Paso de los Toros | 132A-161, 154D-105, 60A-161 |
| Mercedes (río Negro) | 10D-105: 08-13, **08-25** · 161A-161: **08-24** · 60A-161: 08-17, 08-29 |

Hueco global de datos: 27/7–10/8 (sin línea de base inmediata antes del evento; usar julio).

## "% de Uruguay inundado"
No hay estadística oficial de área inundada nacional. Con NISAR se puede calcular **% de área con agua nueva** respecto a una línea de base de julio, por cuenca (Laguna Merín, Yí, Negro) — viable. Un mosaico nacional completo (≈25–30 frames por ciclo, 1–2 GB c/u) es posible pero pesado; conviene hacerlo a 100–200 m o en la nube (us-west-2). Alternativa liviana para un mapa país: producto L3 SME2 (humedad del suelo, PROVISIONAL, no calibrado del todo) como capa de "suelo saturado".

## Fuentes
- https://inforocha.uy/2026/08/15/inumet-emite-aviso-por-granizo-rayos-y-250-milimetros-de-lluvia-en-5-departamentos-entre-ellos-rocha/
- https://www.apu.uy/noticias/lluvias-extraordinarias-rios-desbordados-y-una-emergencia-que-sigue-abierta
- https://grupormultimedio.com/el-nino-ya-enciende-alarmas-miles-de-evacuados-campos-bajo-agua-y-reclamo-de-recursos-nacionales-id204181/
- https://www.subrayado.com.uy/sinae-registro-2229-personas-desplazadas-las-inundaciones-este-sabado-n1016070
- https://www.subrayado.com.uy/inundaciones-descendio-la-cantidad-desplazados-nivel-pais-pero-aumento-durazno-n1016082
- https://treintaytres.gub.uy/2026/08/21/sigue-bajando-el-olimar/
- https://www.duraznodigital.uy/2026/07/57-personas-dejaron-sus-hogares-en.html
- https://www.duraznodigital.uy/2026/08/el-rio-yi-trepo-915-m-supero-la-crecida.html
- https://www.duraznodigital.uy/2026/08/el-rio-yi-en-retirada-en-su-pasaje-por.html
- https://ahoradosul.com.br/conteudos/2026/08/18/cheia-do-rio-jaguarao-mobiliza-forcas-de-resgate/
- https://www.elobservador.com.uy/nacional/cerro-largo-agua-mas-100-desplazados-comercios-paralizados-y-la-espera-recursos-economicos-afrontar-el-dia-despues-n6054723
