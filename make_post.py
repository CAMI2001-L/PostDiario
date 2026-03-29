import json
import os
import random
import shutil
from datetime import datetime
from typing import Any

from dateutil import tz
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from google import genai
from google.genai import types

OUT_DIR    = "out"
PUBLIC_DIR = "public"
IMG_NAME   = "post.jpg"
CANVAS_SIZE = 1080
DEBUG = True

# ── Paleta azul profundo ──────────────────────────────────────────────────────
BG1     = (2,   6,  23)
BG2     = (15,  23,  42)
BG3     = (30,  64, 175)
CIRCLE1 = (29,  78, 216)
CIRCLE2 = (30,  58, 138)
CIRCLE3 = (59, 130, 246)
CIRCLE4 = (96, 165, 250)
ACCENT  = (191, 219, 254)
ACCENT2 = (253, 230, 138)
TEXT_COL = (239, 246, 255)
SUB_COL  = (147, 197, 253)
# ─────────────────────────────────────────────────────────────────────────────


def debug(msg: str) -> None:
    if DEBUG:
        print(f"[DEBUG] {msg}")


def today_madrid() -> str:
    madrid = tz.gettz("Europe/Madrid")
    return datetime.now(tz=madrid).date().isoformat()


def get_client() -> genai.Client:
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
    client = get_client()

    prompt = """
Eres copywriter de una cuenta de Instagram de reflexiones psicológicas y emocionales en español.

Genera:
1. Una frase breve y emocional (máximo 12 palabras, sin comillas).
2. Un caption completo para Instagram.
3. Un theme (una sola palabra en inglés).

Reglas de la frase:
- Máximo 12 palabras.
- Debe sonar humana, emocional y compartible.
- Evita clichés muy usados.
- Sin comillas en el JSON.

Reglas del caption:
- Línea 1: hook corto e impactante.
- Luego 2-4 párrafos breves que validen una emoción real.
- Cierra con CTA suave.
- 8-10 hashtags relevantes en español al final.

Devuelve SOLO JSON válido:
{
  "theme": "...",
  "phrase": "...",
  "caption": "..."
}
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
            "Sanar no es olvidar, es aprender a seguir.",
            "No tienes que borrarlo todo para avanzar.\n\n"
            "Sanar es aprender a cargar con lo vivido de una forma más liviana.\n\n"
            "A tu ritmo. Sin prisa. Sin juicio.\n\n"
            "Guárdalo si hoy lo necesitas.\n\n"
            "#sanar #saludmental #crecimientopersonal #autocuidado #amorpropio "
            "#bienestar #reflexiones #psicologia #ansiedad #paz",
        )


# ── Helpers de dibujo ─────────────────────────────────────────────────────────

def alpha_paste(base: Image.Image, overlay: Image.Image) -> Image.Image:
    result = Image.alpha_composite(base.convert("RGBA"), overlay)
    return result.convert("RGB")


def draw_radial_glow(size: int, cx: float, cy: float,
                      radius: float, color: tuple, max_alpha: int) -> Image.Image:
    """Crea una capa RGBA con un círculo difuminado."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw  = ImageDraw.Draw(layer)
    steps = 24
    for i in range(steps, 0, -1):
        ratio = i / steps
        alpha = int(max_alpha * (1 - ratio) ** 1.7)
        r     = radius * ratio
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, alpha))
    return layer


def make_background(size: int) -> Image.Image:
    img  = Image.new("RGB", (size, size), BG1)
    draw = ImageDraw.Draw(img)
    cx, cy = size * 0.38, size * 0.32
    steps = 70
    for i in range(steps, 0, -1):
        ratio = i / steps
        r = size * 0.9 * ratio
        t = ratio ** 1.9
        col = tuple(int(BG1[c] + (BG3[c] - BG1[c]) * (1 - t)) for c in range(3))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    return img


def add_glow_circles(img: Image.Image, size: int) -> Image.Image:
    specs = [
        (size * 0.88, size * 0.11, size * 0.30, CIRCLE1, 60),
        (size * 0.10, size * 0.84, size * 0.23, CIRCLE2, 50),
        (size * 0.78, size * 0.83, size * 0.18, CIRCLE3, 42),
        (size * 0.14, size * 0.20, size * 0.14, CIRCLE4, 36),
    ]
    for cx, cy, r, col, alpha in specs:
        layer = draw_radial_glow(size, cx, cy, r, col, alpha)
        img   = alpha_paste(img, layer)
    return img


