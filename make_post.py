import io
import json
import os
import shutil
import time
from datetime import datetime
from typing import Any

import requests
from dateutil import tz
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from google import genai
from google.genai import types

OUT_DIR = "out"
PUBLIC_DIR = "public"
IMG_NAME = "post.jpg"
CANVAS_SIZE = 1080
DEBUG = True


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


def generate_ia_content() -> tuple[str, str, str, str]:
    """
    Devuelve:
    - theme
    - phrase
    - caption
    - scene_prompt
    """
    client = get_client()

    prompt = """
Eres copywriter y director creativo de una cuenta de Instagram de reflexiones psicológicas y emocionales.

Tu trabajo es generar:
- una frase breve
- un caption
- una descripción visual para una ilustración bonita

IMPORTANTE:
La imagen NO debe ser una fotografía.
La imagen NO debe ser un fondo abstracto.
La imagen debe ser una ilustración emocional bonita para Instagram.

La protagonista visual debe ser:
- una persona joven
- rasgos simples o faceless
- estilo dibujo limpio, bonito, emocional, tipo cuentas virales de reflexiones
- ropa casual cozy (sudadera, pantalón cómodo, calcetines o descalza)
- estética lofi / calm / cozy

Debes devolver SOLO JSON válido con esta estructura exacta:
{
  "theme": "...",
  "phrase": "...",
  "caption": "...",
  "scene_prompt": "..."
}

Reglas:

1) phrase
- Máximo 10 palabras.
- Debe sonar humana, emocional y compartible.
- Evita clichés.
- Mejor corta que larga.

2) caption
- Línea 1: hook corto.
- Luego 2 a 4 párrafos breves.
- Debe validar una emoción real.
- Debe cerrar con CTA suave.
- Añade 8 a 10 hashtags relevantes.

3) theme
- Una sola palabra en inglés.

4) scene_prompt
- Debe describir una escena ilustrada relacionada con la frase.
- Debe incluir SIEMPRE a la persona descrita.
- Debe ser visualmente clara y bonita.
- Debe poder funcionar en un post cuadrado de Instagram.
- Debe evitar fondos vacíos o de un solo color.
- Debe incluir uno o dos elementos visuales relacionados con la emoción.
- Debe terminar SIEMPRE con: "soft pastel illustration, instagram art style, NOT photography, NOT realistic, high quality digital art"

Buenos ejemplos de scene_prompt:
- "a young person with dark messy hair lying on the floor writing in a notebook, wearing an oversized cozy hoodie, headphones nearby, tea cup, books, soft purple room, emotional pastel illustration, instagram art style, NOT photography, NOT realistic, high quality digital art"
- "a young person hugging themselves softly while small tangled scribbles float above their head in a cozy bedroom, soft pastel illustration, instagram art style, NOT photography, NOT realistic, high quality digital art"
- "a young person sitting quietly while a large soft wave shape rises behind them as a metaphor for overwhelming thoughts, soft pastel illustration, instagram art style, NOT photography, NOT realistic, high quality digital art"

Devuelve SOLO JSON.
""".strip()

    schema = {
        "type": "object",
        "properties": {
            "theme": {"type": "string"},
            "phrase": {"type": "string"},
            "caption": {"type": "string"},
            "scene_prompt": {"type": "string"},
        },
        "required": ["theme", "phrase", "caption", "scene_prompt"],
        "propertyOrdering": ["theme", "phrase", "caption", "scene_prompt"],
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
        scene_prompt = str(content["scene_prompt"]).strip()

        debug(f"theme={theme}")
        debug(f"phrase={phrase}")
        debug(f"scene_prompt={scene_prompt}")

        return theme, phrase, caption, scene_prompt

    except Exception as e:
        debug(f"Error Gemini texto: {e}")
        return (
            "boundaries",
            "A veces poner límites también es quererte.",
            "No todo límite nace desde el rechazo.\n\n"
            "Muchos nacen desde el cansancio de seguir dándote por completo donde ya no hay cuidado.\n\n"
            "Poner distancia no siempre es frialdad.\n"
            "A veces es respeto por tu paz.\n\n"
            "Guárdalo si hoy necesitas recordarlo.\n\n"
            "#limites #saludmental #psicologia #autocuidado #amorpropio #bienestar #reflexiones #ansiedad #sanar",
            "a young person with dark messy hair standing in a cozy room, soft light coming through curtains, wearing an oversized hoodie, small plants nearby, peaceful expression, soft pastel illustration, instagram art style, NOT photography, NOT realistic, high quality digital art",
        )


# ---------------------------------------------------------------------------
# GENERACIÓN DE IMAGEN CON GEMINI IMAGEN
# ---------------------------------------------------------------------------

def get_gemini_image(scene_prompt: str, size=(1080, 1080)) -> Image.Image:
    """
    Genera la imagen usando Gemini Imagen (mismo GEMINI_API_KEY que ya tienes).
    Modelo: imagen-3.0-generate-002
    Cuota gratuita: suficiente para uso diario automatizado.
    """
    client = get_client()

    # Prompt reforzado para estilo ilustración
    full_prompt = (
        f"{scene_prompt}, "
        "soft pastel color palette, cozy lofi aesthetic, clean smooth lines, "
        "emotional digital illustration, pinterest art style, "
        "instagram mental health illustration, high quality, "
        "no text, no watermark, no letters"
    )

    debug(f"Solicitando imagen a Gemini Imagen...")
    debug(f"Prompt: {full_prompt[:120]}...")

    try:
        response = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=full_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="1:1",
                safety_filter_level="block_only_high",
                person_generation="allow_adult",
            ),
        )

        if not response.generated_images:
            raise RuntimeError("Gemini Imagen no devolvió imágenes.")

        img_bytes = response.generated_images[0].image.image_bytes
        debug("Imagen generada correctamente con Gemini Imagen ✓")

        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        # Leve mejora de color para posts de Instagram
        img = ImageEnhance.Contrast(img).enhance(1.05)
        img = ImageEnhance.Color(img).enhance(1.08)
        img = ImageEnhance.Brightness(img).enhance(1.02)
        img = img.filter(ImageFilter.GaussianBlur(radius=0.2))
        img = img.resize(size, Image.LANCZOS)

        return img

    except Exception as e:
        debug(f"Error Gemini Imagen: {e}")
        debug("Usando imagen de fallback.")
        return generate_fallback_image(size=size)


