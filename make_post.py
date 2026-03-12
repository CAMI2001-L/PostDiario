import io
import json
import os
import random
from datetime import datetime
from typing import Any

from dateutil import tz
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
from google import genai
from google.genai import types

OUT_DIR = "out"
IMG_NAME = "post.jpg"


def today_madrid() -> str:
    madrid = tz.gettz("Europe/Madrid")
    return datetime.now(tz=madrid).date().isoformat()


def get_client() -> genai.Client:
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("Falta GEMINI_API_KEY en variables de entorno.")
    return genai.Client()


def safe_json_from_response(response: Any) -> dict:
    """
    Intenta extraer JSON fiable desde response.text.
    """
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini no devolvió texto para el JSON.")

    text = text.strip()

    # Por si viniera envuelto en markdown
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
    - visual_style
    """
    client = get_client()

    prompt = """
Eres guionista y copywriter senior de una cuenta de Instagram de reflexiones psicológicas y emocionales.

Tu trabajo NO es sonar motivacional genérico.
Tu trabajo es escribir frases que hagan que la persona piense:
“Esto describe exactamente lo que estoy sintiendo”.

Objetivo:
Crear una pieza emocional, honesta, compartible y visualmente potente.

Contexto de la cuenta:
- Tema general: psicología cotidiana, límites, ansiedad silenciosa, duelo emocional, autoestima, cansancio mental, desapego, sanar.
- Tono: íntimo, elegante, profundo, claro, humano.
- Estilo: menos autoayuda vacía, más verdad emocional.
- Público: personas que se sienten sobrepasadas, sensibles, agotadas emocionalmente o en proceso de sanar.
- Idioma: español.
- Prohibido sonar a coach barato.

Reglas estrictas:

1) phrase
- Máximo 14 palabras.
- Debe sentirse como una verdad incómoda, un límite sano o una revelación emocional.
- Debe poder ir sola en una imagen.
- Debe ser compartible.
- No uses clichés como:
  "todo pasa por algo"
  "cree en ti"
  "persigue tus sueños"
  "todo estará bien"
  "eres suficiente"
- Evita frases demasiado abstractas o espirituales.
- Debe sonar humana, concreta y emocional.

2) caption
Estructura exacta:
- Línea 1: gancho muy fuerte, corto, que frene el scroll.
- Luego 2 a 4 párrafos breves.
- Debe validar una emoción real.
- Debe desarrollar la idea de la frase sin repetirla literalmente.
- Debe cerrar con un CTA natural, suave y humano.
- Añade 8 a 10 hashtags relevantes y no genéricos.

3) theme
- Una sola palabra en inglés.
- Debe servir para inspirar el fondo visual.
- Ejemplos válidos: healing, solitude, boundaries, overthinking, grief, softness, release, peace

4) visual_style
- Devuelve una descripción visual breve para generar el fondo.
- Tiene que ser estética, cinematográfica y útil para una imagen de Instagram.
- Debe describir solo el fondo, no texto.
- Ejemplo: "dreamy foggy landscape with soft golden light and blurred flowers"

5) style_guardrails
El contenido debe sonar:
- honesto
- emocionalmente inteligente
- elegante
- íntimo
- no cursi
- no influencer motivacional
- no pseudoespiritual

Devuelve SOLO un JSON válido con estas claves exactas:
{
  "theme": "...",
  "phrase": "...",
  "caption": "...",
  "visual_style": "..."
}
""".strip()

    schema = {
        "type": "object",
        "properties": {
            "theme": {"type": "string"},
            "phrase": {"type": "string"},
            "caption": {"type": "string"},
            "visual_style": {"type": "string"},
        },
        "required": ["theme", "phrase", "caption", "visual_style"],
        "propertyOrdering": ["theme", "phrase", "caption", "visual_style"],
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
        visual_style = str(content["visual_style"]).strip()

        return theme, phrase, caption, visual_style

    except Exception as e:
        print(f"Error Gemini texto: {e}")
        return (
            "healing",
            "No te agotaste por sentir, sino por sostener demasiado tiempo.",
            "A veces no estás rota.\nEstás cansada.\n\nCansada de sostener, de entender, de esperar que algo cambie mientras tú sigues cargando con todo.\n\nSanar también es dejar de exigirte tanta fortaleza.\n\nGuárdalo para esos días en los que se te olvida tratarte con más ternura. 🤍\n\n#sanar #saludmental #psicologia #amorpropio #ansiedad #bienestar #crecimientopersonal #limites",
            "dreamy foggy field with soft golden sunrise light and delicate blurred flowers",
        )


def extract_first_image(response: Any) -> Image.Image:
    """
    Extrae la primera imagen inline del response de Gemini.
    """
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
                image_bytes = inline_data.data
                return Image.open(io.BytesIO(image_bytes)).convert("RGB")

    raise RuntimeError("No se encontró ninguna imagen en la respuesta de Gemini.")


def apply_vignette(img: Image.Image, strength: float = 0.12) -> Image.Image:
    """
    Viñeta suave para mejorar legibilidad del texto sin apagar demasiado el fondo.
    """
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)

    draw.ellipse(
        (-w * 0.10, -h * 0.10, w * 1.10, h * 1.10),
        fill=255,
    )
    mask = mask.filter(ImageFilter.GaussianBlur(int(min(w, h) * 0.10)))
    mask = ImageOps.autocontrast(mask)

    dark = Image.new("RGB", (w, h), (10, 10, 12))
    darkened = Image.blend(img, dark, strength)

    return Image.composite(img, darkened, ImageOps.invert(mask))


def get_ia_background(theme: str, visual_style: str, size=(1080, 1080)) -> Image.Image:
    client = get_client()
    w, h = size

    prompt = f"""
