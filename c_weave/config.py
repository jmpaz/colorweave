import os

COLORWEAVE_DIR = os.path.expanduser("~/.local/share/colorweave")
SCHEMES_DIR = os.path.join(COLORWEAVE_DIR, "schemes")
WALLPAPER_DIR = os.path.join(COLORWEAVE_DIR, "wallpapers")
CACHE_DIR = os.path.expanduser("~/.cache/colorweave")
CACHE_LIGHT_PATH = os.path.join(CACHE_DIR, "light.json")
CACHE_DARK_PATH = os.path.join(CACHE_DIR, "dark.json")


def ensure_directories():
    for directory in [COLORWEAVE_DIR, SCHEMES_DIR, WALLPAPER_DIR, CACHE_DIR]:
        os.makedirs(directory, exist_ok=True)
