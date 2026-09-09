"""
Pre-renders placeholder avatars (colored circle + initials) for players, and
for any hero that doesn't already have a real avatar image in assets/avatars/.

Hero avatars are normally the REAL portraits downloaded from the official
Garena Liên Quân Mobile site (assets/avatars/<Tên tướng>.png, one per entry
in data.HEROES) — this script does NOT overwrite those. It only fills in a
generated placeholder for a hero that's missing an avatar file entirely
(e.g. right after you add a brand-new hero name to data.HEROES and haven't
sourced a real image yet), and it always (re)generates player avatars, since
players don't have real portraits.

Run once / whenever needed: `python generate_avatars.py`.
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

    hero_generated = 0
    for hero in data.HEROES:
        out_path = f"assets/avatars/{hero}.png"
        if os.path.exists(out_path):
            continue  # real avatar already downloaded — don't clobber it
        render_avatar(hero, out_path)
        hero_generated += 1

    for player in data.PLAYERS:
        render_avatar(player, f"assets/players/{player}.png")

    print(
        f"Generated {hero_generated} placeholder hero avatar(s) (skipped "
        f"{len(data.HEROES) - hero_generated} that already have a real "
        f"image) and {len(data.PLAYERS)} player avatars."
    )


if __name__ == "__main__":
    main()
