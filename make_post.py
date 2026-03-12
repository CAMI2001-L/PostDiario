import io
import json
import os
import random
from datetime import datetime
from typing import Any

from dateutil import tz
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps, ImageStat
from google import genai
from google.genai import types

OUT_DIR = "out"
IMG_NAME = "post.jpg"
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


def generate_ia_content() -> tuple[str, str, str, dict]:
    client = get_client()

    prompt = """
Eres copywriter y director creativo de una cuenta de Instagram de reflexiones psicológicas y emocionales.

Tu trabajo es crear:
- una frase breve
- un caption
- una dirección visual para una ILUSTRACIÓN emocional

MUY IMPORTANTE:
La imagen NO debe ser una fotografía realista.
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
- No debe dejar la imagen vacía.
- La parte más limpia debe seguir teniendo elementos ilustrados sutiles.
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

        theme = str(content["theme"]).strip()
        phrase = str(content["phrase"]).strip()
        caption = str(content["caption"]).strip()
        image_prompt_data = content["image_prompt_data"]

        debug(f"Theme: {theme}")
        debug(f"Phrase: {phrase}")
        debug(f"Image prompt data: {json.dumps(image_prompt_data, ensure_ascii=False)}")

        return theme, phrase, caption, image_prompt_data

    except Exception as e:
        debug(f"Error Gemini texto: {e}")
        return (
            "overthinking",
            "No todos los silencios son paz; algunos son agotamiento.",
            "A veces no estás en calma.\n\nA veces solo estás demasiado cansada para seguir explicando lo que te duele.\n\nY desde fuera parece silencio, pero por dentro es puro desgaste.\n\nSi esto te encontró hoy, respira un momento. 🤍\n\n#agotamientomental #ansiedad #saludmental #psicologia #reflexiones #cansancioemocional #autocuidado #sanar #limites",
            {
                "scene_description": "A simple hand-drawn character sitting with visible exhaustion, hugging their knees while a dark scribble cloud hangs above their head",
                "character_style": "emotional editorial illustration, simple expressive character, hand-drawn black outlines, soft imperfect digital drawing, minimal facial detail",
                "composition": "main character in lower half, upper third cleaner but still illustrated with subtle contextual elements, light background with visual texture, Instagram illustrated quote post layout",
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
        "minimal wallpaper",
        "single color",
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
        "rain",
        "hourglass",
        "hugging",
        "walking",
    ]

    if any(term in text for term in weak_terms):
        return True

    score = sum(1 for cue in strong_cues if cue in text)
    return score < 3


def is_visually_flat(img: Image.Image) -> bool:
    """
    Detecta imágenes demasiado planas, vacías o con muy poca variación.
    """
    small = img.resize((128, 128)).convert("RGB")
    stat = ImageStat.Stat(small)

    mean_std = sum(stat.stddev) / len(stat.stddev)

    extrema = small.getextrema()
    mean_range = 0
    for ch in extrema:
        mean_range += (ch[1] - ch[0])
    mean_range /= len(extrema)

    debug(f"Visual flat check -> mean_std={mean_std:.2f}, mean_range={mean_range:.2f}")

    return mean_std < 18 or mean_range < 60


def build_image_prompt(theme: str, image_prompt_data: dict) -> str:
    scene = image_prompt_data["scene_description"].strip()
    character_style = image_prompt_data["character_style"].strip()
    composition = image_prompt_data["composition"].strip()
    palette = image_prompt_data["palette"].strip()
    mood = image_prompt_data["mood"].strip()

    return f"""
Create a square 1:1 emotional illustration with NO text, NO letters, NO typography, NO watermark.

This must be an illustrated Instagram post background in the style of viral emotional quote accounts.
It must be an illustrated scene, not a plain background.
It must contain a clear subject, a visible action or metaphor, and a composition with intention.

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

Required visual characteristics:
- one clear main character or metaphorical subject
- hand-drawn digital illustration
- visible black outlines
- soft muted color palette
- simple but expressive shapes
- emotional editorial illustration style
- clear figure-background separation
- background with contextual illustrated elements, not empty
- composition must feel like a complete illustrated post, not just a canvas for text
- upper or side clean areas must still contain subtle illustrated context, never blank color fields

Very important:
- DO NOT generate a plain color background
- DO NOT generate an empty beige, gray, brown, or pastel backdrop
- DO NOT generate a flat gradient
- DO NOT leave most of the canvas empty
- DO NOT create a minimalist wallpaper
- the image must include visual elements beyond the central subject
- the frame must feel intentionally illustrated, not blank

