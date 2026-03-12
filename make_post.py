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
    """
    Devuelve:
    - theme
    - phrase
    - caption
    - image_prompt_data (dict)
    """
    client = get_client()

    prompt = """
Eres guionista y director creativo de una cuenta de Instagram de reflexiones psicológicas y emocionales.

Tu trabajo NO es sonar motivacional genérico.
Tu trabajo es escribir frases que hagan que la persona piense:
“Esto describe exactamente lo que estoy sintiendo”.

Además, debes proponer una dirección visual para una imagen que acompañe esa frase.

IMPORTANTE:
La imagen NO debe ser diseño gráfico.
La imagen NO debe ser un fondo abstracto.
La imagen NO debe parecer una plantilla para quotes.
La imagen debe parecer una fotografía emocional real, cinematográfica, nostálgica y con profundidad visual.

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
- Debe servir para inspirar el universo emocional.

4) image_prompt_data.scene_description
- Debe describir una escena fotográfica real, no abstracta.
- Debe incluir un sujeto, lugar o situación concreta.
- Debe sentirse como una fotografía artística o cinematic still.
- Debe sugerir historia, atmósfera y contexto.
- NO debe ser diseño gráfico.
- NO debe ser fondo minimalista.
- NO debe ser un color plano.
- NO debe ser algo tipo wallpaper vacío.

5) image_prompt_data.lighting
- Describe una luz realista y natural.
- Ejemplos:
  "soft gray daylight filtered through wet glass"
  "warm sunset haze with gentle shadow falloff"
  "foggy dawn light with muted contrast"
  "soft indoor window light with dust in the air"

6) image_prompt_data.composition
- Debe forzar profundidad visual.
- Debe incluir foreground, midground y background cuando sea posible.
- Debe dejar algo de espacio orgánico para superponer texto después.
- No debe sentirse vacío, plano ni simétrico como póster.
- Debe evitar composiciones gráficas de diseño.

7) image_prompt_data.texture
- Debe describir imperfección fotográfica real.
- Ejemplos:
  "analog film grain, slight blur, soft imperfections"
  "visible grain, subtle softness, imperfect exposure"
  "nostalgic photographic texture, natural softness"

8) image_prompt_data.mood
- Emociones concretas:
  melancholic, intimate, reflective, tender, lonely, peaceful, quiet, wistful

9) style_guardrails
El contenido debe sonar:
- honesto
- emocionalmente inteligente
- elegante
- íntimo
- no cursi
- no influencer motivacional
- no pseudoespiritual

Evita COMPLETAMENTE en la dirección visual:
- flat gradients
- plain color backgrounds
- minimal wallpaper backgrounds
- graphic design
- poster style
- vector art
- 3D renders
- studio isolated objects
- abstract backdrops
- empty pastel backgrounds

Devuelve SOLO un JSON válido con estas claves exactas:
{
  "theme": "...",
  "phrase": "...",
  "caption": "...",
  "image_prompt_data": {
    "scene_description": "...",
    "lighting": "...",
    "composition": "...",
    "texture": "...",
    "mood": "..."
  }
}
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
                    "lighting": {"type": "string"},
                    "composition": {"type": "string"},
                    "texture": {"type": "string"},
                    "mood": {"type": "string"},
                },
                "required": [
                    "scene_description",
                    "lighting",
                    "composition",
                    "texture",
                    "mood",
                ],
                "propertyOrdering": [
                    "scene_description",
                    "lighting",
                    "composition",
                    "texture",
                    "mood",
                ],
            },
        },
        "required": ["theme", "phrase", "caption", "image_prompt_data"],
        "propertyOrdering": ["theme", "phrase", "caption", "image_prompt_data"],
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

        theme = str(content["theme"]).strip()
        phrase = str(content["phrase"]).strip()
        caption = str(content["caption"]).strip()
        image_prompt_data = content["image_prompt_data"]

        return theme, phrase, caption, image_prompt_data

    except Exception as e:
        print(f"Error Gemini texto: {e}")
        return (
            "grief",
            "A veces sanar también se parece a soltar sin respuesta.",
            "Hay dolores que no piden soluciones.\n\nSolo piden tiempo, silencio y un lugar seguro donde dejar de fingir que ya pasó.\n\nNo todo lo que te pesa necesita explicación inmediata. A veces solo necesita que te trates con más ternura.\n\nSi hoy estás cansada de sostenerlo todo, quédate aquí un momento. 🤍\n\n#dueloemocional #sanar #saludmental #psicologia #ansiedad #amorpropio #bienestar #reflexiones #cansanciomental",
            {
                "scene_description": "Two children quietly looking at the ocean through an old window at dusk from inside a dim room",
                "lighting": "soft fading dusk light entering through the glass with gentle shadow falloff and a warm nostalgic haze",
                "composition": "blurred foreground elements near the window, children in the midground, hazy sea horizon in the background, layered depth, organic central breathing space for future text",
                "texture": "analog film grain, slight blur, imperfect softness, nostalgic photographic texture",
                "mood": "nostalgic, tender, reflective",
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
            image_prompt_data.get("lighting", ""),
            image_prompt_data.get("composition", ""),
            image_prompt_data.get("texture", ""),
            image_prompt_data.get("mood", ""),
        ]
    ).lower()

    weak_terms = [
        "abstract",
        "background",
        "gradient",
        "minimal",
        "plain",
        "wallpaper",
        "solid color",
        "clean backdrop",
        "simple backdrop",
        "poster",
        "vector",
    ]

    strong_cues = [
        "foreground",
        "midground",
        "background",
        "window",
        "fog",
        "rain",
        "light",
        "shadow",
        "room",
        "road",
        "ocean",
        "flower",
        "glass",
        "curtain",
        "haze",
        "reflection",
        "dusk",
        "dawn",
    ]

    if any(term in text for term in weak_terms):
        return True

    score = sum(1 for cue in strong_cues if cue in text)
    return score < 3


def apply_vignette(img: Image.Image, strength: float = 0.08) -> Image.Image:
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)

    draw.ellipse(
        (-w * 0.08, -h * 0.08, w * 1.08, h * 1.08),
        fill=255,
    )
    mask = mask.filter(ImageFilter.GaussianBlur(int(min(w, h) * 0.09)))
    mask = ImageOps.autocontrast(mask)

    dark = Image.new("RGB", (w, h), (8, 8, 10))
    darkened = Image.blend(img, dark, strength)

    return Image.composite(img, darkened, ImageOps.invert(mask))


def build_image_prompt(theme: str, image_prompt_data: dict) -> str:
    scene = image_prompt_data["scene_description"].strip()
    lighting = image_prompt_data["lighting"].strip()
    composition = image_prompt_data["composition"].strip()
    texture = image_prompt_data["texture"].strip()
    mood = image_prompt_data["mood"].strip()

    return f"""
