import hashlib
import json
import logging
import os
import random
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from fuzzywuzzy import process as fuzzy_process
from PIL import Image

from c_weave.scheme import Scheme, Variant
from c_weave.utils.color import (
    calculate_color_similarity,
    get_varying_colors,
    infer_palette,
)

# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


WALLPAPER_DIR = os.path.expanduser("~/.local/share/colorweave/wallpapers")


def ensure_wallpaper_dir():
    os.makedirs(WALLPAPER_DIR, exist_ok=True)


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def import_wallpaper(path: str, name: Optional[str], type: str) -> str:
    ensure_wallpaper_dir()

    # check for duplicates
    hash = calculate_file_hash(path)
    existing_wallpapers = list_wallpapers()
    for wallpaper in existing_wallpapers:
        if wallpaper.get("hash") == hash:
            raise ValueError(
                f"This wallpaper already exists with ID: {wallpaper['id']}"
            )

    wallpaper_id = str(uuid.uuid4())
    ext = Path(path).suffix
    new_filename = f"{wallpaper_id}{ext}"
    new_path = os.path.join(WALLPAPER_DIR, new_filename)

    # copy wallpaper
    shutil.copy2(path, new_path)

    # get metadata
    with Image.open(new_path) as img:
        width, height = img.size
        resolution = f"{width}x{height}"
        if width == height:
            orientation = "both"
        elif width > height:
            orientation = "landscape"
        else:
            orientation = "portrait"
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
        "resolution": resolution,
        "orientation": orientation,
        "filesize": filesize,
        "extension": ext,
        "hash": hash,
    }

    with open(os.path.join(WALLPAPER_DIR, f"{wallpaper_id}.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    return wallpaper_id


def get_wallpaper_path(wallpaper: Dict) -> str:
    return os.path.join(
        WALLPAPER_DIR, f"{wallpaper['id']}.{wallpaper['extension'].lstrip('.')}"
    )


def analyze_wallpaper(wallpaper_id: str) -> List[str]:
    """Analyze a wallpaper and extract colors and orientation."""
    wallpaper = get_wallpaper(wallpaper_id)
    if not wallpaper:
        raise ValueError(f"Wallpaper with ID {wallpaper_id} not found.")

    full_id = wallpaper["id"]
    wallpaper_path = get_wallpaper_path(wallpaper)

    # extract colors if not present
    if "colors" not in wallpaper:
        colors = infer_palette(wallpaper_path, n=6)
        wallpaper["colors"] = colors
    else:
        colors = wallpaper["colors"]

    # calculate orientation if not present
    if "orientation" not in wallpaper or wallpaper["orientation"] == "N/A":
        width, height = map(int, wallpaper["resolution"].split("x"))
        if abs(width - height) <= min(width, height) * 0.05:
            orientation = "both"  # within 5% of square
        elif width > height:
            orientation = "landscape"
        else:
            orientation = "portrait"
        wallpaper["orientation"] = orientation

    # Update wallpaper metadata
    metadata_path = os.path.join(WALLPAPER_DIR, f"{full_id}.json")
    with open(metadata_path, "w") as f:
        json.dump(wallpaper, f, indent=2)

    return colors


def get_wallpapers_missing_metadata():
    """Return a list of wallpapers that don't have extracted colors or orientation."""
    wallpapers = list_wallpapers()
    return [
        w
        for w in wallpapers
        if "colors" not in w or "orientation" not in w or w.get("orientation") == "N/A"
    ]


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


def get_compatible_wallpapers(
    scheme: Scheme, variant: Variant, p: Optional[float] = None
) -> List[Dict]:
    wallpapers = list_wallpapers()
    logger.info(f"Total wallpapers: {len(wallpapers)}")

    filtered_wallpapers = filter_wallpapers_by_type(wallpapers, variant.type)
    logger.info(f"Wallpapers after type filtering: {len(filtered_wallpapers)}")

    scheme_colors = [variant.get_color("background")] + [
        variant.get_color(f"color{i}") for i in range(1, 7)
    ]
    logger.info(f"Scheme colors: {scheme_colors}")

    ranked_wallpapers = rank_wallpapers_by_color_similarity(
        filtered_wallpapers, scheme_colors, p
    )
    logger.info(f"Ranked wallpapers: {len(ranked_wallpapers)}")

    return ranked_wallpapers


def filter_wallpapers_by_type(wallpapers: List[Dict], target_type: str) -> List[Dict]:
    return [w for w in wallpapers if w["type"] == target_type or w["type"] == "both"]


def rank_wallpapers_by_color_similarity(
    wallpapers: List[Dict], scheme_colors: List[str], p: Optional[float] = None
) -> List[Dict]:
    ranked_wallpapers = []
    for wallpaper in wallpapers:
        logger.info(f"Processing wallpaper: {wallpaper['name']}")
        if "colors" not in wallpaper:
            logger.warning(f"Wallpaper {wallpaper['name']} has no colors, skipping")
            continue
        wallpaper_colors = get_varying_colors(wallpaper["colors"], n=4)
        logger.info(f"Wallpaper colors: {wallpaper_colors}")
        similarity_score = calculate_color_similarity(wallpaper_colors, scheme_colors)
        logger.info(f"Similarity score: {similarity_score}")
        ranked_wallpapers.append((wallpaper, similarity_score))

    ranked_wallpapers.sort(key=lambda x: x[1], reverse=True)

    if p is not None:
        top_n = max(1, int(len(ranked_wallpapers) * p))
        logger.info(f"Selecting top {top_n} wallpapers")
        return [w[0] for w in ranked_wallpapers[:top_n]]
    else:
        logger.info(f"Returning all {len(ranked_wallpapers)} ranked wallpapers")
        return [w[0] for w in ranked_wallpapers]