Strictly avoid:
realistic photography, analog film, cinematic still, abstract background, empty background, plain backdrop, poster mockup, typography, watermark, glossy 3D, vector corporate style
""".strip()


def generate_fallback_image(size=(1080, 1080)) -> Image.Image:
    """
    Fallback menos horrible que un color plano.
    No ideal, pero al menos con algo de estructura visual.
    """
    w, h = size
    base = Image.new("RGB", size, (210, 214, 220))

    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    # nube tipo scribble
    d.ellipse((w * 0.32, h * 0.18, w * 0.68, h * 0.42), fill=(90, 100, 115, 80))
    d.ellipse((w * 0.25, h * 0.22, w * 0.50, h * 0.40), fill=(90, 100, 115, 80))
    d.ellipse((w * 0.50, h * 0.22, w * 0.75, h * 0.40), fill=(90, 100, 115, 80))

    # suelo suave
    d.rectangle((0, h * 0.74, w, h), fill=(180, 186, 192, 120))

    # personaje simple
    d.ellipse((w * 0.43, h * 0.48, w * 0.57, h * 0.62), fill=(70, 80, 95, 180))
    d.line((w * 0.50, h * 0.62, w * 0.50, h * 0.78), fill=(50, 58, 70, 200), width=10)
    d.line((w * 0.50, h * 0.68, w * 0.42, h * 0.74), fill=(50, 58, 70, 200), width=8)
    d.line((w * 0.50, h * 0.68, w * 0.58, h * 0.74), fill=(50, 58, 70, 200), width=8)
    d.line((w * 0.50, h * 0.78, w * 0.43, h * 0.88), fill=(50, 58, 70, 200), width=8)
    d.line((w * 0.50, h * 0.78, w * 0.57, h * 0.88), fill=(50, 58, 70, 200), width=8)

    img = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    img = img.filter(ImageFilter.GaussianBlur(radius=0.6))

    texture = Image.effect_noise(img.size, 10).convert("L")
    texture = ImageOps.colorize(texture, black=(235, 235, 235), white=(255, 255, 255)).convert("RGB")
    img = Image.blend(img, texture, 0.05)

    return img


def get_ia_background(
    theme: str,
    image_prompt_data: dict,
    size=(1080, 1080),
    max_attempts: int = 3,
) -> Image.Image:
    client = get_client()
    w, h = size
    prompt = build_image_prompt(theme, image_prompt_data)
    last_error = None

    debug("Prompt final para Gemini Image:")
    debug(prompt)

    for attempt in range(1, max_attempts + 1):
        try:
            debug(f"Intento de imagen {attempt}/{max_attempts}")

            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    image_config=types.ImageConfig(aspect_ratio="1:1")
                ),
            )

            img = extract_first_image(response)
            debug("Gemini devolvió una imagen.")

            if is_visually_flat(img):
                raise RuntimeError("Imagen visualmente plana o vacía.")

            img = ImageEnhance.Contrast(img).enhance(1.03)
            img = ImageEnhance.Color(img).enhance(0.97)
            img = ImageEnhance.Brightness(img).enhance(1.00)

            img = img.filter(ImageFilter.GaussianBlur(radius=0.12))

            texture = Image.effect_noise(img.size, random.uniform(8, 14)).convert("L")
            texture = ImageOps.colorize(
                texture, black=(232, 232, 232), white=(255, 255, 255)
            ).convert("RGB")
            img = Image.blend(img, texture, 0.04)

            img = img.resize((w, h), Image.LANCZOS)

            if is_visually_flat(img):
                raise RuntimeError("La imagen siguió demasiado plana tras el postproceso.")

            debug("Imagen aceptada.")
            return img

        except Exception as e:
            last_error = e
            debug(f"Intento fallido: {e}")

    debug(f"Todos los intentos fallaron. Último error: {last_error}")
    debug("Usando fallback ilustrado.")
    return generate_fallback_image(size=size)


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


def choose_text_box(image_prompt_data: dict, img_size: tuple[int, int]) -> tuple[int, int, int]:
    composition = image_prompt_data.get("composition", "").lower()
    w, h = img_size

    if "upper" in composition or "top" in composition:
        return w // 2, int(h * 0.22), int(w * 0.74)

    if "lower" in composition or "bottom" in composition:
        return w // 2, int(h * 0.72), int(w * 0.74)

    if "left" in composition:
        return int(w * 0.35), int(h * 0.25), int(w * 0.50)

    if "right" in composition:
        return int(w * 0.65), int(h * 0.25), int(w * 0.50)

    return w // 2, int(h * 0.22), int(w * 0.74)


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
        debug("Escena débil detectada, regenerando una vez...")
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
