"""Free scene images via Pollinations.ai's classic anonymous image
endpoint, plus a local, API-free thumbnail generator built with
Pillow.

Deliberately NOT using an API key here: Pollinations' authenticated
path enforces a per-key Pollen budget that returns 402 once it's
exhausted, while the anonymous path only rate-limits (~1 request per
15s) and never bills. For a video every 2 days, the rate limit costs
a couple of minutes of wait time and nothing else.
"""

import os
import time
from urllib.parse import quote
import requests
from PIL import Image, ImageDraw, ImageFont

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt/"
ANONYMOUS_DELAY_SECONDS = 16  # stay comfortably under the ~1 req/15s anonymous limit


def generate_image(prompt, out_path, width=1080, height=1920, retries=2):
    url = f"{POLLINATIONS_BASE}{quote(prompt)}"
    params = {"model": "flux", "width": width, "height": height, "nologo": "true"}

    last_resp = None
    for attempt in range(1, retries + 2):
        resp = requests.get(url, params=params, timeout=90)
        if resp.status_code == 200:
            with open(out_path, "wb") as f:
                f.write(resp.content)
            return out_path
        last_resp = resp
        print(f"Image gen attempt {attempt} failed: {resp.status_code}, retrying...")
        time.sleep(ANONYMOUS_DELAY_SECONDS)

    last_resp.raise_for_status()


def generate_scene_images(beat_prompts, out_dir="scenes"):
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for i, prompt in enumerate(beat_prompts):
        if i > 0:
            time.sleep(ANONYMOUS_DELAY_SECONDS)  # respect the anonymous rate limit
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