"""
One-off script that pre-renders simple placeholder avatars (colored circle +
initials) for every hero and player, so the dashboard has something nicer
than blank cells in its tables without bundling any real game artwork.

Run once: `python generate_avatars.py`. The generated PNGs are committed to
assets/ so end users don't need Pillow installed just to run the dashboard.
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

import data

SIZE = 96
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def initials(name: str) -> str:
    letters = [c for c in name if c.isalpha()]
    if not letters:
        return "?"
    # Grab first letter, plus first uppercase letter after position 0 if any
    # (keeps things like "TrPhuoc" -> "TP", "Nakroth" -> "N").
    first = letters[0].upper()
    rest_upper = [c for c in name[1:] if c.isupper()]
    second = rest_upper[0].upper() if rest_upper else ""
    return (first + second)[:2]


def render_avatar(name: str, out_path: str) -> None:
    color = data.color_for(name)
    img = Image.new("RGB", (SIZE, SIZE), color)
    draw = ImageDraw.Draw(img)

    # Subtle darker ring for depth.
    draw.ellipse((2, 2, SIZE - 2, SIZE - 2), outline=(0, 0, 0, 60), width=2)

    text = initials(name)
    font = _font(int(SIZE * 0.42))
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((SIZE - w) / 2 - bbox[0], (SIZE - h) / 2 - bbox[1]),
        text,
        font=font,
        fill="white",
    )

    # Circular mask.
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, SIZE, SIZE), fill=255)
    out = Image.new("RGBA", (SIZE, SIZE))
    out.paste(img, (0, 0), mask)
    out.save(out_path)


def main() -> None:
    os.makedirs("assets/avatars", exist_ok=True)
    os.makedirs("assets/players", exist_ok=True)

    for hero in data.HEROES:
        render_avatar(hero, f"assets/avatars/{hero}.png")

    for player in data.PLAYERS:
        render_avatar(player, f"assets/players/{player}.png")

    print(f"Generated {len(data.HEROES)} hero avatars and {len(data.PLAYERS)} player avatars.")


if __name__ == "__main__":
    main()
