import json
import platform
import subprocess
import tempfile
import time


class Scheme:
    def __init__(self, name, variants=None):
        self.name = name
        self.variants = {}
        if variants:
            for variant in variants:
                self.add_variant(variant)

    def add_variant(self, variant):
        self.variants[variant.name] = variant
        return variant

    def get_details(self):
        variants_detail = {
            variant: self.variants[variant].get_details() for variant in self.variants
        }
        return {"Theme Name": self.name, "Variants": variants_detail}


class Variant:
    def __init__(self, name, colors, type="dark"):
        super().__init__()
        self.name = name
        self.colors = dict(colors)
        self.type = type

    def get_color(self, color_name):
        return self.colors.get(color_name, None)

    def get_details(self):
        return {"Variant Name": self.name, "Colors": self.colors}

    def _execute_wallust(self, tmp_path, flags=""):
        command = f"wallust cs {tmp_path} --format pywal -d ~/.config/wallust {flags}"
        try:
            if platform.system() == "Darwin" and not flags:
                process = subprocess.Popen(command, shell=True)
                time.sleep(0.1)
                process.terminate()
            else:
                subprocess.run(command, check=True, shell=True)
        except subprocess.CalledProcessError as e:
            print(f"Error executing wallust: {e}")

    def apply(self):
        pywal_scheme = {
            "special": {
                "background": self.get_color("background")
                if self.get_color("background")
                else self.get_color("color0"),
                "foreground": self.get_color("foreground")
                if self.get_color("foreground")
                else self.get_color("color7"),
                "cursor": self.get_color("cursor")
                if self.get_color("cursor")
                else self.get_color("color7"),
            },
            "colors": {f"color{i}": self.get_color(f"color{i}") for i in range(16)},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump(pywal_scheme, tmp)
            tmp_path = tmp.name

        if platform.system() == "Darwin":
            self._execute_wallust(tmp_path, "-sq")
            self._execute_wallust(tmp_path, "-q")
        else:
            self._execute_wallust(tmp_path, "-q")
