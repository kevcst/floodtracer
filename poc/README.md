# POC web — "How long does the water stay?"

Prueba de concepto para que el equipo decida si seguimos con esta idea. Está en inglés, igual que el entregable final.
El contexto completo y el pipeline de datos están en el [README principal](../README.md).

## Verla

```bash
open dist/index.html     # macOS · Linux: xdg-open · Windows: start
```

`dist/index.html` es autocontenido (datos e imágenes embebidos, ~6 MB): no necesita servidor ni Python.

## Editarla

- `index.html` es la **fuente**. Carga los datos desde `data/` con `fetch`, así que para verla mientras la editan hay que servirla, porque el navegador bloquea `fetch` sobre `file://`:
  ```bash
  cd poc && python3 -m http.server 8000     # abrir http://localhost:8000
  ```
- `data/` sale de `python scripts/exportar_poc.py`: imágenes HH (JPEG), agua por fecha, extensión y persistencia (PNG) y `poc.json` con las series y el mapa de contexto.
- Después de editar `index.html` o regenerar `data/`, armen la versión publicable:
  ```bash
  python scripts/build_poc.py               # -> poc/dist/index.html
  ```
- No editen `dist/index.html` a mano: se sobrescribe en cada build.

## Qué decide cada parte de la página

| Sección | Datos | Script que los genera |
|---|---|---|
| Cifras clave | Merín 53D: extensión máxima y % bajo agua por fecha; desplazados SINAE (texto fijo, contexto) | `metricas_evento.py` → `exportar_poc.py` |
| Mapa de contexto | Contornos Natural Earth + AOIs de `scripts/zonas.py` | `exportar_poc.py` |
| Visor de radar | Merín (53D) y Treinta y Tres (154D): HH y agua por fecha, extensión, persistencia | `metricas_evento.py` → `exportar_poc.py` |
| Pulso por zona | `data_nisar/zonas/metricas_por_fecha.csv` (un track por zona, lista `PULSO` en `exportar_poc.py`) | `metricas_evento.py` |
| Agua bajo el monte | `data_nisar/zonas/monte_ribereno.csv` (Mercedes, 3 tracks) | `monte_ribereno.py` |
| Tabla desplegable | `metricas_resumen.csv` + `combinado_resumen.csv` | `metricas_evento.py`, `combinar_tracks.py` |

La línea de tiempo y los textos están escritos a mano en `index.html`. Si cambian los números, revisen también las cifras que aparecen en el texto, que no se actualizan solas.

Para cambiar de track o de zona en el visor, editen `VISOR` en `scripts/exportar_poc.py`.
