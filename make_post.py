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


def generate_ia_content() -> tuple[str, str, str, dict]:
    client = get_client()

    prompt = """
Eres copywriter y director creativo de una cuenta de Instagram de reflexiones psicológicas y emocionales.

Tu trabajo es crear:
- una frase breve
- un caption
- una dirección visual para una ILUSTRACIÓN emocional

MUY IMPORTANTE:
La imagen que acompañará la frase NO debe ser una fotografía realista.
Debe parecer una ilustración emocional tipo cuenta viral de Instagram.
Piensa en:
- dibujo editorial
- personaje simple y expresivo
- ilustración digital con líneas visibles
- composición limpia pero con intención
- estética sensible, íntima y compartible

NO quiero:
- fotografía analógica
- cinematic still
- fondos abstractos vacíos
- degradados planos
- fondos de un solo color
- renders 3D
- diseño corporativo
- vector frío
- stock image

Contexto de la cuenta:
- psicología cotidiana
- agotamiento mental
- ansiedad silenciosa
- límites
- duelo emocional
- autoestima
- sanar
- desapego

Tono:
- íntimo
- elegante
- claro
- humano
- emocionalmente inteligente
- no cursi
- no coach barato
- no pseudoespiritual

Devuelve SOLO JSON válido con esta estructura exacta:
{
  "theme": "...",
  "phrase": "...",
  "caption": "...",
  "image_prompt_data": {
    "scene_description": "...",
    "character_style": "...",
    "composition": "...",
    "palette": "...",
    "mood": "..."
  }
}

Reglas:

1) phrase
- Máximo 14 palabras.
- Debe ser compartible.
- Debe sonar humana y emocional.
- Evita clichés de autoayuda.

2) caption
- Línea 1: hook corto y fuerte.
- Luego 2 a 4 párrafos breves.
- Validar emoción real.
- Cerrar con CTA suave.
- Añadir 8 a 10 hashtags relevantes.

3) theme
- Una sola palabra en inglés.

4) image_prompt_data.scene_description
- Debe describir una escena ilustrable, no una foto.
- Debe incluir un personaje, acción o metáfora visual clara.
- Debe encajar con una cuenta viral de frases ilustradas.
- Buenos tipos de escena:
  - persona caminando bajo una nube de lluvia
  - personaje cargando un reloj de arena enorme
  - persona abrazándose a sí misma
  - figura sentada con agotamiento
  - personaje pequeño frente a una emoción grande
  - metáfora visual simple y potente

5) image_prompt_data.character_style
- Describe un estilo de ilustración:
  simple expressive character, hand-drawn linework, soft imperfect outlines, emotional editorial illustration, minimal facial detail

6) image_prompt_data.composition
- Debe dejar un área clara para superponer texto.
- Debe sentirse como post ilustrado de Instagram.
- Composición simple pero no vacía.
- Un personaje principal claro.
- Fondo ligero con algo de contexto visual.

7) image_prompt_data.palette
- Paleta suave, apagada, emocional.
- Ejemplos:
  muted blue gray
  dusty pink and sage
  warm beige and charcoal
  soft desaturated tones

8) image_prompt_data.mood
- Emociones concretas:
  tired, tender, melancholic, reflective, overwhelmed, healing, quiet, vulnerable

Evitar completamente:
- realistic photography
- film photography
- dramatic cinematic realism
- abstract gradient background
- empty plain backdrop
- detailed realism
- glossy commercial look
- 3D render
- vector corporate style
- text inside the generated image
- watermark

La imagen debe sentirse como una ilustración emocional viral de Instagram.
""".strip()

    schema = {
        "type": "object",
        "properties": {
            "theme": {"type": "string"},
            "phrase": {"type": "string"},
            "caption": {"type": "string"},
            "image_prompt_data": {
                "type": "object",
                "properties": {
                    "scene_description": {"type": "string"},
                    "character_style": {"type": "string"},
                    "composition": {"type": "string"},
                    "palette": {"type": "string"},
                    "mood": {"type": "string"},
                },
                "required": [
                    "scene_description",
                    "character_style",
                    "composition",
                    "palette",
                    "mood",
                ],
            },
        },
        "required": ["theme", "phrase", "caption", "image_prompt_data"],
    }

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=schema,
                temperature=0.95,
            ),
        )
        content = safe_json_from_response(response)

        return (
            str(content["theme"]).strip(),
            str(content["phrase"]).strip(),
            str(content["caption"]).strip(),
            content["image_prompt_data"],
        )

    except Exception as e:
        print(f"Error Gemini texto: {e}")
        return (
            "overthinking",
            "No todos los silencios son paz; algunos son agotamiento.",
            "A veces no estás en calma.\n\nA veces solo estás demasiado cansada para seguir explicando lo que te duele.\n\nY desde fuera parece silencio, pero por dentro es puro desgaste.\n\nSi esto te encontró hoy, respira un momento. 🤍\n\n#agotamientomental #ansiedad #saludmental #psicologia #reflexiones #cansancioemocional #autocuidado #sanar #limites",
            {
                "scene_description": "A simple hand-drawn character sitting with visible exhaustion, hugging their knees while a dark scribble cloud hangs above their head",
                "character_style": "emotional editorial illustration, simple expressive character, hand-drawn black outlines, soft imperfect digital drawing, minimal facial detail",
                "composition": "main character centered slightly low, enough upper area for text, light background with subtle visual texture, Instagram illustrated quote post layout",
                "palette": "muted blue gray, charcoal, soft desaturated tones",
                "mood": "tired, overwhelmed, reflective",
            },
        )


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