def generate_fallback_image(size=(1080, 1080)) -> Image.Image:
    """
    Fallback mejorado con gradiente y composición más cuidada.
    Solo se usa si Gemini Imagen falla.
    """
    img = Image.new("RGB", size, (200, 185, 215))
    draw = ImageDraw.Draw(img)

    # Fondo con gradiente suave simulado por capas
    for i in range(size[1]):
        ratio = i / size[1]
        r = int(200 + (225 - 200) * ratio)
        g = int(185 + (210 - 185) * ratio)
        b = int(215 + (200 - 215) * ratio)
        draw.line([(0, i), (size[0], i)], fill=(r, g, b))

    # Suelo
    draw.ellipse(
        (100, int(size[1] * 0.72), size[0] - 100, int(size[1] * 0.88)),
        fill=(210, 195, 180),
    )

    # Sombra persona
    draw.ellipse((380, 820, 700, 870), fill=(185, 170, 155))

    # Cuerpo sudadera
    draw.rounded_rectangle((420, 560, 680, 820), radius=50, fill=(90, 70, 130))

    # Cabeza
    draw.ellipse((460, 440, 590, 570), fill=(235, 210, 195))

    # Pelo
    draw.ellipse((448, 425, 598, 535), fill=(35, 25, 45))
    draw.ellipse((448, 425, 530, 490), fill=(35, 25, 45))

    # Brazo izquierdo extendido (leyendo)
    draw.rounded_rectangle((310, 640, 440, 680), radius=20, fill=(90, 70, 130))
    draw.ellipse((290, 630, 330, 695), fill=(235, 210, 195))

    # Libro / libreta
    draw.rounded_rectangle((150, 640, 310, 790), radius=10, fill=(248, 240, 230))
    draw.line([(230, 640), (230, 790)], fill=(200, 185, 170), width=2)
    draw.line([(165, 680), (225, 680)], fill=(180, 170, 155), width=2)
    draw.line([(165, 710), (225, 710)], fill=(180, 170, 155), width=2)
    draw.line([(165, 740), (225, 740)], fill=(180, 170, 155), width=2)

    # Taza de té (derecha)
    draw.rounded_rectangle((700, 720, 800, 800), radius=8, fill=(160, 120, 110))
    draw.ellipse((700, 710, 800, 735), fill=(175, 135, 125))
    draw.line([(800, 745), (830, 745), (830, 770), (800, 770)], fill=(130, 95, 85), width=4)
    # Vaporcito
    for xi, offset in [(725, 0), (755, 5), (785, 0)]:
        draw.line([(xi, 710), (xi + offset, 688), (xi, 666)], fill=(220, 215, 225), width=2)

    # Planta pequeña derecha
    draw.rectangle((840, 820, 860, 870), fill=(100, 80, 60))
    draw.ellipse((800, 750, 900, 835), fill=(100, 155, 100))
    draw.ellipse((820, 730, 880, 800), fill=(120, 175, 115))

    # Blur suave para aspecto más cuidado
    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
    return img