Create a premium Instagram quote background.

Square composition, no text, no letters, no typography, no watermark, no words.
Style: cinematic, aesthetic, elegant, soft depth of field, premium editorial feel.
Theme: {theme}
Scene: {visual_style}

Requirements:
- visually rich and beautiful
- not flat, not plain, not empty
- suitable for centered white quote text
- soft light
- depth, atmosphere, texture
- premium Instagram aesthetic
- no people faces
- no readable text
- no black empty background
- no gray empty gradient
""".strip()

    try:
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

        # Ajustes visuales suaves para feed tipo Instagram
        img = ImageEnhance.Contrast(img).enhance(1.12)
        img = ImageEnhance.Color(img).enhance(1.08)
        img = ImageEnhance.Brightness(img).enhance(1.03)

        # Blur muy suave para look más editorial
        img = img.filter(ImageFilter.GaussianBlur(radius=0.8))

        # Grain fino tipo film
        noise = Image.effect_noise(img.size, random.uniform(12, 20)).convert("L")
        noise = ImageOps.colorize(noise, black=(0, 0, 0), white=(255, 255, 255)).convert("RGB")
        img = Image.blend(img, noise, 0.04)

        # Overlay muy leve para variar el mood
        tints = [
            (255, 228, 220),
            (221, 233, 255),
            (223, 242, 231),
            (255, 239, 212),
        ]
        overlay = Image.new("RGB", img.size, random.choice(tints))
        img = Image.blend(img, overlay, random.uniform(0.03, 0.06))

        # Viñeta suave para legibilidad
        img = apply_vignette(img, strength=random.uniform(0.08, 0.14))

        # Redimensionar por si Gemini devuelve 1024x1024
        img = img.resize((w, h), Image.LANCZOS)

        return img

    except Exception as e:
        print(f"Error Gemini imagen: {e}")

    # Fallback bonito si falla la API
    base = Image.new("RGB", size, (232, 229, 239))
    glow = Image.new("RGB", size, (255, 234, 220)).filter(ImageFilter.GaussianBlur(180))
    img = Image.blend(base, glow, 0.24)
    img = apply_vignette(img, strength=0.10)
    return img


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


def render_quote_image(
    quote: str,
    theme: str,
    visual_style: str,
    handle: str = "@tu_cuenta",
    out_path: str = f"{OUT_DIR}/{IMG_NAME}",
) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    img = get_ia_background(theme, visual_style)
    draw = ImageDraw.Draw(img)

    font_path = "assets/fonts/PlayfairDisplay-Regular.ttf"
    if os.path.exists(font_path):
        quote_font = ImageFont.truetype(font_path, 66)
        small_font = ImageFont.truetype(font_path, 34)
    else:
        quote_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    max_width = img.size[0] - 240
    lines = wrap_text(draw, f"“{quote}”", quote_font, max_width)

    line_height = 82
    block_height = len(lines) * line_height
    y = (img.size[1] - block_height) // 2 - 30

    for line in lines:
        x = (img.size[0] - draw.textlength(line, font=quote_font)) / 2
        draw.text((x + 2, y + 3), line, font=quote_font, fill=(0, 0, 0))
        draw.text((x, y), line, font=quote_font, fill=(247, 247, 245))
        y += line_height

    hx = (img.size[0] - draw.textlength(handle, font=small_font)) / 2
    draw.text((hx, img.size[1] - 130), handle, font=small_font, fill=(220, 220, 220))

    img = img.convert("RGB")
    img.save(out_path, "JPEG", quality=92, optimize=True)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    theme, phrase, caption, visual_style = generate_ia_content()
    handle = os.environ.get("IG_HANDLE", "@tu_cuenta")

    render_quote_image(
        quote=phrase,
        theme=theme,
        visual_style=visual_style,
        handle=handle,
        out_path=f"{OUT_DIR}/{IMG_NAME}",
    )

    payload = {
        "date": today_madrid(),
        "theme": theme,
        "phrase": phrase,
        "caption": caption,
        "visual_style": visual_style,
        "image_path": f"{OUT_DIR}/{IMG_NAME}",
    }

    with open(f"{OUT_DIR}/post.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("Post Gemini generado con éxito.")


if __name__ == "__main__":
    main()
