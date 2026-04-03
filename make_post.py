"""
PostDiario — Generador de imágenes profesionales para Instagram
Usa HTML/CSS renderizado con Playwright en lugar de Pillow.
"""

import json
import os
import random
import shutil
from datetime import datetime
from typing import Any

from dateutil import tz

OUT_DIR    = "out"
PUBLIC_DIR = "public"
IMG_NAME   = "post.jpg"
CANVAS_SIZE = 1080
DEBUG = True


# ── Templates ────────────────────────────────────────────────────────────────

TEMPLATES = {
    "minimal_cream": {
        "bg": "linear-gradient(160deg, #faf7f2 0%, #f0ebe3 50%, #e8e0d4 100%)",
        "text_color": "#2c2c2c",
        "accent": "#b8860b",
        "handle_color": "#8a8074",
        "font_display": "'Playfair Display', serif",
        "font_body": "'DM Sans', sans-serif",
        "style": "light",
    },
    "deep_ocean": {
        "bg": "linear-gradient(145deg, #0a1628 0%, #1a2744 40%, #0d1f3c 100%)",
        "text_color": "#e8edf5",
        "accent": "#64b5f6",
        "handle_color": "#7a9cc6",
        "font_display": "'Cormorant Garamond', serif",
        "font_body": "'Inter', sans-serif",
        "style": "dark",
    },
    "warm_sunset": {
        "bg": "linear-gradient(170deg, #1a1215 0%, #2d1b2e 30%, #3d1f30 60%, #1a1215 100%)",
        "text_color": "#f5e6d3",
        "accent": "#e8a87c",
        "handle_color": "#c4917a",
        "font_display": "'Libre Baskerville', serif",
        "font_body": "'Karla', sans-serif",
        "style": "dark",
    },
    "sage_garden": {
        "bg": "linear-gradient(155deg, #f5f7f0 0%, #e8ede0 40%, #dce4d0 100%)",
        "text_color": "#2d3b2d",
        "accent": "#5a7a5a",
        "handle_color": "#7a937a",
        "font_display": "'Lora', serif",
        "font_body": "'Source Sans 3', sans-serif",
        "style": "light",
    },
    "midnight_violet": {
        "bg": "linear-gradient(160deg, #0f0a1a 0%, #1a1030 40%, #251545 70%, #0f0a1a 100%)",
        "text_color": "#e8dff5",
        "accent": "#c4a7e7",
        "handle_color": "#9d89b8",
        "font_display": "'Crimson Pro', serif",
        "font_body": "'Nunito Sans', sans-serif",
        "style": "dark",
    },
    "paper_white": {
        "bg": "linear-gradient(180deg, #ffffff 0%, #f8f8f8 50%, #f2f0ed 100%)",
        "text_color": "#1a1a1a",
        "accent": "#c9a96e",
        "handle_color": "#999999",
        "font_display": "'EB Garamond', serif",
        "font_body": "'Work Sans', sans-serif",
        "style": "light",
    },
}

THEME_TEMPLATE_MAP = {
    "ansiedad":    ["deep_ocean", "midnight_violet", "warm_sunset"],
    "autoestima":  ["sage_garden", "warm_sunset", "minimal_cream"],
    "vida":        ["paper_white", "minimal_cream", "sage_garden"],
    "amor":        ["warm_sunset", "midnight_violet", "minimal_cream"],
    "healing":     ["sage_garden", "deep_ocean", "paper_white"],
    "soledad":     ["deep_ocean", "midnight_violet", "warm_sunset"],
    "resilience":  ["warm_sunset", "sage_garden", "paper_white"],
    "change":      ["minimal_cream", "paper_white", "deep_ocean"],
    "growth":      ["sage_garden", "minimal_cream", "paper_white"],
    "peace":       ["sage_garden", "paper_white", "deep_ocean"],
    "strength":    ["warm_sunset", "midnight_violet", "deep_ocean"],
    "self-love":   ["warm_sunset", "minimal_cream", "sage_garden"],
    "letting-go":  ["deep_ocean", "midnight_violet", "paper_white"],
    "boundaries":  ["paper_white", "minimal_cream", "sage_garden"],
    "hope":        ["minimal_cream", "sage_garden", "warm_sunset"],
}


