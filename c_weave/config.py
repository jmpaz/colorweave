import os

COLORWEAVE_DIR = os.path.expanduser("~/.local/share/colorweave")
SCHEMES_DIR = os.path.join(COLORWEAVE_DIR, "schemes")
WALLPAPER_DIR = os.path.join(COLORWEAVE_DIR, "wallpapers")


def ensure_directories():
    for directory in [COLORWEAVE_DIR, SCHEMES_DIR, WALLPAPER_DIR]:
        os.makedirs(directory, exist_ok=True)
