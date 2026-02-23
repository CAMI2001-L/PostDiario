import json, os, random
from datetime import datetime
from dateutil import tz
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT_DIR = "out"
IMG_NAME = "post.jpg"

def today_madrid():
    madrid = tz.gettz("Europe/Madrid")
    return datetime.now(tz=madrid).date().isoformat()

def load_library():
    with open("phrases_es.json", "r", encoding="utf-8") as f:
        return json.load(f)

def pick_phrase(lib):
    theme = random.choice(list(lib["themes"].keys()))
    phrase = random.choice(lib["themes"][theme])
    return theme, phrase

def build_caption(theme, phrase, lib):
    intros = [
        "Una reflexión corta para hoy:",
        "Un recordatorio suave:",
        "Si hoy te pesa la cabeza, lee esto:",
        "Hoy, una idea para respirar un poco mejor:"
    ]
    bodies = [
        "A veces el problema no es lo que pasa, sino lo que te dices sobre lo que pasa.",
        "No tienes que resolver tu vida hoy. Solo dar un paso honesto.",
        "Lo que sientes tiene sentido. Y aun así, no define quién eres.",
        "Tu mente habla fuerte. Tú puedes hablarle más claro."
    ]
    ctas = [
        "Guárdalo si te sirve 🤍",
        "¿Te pasa últimamente? Te leo en comentarios.",
        "Envíalo a alguien que lo necesite hoy.",
        "Si te resonó, dale guardar para volver cuando lo necesites."
    ]

    tags = lib["hashtags"][:]
    random.shuffle(tags)
    hashtags = " ".join(tags[:10])

    caption = (
        f"{random.choice(intros)}\n\n"
        f"“{phrase}”\n\n"
        f"{random.choice(bodies)}\n\n"
        f"{random.choice(ctas)}\n\n"
        f"{hashtags}"
    )
    return caption, hashtags

def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    line = []
    for w in words:
        test = " ".join(line + [w])
        if draw.textlength(test, font=font) <= max_width:
            line.append(w)
        else:
            lines.append(" ".join(line))
            line = [w]
    if line:
        lines.append(" ".join(line))
    return lines

def make_background(size=(1080, 1080)):
    w, h = size
    base = Image.new("RGB", size, (18, 18, 20))
    glow = Image.new("RGB", size, (60, 60, 75)).filter(ImageFilter.GaussianBlur(180))
    base = Image.blend(base, glow, 0.28)
    return base

def render_quote_image(quote, handle="@tu_cuenta", out_path=f"{OUT_DIR}/{IMG_NAME}"):
    os.makedirs(OUT_DIR, exist_ok=True)
    img = make_background()
    draw = ImageDraw.Draw(img)

    font_path = "assets/fonts/PlayfairDisplay-Regular.ttf"
    if not os.path.exists(font_path):
        raise FileNotFoundError(
            "Falta la fuente TTF en assets/fonts/PlayfairDisplay-Regular.ttf"
        )

    quote_font = ImageFont.truetype(font_path, 64)
    small_font = ImageFont.truetype(font_path, 34)

    margin = 120
    max_width = img.size[0] - 2 * margin

    lines = wrap_text(draw, f"“{quote}”", quote_font, max_width)

    line_h = 78
    block_h = len(lines) * line_h
    y = (img.size[1] - block_h) // 2 - 40

    for line in lines:
        x = (img.size[0] - draw.textlength(line, font=quote_font)) / 2
        draw.text((x + 2, y + 2), line, font=quote_font, fill=(0, 0, 0))
        draw.text((x, y), line, font=quote_font, fill=(245, 245, 245))
        y += line_h

    sig = handle
    sx = (img.size[0] - draw.textlength(sig, font=small_font)) / 2
    sy = img.size[1] - 140
    draw.text((sx, sy), sig, font=small_font, fill=(200, 200, 200))

    img.save(out_path, quality=95)

def main():
    lib = load_library()
    date_str = today_madrid()
    theme, phrase = pick_phrase(lib)
    caption, hashtags = build_caption(theme, phrase, lib)

    handle = os.environ.get("IG_HANDLE", "@tu_cuenta")
    render_quote_image(phrase, handle=handle)

    payload = {
        "date": date_str,
        "theme": theme,
        "phrase": phrase,
        "caption": caption,
        "hashtags": hashtags,
        "image_path": f"{OUT_DIR}/{IMG_NAME}"
    }

    with open(f"{OUT_DIR}/post.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("OK:", payload["date"], payload["theme"])

if __name__ == "__main__":
    main()
