import json, os, random, uuid
from datetime import datetime
from dateutil import tz
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance
import requests
from io import BytesIO
from groq import Groq

OUT_DIR = "out"
IMG_NAME = "post.jpg"


def today_madrid():
    madrid = tz.gettz("Europe/Madrid")
    return datetime.now(tz=madrid).date().isoformat()


def generate_ia_content():
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    prompt = """
Eres un copywriter experto en psicología y redes sociales, famoso por crear posts virales en Instagram que conectan profundamente con la gente.
Tu objetivo es hacer que el lector sienta: "Wow, parece que me leyeron la mente, esto está escrito para mí".

Reglas estrictas para el contenido:
1. Frase ("phrase"): Máximo 15 palabras. Tiene que ser cruda, honesta y directa. CERO clichés de autoayuda barata (prohibido usar "persigue tus sueños" o "sonríele a la vida"). Debe ser una revelación o un límite sano que la gente quiera compartir en sus historias de inmediato.
2. Pie de foto ("caption"):
   - LÍNEA 1 (Gancho): Una frase corta que obligue a detener el scroll (ej: "Nadie te dice esto cuando estás sanando, pero...").
   - CUERPO: Habla de tú a tú. Valida emociones reales y difíciles (el cansancio mental, soltar a alguien, poner límites, la ansiedad silenciosa).
   - CIERRE (CTA): Termina SIEMPRE pidiendo interacción de forma natural (ej: "Guárdalo para leerlo cuando tu mente haga mucho ruido 🤍", "¿En qué etapa estás tú? Te leo", "Envíalo a quien necesite este abrazo virtual").
   - EMOJIS: Usa pocos, pero estéticos (🤍, ✨, 🌿, 🩹). Incluye 10 hashtags estratégicos al final.
3. Tema ("theme"): Una sola palabra en INGLÉS que describa la vibra visual (ej: overthinking, healing, boundaries, solitude, letting-go).

Devuelve ÚNICAMENTE un objeto JSON válido con estas tres claves exactas: "theme", "phrase", "caption". No escribas nada más.
"""

    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        content = json.loads(response.choices[0].message.content)
        return content["theme"], content["phrase"], content["caption"]
    except Exception as e:
        print(f"Error IA Texto: {e}")
        return (
            "peace",
            "No tienes que resolver toda tu vida hoy.",
            "Respira. Guarda esto para recordarlo mañana. 🤍 #pazmental"
        )


def apply_vignette(img: Image.Image, strength: float = 0.15) -> Image.Image:
    """
    Viñeta suave: oscurece bordes y mantiene centro más claro.
    strength: 0.0 -> 1.0
    """
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)

    # Centro claro (elipse grande), bordes oscurecen
    d.ellipse((-w * 0.12, -h * 0.12, w * 1.12, h * 1.12), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(int(min(w, h) * 0.10)))
    mask = ImageOps.autocontrast(mask)

    dark = Image.new("RGB", (w, h), (12, 12, 14))
    darkened = Image.blend(img, dark, strength)

    # Invertimos máscara para que se oscurezcan más los bordes
    return Image.composite(img, darkened, ImageOps.invert(mask))


