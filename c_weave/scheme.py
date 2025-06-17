import json
import os

from c_weave.models import Scheme, Variant

from .config import CACHE_DARK_PATH, CACHE_LIGHT_PATH, SCHEMES_DIR


def load_scheme(scheme_name):
    scheme_path = os.path.join(SCHEMES_DIR, f"{scheme_name}.json")
    if not os.path.isfile(scheme_path):
        raise FileNotFoundError(f"Scheme '{scheme_name}' not found.")

    with open(scheme_path, "r") as f:
        scheme_data = json.load(f)

    scheme = Scheme(scheme_data["name"])
    for variant_name, variant_data in scheme_data["variants"].items():
        scheme.add_variant(
            Variant(
                name=variant_name,
                colors=variant_data["colors"],
                type=variant_data.get("type", "dark"),
            )
        )
    return scheme


def analyze_scheme(scheme_name):
    scheme = load_scheme(scheme_name)
    color_profile = create_color_profile(scheme)

    profiles_dir = os.path.join(SCHEMES_DIR, "_profiles")
    os.makedirs(profiles_dir, exist_ok=True)

    with open(os.path.join(profiles_dir, f"{scheme_name}.json"), "w") as f:
        json.dump(color_profile, f, indent=2)


def get_schemes_without_profiles():
    """Return a list of scheme names that don't have color profiles."""
    all_schemes = [
        f.replace(".json", "") for f in os.listdir(SCHEMES_DIR) if f.endswith(".json")
    ]
    profiles_dir = os.path.join(SCHEMES_DIR, "_profiles")
    existing_profiles = [
        f.replace(".json", "") for f in os.listdir(profiles_dir) if f.endswith(".json")
    ]
    return [scheme for scheme in all_schemes if scheme not in existing_profiles]


def create_color_profile(scheme):
    profile = {
        "analysis_type": "base16",
        "metadata": {
            "mapping": {
                "background": "color0",
                "foreground": "color7",
                "accent1": "color1",
                "accent2": "color4",
            }
        },
        "variants": {},
    }

    for variant_name, variant in scheme.variants.items():
        profile["variants"][variant_name] = {
            "background": variant.get_color("color0"),
            "foreground": variant.get_color("color7"),
            "accent1": variant.get_color("color1"),
            "accent2": variant.get_color("color4"),
        }
    return profile


def cache_variant(variant, scheme_name):
    """Cache a specific variant to the appropriate cache file based on its type."""
    cache_path = CACHE_LIGHT_PATH if variant.type == "light" else CACHE_DARK_PATH

    cache_data = {
        "scheme_name": scheme_name,
        "variant_name": variant.name,
        "variant_type": variant.type,
        "colors": variant.colors,
        "timestamp": os.path.getmtime(os.path.join(SCHEMES_DIR, f"{scheme_name}.json")),
    }

    with open(cache_path, "w") as f:
        json.dump(cache_data, f, indent=2)


def get_cached_variant(variant_type="dark"):
    """Get the last cached variant of the specified type."""
    cache_path = CACHE_LIGHT_PATH if variant_type == "light" else CACHE_DARK_PATH

    if not os.path.exists(cache_path):
        return None

    try:
        with open(cache_path, "r") as f:
            cache_data = json.load(f)

        scheme_name = cache_data["scheme_name"]
        variant_name = cache_data["variant_name"]
        colors = cache_data["colors"]

        variant = Variant(variant_name, colors, variant_type)
        return {"variant": variant, "scheme_name": scheme_name}
    except (json.JSONDecodeError, KeyError):
        return None
