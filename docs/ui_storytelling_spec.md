# Especificación: nueva UI narrativa — "After the rain"

Escrita 2026-11-15. Es el brief para construir, en una branch nueva, una versión de la app que **cuenta una historia** en lugar de mostrar un tablero. La app actual (`app/index.html`) queda intacta como "explorador".

Contexto previo: `CLAUDE.md`, `docs/idea_principal.md`, `docs/contexto_nacional_ago2026.md`, `docs/validacion.md`. Datos: `app/data/manifest.json` (generado por `scripts/exportar_app.py`).

---

## 1. Objetivo

Que **cualquier persona** (jurado de NASA, autoridad del SINAE, intendente, productor, público general) entienda en ~3 minutos:

1. Qué pasó: la tormenta de agosto 2026 y la crecida del río Uruguay de octubre.
2. Qué mostró NISAR que no se podía ver con otras fuentes.
3. **Cuánto tiempo se quedó el agua** y dónde tardó más en secarse (el foco del proyecto).
4. Qué deberían hacer las autoridades en la próxima inundación, y por qué vale la pena seguir con estos análisis.

Frase central (aparece en el hero y en el cierre):

> **Knowing where the water reached isn't enough. What decides the damage is how long it stays. NISAR measures it — through clouds, across the whole country, for free.**

Título: **After the rain** — subtítulo: *How long does Uruguay stay under water?*

## 2. Audiencias y niveles de lectura

| Nivel | Para quién | Qué ve |
|---|---|---|
| Historia (3 min) | Todos | 6 escenas con scroll, una idea y un número por pantalla |
| "How do we know?" | Técnicos, jurado | Desplegables dentro de cada escena (método, validación, incertidumbre) |
| Explorador | Analistas, CECOED | Link a la app actual (`index.html` → renombrar a `explorer.html` sólo si se decide al final, ver §9) |

## 3. Arquitectura y restricciones

- **Archivo nuevo:** `app/story.html` (+ `app/story.js`, `app/story.css` si conviene separar). Reutiliza `app/data/` y `app/vendor/` (MapLibre ya vendorizado). **No modificar** `app/index.html` salvo agregar un link a la historia.
- **Estática**, sin backend ni build step obligatorio. Se sirve con `python3 -m http.server -d app 8000`.
- **Ninguna cifra escrita a mano**: todo número sale de `manifest.json` (regla del repo). Si falta un dato, agregarlo en `scripts/exportar_app.py`, no en el HTML.
- **Bilingüe EN/ES** con un toggle (EN por defecto para Space Apps). Todo el texto en un diccionario `STRINGS = {en: {...}, es: {...}}`; los números se formatean con `Intl.NumberFormat` según idioma.
- **Mobile primero**: gutter de 16 px, sin scroll horizontal, mapa arriba y tarjeta abajo en pantallas angostas. Probar a 375 px.
- **Modo oscuro** con variables CSS. Contraste AA.
- **Accesibilidad**: cada mapa/gráfico tiene un texto alternativo con la cifra clave; navegable con teclado; `prefers-reduced-motion` desactiva autoplay y animaciones.
- **Rendimiento**: primera escena visible en < 3 s; imágenes por zona/fecha con carga diferida.
- Reglas científicas del repo siguen vigentes: no mezclar PROVISIONAL/VALIDATED, mostrar incertidumbre, marcar zonas no concluyentes (`resumen.concluyente`).

## 4. Lenguaje visual (se mantiene en toda la historia)

| Elemento | Codificación |
|---|---|
| Agua de siempre (ríos, lagunas) | Azul (`leyendas`/color existente de agua base) |
| Agua nueva de la inundación | Naranja |
| Agua ya presente antes de la lluvia | Gris (`leyendas.previa`) — siempre aparte |
| Días bajo agua | Escala secuencial amarillo claro (≤ 1 semana) → marrón oscuro (5+ semanas); reutilizar `leyendas.persistencia` |
| Sigue con agua al final | `leyendas.sigue` |
| Radar | Gris; la leyenda dice "darker = water", **nunca dB** en la historia |

Iconos (Tabler o SVG inline simples): persona (desplazados), campo, camino, árbol (agua bajo monte), nube (óptico ciego), satélite.

Tipografía: títulos de escena **que son respuestas**, no temas ("Half the land was still wet three weeks later", no "Persistence"). Un número grande por pantalla.

**Equivalencias humanas** (calcular en JS desde el manifest, constantes documentadas y verificadas antes de publicar): ej. hectáreas inundadas en "veces el departamento de Montevideo" (verificar superficie oficial) y km de caminos en una distancia conocida entre ciudades.

## 5. Las 6 escenas

