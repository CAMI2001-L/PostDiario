import io
import json
import os
import shutil
from datetime import datetime
from typing import Any

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


def extract_first_image(response: Any) -> Image.Image:
    candidates = getattr(response, "candidates", None)
    if not candidates:
        raise RuntimeError("Gemini no devolvió candidates para la imagen.")

    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content:
            continue
        parts = getattr(content, "parts", None) or []
        for part in parts:
            inline_data = getattr(part, "inline_data", None)
            if inline_data and getattr(inline_data, "data", None):
                return Image.open(io.BytesIO(inline_data.data)).convert("RGB")

    raise RuntimeError("No se encontró ninguna imagen en la respuesta de Gemini.")


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

La protagonista visual SIEMPRE debe ser:
- una chica joven
- pelo castaño oscuro casi negro
- vestido
- estilo dibujo simple bonito, limpio, emocional, tipo cuentas virales de reflexiones

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
- Debe incluir SIEMPRE a la chica descrita.
- Debe ser visualmente clara y bonita.
- Debe poder funcionar en un post cuadrado de Instagram.
- Debe evitar fondos vacíos o de un solo color.
- Debe incluir uno o dos elementos visuales relacionados con la emoción.

Buenos ejemplos de scene_prompt:
- "a young woman with dark brown almost black hair and a dress standing under a small rain cloud while the rest of the sky is calm"
- "a young woman with dark brown almost black hair and a dress hugging herself softly while small tangled scribbles float above her head"
- "a young woman with dark brown almost black hair and a dress walking while carrying a backpack made of stones as a metaphor for emotional weight"
- "a young woman with dark brown almost black hair and a dress sitting quietly while a large soft wave shape rises behind her as a metaphor for overwhelming thoughts"
- "a young woman with dark brown almost black hair and a dress beside a large hourglass as a metaphor for time and healing"

Evitar completamente:
- photography
- realistic photo
- cinematic still
- plain background
- abstract gradient
- empty backdrop
- stick figure
- ugly sketch
- rough doodle
- text inside image
- watermark

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
            "No todo límite nace desde el rechazo.\n\nMuchos nacen desde el cansancio de seguir dándote por completo donde ya no hay cuidado.\n\nPoner distancia no siempre es frialdad. A veces es respeto por tu paz.\n\nGuárdalo si hoy necesitas recordarlo. 🤍\n\n#limites #saludmental #psicologia #autocuidado #amorpropio #bienestar #reflexiones #ansiedad #sanar",
            "a young woman with dark brown almost black hair and a dress standing under a small rain cloud while the rest of the sky is calm, soft emotional Instagram illustration, clean composition, subtle contextual elements, not empty background",
        )


def build_image_prompt(theme: str, scene_prompt: str) -> str:
    return f"""
Create a square 1:1 digital illustration with NO text, NO letters, NO typography, NO watermark.

This must look like a polished emotional Instagram illustration, not a photograph.
The illustration should be aesthetically pleasing, soft, expressive, and shareable.

Theme:
{theme}

Main visual scene:
{scene_prompt}

Main character requirements:
- always a young woman
- dark brown almost black hair
- wearing a dress
- simple but pretty illustrated style
- soft clean outlines
- visually appealing, not childish, not ugly, not crude
- consistent Instagram illustration aesthetic

Style:
soft emotional Instagram illustration, hand-drawn digital art, clean outlines, soft muted pastel palette, elegant simple character design, polished minimal illustration, expressive but clean, cute and tasteful

Composition:
- centered or slightly lower character placement
- room for quote overlay in upper half
- background should be simple but not empty
- include gentle contextual elements related to the emotion
- visually balanced
- must feel like a finished illustrated post, not just a canvas

Very important:
- DO NOT generate a plain solid background
- DO NOT generate a single-color empty backdrop
- DO NOT generate a flat gradient only
- DO NOT generate a stick figure
- DO NOT generate a rough doodle
- DO NOT generate a bad sketch
- DO NOT generate a placeholder-looking drawing
- DO NOT generate an ugly face
- DO NOT generate text inside the image

Avoid:
photography, realistic photo, cinematic still, 3D render, vector corporate style, empty background, abstract color field, watermark, typography
""".strip()


