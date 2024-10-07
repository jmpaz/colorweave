import json
import os
import random
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from fuzzywuzzy import process as fuzzy_process
from PIL import Image

from c_weave.utils.color import infer_palette

WALLPAPER_DIR = os.path.expanduser("~/.local/share/colorweave/wallpapers")


def ensure_wallpaper_dir():
    os.makedirs(WALLPAPER_DIR, exist_ok=True)


def import_wallpaper(path: str, name: Optional[str], type: str) -> str:
    ensure_wallpaper_dir()

    wallpaper_id = str(uuid.uuid4())
    ext = Path(path).suffix
    new_filename = f"{wallpaper_id}{ext}"
    new_path = os.path.join(WALLPAPER_DIR, new_filename)

    # copy wallpaper
    shutil.copy2(path, new_path)

    # get metadata
    with Image.open(new_path) as img:
        resolution = img.size
    filesize = os.path.getsize(new_path)

    # create metadata
    if name is None:
        name = Path(path).stem
        name_source = "filename"
    else:
        name_source = "manual"

    metadata = {
        "id": wallpaper_id,
        "name": name,
        "type": type,
        "name_source": name_source,
        "resolution": f"{resolution[0]}x{resolution[1]}",
        "filesize": filesize,
        "extension": ext,
    }

    with open(os.path.join(WALLPAPER_DIR, f"{wallpaper_id}.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    return wallpaper_id


def get_wallpaper_path(wallpaper: Dict) -> str:
    return os.path.join(
        WALLPAPER_DIR, f"{wallpaper['id']}.{wallpaper['extension'].lstrip('.')}"
    )


def analyze_wallpaper(wallpaper_id: str) -> List[str]:
    """Analyze a wallpaper and extract colors."""
    wallpaper = get_wallpaper(wallpaper_id) or fuzzy_match_wallpaper(wallpaper_id)
    if not wallpaper:
        raise ValueError(f"Wallpaper with ID {wallpaper_id} not found.")

    full_id = wallpaper["id"]  # ensure full id
    wallpaper_path = get_wallpaper_path(wallpaper)
    colors = infer_palette(wallpaper_path, n=6)

    # Update wallpaper metadata with colors
    wallpaper["colors"] = colors
    metadata_path = os.path.join(WALLPAPER_DIR, f"{full_id}.json")
    with open(metadata_path, "w") as f:
        json.dump(wallpaper, f, indent=2)

    return colors


def list_wallpapers() -> List[Dict]:
    ensure_wallpaper_dir()
    wallpapers = []
    for file in os.listdir(WALLPAPER_DIR):
        if file.endswith(".json"):
            with open(os.path.join(WALLPAPER_DIR, file), "r") as f:
                wallpapers.append(json.load(f))
    return wallpapers


def get_wallpaper(identifier: str) -> Optional[Dict]:
    wallpapers = list_wallpapers()
    for wallpaper in wallpapers:
        if wallpaper["id"].startswith(identifier) or wallpaper["name"] == identifier:
            return wallpaper
    return None


def get_random_wallpaper(type: Optional[str] = None) -> Optional[Dict]:
    wallpapers = list_wallpapers()
    if type:
        wallpapers = [w for w in wallpapers if w["type"] == type or w["type"] == "both"]
    return random.choice(wallpapers) if wallpapers else None


def fuzzy_match_wallpaper(query: str) -> Optional[Dict]:
    wallpapers = list_wallpapers()
    matches = fuzzy_process.extract(query, [w["name"] for w in wallpapers], limit=1)
    if matches and matches[0][1] > 70:  # 70% similarity threshold
        return next(w for w in wallpapers if w["name"] == matches[0][0])
    return None
