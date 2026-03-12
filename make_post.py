import json
import math
import os
import random
from datetime import datetime
from typing import Any

from dateutil import tz
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from google import genai
from google.genai import types

OUT_DIR = "out"
IMG_NAME = "post.jpg"
DEBUG = True

CANVAS_SIZE = 1080


# =========================
# Utils
# =========================

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
        raise RuntimeError("Gemini no devolvió texto para el JSON.")

    text = text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    return json.loads(text)


# =========================
# AI text only
# =========================

def generate_ia_content() -> tuple[str, str, str, str]:
    """
    Devuelve:
    - theme
    - phrase
    - caption
    - visual_metaphor
    """
    client = get_client()

    prompt = """
Eres copywriter y director creativo de una cuenta de Instagram de reflexiones psicológicas y emocionales.

Tu tarea es generar:
- una frase breve
- un caption
- una metáfora visual simple para una ilustración minimal emocional

IMPORTANTE:
NO debes describir una foto.
NO debes describir un fondo abstracto.
NO debes describir una escena cinematográfica.
Debes elegir una metáfora visual SIMPLE que pueda ilustrarse con un personaje y pocos elementos.

El estilo visual final será:
- ilustración emocional minimal
- personaje simple
- líneas suaves
- composición limpia
- estética viral de cuenta de reflexiones

Temas de la cuenta:
- límites
- ansiedad
- agotamiento mental
- duelo
- autoestima
- sanar
- culpa
- sobrepensar
- desapego

Tono:
- íntimo
- humano
- claro
- elegante
- no cursi
- no coach barato

Devuelve SOLO JSON válido con esta estructura:
{
  "theme": "...",
  "phrase": "...",
  "caption": "...",
  "visual_metaphor": "..."
}

Reglas:

1) phrase
- Máximo 12 palabras.
- Debe sonar humana, compartible y emocional.
- Evita clichés de autoayuda.
- Mejor corta que larga.

2) caption
- Primera línea: hook corto.
- Luego 2 a 4 párrafos breves.
- Debe validar emoción real.
- Cierra con CTA suave.
- Añade 8 a 10 hashtags relevantes.

3) theme
- Una sola palabra en inglés.

4) visual_metaphor
Debe ser SOLO una de estas opciones exactas:
- rain_cloud
- hourglass
- self_hug
- heavy_backpack
- shadow_wave
- sitting_scribble

Elige la que mejor represente la frase.

Devuelve SOLO JSON.
""".strip()

    schema = {
        "type": "object",
        "properties": {
            "theme": {"type": "string"},
            "phrase": {"type": "string"},
            "caption": {"type": "string"},
            "visual_metaphor": {
                "type": "string",
                "enum": [
                    "rain_cloud",
                    "hourglass",
                    "self_hug",
                    "heavy_backpack",
                    "shadow_wave",
                    "sitting_scribble",
                ],
            },
        },
        "required": ["theme", "phrase", "caption", "visual_metaphor"],
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

        theme = str(content["theme"]).strip()
        phrase = str(content["phrase"]).strip()
        caption = str(content["caption"]).strip()
        visual_metaphor = str(content["visual_metaphor"]).strip()

        debug(f"theme={theme}")
        debug(f"phrase={phrase}")
        debug(f"visual_metaphor={visual_metaphor}")

        return theme, phrase, caption, visual_metaphor

    except Exception as e:
        debug(f"Error Gemini texto: {e}")
        return (
            "boundaries",
            "A veces el límite sano es dejar de explicarte.",
            "No todo necesita una defensa extensa.\n\nA veces insistir en que te entiendan solo te agota más.\n\nPoner un límite también es elegir en qué gastas tu energía.\n\nGuárdalo si hoy necesitas recordarlo. 🤍\n\n#limites #saludmental #psicologia #ansiedad #autocuidado #amorpropio #bienestar #reflexiones #cansancioemocional",
            "rain_cloud",
        )


# =========================
# Visual system
# =========================

PALETTES = {
    "blue_gray": {
        "bg": (224, 229, 235),
        "ground": (204, 211, 219),
        "line": (86, 96, 110),
        "accent": (124, 136, 152),
        "soft": (200, 208, 218),
        "text": (245, 244, 239),
        "shadow": (25, 25, 25),
    },
    "sage": {
        "bg": (225, 231, 224),
        "ground": (207, 215, 206),
        "line": (90, 102, 92),
        "accent": (122, 138, 124),
        "soft": (206, 214, 205),
        "text": (246, 244, 239),
        "shadow": (25, 25, 25),
    },
    "dusty_pink": {
        "bg": (233, 223, 225),
        "ground": (216, 205, 208),
        "line": (110, 92, 97),
        "accent": (145, 120, 128),
        "soft": (223, 214, 217),
        "text": (246, 244, 239),
        "shadow": (25, 25, 25),
    },
    "beige": {
        "bg": (229, 224, 215),
        "ground": (214, 207, 196),
        "line": (102, 96, 88),
        "accent": (140, 132, 120),
        "soft": (220, 214, 205),
        "text": (246, 244, 239),
        "shadow": (25, 25, 25),
    },
}


def choose_palette(theme: str, metaphor: str) -> dict:
    if metaphor in {"rain_cloud", "sitting_scribble", "shadow_wave"}:
        return PALETTES["blue_gray"]
    if metaphor == "self_hug":
        return PALETTES["dusty_pink"]
    if metaphor == "heavy_backpack":
        return PALETTES["sage"]
    if metaphor == "hourglass":
        return PALETTES["beige"]
    return PALETTES["blue_gray"]


def create_base_canvas(size: int, palette: dict) -> Image.Image:
    img = Image.new("RGB", (size, size), palette["bg"])
    draw = ImageDraw.Draw(img)

    # suelo suave
    draw.rectangle((0, int(size * 0.74), size, size), fill=palette["ground"])

    # textura muy sutil
    noise = Image.effect_noise((size, size), 8).convert("L")
    noise = ImageOps.colorize(
        noise,
        black=tuple(max(0, c - 10) for c in palette["bg"]),
        white=tuple(min(255, c + 8) for c in palette["bg"]),
    ).convert("RGB")
    img = Image.blend(img, noise, 0.05)

    return img


def line(draw: ImageDraw.ImageDraw, pts, fill, width=7):
    draw.line(pts, fill=fill, width=width, joint="curve")


def circle(draw: ImageDraw.ImageDraw, xy, fill=None, outline=None, width=5):
    draw.ellipse(xy, fill=fill, outline=outline, width=width)


def rounded_rect(draw: ImageDraw.ImageDraw, xy, radius, fill=None, outline=None, width=4):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_cloud(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float, fill, outline=None):
    r1 = int(70 * scale)
    r2 = int(85 * scale)
    r3 = int(68 * scale)

    circle(draw, (cx - 130 * scale, cy - 25 * scale, cx - 20 * scale, cy + 70 * scale), fill=fill, outline=outline, width=4)
    circle(draw, (cx - 55 * scale, cy - 70 * scale, cx + 75 * scale, cy + 65 * scale), fill=fill, outline=outline, width=4)
    circle(draw, (cx + 35 * scale, cy - 20 * scale, cx + 150 * scale, cy + 70 * scale), fill=fill, outline=outline, width=4)
    draw.rectangle((cx - 120 * scale, cy + 10 * scale, cx + 115 * scale, cy + 65 * scale), fill=fill)


def draw_scribble(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, color, width=6):
    points = []
    for i in range(28):
        ang = (math.pi * 2 / 28) * i
        rr = radius * (0.65 + 0.35 * random.random())
        x = cx + rr * math.cos(ang)
        y = cy + rr * math.sin(ang)
        points.append((x, y))
    points.append(points[0])
    line(draw, points, fill=color, width=width)


def draw_stick_person(draw: ImageDraw.ImageDraw, cx: int, base_y: int, scale: float, color):
    head_r = int(42 * scale)
    torso = int(120 * scale)
    arm = int(78 * scale)
    leg = int(90 * scale)

    circle(draw, (cx - head_r, base_y - torso - head_r * 2, cx + head_r, base_y - torso), fill=None, outline=color, width=7)
    line(draw, [(cx, base_y - torso), (cx, base_y)], fill=color, width=8)
    line(draw, [(cx, base_y - torso + 45 * scale), (cx - arm, base_y - torso + 90 * scale)], fill=color, width=7)
    line(draw, [(cx, base_y - torso + 45 * scale), (cx + arm, base_y - torso + 90 * scale)], fill=color, width=7)
    line(draw, [(cx, base_y), (cx - leg, base_y + leg)], fill=color, width=7)
    line(draw, [(cx, base_y), (cx + leg, base_y + leg)], fill=color, width=7)


def draw_person_with_backpack(draw: ImageDraw.ImageDraw, cx: int, base_y: int, scale: float, palette: dict):
    color = palette["line"]
    accent = palette["accent"]
    head_r = int(42 * scale)

    circle(draw, (cx - head_r, base_y - 230 * scale, cx + head_r, base_y - 146 * scale), fill=None, outline=color, width=7)
    line(draw, [(cx, base_y - 146 * scale), (cx, base_y - 20 * scale)], fill=color, width=8)
    line(draw, [(cx, base_y - 110 * scale), (cx - 75 * scale, base_y - 50 * scale)], fill=color, width=7)
    line(draw, [(cx, base_y - 110 * scale), (cx + 55 * scale, base_y - 65 * scale)], fill=color, width=7)
    line(draw, [(cx, base_y - 20 * scale), (cx - 60 * scale, base_y + 80 * scale)], fill=color, width=7)
    line(draw, [(cx, base_y - 20 * scale), (cx + 60 * scale, base_y + 80 * scale)], fill=color, width=7)

    rounded_rect(
        draw,
        (cx + 20 * scale, base_y - 160 * scale, cx + 125 * scale, base_y - 20 * scale),
        radius=int(16 * scale),
        fill=None,
        outline=accent,
        width=6,
    )


def draw_person_self_hug(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float, palette: dict):
    color = palette["line"]
    accent = palette["accent"]

    head_r = int(46 * scale)
    circle(draw, (cx - head_r, cy - 180 * scale, cx + head_r, cy - 88 * scale), fill=None, outline=color, width=7)

    # torso oval
    circle(draw, (cx - 70 * scale, cy - 90 * scale, cx + 70 * scale, cy + 95 * scale), fill=None, outline=color, width=7)

    # arms hugging
    line(draw, [(cx - 78 * scale, cy - 35 * scale), (cx - 10 * scale, cy + 20 * scale), (cx + 45 * scale, cy - 5 * scale)], fill=accent, width=8)
    line(draw, [(cx + 78 * scale, cy - 35 * scale), (cx + 10 * scale, cy + 22 * scale), (cx - 46 * scale, cy - 4 * scale)], fill=accent, width=8)

    # legs
    line(draw, [(cx - 22 * scale, cy + 90 * scale), (cx - 50 * scale, cy + 165 * scale)], fill=color, width=7)
    line(draw, [(cx + 22 * scale, cy + 90 * scale), (cx + 50 * scale, cy + 165 * scale)], fill=color, width=7)


def draw_hourglass(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float, palette: dict):
    color = palette["line"]
    accent = palette["accent"]

    w = 180 * scale
    h = 260 * scale

    # frame
    line(draw, [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2)], fill=color, width=8)
    line(draw, [(cx - w / 2, cy + h / 2), (cx + w / 2, cy + h / 2)], fill=color, width=8)
    line(draw, [(cx - w / 2 + 15 * scale, cy - h / 2), (cx - w / 2 + 30 * scale, cy + h / 2)], fill=color, width=7)
    line(draw, [(cx + w / 2 - 15 * scale, cy - h / 2), (cx + w / 2 - 30 * scale, cy + h / 2)], fill=color, width=7)

    # glass
    line(draw, [(cx - 50 * scale, cy - 85 * scale), (cx + 50 * scale, cy - 85 * scale)], fill=accent, width=5)
    line(draw, [(cx - 50 * scale, cy + 85 * scale), (cx + 50 * scale, cy + 85 * scale)], fill=accent, width=5)
    line(draw, [(cx - 50 * scale, cy - 85 * scale), (cx, cy)], fill=accent, width=5)
    line(draw, [(cx + 50 * scale, cy - 85 * scale), (cx, cy)], fill=accent, width=5)
    line(draw, [(cx - 50 * scale, cy + 85 * scale), (cx, cy)], fill=accent, width=5)
    line(draw, [(cx + 50 * scale, cy + 85 * scale), (cx, cy)], fill=accent, width=5)

    # sand
    draw.polygon(
        [(cx - 38 * scale, cy - 52 * scale), (cx + 38 * scale, cy - 52 * scale), (cx, cy - 8 * scale)],
        fill=palette["soft"],
    )
    draw.polygon(
        [(cx - 34 * scale, cy + 60 * scale), (cx + 34 * scale, cy + 60 * scale), (cx, cy + 25 * scale)],
        fill=palette["soft"],
    )
    line(draw, [(cx, cy - 4 * scale), (cx, cy + 20 * scale)], fill=palette["soft"], width=3)


