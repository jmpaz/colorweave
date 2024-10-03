import json
import os
import subprocess

import click
from rich.console import Console
from rich.table import Table

from c_weave.design import generate_palette
from c_weave.generate import generate_wallpaper
from c_weave.theme import Scheme, Variant
from c_weave.utils.color import estimate_colors, infer_palette
from c_weave.wallpaper import (
    fuzzy_match_wallpaper,
    get_random_wallpaper,
    get_wallpaper,
    get_wallpaper_path,
    import_wallpaper,
    list_wallpapers,
)

console = Console()

COLORWEAVE_DIR = os.path.expanduser("~/.local/share/colorweave")
SCHEMES_DIR = os.path.join(COLORWEAVE_DIR, "schemes")
WALLPAPER_DIR = os.path.join(COLORWEAVE_DIR, "wallpapers")


def ensure_directories():
    """Ensure necessary directories exist."""
    directories = [COLORWEAVE_DIR, SCHEMES_DIR, WALLPAPER_DIR]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


@click.group()
def cli():
    """CLI for managing color schemes and generating palettes."""
    ensure_directories()


@cli.group()
def scheme():
    """Manage color schemes."""
    pass


@scheme.command("list")
def list_schemes():
    """List available schemes."""
    schemes = [
        f.replace(".json", "") for f in os.listdir(SCHEMES_DIR) if f.endswith(".json")
    ]

    table = Table(title="Color Schemes")
    table.add_column("Scheme Name", style="cyan")

    for scheme in schemes:
        table.add_row(scheme)

    console.print(table)


@scheme.command("show")
@click.argument("scheme_name")
@click.option("--variant", help="Specify a variant by name")
@click.option(
    "--type",
    "variant_type",
    type=click.Choice(["dark", "light"]),
    help="Specify variant type",
)
def show_scheme(scheme_name, variant, variant_type):
    """Display scheme details."""
    scheme = load_scheme(scheme_name)

    if variant:
        if variant not in scheme.variants:
            raise click.UsageError(
                f"Variant '{variant}' not found in scheme '{scheme.name}'"
            )
        variants_to_show = [scheme.variants[variant]]
    elif variant_type:
        variants_to_show = [
            v for v in scheme.variants.values() if v.type == variant_type
        ]
    else:
        variants_to_show = scheme.variants.values()

    for variant in variants_to_show:
        table = Table(title=f"{scheme.name} - {variant.name} ({variant.type})")
        table.add_column("Color Name", style="cyan")
        table.add_column("Hex Value", style="magenta")

        for color_name, color_value in variant.colors.items():
            table.add_row(color_name, color_value)

        console.print(table)
        console.print("\n")


@scheme.command("import")
@click.argument("file_path", type=click.Path(exists=True))
def import_scheme(file_path):
    """Import a new scheme from a JSON file."""
    with open(file_path, "r") as f:
        scheme_data = json.load(f)

    scheme_name = scheme_data["name"]
    output_path = os.path.join(SCHEMES_DIR, f"{scheme_name}.json")

    with open(output_path, "w") as f:
        json.dump(scheme_data, f, indent=2)

    click.echo(f"Imported scheme '{scheme_name}' successfully.")


@cli.command()
@click.argument("scheme_name")
@click.option("--variant", help="Specify a variant by name")
@click.option(
    "--type",
    "variant_type",
    type=click.Choice(["dark", "light"]),
    help="Specify variant type",
)
def apply(scheme_name, variant, variant_type):
    """Apply a color scheme variant."""
    scheme = load_scheme(scheme_name)

    if variant:
        if variant not in scheme.variants:
            raise click.UsageError(
                f"Variant '{variant}' not found in scheme '{scheme.name}'"
            )
        variant_to_apply = scheme.variants[variant]
    elif variant_type:
        variants = [v for v in scheme.variants.values() if v.type == variant_type]
        if not variants:
            raise click.UsageError(
                f"No {variant_type} variant found in scheme '{scheme.name}'"
            )
        variant_to_apply = variants[0]
    else:
        variant_to_apply = next(iter(scheme.variants.values()))

    variant_to_apply.apply()
    click.echo(
        f"Applied {scheme.name} - {variant_to_apply.name} ({variant_to_apply.type})"
    )


@cli.group()
def generate():
    """Generate content."""
    pass


