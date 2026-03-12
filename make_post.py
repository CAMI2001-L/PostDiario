import json
import os
import random
import shutil
from datetime import datetime
from typing import Any

from dateutil import tz
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from google import genai
from google.genai import types


OUT_DIR = "out"
PUBLIC_DIR = "public"
IMG_NAME = "post.jpg"

SIZE = 1080


# =========================
# Utils
# =========================

def today_madrid():
    madrid = tz.gettz("Europe/Madrid")
    return datetime.now(tz=madrid).date().isoformat()


def get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta GEMINI_API_KEY")
    return genai.Client(api_key=api_key)


def safe_json(response: Any):
    text = response.text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    return json.loads(text)


# =========================
# AI TEXT
# =========================

def generate_text():

    client = get_client()

    prompt = """
Eres copywriter de una cuenta de Instagram de psicología emocional.

Devuelve SOLO JSON:

{
 "theme":"",
 "phrase":"",
 "caption":"",
 "visual_metaphor":""
}

Reglas:

phrase
máximo 10 palabras

caption
2-4 párrafos breves
8-10 hashtags

visual_metaphor debe ser uno de:

rain_cloud
shadow_wave
self_hug
heavy_backpack
scribble_thoughts
hourglass
"""

    schema = {
        "type": "object",
        "properties": {
            "theme": {"type": "string"},
            "phrase": {"type": "string"},
            "caption": {"type": "string"},
            "visual_metaphor": {"type": "string"},
        },
        "required": ["theme", "phrase", "caption", "visual_metaphor"],
    }

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=schema,
            temperature=0.9,
        ),
    )

    data = safe_json(response)

    return (
        data["theme"],
        data["phrase"],
        data["caption"],
        data["visual_metaphor"],
    )


# =========================
# VISUAL STYLE
# =========================

BG = (226, 230, 235)
GROUND = (206, 210, 215)
LINE = (75, 85, 95)
ACCENT = (140, 150, 160)

HAIR = (35, 35, 35)
DRESS = (70, 75, 85)


def canvas():

    img = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, SIZE * 0.75, SIZE, SIZE), fill=GROUND)

    return img, draw


# =========================
# GIRL CHARACTER
# =========================

def draw_girl(draw, cx=540, base=820):

    # head
    draw.ellipse((cx-40, base-220, cx+40, base-140), outline=LINE, width=6)

    # hair
    draw.ellipse((cx-45, base-235, cx+45, base-150), fill=HAIR)

    # body
    draw.line((cx, base-140, cx, base-20), fill=LINE, width=6)

    # dress
    draw.polygon([
        (cx-50, base-140),
        (cx+50, base-140),
        (cx+30, base-40),
        (cx-30, base-40),
    ], outline=LINE, fill=DRESS)

    # arms
    draw.line((cx, base-120, cx-60, base-70), fill=LINE, width=5)
    draw.line((cx, base-120, cx+60, base-70), fill=LINE, width=5)

    # legs
    draw.line((cx, base-40, cx-40, base+50), fill=LINE, width=5)
    draw.line((cx, base-40, cx+40, base+50), fill=LINE, width=5)


# =========================
# METAPHORS
# =========================

def rain_cloud(draw):

    draw.ellipse((380,220,700,360), fill=(200,205,210))

    for x in range(420,680,40):
        draw.line((x,360,x-10,400), fill=ACCENT, width=4)


def shadow_wave(draw):

    points=[]

    for x in range(0,SIZE,40):
        y=650+40*random.random()
        points.append((x,y))

    points.append((SIZE,SIZE))
    points.append((0,SIZE))

    draw.polygon(points,fill=(190,200,210))


def self_hug(draw):

    draw.ellipse((480,300,600,420),outline=ACCENT,width=5)
    draw.line((500,350,560,380),fill=ACCENT,width=6)
    draw.line((560,350,500,380),fill=ACCENT,width=6)


def heavy_backpack(draw):

    draw.rectangle((600,550,680,660),outline=ACCENT,width=5)


def scribble(draw):

    for _ in range(40):
        x=random.randint(430,650)
        y=random.randint(200,340)
        draw.line((x,y,x+random.randint(-30,30),y+random.randint(-30,30)),fill=ACCENT,width=3)


def hourglass(draw):

    draw.line((450,450,650,450),fill=ACCENT,width=5)
    draw.line((450,450,540,520),fill=ACCENT,width=5)
    draw.line((650,450,540,520),fill=ACCENT,width=5)

    draw.line((450,600,650,600),fill=ACCENT,width=5)
    draw.line((450,600,540,520),fill=ACCENT,width=5)
    draw.line((650,600,540,520),fill=ACCENT,width=5)


def draw_metaphor(draw, name):

    if name=="rain_cloud":
        rain_cloud(draw)

    elif name=="shadow_wave":
        shadow_wave(draw)

    elif name=="self_hug":
        self_hug(draw)

    elif name=="heavy_backpack":
        heavy_backpack(draw)

    elif name=="scribble_thoughts":
        scribble(draw)

    elif name=="hourglass":
        hourglass(draw)


# =========================
# TEXT
# =========================

def wrap(draw,text,font,max_width):

    words=text.split()
    lines=[]
    line=[]

    for w in words:

        test=" ".join(line+[w])

        if draw.textlength(test,font=font)<=max_width:
            line.append(w)
        else:
            lines.append(" ".join(line))
            line=[w]

    if line:
        lines.append(" ".join(line))

    return lines


def draw_text(img,phrase):

    draw=ImageDraw.Draw(img)

    font_path="assets/fonts/PlayfairDisplay-Regular.ttf"

    if os.path.exists(font_path):
        font=ImageFont.truetype(font_path,60)
    else:
        font=ImageFont.load_default()

    lines=wrap(draw,f"“{phrase}”",font,760)

    y=150

    for line in lines:

        w=draw.textlength(line,font=font)
        x=(SIZE-w)/2

        draw.text((x+2,y+2),line,font=font,fill=(0,0,0))
        draw.text((x,y),line,font=font,fill=(245,245,240))

        y+=70


# =========================
# MAIN RENDER
# =========================

def render_image(phrase,metaphor):

    img,draw=canvas()

    draw_metaphor(draw,metaphor)

    draw_girl(draw)

    draw_text(img,phrase)

    img=img.filter(ImageFilter.GaussianBlur(0.2))

    return img


# =========================
# MAIN
# =========================

def main():

    os.makedirs(OUT_DIR,exist_ok=True)
    os.makedirs(PUBLIC_DIR,exist_ok=True)

    theme,phrase,caption,metaphor=generate_text()

    img=render_image(phrase,metaphor)

    out_img=f"{OUT_DIR}/{IMG_NAME}"

    img.save(out_img,"JPEG",quality=95)

    payload={
        "date":today_madrid(),
        "theme":theme,
        "phrase":phrase,
        "caption":caption,
        "visual_metaphor":metaphor
    }

    with open(f"{OUT_DIR}/post.json","w",encoding="utf-8") as f:
        json.dump(payload,f,ensure_ascii=False,indent=2)

    # 🔥 COPIA A PUBLIC PARA QUE IG SUBA LA IMAGEN NUEVA

    shutil.copyfile(out_img,"public/latest.jpg")

    with open("public/latest.json","w",encoding="utf-8") as f:
        json.dump(payload,f,ensure_ascii=False,indent=2)

    print("Post generado correctamente")


if __name__=="__main__":
    main()