def pick_template(theme: str) -> tuple[str, dict]:
    theme_lower = theme.lower().strip()
    candidates = THEME_TEMPLATE_MAP.get(theme_lower, list(TEMPLATES.keys()))
    weights = [60, 25, 15]
    if len(candidates) < 3:
        candidates = list(TEMPLATES.keys())
        weights = [1] * len(candidates)
    name = random.choices(candidates[:3], weights=weights[:3], k=1)[0]
    return name, TEMPLATES[name]


# ── HTML Generation ──────────────────────────────────────────────────────────

def build_html(phrase: str, handle: str, template: dict, template_name: str) -> str:
    is_dark = template["style"] == "dark"

    if is_dark:
        decorations = _dark_decorations(template, template_name)
    else:
        decorations = _light_decorations(template, template_name)

    phrase_len = len(phrase)
    if phrase_len <= 30:
        font_size = "52px"
    elif phrase_len <= 60:
        font_size = "44px"
    elif phrase_len <= 90:
        font_size = "38px"
    else:
        font_size = "32px"

    fonts_url = (
        "https://fonts.googleapis.com/css2?"
        "family=Playfair+Display:ital,wght@0,400;0,600;1,400&"
        "family=DM+Sans:wght@400;500&"
        "family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&"
        "family=Inter:wght@400;500&"
        "family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&"
        "family=Karla:wght@400;500&"
        "family=Lora:ital,wght@0,400;0,600;1,400&"
        "family=Source+Sans+3:wght@400;500&"
        "family=Crimson+Pro:ital,wght@0,400;0,600;1,400&"
        "family=Nunito+Sans:wght@400;500&"
        "family=EB+Garamond:ital,wght@0,400;0,600;1,400&"
        "family=Work+Sans:wght@400;500&"
        "display=swap"
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="{fonts_url}" rel="stylesheet">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    width: {CANVAS_SIZE}px;
    height: {CANVAS_SIZE}px;
    overflow: hidden;
    background: {template["bg"]};
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
}}

{decorations}

.content {{
    position: relative;
    z-index: 10;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 80px 70px;
}}

.accent-line {{
    width: 48px;
    height: 3px;
    background: {template["accent"]};
    border-radius: 2px;
    margin-bottom: 44px;
    opacity: 0.9;
}}

.phrase {{
    font-family: {template["font_display"]};
    font-size: {font_size};
    font-weight: 400;
    color: {template["text_color"]};
    text-align: center;
    line-height: 1.5;
    letter-spacing: -0.01em;
    max-width: 860px;
    font-style: italic;
}}

.accent-line-bottom {{
    width: 48px;
    height: 3px;
    background: {template["accent"]};
    border-radius: 2px;
    margin-top: 44px;
    opacity: 0.9;
}}

.handle {{
    position: absolute;
    bottom: 48px;
    left: 0;
    right: 0;
    text-align: center;
    font-family: {template["font_body"]};
    font-size: 16px;
    font-weight: 500;
    color: {template["handle_color"]};
    letter-spacing: 2.5px;
    text-transform: uppercase;
}}

.quote-open,
.quote-close {{
    font-family: {template["font_display"]};
    font-size: 120px;
    color: {template["accent"]};
    opacity: 0.12;
    position: absolute;
    line-height: 1;
    user-select: none;
}}
.quote-open {{ top: 160px; left: 55px; }}
.quote-close {{ bottom: 130px; right: 55px; }}
</style>
</head>
<body>
    <div class="quote-open">\u201c</div>
    <div class="quote-close">\u201d</div>

    <div class="content">
        <div class="accent-line"></div>
        <p class="phrase">{phrase}</p>
        <div class="accent-line-bottom"></div>
    </div>

    <div class="handle">{handle}</div>
</body>
</html>"""
    return html


def _dark_decorations(template: dict, name: str) -> str:
    accent = template["accent"]
    if name == "deep_ocean":
        return f"""
body::before {{
    content: '';
    position: absolute; inset: 0;
    background:
        radial-gradient(1px 1px at 15% 25%, rgba(255,255,255,0.12) 0%, transparent 100%),
        radial-gradient(1px 1px at 72% 18%, rgba(255,255,255,0.08) 0%, transparent 100%),
        radial-gradient(1px 1px at 88% 62%, rgba(255,255,255,0.1) 0%, transparent 100%),
        radial-gradient(1px 1px at 35% 78%, rgba(255,255,255,0.07) 0%, transparent 100%),
        radial-gradient(1px 1px at 55% 45%, rgba(255,255,255,0.09) 0%, transparent 100%),
        radial-gradient(1px 1px at 8% 88%, rgba(255,255,255,0.06) 0%, transparent 100%);
    z-index: 1;
}}"""
    elif name == "warm_sunset":
        return f"""