# ---------------------------------------------------------------------------
# TEXTO SOBRE LA IMAGEN
# ---------------------------------------------------------------------------

def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    words = text.split()
    lines = []
    line = []
    for word in words:
        candidate = " ".join(line + [word])
        if draw.textlength(candidate, font=font) <= max_width:
            line.append(word)
        else:
            if line:
                lines.append(" ".join(line))
            line = [word]
    if line:
        lines.append(" ".join(line))
    return lines


def draw_quote_text(img: Image.Image, phrase: str, handle: str) -> Image.Image:
    draw = ImageDraw.Draw(img)
    w, h = img.size

    font_path = "assets/fonts/PlayfairDisplay-Regular.ttf"
    if os.path.exists(font_path):
        quote_font = ImageFont.truetype(font_path, 58)
        handle_font = ImageFont.truetype(font_path, 24)
    else:
        quote_font = ImageFont.load_default()
        handle_font = ImageFont.load_default()

    max_width = w - 260
    lines = wrap_text(draw, f"\u201c{phrase}\u201d", quote_font, max_width)
    line_height = 72
    block_height = len(lines) * line_height

    # Fondo semitransparente detrás del texto para legibilidad
    padding = 24
    text_area_top = 140
    text_area_bottom = text_area_top + block_height + padding * 2

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [80, text_area_top - padding, w - 80, text_area_bottom],
        radius=18,
        fill=(0, 0, 0, 75),
    )
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    # Texto de la frase
    y = text_area_top
    for line in lines:
        x = (w - draw.textlength(line, font=quote_font)) / 2
        # Sombra
        draw.text((x + 2, y + 2), line, font=quote_font, fill=(0, 0, 0, 120) if hasattr(draw, "alpha_composite") else (0, 0, 0))
        # Texto principal
        draw.text((x, y), line, font=quote_font, fill=(250, 247, 240))
        y += line_height

    # Handle en la parte inferior
    if handle:
        hx = (w - draw.textlength(handle, font=handle_font)) / 2
        draw.text((hx + 1, h - 88 + 1), handle, font=handle_font, fill=(0, 0, 0))
        draw.text((hx, h - 88), handle, font=handle_font, fill=(240, 238, 232))

    return img


# ---------------------------------------------------------------------------
# PIPELINE PRINCIPAL
# ---------------------------------------------------------------------------

def render_quote_image(
    quote: str,
    scene_prompt: str,
    handle: str = "@tu_cuenta",
    out_path: str = f"{OUT_DIR}/{IMG_NAME}",
) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    img = get_gemini_image(scene_prompt, size=(CANVAS_SIZE, CANVAS_SIZE))
    img = draw_quote_text(img, quote, handle)
    img = img.convert("RGB")
    img.save(out_path, "JPEG", quality=94, optimize=True)
    debug(f"Imagen guardada en {out_path}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    theme, phrase, caption, scene_prompt = generate_ia_content()

    handle = os.environ.get("IG_HANDLE", "@tu_cuenta")

    render_quote_image(
        quote=phrase,
        scene_prompt=scene_prompt,
        handle=handle,
        out_path=f"{OUT_DIR}/{IMG_NAME}",
    )

    payload = {
        "date": today_madrid(),
        "theme": theme,
        "phrase": phrase,
        "caption": caption,
        "scene_prompt": scene_prompt,
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