def draw_wave(draw: ImageDraw.ImageDraw, size: int, palette: dict):
    color = palette["soft"]
    pts = []
    for x in range(0, size + 1, 30):
        y = int(675 + 40 * math.sin(x / 90))
        pts.append((x, y))
    pts += [(size, size), (0, size)]
    draw.polygon(pts, fill=color)


def render_metaphor_background(size: int, theme: str, metaphor: str) -> Image.Image:
    palette = choose_palette(theme, metaphor)
    img = create_base_canvas(size, palette)
    draw = ImageDraw.Draw(img)

    # decor sutil arriba, para que no quede vacío total
    for i in range(8):
        x = random.randint(60, size - 60)
        y = random.randint(70, 250)
        draw.arc((x - 24, y - 10, x + 24, y + 10), 15, 165, fill=palette["soft"], width=2)

    if metaphor == "rain_cloud":
        draw_cloud(draw, cx=size // 2, cy=330, scale=1.25, fill=palette["soft"])
        for x in [420, 470, 520, 570, 620]:
            line(draw, [(x, 420), (x - 8, 455)], fill=palette["accent"], width=4)
        draw_stick_person(draw, cx=size // 2, base_y=805, scale=1.1, color=palette["line"])

    elif metaphor == "hourglass":
        draw_hourglass(draw, cx=620, cy=705, scale=1.3, palette=palette)
        # persona empujando
        draw_person_with_backpack(draw, cx=330, base_y=820, scale=1.05, palette=palette)
        line(draw, [(395, 690), (510, 660)], fill=palette["line"], width=6)

    elif metaphor == "self_hug":
        draw_person_self_hug(draw, cx=size // 2, cy=690, scale=1.3, palette=palette)
        for i in range(6):
            draw.arc((180 + i * 110, 180, 280 + i * 110, 240), 20, 160, fill=palette["soft"], width=3)

    elif metaphor == "heavy_backpack":
        draw_person_with_backpack(draw, cx=size // 2, base_y=820, scale=1.25, palette=palette)
        # piedras simples
        for i in range(4):
            circle(draw, (640 + i * 12, 470 + i * 18, 690 + i * 12, 510 + i * 18), outline=palette["accent"], width=4)

    elif metaphor == "shadow_wave":
        draw_wave(draw, size=size, palette=palette)
        draw_stick_person(draw, cx=320, base_y=800, scale=1.0, color=palette["line"])
        # sombra/ola grande
        draw.polygon(
            [(650, 760), (860, 430), (980, 760)],
            outline=palette["accent"],
            fill=None,
        )
        line(draw, [(650, 760), (860, 430), (980, 760)], fill=palette["accent"], width=8)

    elif metaphor == "sitting_scribble":
        draw_scribble(draw, cx=size // 2, cy=315, radius=95, color=palette["accent"], width=6)
        # persona sentada
        circle(draw, (500, 465, 580, 545), fill=None, outline=palette["line"], width=7)
        line(draw, [(540, 545), (540, 655)], fill=palette["line"], width=8)
        line(draw, [(540, 585), (485, 635)], fill=palette["line"], width=7)
        line(draw, [(540, 595), (605, 645)], fill=palette["line"], width=7)
        line(draw, [(540, 655), (470, 760)], fill=palette["line"], width=7)
        line(draw, [(540, 655), (620, 760)], fill=palette["line"], width=7)

    else:
        draw_stick_person(draw, cx=size // 2, base_y=805, scale=1.1, color=palette["line"])

    # textura final
    img = img.filter(ImageFilter.GaussianBlur(radius=0.2))
    return img


# =========================
# Text layout
# =========================

def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines = []
    line_words = []

    for word in words:
        candidate = " ".join(line_words + [word])
        if draw.textlength(candidate, font=font) <= max_width:
            line_words.append(word)
        else:
            if line_words:
                lines.append(" ".join(line_words))
            line_words = [word]

    if line_words:
        lines.append(" ".join(line_words))

    return lines


def choose_layout(metaphor: str) -> dict:
    # texto arriba, dibujo abajo: estilo más consistente
    return {
        "text_center_x": CANVAS_SIZE // 2,
        "text_center_y": 210,
        "text_width": 760,
        "handle_y": 980,
    }


def load_fonts():
    serif_path = "assets/fonts/PlayfairDisplay-Regular.ttf"
    handle_path = "assets/fonts/PlayfairDisplay-Regular.ttf"

    if os.path.exists(serif_path):
        quote_font = ImageFont.truetype(serif_path, 56)
        handle_font = ImageFont.truetype(handle_path, 22)
    else:
        quote_font = ImageFont.load_default()
        handle_font = ImageFont.load_default()

    return quote_font, handle_font


def render_text_overlay(
    img: Image.Image,
    quote: str,
    metaphor: str,
    palette: dict,
    handle: str,
) -> Image.Image:
    draw = ImageDraw.Draw(img)
    quote_font, handle_font = load_fonts()
    layout = choose_layout(metaphor)

    quote_text = f"“{quote}”"
    lines = wrap_text(draw, quote_text, quote_font, layout["text_width"])

    line_height = 72
    total_h = len(lines) * line_height
    y = layout["text_center_y"] - total_h // 2

    for line_txt in lines:
        text_w = draw.textlength(line_txt, font=quote_font)
        x = layout["text_center_x"] - text_w / 2

        # sombra suave
        draw.text((x + 2, y + 2), line_txt, font=quote_font, fill=palette["shadow"])
        draw.text((x, y), line_txt, font=quote_font, fill=palette["text"])
        y += line_height

    if handle:
        hw = draw.textlength(handle, font=handle_font)
        hx = (img.size[0] - hw) / 2
        draw.text((hx, layout["handle_y"]), handle, font=handle_font, fill=tuple(max(150, c - 20) for c in palette["text"]))

    return img


# =========================
# Main render
# =========================

def render_quote_image(
    quote: str,
    theme: str,
    visual_metaphor: str,
    handle: str = "@tu_cuenta",
    out_path: str = f"{OUT_DIR}/{IMG_NAME}",
) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    palette = choose_palette(theme, visual_metaphor)
    img = render_metaphor_background(CANVAS_SIZE, theme, visual_metaphor)
    img = render_text_overlay(img, quote, visual_metaphor, palette, handle)

    img = img.convert("RGB")
    img.save(out_path, "JPEG", quality=94, optimize=True)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    theme, phrase, caption, visual_metaphor = generate_ia_content()
    handle = os.environ.get("IG_HANDLE", "@tu_cuenta")

    render_quote_image(
        quote=phrase,
        theme=theme,
        visual_metaphor=visual_metaphor,
        handle=handle,
        out_path=f"{OUT_DIR}/{IMG_NAME}",
    )

    payload = {
        "date": today_madrid(),
        "theme": theme,
        "phrase": phrase,
        "caption": caption,
        "visual_metaphor": visual_metaphor,
        "image_path": f"{OUT_DIR}/{IMG_NAME}",
    }

    with open(f"{OUT_DIR}/post.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("Post generado con éxito.")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
