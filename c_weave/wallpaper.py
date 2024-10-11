import hashlib
import imghdr
import json
import logging
import os
import platform
import random
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Union

from fuzzywuzzy import process as fuzzy_process
from PIL import Image

from c_weave.config import WALLPAPER_DIR
from c_weave.scheme import Scheme, Variant
from c_weave.utils.color import (
    calculate_color_similarity,
    get_varying_colors,
    infer_palette,
)

# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    for wallpaper in ranked_wallpapers:
        width, height = map(int, wallpaper["resolution"].split("x"))
        wallpaper["width"] = width
        wallpaper["height"] = height

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


def get_displays() -> List[Dict[str, Union[str, int]]]:
    """Return a list of dictionaries containing information about connected displays."""
    system = platform.system()
    displays = []

    if system == "Darwin":  # macOS
        output = subprocess.check_output(
            ["system_profiler", "SPDisplaysDataType", "-json"]
        ).decode()
        data = json.loads(output)
        for display in data["SPDisplaysDataType"][0]["spdisplays_ndrvs"]:
            displays.append(
                {
                    "identifier": display.get(
                        "spdisplays_device-id", str(len(displays))
                    ),
                    "resolution": f"{display['_spdisplays_pixels']}x{display['_spdisplays_resolution']}",
                }
            )
    elif system == "Linux":
        if os.environ.get("WAYLAND_DISPLAY"):  # Wayland
            output = subprocess.check_output(["wlr-randr", "--json"]).decode()
            data = json.loads(output)
            for name, display in data.items():
                if display["active"]:
                    displays.append(
                        {
                            "identifier": name,
                            "resolution": f"{display['width']}x{display['height']}",
                        }
                    )
        else:  # X11
            output = subprocess.check_output(["xrandr", "--current"]).decode()
            for line in output.split("\n"):
                if " connected" in line and "+" in line:  # Look for active displays
                    parts = line.split()
                    identifier = parts[0]
                    # Find the resolution, which is typically in the format WIDTHxHEIGHT+X+Y
                    resolution_part = next(p for p in parts if "x" in p and "+" in p)
                    resolution = resolution_part.split("+")[
                        0
                    ]  # This removes the position information
                    displays.append(
                        {"identifier": identifier, "resolution": resolution}
                    )

    return displays


def determine_wallpapers_to_set(
    wallpapers: List[Dict],
    displays: List[Dict],
    use_random: bool = False,
    filter_threshold: float = 0.2,
) -> List[Dict[str, str]]:
    """Determine which wallpapers to set for each display."""
    result = []

    for display in displays:
        try:
            display_width, display_height = map(int, display["resolution"].split("x"))

            candidates = []
            for wallpaper in wallpapers:
                wallpaper_path = get_wallpaper_path(wallpaper)
                if not is_image_file(wallpaper_path):
                    logger.warning(f"Skipping non-image file: {wallpaper_path}")
                    continue

                if (
                    wallpaper["width"] >= display_width
                    and wallpaper["height"] >= display_height
                ):
                    candidates.append(wallpaper)

            if use_random and candidates:
                candidates = sorted(
                    candidates, key=lambda w: w.get("similarity_score", 0), reverse=True
                )
                num_candidates = max(1, int(len(candidates) * filter_threshold))
                selected_wallpaper = random.choice(candidates[:num_candidates])
            elif candidates:
                selected_wallpaper = candidates[0]
            else:
                selected_wallpaper = None

            if selected_wallpaper:
                result.append(
                    {
                        "display": display["identifier"],
                        "wallpaper": get_wallpaper_path(selected_wallpaper),
                    }
                )
            else:
                logger.warning(
                    f"No suitable wallpaper found for display {display['identifier']} ({display_width}x{display_height})"
                )
        except Exception as e:
            logger.error(
                f"Error processing display {display.get('identifier', 'unknown')}: {str(e)}"
            )

    return result


def is_image_file(file_path):
    return imghdr.what(file_path) is not None


def set_wallpapers(wallpapers: List[Dict[str, str]]) -> str:
    """Set wallpapers for all connected displays."""
    try:
        system = platform.system()

        if system == "Darwin":  # macOS
            for item in wallpapers:
                subprocess.run(
                    [
                        "osascript",
                        "-e",
                        f'tell application "System Events" to set picture of desktop {item["display"]} to "{item["wallpaper"]}"',
                    ]
                )
        elif system == "Linux":
            if os.environ.get("WAYLAND_DISPLAY"):  # Wayland
                for item in wallpapers:
                    subprocess.Popen(
                        ["swaybg", "-o", item["display"], "-i", item["wallpaper"]]
                    )
            else:  # X11
                wallpaper_args = []
                for item in wallpapers:
                    wallpaper_args.extend(["--bg-fill", item["wallpaper"]])
                if wallpaper_args:
                    subprocess.run(["feh"] + wallpaper_args)
                else:
                    return "No valid wallpapers to set"
        else:
            return "Unsupported operating system"

        return f"Successfully set wallpapers for {len(wallpapers)} displays"
    except Exception as e:
        raise RuntimeError(f"Failed to set wallpapers: {str(e)}")