def is_weak_scene(image_prompt_data: dict) -> bool:
    text = " ".join(
        [
            image_prompt_data.get("scene_description", ""),
            image_prompt_data.get("character_style", ""),
            image_prompt_data.get("composition", ""),
            image_prompt_data.get("palette", ""),
            image_prompt_data.get("mood", ""),
        ]
    ).lower()

    weak_terms = [
        "photo",
        "photograph",
        "cinematic",
        "film photography",
        "realistic photography",
        "gradient",
        "plain background",
        "abstract background",
        "empty backdrop",
    ]

    strong_cues = [
        "character",
        "hand-drawn",
        "illustration",
        "outlines",
        "editorial",
        "text area",
        "instagram",
        "scribble",
        "cloud",
        "metaphor",
    ]

    if any(term in text for term in weak_terms):
        return True

    score = sum(1 for cue in strong_cues if cue in text)
    return score < 3


def build_image_prompt(theme: str, image_prompt_data: dict) -> str:
    scene = image_prompt_data["scene_description"].strip()
    character_style = image_prompt_data["character_style"].strip()
    composition = image_prompt_data["composition"].strip()
    palette = image_prompt_data["palette"].strip()
    mood = image_prompt_data["mood"].strip()

    return f"""
Create a square 1:1 emotional illustration with no text, no letters, no typography, no watermark.

This must be an illustrated Instagram post background in the style of viral emotional quote accounts.
Do NOT create a real photograph.
Do NOT create a cinematic film still.

Theme:
{theme}

Scene:
{scene}

Character style:
{character_style}

Composition:
{composition}

Palette:
{palette}

Mood:
{mood}

Base style:
emotional editorial illustration, hand-drawn digital art, simple expressive character design, visible black linework, soft imperfect outlines, muted soft colors, slightly textured flat shading, minimal but emotionally strong composition

Important requirements:
- one clear main character or metaphorical subject
- composition must support overlay text later
- leave breathing room for quote placement
- simple background with visual intention, not empty
- viral Instagram illustrated quote aesthetic
- emotionally readable at first glance
- shareable, clean, intimate, slightly melancholic

Strictly avoid:
realistic photography, analog film look, cinematic realism, flat abstract gradients, plain empty backgrounds, vector corporate style, glossy 3D render, overly detailed realism, text inside image, watermark
""".strip()