Create a square 1:1 photographic image with no text, no letters, no typography, no watermark.

Generate a real emotional photographic scene, not a graphic design background.
This image may later be used for an Instagram quote overlay, but it must first feel like a true photograph with atmosphere, depth, texture, and story.

Theme:
{theme}

Scene:
{scene}

Lighting:
{lighting}

Composition:
{composition}

Texture:
{texture}

Mood:
{mood}

Base visual style:
analog film photography, cinematic still, nostalgic mood, emotional realism, visible film grain, subtle softness, shallow depth of field, realistic textures, imperfect photographic details, natural light falloff

Important requirements:
- the frame must feel visually rich and layered
- include foreground, midground, and background when possible
- create real environmental depth
- include one believable light source
- include one clear environmental context
- include one visible texture
- keep the image organic, not empty, not flat
- the scene must feel lived-in, atmospheric, and emotionally believable
- leave only subtle organic breathing room for future text overlay, never a blank empty backdrop
- do not simplify the scene into a soft color field

Strictly avoid:
text, letters, watermark, poster layout, graphic design, flat gradients, plain color backgrounds, empty wallpaper backgrounds, vector art, 3D renders, isolated studio objects, minimal abstract compositions, overly clean commercial sharpness
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
                image_config=types.ImageConfig(
                    aspect_ratio="1:1",
                )
            ),
        )

        img = extract_first_image(response)

        img = ImageEnhance.Contrast(img).enhance(1.06)
        img = ImageEnhance.Color(img).enhance(0.95)
        img = ImageEnhance.Brightness(img).enhance(0.99)

        img = img.filter(ImageFilter.GaussianBlur(radius=0.25))

        noise = Image.effect_noise(img.size, random.uniform(20, 30)).convert("L")
        noise = ImageOps.colorize(
            noise, black=(0, 0, 0), white=(255, 255, 255)
        ).convert("RGB")
        img = Image.blend(img, noise, 0.06)

        img = apply_vignette(img, strength=random.uniform(0.04, 0.08))

        img = img.resize((w, h), Image.LANCZOS)
        return img

    except Exception as e:
        print(f"Error Gemini imagen: {e}")

    # fallback
    base = Image.new("RGB", size, (118, 112, 103))
    light = Image.new("RGB", size, (182, 169, 150)).filter(ImageFilter.GaussianBlur(200))
    img = Image.blend(base, light, 0.20)
    img = apply_vignette(img, strength=0.08)
    return img


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int
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
        quote_font = ImageFont.truetype(font_path, 66)
        small_font = ImageFont.truetype(font_path, 30)
    else:
        quote_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    max_width = img.size[0] - 220
    lines = wrap_text(draw, f"“{quote}”", quote_font, max_width)

    line_height = 82
    block_height = len(lines) * line_height
    y = (img.size[1] - block_height) // 2 - 30

    for line in lines:
        x = (img.size[0] - draw.textlength(line, font=quote_font)) / 2

        draw.text((x + 2, y + 3), line, font=quote_font, fill=(0, 0, 0))
        draw.text((x, y), line, font=quote_font, fill=(246, 246, 242))
        y += line_height

    hx = (img.size[0] - draw.textlength(handle, font=small_font)) / 2
    draw.text((hx, img.size[1] - 120), handle, font=small_font, fill=(225, 225, 225))

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

    print("Post Gemini generado con éxito.")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