def get_ia_background(theme, size=(1080, 1080)):
    """
    Genera un fondo estético con Pollinations + acabado pro:
    - prompts más "instagram"
    - uuid para evitar cache
    - contraste/color suave
    - blur suave
    - grain film suave
    - overlay de color suave
    - viñeta suave para legibilidad
    """
    w, h = size

    prompts_mejorados = [
        f"aesthetic landscape photography background related to {theme}, golden hour light, fog, depth of field, cinematic, 35mm film look, high detail, no text",
        f"dreamy nature photography background related to {theme}, soft sunlight, flowers, bokeh, shallow depth of field, aesthetic instagram background, no text",
        f"cozy aesthetic interior photography background related to {theme}, warm window light, plants, soft shadows, film photography, no text",
        f"modern abstract gradient background related to {theme}, smooth colorful shapes, aesthetic design, soft lighting, high detail, no text",
    ]

    prompt_img = random.choice(prompts_mejorados)
    formatted_prompt = prompt_img.replace(" ", "-").replace(",", "") + "-" + str(uuid.uuid4())
    url = f"https://image.pollinations.ai/prompt/{formatted_prompt}?width={w}&height={h}&nologo=true"

    print(f"Generando fondo IA con prompt: {prompt_img[:80]}...")

    try:
        response = requests.get(url, timeout=40)

        if response.status_code == 200:
            img = Image.open(BytesIO(response.content)).convert("RGB")

            # Mejoras para evitar fondos apagados
            img = ImageEnhance.Contrast(img).enhance(1.15)
            img = ImageEnhance.Color(img).enhance(1.10)

            # Blur suave
            img = img.filter(ImageFilter.GaussianBlur(radius=1.0))

            # Grain tipo film
            noise = Image.effect_noise(img.size, random.uniform(18, 28)).convert("L")
            noise = ImageOps.colorize(noise, black=(0, 0, 0), white=(255, 255, 255)).convert("RGB")
            img = Image.blend(img, noise, 0.05)

            # Overlay de color suave
            tints = [(255, 180, 190), (180, 220, 255), (200, 255, 210), (255, 230, 180)]
            overlay = Image.new("RGB", size, random.choice(tints))
            img = Image.blend(img, overlay, random.uniform(0.04, 0.08))

            # Viñeta suave para legibilidad del texto
            img = apply_vignette(img, strength=random.uniform(0.10, 0.18))

            return img

        else:
            print(f"Pollinations status: {response.status_code}")

    except Exception as e:
        print(f"Error descargando imagen IA (usando fallback): {e}")

    # Fallback bonito si falla internet
    base = Image.new("RGB", size, (220, 220, 230))
    glow = Image.new("RGB", size, (255, 230, 240)).filter(ImageFilter.GaussianBlur(180))
    img = Image.blend(base, glow, 0.22)
    img = apply_vignette(img, strength=0.15)
    return img


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, line = [], []
    for w in words:
        if draw.textlength(" ".join(line + [w]), font=font) <= max_width:
            line.append(w)
        else:
            lines.append(" ".join(line))
            line = [w]
    if line:
        lines.append(" ".join(line))
    return lines


def render_quote_image(quote, theme, handle="@tu_cuenta", out_path=f"{OUT_DIR}/{IMG_NAME}"):
    os.makedirs(OUT_DIR, exist_ok=True)

    img = get_ia_background(theme)
    draw = ImageDraw.Draw(img)

    font_path = "assets/fonts/PlayfairDisplay-Regular.ttf"
    if not os.path.exists(font_path):
        quote_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    else:
        quote_font = ImageFont.truetype(font_path, 64)
        small_font = ImageFont.truetype(font_path, 34)

    lines = wrap_text(draw, f"“{quote}”", quote_font, img.size[0] - 240)

    y = (img.size[1] - (len(lines) * 78)) // 2 - 40
    for line in lines:
        x = (img.size[0] - draw.textlength(line, font=quote_font)) / 2

        # sombra suave
        draw.text((x + 2, y + 2), line, font=quote_font, fill=(0, 0, 0))
        draw.text((x, y), line, font=quote_font, fill=(245, 245, 245))
        y += 78

    # handle abajo
    hx = (img.size[0] - draw.textlength(handle, font=small_font)) / 2
    draw.text((hx, img.size[1] - 140), handle, font=small_font, fill=(200, 200, 200))

    img = img.convert("RGB")
    img.save(out_path, "JPEG", quality=92, optimize=True)


def main():
    theme, phrase, caption = generate_ia_content()
    handle = os.environ.get("IG_HANDLE", "@tu_cuenta")

    render_quote_image(phrase, theme, handle=handle)

    payload = {
        "date": today_madrid(),
        "theme": theme,
        "phrase": phrase,
        "caption": caption,
        "image_path": f"{OUT_DIR}/{IMG_NAME}",
    }

    with open(f"{OUT_DIR}/post.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("Post IA Generado con éxito.")


if __name__ == "__main__":
    main()