def get_ia_background(theme: str, image_prompt_data: dict, size=(1080, 1080)) -> Image.Image:
    client = get_client()
    w, h = size
    prompt = build_image_prompt(theme, image_prompt_data)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt],
            config=types.GenerateContentConfig(
                image_config=types.ImageConfig(aspect_ratio="1:1")
            ),
        )

        img = extract_first_image(response)

        img = ImageEnhance.Contrast(img).enhance(1.03)
        img = ImageEnhance.Color(img).enhance(0.96)
        img = ImageEnhance.Brightness(img).enhance(1.00)

        img = img.filter(ImageFilter.GaussianBlur(radius=0.15))

        texture = Image.effect_noise(img.size, random.uniform(8, 14)).convert("L")
        texture = ImageOps.colorize(
            texture, black=(230, 230, 230), white=(255, 255, 255)
        ).convert("RGB")
        img = Image.blend(img, texture, 0.05)

        img = img.resize((w, h), Image.LANCZOS)
        return img

    except Exception as e:
        print(f"Error Gemini imagen: {e}")

    fallback = Image.new("RGB", size, (205, 210, 214))
    return fallback


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


def choose_text_box(image_prompt_data: dict, img_size: tuple[int, int]) -> tuple[int, int, int]:
    composition = image_prompt_data.get("composition", "").lower()
    w, h = img_size

    if "upper area" in composition or "top" in composition:
        return w // 2, int(h * 0.22), int(w * 0.72)

    if "lower area" in composition or "bottom" in composition:
        return w // 2, int(h * 0.72), int(w * 0.72)

    return w // 2, int(h * 0.22), int(w * 0.72)


def render_quote_image(
    quote: str,
    theme: str,
    image_prompt_data: dict,
    handle: str = "@tu_cuenta",
    out_path: str = f"{OUT_DIR}/{IMG_NAME}",
) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    img = get_ia_background(theme, image_prompt_data)
    draw = ImageDraw.Draw(img)

    font_path = "assets/fonts/PlayfairDisplay-Regular.ttf"
    if os.path.exists(font_path):
        quote_font = ImageFont.truetype(font_path, 74)
        small_font = ImageFont.truetype(font_path, 28)
    else:
        quote_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    cx, cy, max_width = choose_text_box(image_prompt_data, img.size)
    lines = wrap_text(draw, f"“{quote}”", quote_font, max_width)

    line_height = 88
    block_height = len(lines) * line_height
    y = cy - block_height // 2

    for line in lines:
        x = cx - draw.textlength(line, font=quote_font) / 2
        draw.text((x + 2, y + 2), line, font=quote_font, fill=(0, 0, 0))
        draw.text((x, y), line, font=quote_font, fill=(245, 245, 240))
        y += line_height

    hx = (img.size[0] - draw.textlength(handle, font=small_font)) / 2
    draw.text((hx, img.size[1] - 90), handle, font=small_font, fill=(230, 230, 230))

    img = img.convert("RGB")
    img.save(out_path, "JPEG", quality=92, optimize=True)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    theme, phrase, caption, image_prompt_data = generate_ia_content()

    if is_weak_scene(image_prompt_data):
        print("Escena débil detectada, regenerando una vez...")
        theme, phrase, caption, image_prompt_data = generate_ia_content()

    handle = os.environ.get("IG_HANDLE", "@tu_cuenta")

    render_quote_image(
        quote=phrase,
        theme=theme,
        image_prompt_data=image_prompt_data,
        handle=handle,
        out_path=f"{OUT_DIR}/{IMG_NAME}",
    )

    payload = {
        "date": today_madrid(),
        "theme": theme,
        "phrase": phrase,
        "caption": caption,
        "image_prompt_data": image_prompt_data,
        "image_path": f"{OUT_DIR}/{IMG_NAME}",
    }

    with open(f"{OUT_DIR}/post.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("Post generado con éxito.")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
