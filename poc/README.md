# POC web — "How long does the water stay?"

> **Histórica.** La entrega principal es la app de `app/` (ver README §1). Esta POC quedó con las cifras del detector viejo (umbral absoluto) y no se regenera con el pipeline nuevo.

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

## Publicar en GitHub Pages

El workflow `.github/workflows/pages.yml` reconstruye la página con
`python3 scripts/build_poc.py` y publica únicamente `poc/dist/`. Se ejecuta al
hacer push a `main` con cambios en `poc/`, en el constructor o en el propio
workflow. También se puede ejecutar manualmente desde **Actions → Deploy GitHub
Pages → Run workflow**.

### Activación inicial (administrador del repositorio)

1. Entrar a **Settings → Pages**.
2. En **Build and deployment → Source**, seleccionar **GitHub Actions**.
3. Ejecutar el workflow desde Actions o hacer un push que lo active.
4. Abrir la URL que devuelve el job `deploy` en el entorno `github-pages`.

La cuenta que administra el repositorio debe habilitar Pages y permitir GitHub
Actions. Si el repositorio es privado, el plan de GitHub de su propietario debe
admitir Pages para repositorios privados. Revisar la visibilidad del sitio en
Settings → Pages antes de activarlo: un repositorio privado puede publicar un
sitio público.

### Actualizar el sitio

- Para cambiar textos o estilos: editar `poc/index.html`, hacer commit y push.
- Para actualizar resultados: ejecutar localmente el pipeline de datos hasta
  `scripts/exportar_poc.py` y subir los cambios de `poc/data/`.
- El workflow genera la versión autocontenida a partir de esas fuentes. Para
  revisarla antes del push, ejecutar `python3 scripts/build_poc.py`.

Los datos originales de `data_nisar/` y las credenciales Earthdata permanecen
locales. El despliegue no descarga escenas ni necesita las dependencias
geoespaciales: el constructor usa solamente la biblioteca estándar de Python.

Referencia: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
