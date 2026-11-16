"""
Chequeo "ninguna cifra literal" de las páginas de la app (index.html, method.html, story.js, method.js, nav.js):
todo número visible tiene que salir de data/manifest.json.

  python scripts/check_story_literals.py          # sale con código 1 si encuentra algo

Reglas:
  - story.js, dentro de STRINGS: ningún dígito en la parte estática de ningún string (sí dentro de ${...}).
  - story.js, fuera de STRINGS: ningún string con dígitos que parezca texto para personas (palabras + dígitos),
    salvo patrones técnicos (CSS, URLs, rutas, media queries, formatos de fecha ISO internos).
  - story.html: ningún dígito en nodos de texto ni en atributos visibles (alt, aria-label, title, placeholder).
Para una excepción justificada, poner el comentario `// lit-ok: <motivo>` en la misma línea.
"""
import re
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
# nombres propios con dígitos (no son cifras): se borran antes de buscar dígitos
NOMBRES = re.compile(r"Sentinel-[12]|python3|L2A|GCOV|HydroBASINS|ERA5")
TECH = re.compile(r"(px|rem|em|vh|svh|vw|ms|deg)\b|rgba?\(|#[0-9a-f]{3,8}\b|https?://|data/|\.(webp|png|json|bin|geojson|csv|tif|js|css)\b|"
                  r"max-width|min-width|T\d\d:\d\d|\{z\}|viewBox|^-?[\d.\s,]+$|^[\d.]+%$|M[\d.,\s-]+|translate|matrix|"
                  r"cubic-bezier|\d+fr\b|linear-gradient", re.I)


def strings_js(src):
    """(línea, texto estático, dentro_de_STRINGS) para cada literal de string; ignora comentarios y ${...}."""
    out, i, n, line = [], 0, len(src), 1
    start = src.find("const STRINGS")
    end = src.find("\n};", start) if start >= 0 else -1
    while i < n:
        c = src[i]
        if c == "\n":
            line += 1
        if src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            line += src[i:j].count("\n")
            i = j + 2
            continue
        if c == "/" and re.search(r"[(,=:\[!&|?{};]\s*$", src[max(0, i - 40):i]):    # regex literal: saltar
            j, clase = i + 1, False
            while j < n and src[j] != "\n":
                if src[j] == "\\":
                    j += 2; continue
                if src[j] == "[":
                    clase = True
                elif src[j] == "]":
                    clase = False
                elif src[j] == "/" and not clase:
                    break
                j += 1
            i = j + 1
            continue
        if c in "'\"`":
            q, j, buf, depth, l0 = c, i + 1, [], 0, line
            while j < n:
                d = src[j]
                if d == "\\":
                    buf.append(src[j:j + 2]); j += 2; continue
                if d == "\n":
                    line += 1
                if q == "`" and src.startswith("${", j) and depth == 0:
                    depth, j = 1, j + 2
                    while j < n and depth:
                        depth += {"{": 1, "}": -1}.get(src[j], 0)
                        line += src[j] == "\n"
                        j += 1
                    buf.append(" ")
                    continue
                if d == q:
                    break
                buf.append(d); j += 1
            out.append((l0, "".join(buf), start <= i <= end))
            i = j + 1
            continue
        i += 1
    return out


# las tres páginas de la app
JS = ["story.js", "method.js", "nav.js", "explorer.js"]
HTML = ["index.html", "method.html", "explorer.html"]


def main():
    problemas = []
    for nombre in JS:
        js = (APP / nombre).read_text()
        lineas = js.splitlines()
        for ln, s, en_strings in strings_js(js):
            s = re.sub(r"<[^>]*>", " ", NOMBRES.sub("", s))   # las etiquetas HTML (h4, atributos) no son texto visible
            if not re.search(r"\d", s) or "lit-ok" in lineas[ln - 1]:
                continue
            if en_strings:
                problemas.append(f"{nombre}:{ln}: dígito en STRINGS: {s[:80]!r}")
            elif re.search(r"[A-Za-zÁÉÍÓÚáéíóúñ]{3,}\s", s) and not TECH.search(s):
                problemas.append(f"{nombre}:{ln}: string con dígitos fuera de STRINGS: {s[:80]!r}")
    for nombre in HTML:
        html = (APP / nombre).read_text()
        sin = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), html, flags=re.S)
        for k, l in enumerate(sin.splitlines(), 1):
            texto = re.sub(r"<[^>]*>", " ", l)
            attrs = re.findall(r'(?:alt|aria-label|title|placeholder)="([^"]*)"', l)
            for s in [NOMBRES.sub("", x) for x in [texto] + attrs]:
                if re.search(r"\d", s) and "lit-ok" not in l:
                    problemas.append(f"{nombre}:{k}: dígito en texto visible: {s.strip()[:80]!r}")
    # sin em dashes en los textos visibles (pedido del equipo: no "sonar a IA"); los "–" de rangos numéricos sí van
    for nombre in JS:
        js = (APP / nombre).read_text()
        for ln, txt, en_strings in strings_js(js):
            if en_strings and "—" in txt:
                problemas.append(f"{nombre}:{ln}: em dash en STRINGS: {txt[:80]!r}")
    for nombre in HTML:
        sin = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", " ", (APP / nombre).read_text(), flags=re.S)
        if "—" in re.sub(r"<[^>]*>", " ", sin):
            problemas.append(f"{nombre}: em dash en texto visible")
    if problemas:
        print("\n".join(problemas))
        print(f"\n{len(problemas)} cifra(s) literal(es)")
        sys.exit(1)
    print(f"OK: sin cifras literales en {', '.join(HTML + JS)}")


if __name__ == "__main__":
    main()
