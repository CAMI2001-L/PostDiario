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

Buenos ejemplos de scene_prompt:
- "a young person with dark messy hair lying on the floor writing in a notebook, wearing an oversized cozy hoodie, headphones nearby, tea cup, books, soft purple room, emotional pastel illustration"
- "a young person hugging themselves softly while small tangled scribbles float above their head in a cozy bedroom"
- "a young person walking while carrying an oversized backpack made of stones as a metaphor for emotional weight"
- "a young person sitting quietly while a large soft wave shape rises behind them as a metaphor for overwhelming thoughts"
- "a young person beside a large hourglass as a metaphor for time and healing, warm pastel illustration"

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
            "No todo límite nace desde el rechazo.\n\n"
            "Muchos nacen desde el cansancio de seguir dándote por completo donde ya no hay cuidado.\n\n"
            "Poner distancia no siempre es frialdad.\n"
            "A veces es respeto por tu paz.\n\n"
            "Guárdalo si hoy necesitas recordarlo.\n\n"
            "#limites #saludmental #psicologia #autocuidado #amorpropio #bienestar #reflexiones #ansiedad #sanar",
            "a young person with dark messy hair standing under a small rain cloud while the rest of the room is calm, soft emotional pastel illustration, cozy composition, subtle contextual elements, not empty background",
        )