@generate.command("palette")
@click.argument("image_path", type=click.Path(exists=True))
@click.option(
    "--model",
    type=click.Choice(["instant", "haiku", "sonnet"]),
    default="haiku",
    help="Claude model to use for palette generation",
)
def generate_palette_cmd(image_path, model):
    """Generate a color palette from an image."""
    colors = infer_palette(image_path, n=6)
    named_colors = estimate_colors(colors)
    palette_output = generate_palette(colors, named_colors, model)

    with open("palette.txt", "w") as f:
        f.write(palette_output)

    click.echo("Palette generated successfully.")


@generate.command("wallpaper")
@click.argument("image_path", type=click.Path(exists=True))
def generate_wallpaper_cmd(image_path):
    """Generate a wallpaper based on an image."""
    colors = infer_palette(image_path, n=6)
    named_colors = estimate_colors(colors)
    colors_str = ", ".join(named_colors)
    wallpaper = generate_wallpaper(colors_str)

    with open("wallpaper.png", "wb") as f:
        f.write(wallpaper)

    click.echo("Wallpaper generated successfully.")


@cli.group()
def wallpaper():
    """Manage wallpapers."""
    pass


@wallpaper.command("import")
@click.argument("path", type=click.Path(exists=True))
@click.option("--name", help="Optional name for the wallpaper")
@click.option(
    "--type",
    type=click.Choice(["dark", "light", "both"]),
    required=True,
    help="Wallpaper type",
)
def import_wallpaper_cmd(path, name, type):
    """Import a new wallpaper."""
    wallpaper_id = import_wallpaper(path, name, type)
    click.echo(f"Imported wallpaper with ID: {wallpaper_id}")


@wallpaper.command("apply")
@click.argument("identifier", type=str)
def apply_wallpaper(identifier):
    """Apply a wallpaper by name or ID."""
    if identifier in ["random", "dark", "light"]:
        wallpaper = get_random_wallpaper(identifier if identifier != "random" else None)
    else:
        wallpaper = get_wallpaper(identifier) or fuzzy_match_wallpaper(identifier)

    if wallpaper:
        path = get_wallpaper_path(wallpaper)
        # TODO: Implement apply_wallpaper
        click.echo(f"Would apply wallpaper: {path}")
        click.echo(
            f"Wallpaper details: {wallpaper['name']} (ID: {wallpaper['id'][:6]})"
        )
    else:
        click.echo("Wallpaper not found.")


@wallpaper.command("list")
def list_wallpapers_cmd():
    """List all stored wallpapers."""
    wallpapers = list_wallpapers()

    # Get unique keys
    all_keys = set()
    for wallpaper in wallpapers:
        all_keys.update(wallpaper.keys())
    sorted_keys = sorted(all_keys)

    table = Table(title="Wallpapers")
    for key in sorted_keys:
        table.add_column(key, no_wrap=True)

    for wallpaper in wallpapers:
        row = []
        for key in sorted_keys:
            value = wallpaper.get(key, "")
            if key == "id":
                value = value[:6]
            elif key == "filesize":
                value = f"{value / 1024 / 1024:.2f} MB"
            row.append(str(value))
        table.add_row(*row)

    console.print(table)


@wallpaper.command("show")
@click.argument("identifier", type=str)
@click.option(
    "--open", is_flag=True, help="Open the wallpaper in the system image viewer"
)
def show_wallpaper(identifier, open):
    """Show wallpaper details."""
    if identifier in ["random", "dark", "light"]:
        wallpaper = get_random_wallpaper(identifier if identifier != "random" else None)
    else:
        wallpaper = get_wallpaper(identifier) or fuzzy_match_wallpaper(identifier)

    if wallpaper:
        table = Table(title=f"Wallpaper ({wallpaper['id'][:4]})")
        table.add_column("key")
        table.add_column("value")
        for key, value in wallpaper.items():
            if key == "id":
                value = value
            elif key == "filesize":
                value = f"{value / 1024 / 1024:.2f} MB"
            table.add_row(key, str(value))

        console.print(table)

        if open:
            path = get_wallpaper_path(wallpaper)
            click.echo(f"Opening wallpaper: {path}")
            subprocess.run(["xdg-open", path], check=True)
    else:
        click.echo("Wallpaper not found.")


def load_scheme(scheme_name):
    scheme_path = os.path.join(SCHEMES_DIR, f"{scheme_name}.json")
    if not os.path.isfile(scheme_path):
        raise click.FileError(f"Scheme file not found: {scheme_name}")

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


if __name__ == "__main__":
    cli()
