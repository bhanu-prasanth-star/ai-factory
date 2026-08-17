"""Free scene images via Pollinations.ai (Flux model), plus a local,
API-free thumbnail generator built with Pillow."""

import os
from urllib.parse import quote
import requests
from PIL import Image, ImageDraw, ImageFont

POLLINATIONS_KEY = os.environ.get("POLLINATIONS_API_KEY", "")


def generate_image(prompt, out_path, width=1080, height=1920):
    url = f"https://gen.pollinations.ai/image/{quote(prompt)}"
    params = {"model": "flux", "width": width, "height": height, "nologo": "true"}
    headers = {"Authorization": f"Bearer {POLLINATIONS_KEY}"} if POLLINATIONS_KEY else {}
    resp = requests.get(url, params=params, headers=headers, timeout=90)
    resp.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(resp.content)
    return out_path


def generate_scene_images(beat_prompts, out_dir="scenes"):
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for i, prompt in enumerate(beat_prompts):
        path = os.path.join(out_dir, f"scene_{i:02d}.jpg")
        generate_image(prompt, path)
        paths.append(path)
    return paths


def make_thumbnail(base_image_path, title_text, out_path="thumbnail.jpg"):
    img = Image.open(base_image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 90)
    except OSError:
        font = ImageFont.load_default()

    words = title_text.upper().split()
    lines, current = [], ""
    for w in words:
        test = f"{current} {w}".strip()
        if draw.textlength(test, font=font) > img.width - 80:
            lines.append(current)
            current = w
        else:
            current = test
    lines.append(current)

    y = img.height - 60 - (len(lines) * 100)
    for line in lines:
        w = draw.textlength(line, font=font)
        x = (img.width - w) / 2
        draw.text((x, y), line, font=font, fill="white", stroke_width=6, stroke_fill="black")
        y += 100

    img.save(out_path, quality=92)
    return out_path