def get_ai_horde_headers() -> dict:
    api_key = os.environ.get("AI_HORDE_API_KEY", "0000000000")
    client_name = os.environ.get(
        "AI_HORDE_CLIENT",
        "PostDiario:1.0:https://github.com/CAMI2001-L/PostDiario",
    )
    return {
        "apikey": api_key,
        "Client-Agent": client_name,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def build_ai_horde_prompt(theme: str, scene_prompt: str) -> str:
    positive = f"""
Create a square 1:1 digital illustration with NO text, NO letters, NO typography, NO watermark.

This must look like a polished emotional Instagram illustration, not a photograph.

Theme: {theme}
Main visual scene: {scene_prompt}

Style:
soft emotional Instagram illustration,
hand-drawn digital art,
clean outlines,
soft muted pastel palette,
cozy lo-fi mood,
cute tasteful character design,
faceless or minimally detailed face,
simple but polished composition,
shareable social media illustration

Composition:
- character centered or slightly lower
- leave clean space in the upper half for quote overlay
- background should be simple but not empty
- include gentle contextual elements related to the emotion
- visually balanced
- finished illustrated post look

Very important:
- NOT a photo
- NOT realistic
- NOT a plain solid background
- NOT a flat gradient only
- NOT a stick figure
- NOT a rough doodle
- NOT an ugly sketch
""".strip()

    negative = """
photography, realistic photo, photorealistic, cinematic still,
3d render, vector corporate style, glossy render,
detailed realistic face, detailed eyes, extra fingers, extra limbs,
text, letters, typography, watermark, logo,
empty background, plain background, abstract gradient, flat gradient only,
messy composition, clutter, ugly sketch, stick figure, bad anatomy
""".strip()

    return f"{positive} ### {negative}"


def request_ai_horde_image(theme: str, scene_prompt: str) -> str:
    prompt = build_ai_horde_prompt(theme, scene_prompt)

    payload = {
        "prompt": prompt,
        "params": {
            "width": 1024,
            "height": 1024,
            "steps": 24,
            "cfg_scale": 7,
            "sampler_name": "k_euler_a",
            "n": 1,
        },
        "nsfw": False,
        "trusted_workers": False,
        "slow_workers": True,
        "censor_nsfw": True,
        "models": ["DreamShaper XL"],
    }

    r = requests.post(
        "https://aihorde.net/api/v2/generate/async",
        headers=get_ai_horde_headers(),
        json=payload,
        timeout=60,
    )
    r.raise_for_status()

    data = r.json()
    req_id = data.get("id")

    if not req_id:
        raise RuntimeError(f"AI Horde no devolvió id: {data}")

    return req_id


def poll_ai_horde_image(request_id: str, max_wait_seconds: int = 180) -> str:
    start = time.time()

    while time.time() - start < max_wait_seconds:
        r = requests.get(
            f"https://aihorde.net/api/v2/generate/check/{request_id}",
            headers=get_ai_horde_headers(),
            timeout=30,
        )
        r.raise_for_status()
        status = r.json()

        if status.get("done") is True:
            r2 = requests.get(
                f"https://aihorde.net/api/v2/generate/status/{request_id}",
                headers=get_ai_horde_headers(),
                timeout=30,
            )
            r2.raise_for_status()
            final_data = r2.json()

            generations = final_data.get("generations") or []
            if not generations:
                raise RuntimeError(f"AI Horde terminó sin imágenes: {final_data}")

            img_url = generations[0].get("img")
            if not img_url:
                raise RuntimeError(f"AI Horde no devolvió URL de imagen: {final_data}")

            return img_url

        time.sleep(4)

    raise TimeoutError("AI Horde tardó demasiado en generar la imagen.")


def download_image_as_pil(url: str) -> Image.Image:
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")


def generate_fallback_image(size=(1080, 1080)) -> Image.Image:
    """
    Fallback simple pero decente si AI Horde falla.
    """
    img = Image.new("RGB", size, (212, 192, 214))
    draw = ImageDraw.Draw(img)

    # suelo
    draw.rectangle((0, int(size[1] * 0.78), size[0], size[1]), fill=(216, 202, 190))

    # personaje simple acostado escribiendo
    # cabeza
    draw.ellipse((420, 540, 520, 640), fill=(236, 220, 205), outline=(60, 52, 70), width=3)
    # pelo
    draw.ellipse((405, 520, 530, 620), fill=(25, 20, 30))
    # cuerpo sudadera
    draw.rounded_rectangle((470, 590, 760, 760), radius=40, fill=(72, 56, 102), outline=(52, 40, 75), width=3)
    # brazo
    draw.line((500, 680, 390, 760), fill=(72, 56, 102), width=18)
    draw.line((390, 760, 345, 810), fill=(236, 220, 205), width=10)
    # pierna
    draw.line((710, 720, 860, 640), fill=(55, 47, 83), width=22)
    draw.line((860, 640, 920, 590), fill=(236, 220, 205), width=12)

    # libreta
    draw.rounded_rectangle((280, 780, 440, 860), radius=8, fill=(245, 245, 242), outline=(50, 50, 50), width=3)
    # té
    draw.ellipse((720, 800, 810, 835), fill=(120, 85, 90))
    draw.rectangle((735, 740, 795, 810), fill=(160, 115, 120))

    img = img.filter(ImageFilter.GaussianBlur(0.3))
    return img


def get_ia_background(theme: str, scene_prompt: str, size=(1080, 1080)) -> Image.Image:
    try:
        debug("Solicitando imagen a AI Horde...")
        req_id = request_ai_horde_image(theme, scene_prompt)
        debug(f"Request ID: {req_id}")

        img_url = poll_ai_horde_image(req_id, max_wait_seconds=180)
        debug(f"Imagen lista: {img_url}")

        img = download_image_as_pil(img_url)
        img = ImageEnhance.Contrast(img).enhance(1.02)
        img = ImageEnhance.Color(img).enhance(0.98)
        img = ImageEnhance.Brightness(img).enhance(1.00)
        img = img.filter(ImageFilter.GaussianBlur(radius=0.15))
        img = img.resize(size, Image.LANCZOS)

        return img

    except Exception as e:
        debug(f"Fallo AI Horde: {e}")
        debug("Usando fallback.")
        return generate_fallback_image(size=size)


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

    shutil.copyfile(f"{OUT_DIR}/{IMG_NAME}", f"{PUBLIC_DIR}/latest.jpg")

    with open(f"{PUBLIC_DIR}/latest.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("Post generado correctamente.")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
