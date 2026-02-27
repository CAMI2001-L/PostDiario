import json, os, random, uuid
from datetime import datetime
from dateutil import tz
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
from io import BytesIO
from groq import Groq

OUT_DIR = "out"
IMG_NAME = "post.jpg"

def today_madrid():
    madrid = tz.gettz("Europe/Madrid")
    return datetime.now(tz=madrid).date().isoformat()

def generate_ia_content():
    # Se conecta a Groq usando el Secret de GitHub
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    prompt = """
    Eres un experto en desarrollo personal. Genera contenido para un post de Instagram.
    Devuelve ÚNICAMENTE un objeto JSON con estas tres claves:
    - "theme": Una palabra que resuma el tema en inglés (ej: anxiety, motivation, self-love).
    - "phrase": Una reflexión profunda en español de máximo 20 palabras.
    - "caption": Un pie de foto en español, empático, con emojis y 10 hashtags.
    No añadas texto fuera del JSON.
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
        return "nature", "Lo simple también es una meta.", "Respira. #paz"

def get_ia_background(theme, size=(1080, 1080)):
    # Usa Pollinations (Gratis y sin API Key) para el fondo
    w, h = size
    prompt_img = f"Abstract soft gradient background, dark mode, representing {theme}, aesthetic, no text"
    formatted_prompt = prompt_img.replace(" ", "-") + "-" + str(uuid.uuid4())
    url = f"https://image.pollinations.ai/prompt/{formatted_prompt}?width={w}&height={h}&nologo=true"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content)).convert("RGB")
            dark_layer = Image.new("RGB", size, (18, 18, 20))
            return Image.blend(img, dark_layer, 0.6) # Oscurece para que se lea la letra
    except Exception as e:
        print(f"Error IA Imagen: {e}")
    
    # Fondo de emergencia si falla la IA
    return Image.new("RGB", size, (30, 30, 35))

def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, line = [], []
    for w in words:
        if draw.textlength(" ".join(line + [w]), font=font) <= max_width:
            line.append(w)
        else:
            lines.append(" ".join(line))
            line = [w]
    if line: lines.append(" ".join(line))
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
        draw.text((x + 2, y + 2), line, font=quote_font, fill=(0, 0, 0))
        draw.text((x, y), line, font=quote_font, fill=(245, 245, 245))
        y += 78

    draw.text(((img.size[0] - draw.textlength(handle, font=small_font)) / 2, img.size[1] - 140), handle, font=small_font, fill=(200, 200, 200))
    img.save(out_path, quality=95)

def main():
    theme, phrase, caption = generate_ia_content()
    handle = os.environ.get("IG_HANDLE", "@tu_cuenta")
    
    render_quote_image(phrase, theme, handle=handle)

    payload = {
        "date": today_madrid(),
        "theme": theme,
        "phrase": phrase,
        "caption": caption,
        "image_path": f"{OUT_DIR}/{IMG_NAME}"
    }

    with open(f"{OUT_DIR}/post.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("Post IA Generado con éxito.")

if __name__ == "__main__":
    main()
