#!/usr/bin/env python3
"""Genera un JPEG de fondo de ejemplo para los PDF (requiere Pillow)."""
from pathlib import Path

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "assets"
OUTPUT = ASSETS_DIR / "background.jpg"


def create_placeholder_bg() -> None:
    width, height = 1275, 1650  # carta ~150 DPI
    image = Image.new("RGB", (width, height), (245, 245, 250))
    draw = ImageDraw.Draw(image)
    draw.rectangle([50, 50, width - 50, height - 50], outline=(200, 200, 215), width=10)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, "JPEG", quality=90)
    print(f"Placeholder creado: {OUTPUT}")


if __name__ == "__main__":
    create_placeholder_bg()
