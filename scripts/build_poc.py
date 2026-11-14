"""Arma poc/dist/index.html autocontenido: poc.json e imágenes embebidas (data URIs), sin rutas relativas.
  python scripts/build_poc.py   (después de exportar_poc.py)"""
import base64
import json
from pathlib import Path

POC = Path(__file__).resolve().parents[1] / "poc"
html = (POC / "index.html").read_text()
imgs = {}
for f in sorted((POC / "data").iterdir()):
    if f.suffix in (".png", ".jpg"):
        mime = "image/png" if f.suffix == ".png" else "image/jpeg"
        imgs[f"data/{f.name}"] = f"data:{mime};base64," + base64.b64encode(f.read_bytes()).decode()
datos = (POC / "data" / "poc.json").read_text().replace("</", "<\\/")
inyectar = (f'<script id="poc-data" type="application/json">{datos}</script>\n'
            f'<script>window.POC_IMG = {json.dumps(imgs)};</script>\n')
i = html.index("<script>")
out = html[:i] + inyectar + html[i:]
(POC / "dist").mkdir(exist_ok=True)
(POC / "dist" / "index.html").write_text(out)
print(f"-> {POC / 'dist' / 'index.html'}  ({len(out) / 1e6:.1f} MB)")
