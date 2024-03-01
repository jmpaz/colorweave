import json
import subprocess
import tempfile


class Scheme:
    def __init__(self, name):
        self.name = name
        self.variants = {}

    def add_variant(self, variant):
        self.variants[variant.name] = variant
        return variant

    def get_details(self):
        variants_detail = {
            variant: self.variants[variant].get_details() for variant in self.variants
        }
        return {"Theme Name": self.name, "Variants": variants_detail}


class Variant:
    def __init__(self, name, colors):
        super().__init__()
        self.name = name
        self.colors = dict(colors)

    def get_color(self, color_name):
        return self.colors.get(color_name, None)

    def get_details(self):
        return {"Variant Name": self.name, "Colors": self.colors}

    def apply(self):
        pywal_scheme = {
            "special": {
                "background": self.get_color("background"),
                "foreground": self.get_color("foreground"),
                "cursor": self.get_color("color1"),
            },
            "colors": {f"color{i}": self.get_color(f"color{i}") for i in range(16)},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump(pywal_scheme, tmp)
            tmp_path = tmp.name

        command = f"wallust cs {tmp_path} --format pywal"
        try:
            subprocess.run(command, check=True, shell=True)
        except subprocess.CalledProcessError as e:
            print(f"Error applying colorscheme: {e}")