def generate_fallback_image(size=(1080, 1080)) -> Image.Image:
    """
    Fallback simple pero decente si Gemini Image falla.
    """
    img = Image.new("RGB", size, (228, 232, 237))
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, int(size[1] * 0.76), size[0], size[1]), fill=(208, 213, 220))

    # nube suave
    draw.ellipse((360, 220, 700, 370), fill=(198, 205, 214))
    draw.ellipse((430, 180, 610, 340), fill=(198, 205, 214))

    # lluvia
    for x in range(420, 660, 35):
        draw.line((x, 365, x - 10, 405), fill=(145, 153, 164), width=4)

    # chica simple, menos horrible que un monigote
    cx = 540
    base = 830

    # cabeza
    draw.ellipse((cx - 42, base - 225, cx + 42, base - 141), fill=(236, 220, 205), outline=(90, 96, 108), width=4)
    # pelo
    draw.ellipse((cx - 48, base - 235, cx + 48, base - 150), fill=(38, 35, 35))
    # cuello
    draw.line((cx, base - 142, cx, base - 125), fill=(90, 96, 108), width=4)
    # vestido
    draw.polygon(
        [(cx - 55, base - 125), (cx + 55, base - 125), (cx + 35, base - 30), (cx - 35, base - 30)],
        fill=(83, 88, 101),
        outline=(90, 96, 108),
    )
    # brazos
    draw.line((cx - 10, base - 105, cx - 72, base - 60), fill=(90, 96, 108), width=5)
    draw.line((cx + 10, base - 105, cx + 72, base - 60), fill=(90, 96, 108), width=5)
    # piernas
    draw.line((cx - 12, base - 30, cx - 42, base + 55), fill=(90, 96, 108), width=5)
    draw.line((cx + 12, base - 30, cx + 42, base + 55), fill=(90, 96, 108), width=5)

    img = img.filter(ImageFilter.GaussianBlur(0.3))
    return img


def get_ia_background(theme: str, scene_prompt: str, size=(1080, 1080), max_attempts: int = 3) -> Image.Image:
    client = get_client()
    prompt = build_image_prompt(theme, scene_prompt)
    last_error = None

    debug("Prompt de imagen:")
    debug(prompt)

    for attempt in range(1, max_attempts + 1):
        try:
            debug(f"Intento imagen {attempt}/{max_attempts}")

            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    image_config=types.ImageConfig(
                        aspect_ratio="1:1",
                    )
                ),
            )

            img = extract_first_image(response)

            # Ajustes sutiles
            img = ImageEnhance.Contrast(img).enhance(1.02)
            img = ImageEnhance.Color(img).enhance(0.98)
            img = ImageEnhance.Brightness(img).enhance(1.00)
            img = img.filter(ImageFilter.GaussianBlur(radius=0.15))
            img = img.resize(size, Image.LANCZOS)

            debug("Imagen generada correctamente.")
            return img

        except Exception as e:
            last_error = e
            debug(f"Fallo en generación de imagen: {e}")

    debug(f"Todos los intentos fallaron. Último error: {last_error}")
    debug("Usando fallback.")
    return generate_fallback_image(size=size)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
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

    font_path = "assets/fonts/PlayfairDisplay-Regular.ttf"
    if os.path.exists(font_path):
        quote_font = ImageFont.truetype(font_path, 58)
        handle_font = ImageFont.truetype(font_path, 24)
    else:
        quote_font = ImageFont.load_default()
        handle_font = ImageFont.load_default()

    max_width = img.size[0] - 260
    lines = wrap_text(draw, f"“{phrase}”", quote_font, max_width)

    line_height = 70
    block_height = len(lines) * line_height
    y = 165 - block_height // 2

    for line in lines:
        x = (img.size[0] - draw.textlength(line, font=quote_font)) / 2
        draw.text((x + 2, y + 2), line, font=quote_font, fill=(0, 0, 0))
        draw.text((x, y), line, font=quote_font, fill=(245, 244, 239))
        y += line_height

    if handle:
        hx = (img.size[0] - draw.textlength(handle, font=handle_font)) / 2
        draw.text((hx, img.size[1] - 92), handle, font=handle_font, fill=(235, 235, 232))

    return img


def render_quote_image(
    quote: str,
    theme: str,
    scene_prompt: str,
    handle: str = "@tu_cuenta",
    out_path: str = f"{OUT_DIR}/{IMG_NAME}",
) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    img = get_ia_background(theme, scene_prompt, size=(CANVAS_SIZE, CANVAS_SIZE))
    img = draw_quote_text(img, quote, handle)
    img = img.convert("RGB")
    img.save(out_path, "JPEG", quality=94, optimize=True)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    theme, phrase, caption, scene_prompt = generate_ia_content()
    handle = os.environ.get("IG_HANDLE", "@tu_cuenta")

    render_quote_image(
        quote=phrase,
        theme=theme,
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

    # MUY IMPORTANTE: copiar a public para publicar la imagen NUEVA
    shutil.copyfile(f"{OUT_DIR}/{IMG_NAME}", f"{PUBLIC_DIR}/latest.jpg")

    with open(f"{PUBLIC_DIR}/latest.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("Post generado correctamente.")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
