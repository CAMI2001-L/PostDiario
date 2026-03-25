import io
import json
import os
import shutil
import random
import urllib.parse
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
    Devuelve: theme, phrase, caption, scene_prompt
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
- Describe una escena ilustrada tipo lofi / cozy art de Instagram.
- Incluye SIEMPRE a la persona joven con sudadera oversized.
- Fondo con elementos de ambiente (cuarto, plantas, luz de ventana, libros, taza, etc).
- Termina SIEMPRE con exactamente estas palabras:
  "lofi cozy illustration, soft pastel colors, clean digital art, emotional, instagram art style, masterpiece quality"

Buenos ejemplos de scene_prompt:
- "young person with dark messy hair lying on bedroom floor writing in a journal, oversized purple hoodie, headphones nearby, tea cup, stack of books, soft warm light, cozy purple room, lofi cozy illustration, soft pastel colors, clean digital art, emotional, instagram art style, masterpiece quality"
- "young person sitting by a rainy window wrapped in a blanket, mug of tea in hands, plants on the windowsill, soft diffused light, cozy bedroom atmosphere, lofi cozy illustration, soft pastel colors, clean digital art, emotional, instagram art style, masterpiece quality"
- "young person lying on a soft rug hugging their knees, surrounded by fairy lights and books, warm ambient glow, oversized sweater, cozy evening atmosphere, lofi cozy illustration, soft pastel colors, clean digital art, emotional, instagram art style, masterpiece quality"

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
            "healing",
            "Sanar no es olvidar, es aprender a seguir.",
            "No tienes que borrarlo todo para avanzar.\n\n"
            "Sanar es aprender a cargar con lo vivido de una forma más liviana.\n\n"
            "A tu ritmo. Sin prisa. Sin juicio.\n\n"
            "Guárdalo si hoy lo necesitas.\n\n"
            "#sanar #saludmental #crecimientopersonal #autocuidado #amorpropio #bienestar #reflexiones #psicologia #ansiedad #paz",
            "young person sitting by a rainy window wrapped in a blanket, mug of tea in hands, plants on the windowsill, soft diffused light, cozy bedroom atmosphere, lofi cozy illustration, soft pastel colors, clean digital art, emotional, instagram art style, masterpiece quality",
        )


# ---------------------------------------------------------------------------
# GENERACIÓN DE IMAGEN CON POLLINATIONS.AI (FLUX)
# Sin API key · Sin cuenta · Gratis · Alta calidad
# ---------------------------------------------------------------------------

def get_pollinations_image(scene_prompt: str, size=(1080, 1080)) -> Image.Image:
    """
    Genera imagen usando Pollinations.ai con modelo FLUX.
    API pública, sin key, sin registro, 100% gratis.
    """
    prompt = (
        f"{scene_prompt}, "
        "no text, no watermark, no letters, no words, "
        "square composition, highly detailed, beautiful soft lighting, "
        "professional digital illustration"
    )
    negative = (
        "photography, photo, realistic, 3d render, ugly, low quality, deformed, "
        "text, watermark, logo, letters, words, signature, blurry, "
        "bad anatomy, extra limbs, cartoon, anime, nsfw"
    )

    seed = random.randint(1, 999999)
    encoded_prompt = urllib.parse.quote(prompt)
    encoded_negative = urllib.parse.quote(negative)

    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?negative={encoded_negative}"
        f"&width=1024&height=1024"
        f"&model=flux"
        f"&seed={seed}"
        f"&nologo=true"
        f"&enhance=true"
    )

    debug("Solicitando imagen a Pollinations.ai (FLUX)...")

    try:
        response = requests.get(url, timeout=120)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "image" not in content_type:
            raise RuntimeError(f"Respuesta inesperada. Content-Type: {content_type}")

        img = Image.open(io.BytesIO(response.content)).convert("RGB")

        # Post-procesado suave para estética Instagram
        img = ImageEnhance.Contrast(img).enhance(1.06)
        img = ImageEnhance.Color(img).enhance(1.10)
        img = ImageEnhance.Brightness(img).enhance(1.02)
        img = img.filter(ImageFilter.GaussianBlur(radius=0.3))
        img = img.resize(size, Image.LANCZOS)

        debug("Imagen generada correctamente con Pollinations.ai ✓")
        return img

    except Exception as e:
        debug(f"Error Pollinations.ai: {e}")
        debug("Usando imagen de fallback.")
        return generate_fallback_image(size=size)


def generate_fallback_image(size=(1080, 1080)) -> Image.Image:
    """Fallback con gradiente — solo si Pollinations falla."""
    img = Image.new("RGB", size, (200, 185, 215))
    draw = ImageDraw.Draw(img)

    for i in range(size[1]):
        ratio = i / size[1]
        r = int(200 + (225 - 200) * ratio)
        g = int(185 + (210 - 185) * ratio)
        b = int(215 + (200 - 215) * ratio)
        draw.line([(0, i), (size[0], i)], fill=(r, g, b))

    draw.ellipse((100, int(size[1] * 0.72), size[0] - 100, int(size[1] * 0.88)), fill=(210, 195, 180))
    draw.ellipse((380, 820, 700, 870), fill=(185, 170, 155))
    draw.rounded_rectangle((420, 560, 680, 820), radius=50, fill=(90, 70, 130))
    draw.ellipse((460, 440, 590, 570), fill=(235, 210, 195))
    draw.ellipse((448, 425, 598, 535), fill=(35, 25, 45))
    draw.rounded_rectangle((310, 640, 440, 680), radius=20, fill=(90, 70, 130))
    draw.ellipse((290, 630, 330, 695), fill=(235, 210, 195))
    draw.rounded_rectangle((150, 640, 310, 790), radius=10, fill=(248, 240, 230))
    draw.line([(230, 640), (230, 790)], fill=(200, 185, 170), width=2)
    draw.rounded_rectangle((700, 720, 800, 800), radius=8, fill=(160, 120, 110))
    draw.ellipse((700, 710, 800, 735), fill=(175, 135, 125))
    draw.rectangle((840, 820, 860, 870), fill=(100, 80, 60))
    draw.ellipse((800, 750, 900, 835), fill=(100, 155, 100))
    draw.ellipse((820, 730, 880, 800), fill=(120, 175, 115))

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

    padding = 28
    text_area_top = 120
    text_area_bottom = text_area_top + block_height + padding * 2

    # Fondo semitransparente detrás del texto
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [70, text_area_top - padding, w - 70, text_area_bottom],
        radius=20,
        fill=(0, 0, 0, 90),
    )
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    # Frase con sombra
    y = text_area_top
    for line in lines:
        x = (w - draw.textlength(line, font=quote_font)) / 2
        draw.text((x + 2, y + 2), line, font=quote_font, fill=(0, 0, 0))
        draw.text((x, y), line, font=quote_font, fill=(252, 248, 240))
        y += line_height

    # Handle
    if handle:
        hx = (w - draw.textlength(handle, font=handle_font)) / 2
        draw.text((hx + 1, h - 88 + 1), handle, font=handle_font, fill=(0, 0, 0))
        draw.text((hx, h - 88), handle, font=handle_font, fill=(245, 242, 235))

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
    img = get_pollinations_image(scene_prompt, size=(CANVAS_SIZE, CANVAS_SIZE))
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