def add_stars(img: Image.Image, size: int) -> Image.Image:
    rng = random.Random(42)
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw  = ImageDraw.Draw(layer)

    positions = [
        (0.04, 0.035), (0.27, 0.016), (0.92, 0.026), (0.96, 0.051),
        (0.03, 0.145), (0.96, 0.172), (0.50, 0.016), (0.53, 0.970),
        (0.06, 0.285), (0.94, 0.340), (0.03, 0.565), (0.96, 0.590),
        (0.05, 0.895), (0.27, 0.965), (0.73, 0.965), (0.94, 0.920),
        (0.78, 0.225), (0.20, 0.775), (0.85, 0.50),  (0.10, 0.50),
    ]
    for px, py in positions:
        x, y  = int(px * size), int(py * size)
        alpha = rng.randint(130, 210)
        r     = rng.choice([2, 3, 4])
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(*ACCENT2, alpha))
        arm = int(size * 0.013)
        draw.line([(x - arm, y), (x + arm, y)], fill=(*ACCENT2, alpha // 2), width=1)
        draw.line([(x, y - arm), (x, y + arm)], fill=(*ACCENT2, alpha // 2), width=1)

    return alpha_paste(img, layer)


def add_horizon_lines(img: Image.Image, size: int) -> Image.Image:
    """Líneas horizontales que se desvanecen en los extremos."""
    layer  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw   = ImageDraw.Draw(layer)
    margin = int(size * 0.07)
    usable = size - margin * 2

    for y in [int(size * 0.272), int(size * 0.812)]:
        steps = 60
        for i in range(steps):
            ratio = i / steps
            t     = 1 - abs(ratio - 0.5) * 2       # campana 0→1→0
            alpha = int(130 * t ** 0.6)
            x1    = margin + int(usable * ratio)
            x2    = margin + int(usable * (ratio + 1 / steps))
            draw.line([(x1, y), (x2, y)], fill=(*ACCENT, alpha), width=2)

    return alpha_paste(img, layer)


def add_text_box(img: Image.Image, size: int) -> Image.Image:
    layer  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw   = ImageDraw.Draw(layer)
    margin = int(size * 0.07)
    box_y  = int(size * 0.285)
    box_h  = int(size * 0.435)
    radius = int(size * 0.024)

    draw.rounded_rectangle(
        [margin, box_y, size - margin, box_y + box_h],
        radius=radius,
        fill=(0, 0, 0, 68),
        outline=(*ACCENT, 52),
        width=2,
    )
    return alpha_paste(img, layer)


def add_decorative_quotes(img: Image.Image, size: int, font_path: str | None) -> Image.Image:
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw  = ImageDraw.Draw(layer)
    q_sz  = int(size * 0.21)
    try:
        qfont = ImageFont.truetype(font_path, q_sz) if font_path else ImageFont.load_default()
    except Exception:
        qfont = ImageFont.load_default()

    draw.text((int(size * 0.03), int(size * 0.22)), "\u201C",
              font=qfont, fill=(*ACCENT, 38))
    draw.text((int(size * 0.78), int(size * 0.59)), "\u201D",
              font=qfont, fill=(*ACCENT, 28))
    return alpha_paste(img, layer)


def wrap_lines(text: str, font: ImageFont.FreeTypeFont,
               max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines, current = [], []
    for word in words:
        test = " ".join(current + [word])
        if draw.textlength(test, font=font) <= max_w:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def add_phrase_and_handle(img: Image.Image, phrase: str,
                           handle: str, size: int,
                           font_path: str | None) -> Image.Image:
    max_w    = int(size * 0.80)
    box_top  = int(size * 0.285)
    box_bot  = int(size * 0.720)
    box_mid  = (box_top + box_bot) // 2

    # Encontrar tamaño de fuente que quepa
    chosen_font  = None
    chosen_lines = []
    chosen_lh    = 0

    for fs in range(int(size * 0.078), int(size * 0.034), -2):
        try:
            font = ImageFont.truetype(font_path, fs) if font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        tmp_draw = ImageDraw.Draw(img.copy())
        lines    = wrap_lines(f"\u201c{phrase}\u201d", font, max_w, tmp_draw)
        lh       = int(fs * 1.48)
        total_h  = len(lines) * lh

        if total_h <= (box_bot - box_top - int(size * 0.035)):
            chosen_font  = font
            chosen_lines = lines
            chosen_lh    = lh
            break

    if not chosen_font:
        try:
            chosen_font = ImageFont.truetype(font_path, int(size * 0.038)) if font_path else ImageFont.load_default()
        except Exception:
            chosen_font = ImageFont.load_default()
        tmp_draw     = ImageDraw.Draw(img.copy())
        chosen_lines = wrap_lines(f"\u201c{phrase}\u201d", chosen_font, max_w, tmp_draw)
        chosen_lh    = int(size * 0.038 * 1.48)

    total_h = len(chosen_lines) * chosen_lh
    y_start = box_mid - total_h // 2

    # Sombra difuminada global para el bloque de texto
    shadow_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd           = ImageDraw.Draw(shadow_layer)
    for i, line in enumerate(chosen_lines):
        tw = sd.textlength(line, font=chosen_font)
        sx = (size - tw) / 2
        sy = y_start + i * chosen_lh
        sd.text((sx + 4, sy + 5), line, font=chosen_font, fill=(0, 0, 0, 150))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=7))
    img = alpha_paste(img, shadow_layer)

    # Texto principal
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(chosen_lines):
        tw = draw.textlength(line, font=chosen_font)
        x  = (size - tw) / 2
        y  = y_start + i * chosen_lh
        draw.text((x, y), line, font=chosen_font, fill=TEXT_COL)

    # Handle
    h_size = int(size * 0.027)
    try:
        hfont = ImageFont.truetype(font_path, h_size) if font_path else ImageFont.load_default()
    except Exception:
        hfont = ImageFont.load_default()

    hw   = draw.textlength(handle, font=hfont)
    draw.text(((size - hw) / 2, int(size * 0.908)), handle,
              font=hfont, fill=(*SUB_COL, 185))

    return img


def add_dot_accent(img: Image.Image, size: int) -> Image.Image:
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw  = ImageDraw.Draw(layer)
    cx, cy = size // 2, int(size * 0.258)
    r = int(size * 0.009)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*ACCENT2, 230))
    return alpha_paste(img, layer)


def add_vignette(img: Image.Image, size: int) -> Image.Image:
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw  = ImageDraw.Draw(layer)
    steps = 28
    for i in range(steps):
        alpha  = int(90 * (i / steps) ** 2.2)
        margin = i * 2
        draw.rectangle(
            [margin, margin, size - margin - 1, size - margin - 1],
            outline=(0, 0, 0, alpha), width=2,
        )
    return alpha_paste(img, layer)


# ── Pipeline principal ────────────────────────────────────────────────────────

def render_image(phrase: str, handle: str,
                 out_path: str = f"{OUT_DIR}/{IMG_NAME}") -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    size = CANVAS_SIZE

    font_path = "assets/fonts/PlayfairDisplay-Regular.ttf"
    if not os.path.exists(font_path):
        font_path = None
        debug("Fuente no encontrada, usando default.")

    debug("Generando imagen...")
    img = make_background(size)
    img = add_glow_circles(img, size)
    img = add_stars(img, size)
    img = add_horizon_lines(img, size)
    img = add_text_box(img, size)
    img = add_decorative_quotes(img, size, font_path)
    img = add_phrase_and_handle(img, phrase, handle, size, font_path)
    img = add_dot_accent(img, size)
    img = add_vignette(img, size)

    img.convert("RGB").save(out_path, "JPEG", quality=95, optimize=True)
    debug(f"Imagen guardada: {out_path}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    theme, phrase, caption = generate_ia_content()
    handle = os.environ.get("IG_HANDLE", "@tu_cuenta")

    render_image(phrase=phrase, handle=handle, out_path=f"{OUT_DIR}/{IMG_NAME}")

    payload = {
        "date":       today_madrid(),
        "theme":      theme,
        "phrase":     phrase,
        "caption":    caption,
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