Patrón: *scrollytelling* — mapa MapLibre fijo (sticky) a la derecha / arriba en mobile; tarjetas de texto que entran con el scroll y disparan cambios en el mapa (zona, zoom, capa, fecha). Usar `IntersectionObserver` (sin librerías extra, o Scrollama si se vendoriza).

### Escena 0 — Hero
- Título, subtítulo, frase central, botón "Start the story" y link "Skip to explorer".
- Fondo: imagen radar de la Merín del pico (`merin_arrozales/hh_2026-08-28.webp` + `agua_2026-08-28.png`), sin controles.
- Toggle EN/ES y botón "Presentation mode" (§7).

### Escena 1 — "The day satellites went blind"
- **Mensaje:** cuando más se necesita ver, los satélites ópticos no ven; el radar sí.
- **Visual:** deslizador antes/después (swipe) sobre la misma zona: izquierda imagen óptica nublada de la semana de la lluvia, derecha NISAR con el agua.
- **Datos:** NISAR = `treinta_y_tres` o `merin_arrozales`, primera pasada después de la lluvia. Óptico: **no existe en el repo** → crear `scripts/exportar_optico.py` que baje un Sentinel-2 L2A color verdadero (Planetary Computer, anónimo, colección `sentinel-2-l2a`) del 15–22/8 sobre la zona, sólo como contexto (regla 1), y lo exporte a `app/data/contexto/optico_{zona}.webp` con esquinas en el manifest. Si no hay escena útil, mostrar el porcentaje de nubes del catálogo y un placeholder ilustrado honesto ("no usable optical image between Aug 15–22").
- **Dato ancla:** lluvia acumulada máxima (texto de contexto, la única cifra de prensa permitida; marcar fuente) y fecha de la pasada NISAR.

### Escena 2 — "What we count, and what we don't"
- **Mensaje:** el sistema actual cuenta personas en ciudades; el impacto rural no aparece en ningún informe.
- **Visual:** tres tarjetas grandes con contador animado: `cifras.desplazados` (SINAE, `cifras.desplazados_fecha`) vs `cifras.por_evento.agosto.ha` (tierra bajo agua) vs `cifras.km_7d_todos` / `cifras.km_todos` (caminos rurales). Equivalencia humana debajo.
- Nota pequeña: "Displaced people: SINAE, preliminary" (regla 4).

### Escena 3 — "The water arrives… and stays"
- **Mensaje:** lo que importa no es el pico, es la duración.
- **Visual:** mapa de `merin_arrozales` con la serie de su track (`capas.serie`, `fechas`), **autoplay ~10 s** pasada a pasada (agua nueva en naranja sobre radar gris), luego slider manual con play/pause. Contador grande sincronizado: "% of the flooded area still wet" usando `fechas[].v` (y banda `lo`–`hi` como texto "between X and Y").
- Frase ancla generada: "On {merin_pico_fecha}, {merin_pico_pct}% was under water; on {merin_sep_fecha}, still {merin_sep_pct}%."
- Mini gráfico debajo: curva simple del % mojado con la ventana de lluvia sombreada y el hueco de datos en gris rayado (explicado en el tooltip).
- "How do we know?": detector por cambio, ≥ 2 observaciones, agua previa aparte.

### Escena 4 — "Where the land takes longest to dry" (escena central)
- **Mensaje:** estos son los lugares a priorizar la próxima vez.
- **Visual:** zoom out a todas las zonas de agosto con el **heatmap de secado** (`secado.archivo`, celdas de `secado.celda_m`, escala `leyendas.persistencia`). Panel lateral con **top 5 caminos por días cortados** (todas las zonas: `zonas[*].caminos`, ordenar por `dias_mid`, mostrar `donde`, `km_bajo_agua`, `dias_min`–`dias_max`, marca si `sigue`).
- Interacción **"Tap a place"**: clic en el mapa → tarjeta en lenguaje natural: "This field was under water from {primera} to {retiro}: about {n} weeks" usando `sonda.bin` (ver `capas.sonda.codigo`) o la celda del heatmap. Sin dB.
- Interacción **buscador**: input con autocompletar sobre `localidades[].nombre` y `caminos[].donde` de todas las zonas → vuela al lugar.
- Dato ancla: mitad del área seca por zona (día N) — si no está en el manifest como campo, agregarlo en `exportar_app.py` (ej. `resumen.dia_mitad_seca`).

