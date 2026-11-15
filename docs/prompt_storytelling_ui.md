---
description: Construye en una branch nueva la UI narrativa "After the rain" según docs/ui_storytelling_spec.md
argument-hint: "[fase opcional: 1-6, por defecto todas en orden]"
---

<!--
Uso en Claude Code:
  - Opción A (comando): copiá este archivo a .claude/commands/storytelling-ui.md y ejecutá /storytelling-ui
      mkdir -p .claude/commands && cp docs/prompt_storytelling_ui.md .claude/commands/storytelling-ui.md
  - Opción B (directo): escribí en Claude Code "Seguí las instrucciones de docs/prompt_storytelling_ui.md"
-->

Vas a construir la nueva UI narrativa del proyecto. Fase pedida: $ARGUMENTS (si está vacío o no aplica, avanzá por las fases en orden y frená para mostrarme el resultado después de la fase 2).

1. **Leé primero, sin escribir código:** `CLAUDE.md`, `docs/ui_storytelling_spec.md` (la especificación completa), `app/index.html` (para reutilizar la lógica de mapa, imágenes y sonda), `scripts/exportar_app.py` y la estructura de `app/data/manifest.json`.
2. **Branch:** verificá que el árbol de trabajo esté limpio (`git status`). Si hay cambios sin commitear, frená y preguntame. Creá y cambiate a `feat/storytelling-ui` desde `main` (si ya existe, usala).
3. **Plan:** antes de implementar, mostrame un plan corto: archivos a crear o modificar, campos nuevos del manifest que hacen falta y el orden de las fases. Esperá mi OK.
4. **Implementá por fases** (§9 de la spec). Después de cada fase:
   - servila con `python3 -m http.server -d app 8000` y verificá que carga sin errores de consola (si tenés navegador disponible, revisala en desktop y a 375 px de ancho);
   - corré el chequeo de "ninguna cifra literal" sobre `app/story.*`;
   - hacé un commit con un mensaje descriptivo en inglés.
5. **Reglas que no se negocian:**
   - No modificar `app/index.html` salvo agregar un link a `story.html`.
   - No cambiar el detector ni las métricas. En el pipeline, sólo agregar campos de exportación en `scripts/exportar_app.py` (y crear `scripts/exportar_optico.py` si hace falta), documentados.
   - Todo número de la UI sale del manifest. Textos en diccionario EN/ES.
   - Respetar las reglas científicas de `CLAUDE.md`: agua previa aparte, zonas no concluyentes marcadas, incertidumbre visible, Paysandú no destacado.
6. **Al terminar:** actualizá `README.md` (cómo ver la historia) y `CLAUDE.md` (nueva entrega, decisiones tomadas). Resumime qué quedó hecho, qué quedó pendiente y cualquier dato que no pudiste conseguir. No hagas merge ni push sin que te lo pida.
