import json
import subprocess
import tempfile


class Theme:
    def __init__(self, colorscheme, wallpaper, variant_name="base"):
        self.colorscheme = colorscheme
        self.wallpaper = wallpaper
        self.variant = self.colorscheme.get_variant(variant_name)


class Wallpaper:
    def __init__(self, file, resolution=None, aspect_ratio=None):
        self.file = file
        self.resolution = resolution
        self.aspect_ratio = aspect_ratio


class ColorScheme:
    def __init__(self, name):
        self.name = name
        self.variants = {}

    def add_variant(self, variant):
        self.variants[variant.name] = variant

    def get_variant(self, variant_name):
        return self.variants.get(variant_name, None)


class SchemeVariant:
    def __init__(self, name, colors):
        self.name = name
        self.colors = dict(colors)

    def get_color(self, color_name):
        return self.colors.get(color_name, None)


def apply_colorscheme(scheme_variant, backend="wallust"):
    # Map the SchemeVariant colors to the pywal format
    pywal_scheme = {
        "special": {
            "background": scheme_variant.get_color("background"),
            "foreground": scheme_variant.get_color("foreground"),
            "cursor": scheme_variant.get_color("color1"),
        },
        "colors": {
            f"color{i}": scheme_variant.get_color(f"color{i}") for i in range(16)
        },
    }

    # Convert the scheme to JSON
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        json.dump(pywal_scheme, tmp)
        tmp_path = tmp.name

    # Apply the colorscheme with wallust
    command = f"wallust cs {tmp_path} --format pywal" if backend == "wallust" else ""
    try:
        subprocess.run(command, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Error applying colorscheme with {backend}: {e}")
