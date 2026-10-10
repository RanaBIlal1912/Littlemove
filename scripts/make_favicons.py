#!/usr/bin/env python
"""Generate LittleMove favicons from the brand sheet image.

Usage:  python scripts/make_favicons.py
Output: static/img/favicon-16.png  favicon-32.png  favicon-48.png
                 favicon.ico  apple-touch-icon.png  icon-192.png  icon-512.png
"""
from pathlib import Path
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("Pillow is not installed.  Run: pip install Pillow")

ROOT     = Path(__file__).resolve().parent.parent
IMG_DIR  = ROOT / "static" / "img"
SRC_PATH = IMG_DIR / "All data.jpeg"

CROP_BOX   = (215, 50, 455, 290)   # 240 × 240 px — running-boy logo mark
CREAM      = (253, 251, 246, 255)   # #FDFBF6
RADIUS_PCT = 0.22                   # ~22 % corner radius


def _make_mask(size: int) -> Image.Image:
    r = max(1, int(size * RADIUS_PCT))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [(0, 0), (size - 1, size - 1)], radius=r, fill=255
    )
    return mask


def make_icon(size: int, cropped: Image.Image) -> Image.Image:
    bg   = Image.new("RGBA", (size, size), CREAM)
    mask = _make_mask(size)
    icon = cropped.resize((size, size), Image.LANCZOS)
    bg.paste(icon, mask=mask)
    return bg


def main() -> None:
    if not SRC_PATH.exists():
        sys.exit(f"Source not found: {SRC_PATH}")

    src     = Image.open(SRC_PATH).convert("RGBA")
    cropped = src.crop(CROP_BOX)

    PNG_SIZES = [
        ("favicon-16.png",       16),
        ("favicon-32.png",       32),
        ("favicon-48.png",       48),
        ("apple-touch-icon.png", 180),
        ("icon-192.png",         192),
        ("icon-512.png",         512),
    ]
    for name, sz in PNG_SIZES:
        path = IMG_DIR / name
        make_icon(sz, cropped).save(path, "PNG")
        print(f"  {path.relative_to(ROOT)}")

    ico_path = IMG_DIR / "favicon.ico"
    make_icon(48, cropped).save(
        ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)]
    )
    print(f"  {ico_path.relative_to(ROOT)}")
    print("Done.")


if __name__ == "__main__":
    main()
