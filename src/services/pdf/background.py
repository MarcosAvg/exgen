import os

from reportlab.lib.pagesizes import letter

from src.utils.helpers import get_asset_path


def add_background(canvas, doc):
    canvas.saveState()
    bg_path = get_asset_path("background.jpg")
    if os.path.exists(bg_path):
        try:
            canvas.drawImage(bg_path, 0, 0, width=letter[0], height=letter[1])
        except Exception:
            pass
    canvas.restoreState()
