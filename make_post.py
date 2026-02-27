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
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    # --- EL NUEVO CEREBRO DE TU COPYWRITER ---
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
        return "peace", "No tienes que resolver toda tu vida hoy.", "Respira. Guarda esto para recordarlo mañana. 🤍 #pazmental"

def get_ia_background(theme, size=(1080, 1080)):
    """Usa Pollinations.ai con prompts mejorados para generar fondos artísticos y bonitos."""
    w, h = size
    
    # --- NUEVA LISTA DE ESTILOS VISUALES MEJORADOS ---
    # He incluido estilos que generan imágenes profundas, artísticas y estéticas,
    # pero asegurando que sigan siendo oscuras para la legibilidad del texto.
    prompts_mejorados = [
        # Estilo 1: Fotografía Cinematográfica de Paisaje
        f"Cinematic breathtaking landscape photography, related to {theme}, dark mood lighting, deep rich colors, high definition, 8k, photorealistic, intricate details, ultra-detailed, no text",
        
        # Estilo 2: Ilustración Fantástica Digital
        f"Magical digital fantasy art illustration, inspired by {theme}, dark aesthetic, soft bioluminescence glow, dreaming atmosphere, deep colors, trending on ArtStation, no text",
        
        # Estilo 3: Arte Abstracto Geométrico 3D Moderno
        f"Modern abstract 3D geometric art composition, related to {theme}, dark matte textures with neon accents, soft studio lighting, clean lines, minimalist but complex, cinematic composition, no text",
        
        # Estilo 4: Fotografía Macro Surrealista
        f"Macro surreal photography of textures, related to {theme}, dark ethereal background, sharp focus on intricate details, deep colors, cinematic lighting, conceptual art, no text"
    ]
    
    # Elegimos uno de los estilos al azar para que cada día sea diferente
    prompt_img = random.choice(prompts_mejorados)
    
    # Formateamos el prompt para la URL (reemplazando espacios por guiones y añadiendo un UUID para evitar cacheo)
    formatted_prompt = prompt_img.replace(" ", "-").replace(",", "") + "-" + str(uuid.uuid4())
    url = f"https://image.pollinations.ai/prompt/{formatted_prompt}?width={w}&height={h}&nologo=true"
    
    print(f"Generando fondo IA 'bonito' con prompt: {prompt_img[:50]}...") # Imprimimos solo el inicio del prompt
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content)).convert("RGB")
            
            # --- MANTENEMOS EL FILTRO OSCURO ---
            # Aunque la imagen sea más bonita, necesitamos que siga siendo oscura
            # para que el texto blanco resalte perfectamente.
            dark_layer = Image.new("RGB", size, (18, 18, 20)) # Color casi negro
            return Image.blend(img, dark_layer, 0.6) # Mezclamos al 60% de oscuridad
            
    except Exception as e:
        print(f"Error descargando imagen IA (usando fondo por defecto): {e}")
    
    # Fallback: Fondo de emergencia si falla internet
    base = Image.new("RGB", size, (18, 18, 20))
    glow = Image.new("RGB", size, (60, 60, 75)).filter(ImageFilter.GaussianBlur(180))
    return Image.blend(base, glow, 0.28)

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