### Escena 5 — "What only L-band can see"
Tres tarjetas, cada una abre un antes/después de 2 imágenes y una línea:
1. **Water under grass and rice** — comparación NISAR vs Sentinel-1 de la misma fecha (de la caché de `validar_s1.py`; exportar un par de PNG por `exportar_app.py` → `app/data/contexto/s1_vs_nisar_{zona}_{fecha}.png`). Texto: NISAR found water C-band missed; cifra de `validacion.s1` (exhaustividad/F1 agregada).
2. **Water under the forest** — capa `monte.png` de `rocha_norte` o `mercedes` + exceso ribereño (`resumen.monte` / `monte_mercedes`). Texto: "riverside forest got brighter than hillside forest: water under the trees".
3. **Two kinds of flood** — agosto (lluvia local, campo) vs octubre (`eventos.octubre`, río Uruguay desde Brasil, cauce, monte de islas y costa urbana). Mostrar honestamente que en el litoral casi no hubo agua abierta nueva y por qué (`resumen.sin_agua_permanente`, ciudades). **No destacar la cifra de Paysandú** como número grande.

### Escena 6 — "Next time"
- **Mensaje:** esto se puede repetir en cada evento, con datos gratuitos.
- **Visual 1:** línea de tiempo horizontal de uso operativo: *Before the storm* (suelo ya saturado: `cifras.ha_previa`) → *Day 3–7* (dónde llegó) → *Weeks 1–6* (qué sigue mojado, caminos) → *After* (informe rural, ha·día) → *Between events* (mapas de riesgo).
- **Visual 2:** selector **"I work at…"** (SINAE/CECOED · Intendencia · MGAP/productores/seguros · DINAGUA · INUMET · Cancillería) → tarjeta con *qué obtiene* y *acción concreta* (texto en `STRINGS`, cifras del manifest).
- **Cierre:** propuesta de piloto operativo para la temporada El Niño 2026-27 (pipeline abierto, costo de datos cero) + frase central + links: Explorer, Download data (`descargas`), Method guide, Code.
- **Caja "Limits"** (una sola, honesta): revisita 12 días/track, ciudades (doble rebote → "NISAR counts land, SINAE counts people"), latencia (post-evento, no alerta temprana), zonas no concluyentes (listar desde `resumen.concluyente == false` con `motivo_no_concluyente`).

## 6. Componentes reutilizables a construir

- `StickyMap` (MapLibre + image sources por zona/fecha, ya hay lógica en `index.html` que se puede extraer).
- `SwipeCompare` (dos imágenes georreferenciadas o dos `<img>` con divisor arrastrable; teclado: flechas).
- `TimePlayer` (play/pause, slider de fechas, respeta `prefers-reduced-motion`).
- `BigNumber` (contador animado, formateo por idioma, fuente/nota opcional).
- `HowDoWeKnow` (`<details>` estilizado).
- `PlaceCard` (resultado del clic/búsqueda, lenguaje natural).
- `RoleSelector` (tarjetas por institución).

## 7. Modo presentación

Botón que recorre las escenas automáticamente (≈ 6–8 s por escena, autoplay del agua en la escena 3), oculta controles secundarios y muestra sólo título + número. Sirve para reuniones y para grabar el video de Space Apps. Tecla `Esc` sale.

## 8. Cambios permitidos en el pipeline

Sólo en `scripts/exportar_app.py` (y el nuevo `scripts/exportar_optico.py`) para **agregar** campos que la historia necesite (ej. `dia_mitad_seca`, pares S1/NISAR, imagen óptica, top caminos global). No cambiar métricas ni el detector. Documentar cada campo nuevo en el docstring del exportador.

## 9. Fases y criterios de aceptación

1. **Esqueleto**: `story.html` con las 7 secciones, scroll, mapa sticky, toggle EN/ES, link al explorador. ✔ si se navega de punta a punta en desktop y en 375 px.
2. **Escenas 3 y 4** (las más importantes): autoplay del agua + heatmap de secado + top caminos + clic en un lugar. ✔ si todas las cifras salen del manifest y coinciden con `app/index.html`.
3. **Escenas 1, 2, 5**: comparaciones antes/después y contadores (con el exportador óptico y S1).
4. **Escena 6 + límites + modo presentación.**
5. **Pulido**: accesibilidad (teclado, alt, reduced motion), modo oscuro, rendimiento, revisión de textos (frases cortas, sin jerga; inglés claro; español rioplatense neutro).
6. **Decisión final (con el equipo)**: si la historia pasa a ser `index.html` y el actual pasa a `explorer.html`. No hacerlo sin confirmación.

Checklist final:
- [ ] Ninguna cifra literal en `story.html`/`story.js` (buscar dígitos en strings).
- [ ] Zonas no concluyentes marcadas; Paysandú no destacado.
- [ ] Agua previa siempre separada y explicada.
- [ ] Funciona servida por http, sin errores de consola, en Chrome y Safari.
- [ ] EN y ES completos.
- [ ] README: sección "Ver la historia" con el comando y la URL.