body::after {{
    content: '';
    position: absolute; inset: 0;
    background:
        radial-gradient(ellipse 600px 400px at 20% 80%, {accent}0a 0%, transparent 70%),
        radial-gradient(ellipse 500px 500px at 85% 20%, #e8787815 0%, transparent 70%);
    z-index: 1;
}}
body::before {{
    content: '';
    position: absolute; inset: 0;
    background:
        radial-gradient(1.5px 1.5px at 20% 15%, rgba(232,168,124,0.15) 0%, transparent 100%),
        radial-gradient(1px 1px at 65% 82%, rgba(232,168,124,0.1) 0%, transparent 100%),
        radial-gradient(1px 1px at 90% 35%, rgba(255,255,255,0.06) 0%, transparent 100%),
        radial-gradient(1px 1px at 42% 10%, rgba(255,255,255,0.08) 0%, transparent 100%);
    z-index: 1;
}}"""
    else:
        return f"""
body::after {{
    content: '';
    position: absolute; inset: 0;
    background:
        radial-gradient(ellipse 550px 550px at 75% 25%, {accent}08 0%, transparent 70%),
        radial-gradient(ellipse 400px 300px at 15% 75%, #7c5cbf08 0%, transparent 70%);
    z-index: 1;
}}
body::before {{
    content: '';
    position: absolute; inset: 0;
    background:
        radial-gradient(1px 1px at 25% 20%, rgba(196,167,231,0.12) 0%, transparent 100%),
        radial-gradient(1px 1px at 78% 72%, rgba(196,167,231,0.08) 0%, transparent 100%),
        radial-gradient(1px 1px at 52% 88%, rgba(255,255,255,0.05) 0%, transparent 100%),
        radial-gradient(1px 1px at 10% 55%, rgba(196,167,231,0.06) 0%, transparent 100%);
    z-index: 1;
}}"""


def _light_decorations(template: dict, name: str) -> str:
    accent = template["accent"]
    if name == "minimal_cream":
        return f"""
body::before {{
    content: '';
    position: absolute; inset: 0;
    background:
        radial-gradient(ellipse 600px 600px at 80% 15%, {accent}06 0%, transparent 60%),
        radial-gradient(ellipse 400px 400px at 10% 85%, {accent}04 0%, transparent 60%);
    z-index: 1;
}}"""
    elif name == "sage_garden":
        return f"""
body::before {{
    content: '';
    position: absolute; inset: 0;
    background:
        radial-gradient(ellipse 500px 500px at 75% 20%, {accent}08 0%, transparent 60%),
        radial-gradient(ellipse 350px 350px at 20% 80%, {accent}05 0%, transparent 60%);
    z-index: 1;
}}"""
    else:
        return f"""
body::before {{
    content: '';
    position: absolute; inset: 0;
    background: radial-gradient(ellipse 700px 700px at 50% 50%, {accent}04 0%, transparent 60%);
    z-index: 1;
}}
body::after {{
    content: '';
    position: absolute;
    top: 30px; left: 30px; right: 30px; bottom: 30px;
    border: 1px solid rgba(0,0,0,0.04);
    z-index: 2;
    pointer-events: none;
}}"""


# ── Rendering ────────────────────────────────────────────────────────────────

def render_html_to_image(html: str, out_path: str) -> None:
    from playwright.sync_api import sync_playwright
    from PIL import Image

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    png_path = out_path.replace(".jpg", ".png")

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(
            viewport={"width": CANVAS_SIZE, "height": CANVAS_SIZE},
            device_scale_factor=2,
        )
        page.set_content(html)
        page.wait_for_timeout(2500)
        page.screenshot(path=png_path, type="png")
        browser.close()

    img = Image.open(png_path).convert("RGB")
    img = img.resize((CANVAS_SIZE, CANVAS_SIZE), Image.LANCZOS)
    img.save(out_path, "JPEG", quality=95, optimize=True)

    if os.path.exists(png_path):
        os.remove(png_path)

    if DEBUG:
        print(f"[DEBUG] Imagen guardada: {out_path} ({os.path.getsize(out_path)} bytes)")


# ── Gemini content generation ────────────────────────────────────────────────

def debug(msg: str) -> None:
    if DEBUG:
        print(f"[DEBUG] {msg}")


def today_madrid() -> str:
    madrid = tz.gettz("Europe/Madrid")
    return datetime.now(tz=madrid).date().isoformat()


def get_client():
    from google import genai
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta GEMINI_API_KEY en variables de entorno.")
    return genai.Client(api_key=api_key)


def safe_json_from_response(response: Any) -> dict:
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini no devolvió texto.")
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return json.loads(text)


def generate_ia_content() -> tuple[str, str, str]:
    """Devuelve: theme, phrase, caption."""
    from google import genai
    from google.genai import types

    client = get_client()

    valid_themes = ", ".join(THEME_TEMPLATE_MAP.keys())

    prompt = f"""
Eres copywriter de una cuenta de Instagram de reflexiones psicológicas y emocionales en español.

Genera:
1. Una frase breve y emocional (máximo 12 palabras, sin comillas).
2. Un caption completo para Instagram.
3. Un theme (una sola palabra en inglés o español).

Reglas de la frase:
- Máximo 12 palabras.
- Debe sonar humana, emocional y compartible.
- Evita clichés muy usados como "todo pasa" o "eres suficiente".
- Sin comillas en el JSON.
- Debe provocar una emoción real, no sonar a póster motivacional genérico.

Reglas del caption:
- Línea 1: hook corto e impactante (máx 8 palabras).
- Luego 2-4 párrafos breves que validen una emoción real.
- Cierra con CTA suave ("guárdalo", "comparte si resonó").
- 8-10 hashtags relevantes en español al final.

Themes válidos: {valid_themes}

Devuelve SOLO JSON válido:
{{
  "theme": "...",
  "phrase": "...",
  "caption": "..."
}}
""".strip()

    schema = {
        "type": "object",
        "properties": {
            "theme":   {"type": "string"},
            "phrase":  {"type": "string"},
            "caption": {"type": "string"},
        },
        "required": ["theme", "phrase", "caption"],
        "propertyOrdering": ["theme", "phrase", "caption"],
    }

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=schema,
                temperature=0.9,
            ),
        )
        content = safe_json_from_response(response)
        theme   = str(content["theme"]).strip()
        phrase  = str(content["phrase"]).strip()
        caption = str(content["caption"]).strip()
        debug(f"theme={theme}")
        debug(f"phrase={phrase}")
        return theme, phrase, caption

    except Exception as e:
        debug(f"Error Gemini: {e}")
        return (
            "healing",
            "Sanar no es olvidar, es dejar de sangrar por lo mismo",
            "No tienes que borrarlo todo para avanzar.\n\n"
            "Sanar es aprender a cargar con lo vivido de una forma más liviana.\n\n"
            "A tu ritmo. Sin prisa. Sin juicio.\n\n"
            "Guárdalo si hoy lo necesitas.\n\n"
            "#sanar #saludmental #crecimientopersonal #autocuidado #amorpropio "
            "#bienestar #reflexiones #psicologia #ansiedad #paz",
        )


# ── Pipeline principal ───────────────────────────────────────────────────────

def render_image(phrase: str, handle: str, theme: str = "healing",
                 out_path: str = f"{OUT_DIR}/{IMG_NAME}") -> str:
    os.makedirs(OUT_DIR, exist_ok=True)

    template_name, template = pick_template(theme)

    debug(f"Template: {template_name} (theme: {theme})")
    debug(f"Frase: {phrase}")

    html = build_html(phrase, handle, template, template_name)

    html_path = out_path.replace(".jpg", ".html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    render_html_to_image(html, out_path)
    return template_name


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    theme, phrase, caption = generate_ia_content()
    handle = os.environ.get("IG_HANDLE", "@tu_cuenta")

    template_used = render_image(
        phrase=phrase, handle=handle, theme=theme,
        out_path=f"{OUT_DIR}/{IMG_NAME}",
    )

    payload = {
        "date":       today_madrid(),
        "theme":      theme,
        "phrase":     phrase,
        "caption":    caption,
        "template":   template_used,
        "image_path": f"{OUT_DIR}/{IMG_NAME}",
    }

    with open(f"{OUT_DIR}/post.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    shutil.copyfile(f"{OUT_DIR}/{IMG_NAME}", f"{PUBLIC_DIR}/latest.jpg")

    with open(f"{PUBLIC_DIR}/latest.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("Post generado correctamente.")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
