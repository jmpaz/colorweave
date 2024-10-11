import json
import os
import shutil
import subprocess
import sys
from typing import Optional, Tuple

import click
from rich import box
from rich.color import Color
from rich.columns import Columns
from rich.console import Console, Group
from rich.table import Table
from rich.text import Text

from c_weave.config import COLORWEAVE_DIR, SCHEMES_DIR, WALLPAPER_DIR
from c_weave.design import generate_palette
from c_weave.generate import generate_wallpaper
from c_weave.scheme import analyze_scheme, load_scheme
from c_weave.utils.color import (
    estimate_colors,
    get_varying_colors,
    infer_palette,
    sort_colors,
)
from c_weave.wallpaper import (
    analyze_wallpaper,
    fuzzy_match_wallpaper,
    get_compatible_wallpapers,
    get_random_wallpaper,
    get_wallpaper,
    get_wallpaper_path,
    import_wallpaper,
    list_wallpapers,
)

console = Console()


def ensure_directories():
    """Ensure necessary directories exist."""
    directories = [COLORWEAVE_DIR, SCHEMES_DIR, WALLPAPER_DIR]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def create_color_squares(colors):
    """Create a string of colored squares for the given colors."""
    return " ".join(f"[{color}]■[/]" for color in colors)


@click.group()
def cli():
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

    tables = []
    max_table_width = 0
    for scheme_name in schemes:
        scheme = load_scheme(scheme_name)
        table = Table(title=scheme_name, box=box.ROUNDED, show_header=False)
        table.add_column("variant", style="cyan")
        table.add_column("accents")

        sorted_variants = sort_variants_by_brightness(scheme.variants)

        for variant_name, variant in sorted_variants:
            bg_color = variant.get_color("background") or variant.get_color("color0")
            fg_color = variant.get_color("foreground") or variant.get_color("color7")

            variant_text = Text()
            variant_text.append(variant_name, style=f"on {bg_color} {fg_color}")
            variant_text.append(" ")

            color_squares = create_color_squares(
                [variant.get_color(f"color{i}") for i in range(1, 7)]
            )

            table.add_row(variant_text, color_squares)

        tables.append(table)
        max_table_width = max(max_table_width, len(scheme_name))

    console.print()

    terminal_width = shutil.get_terminal_size().columns
    min_padding, desired_padding = 2, 10
    column_width = max_table_width + 20

    # determine number of columns
    num_columns = 1
    for cols in [3, 2]:
        if (column_width + min_padding * 2) * cols <= terminal_width:
            num_columns = cols
            break

    # calculate padding
    total_table_width = column_width * num_columns
    remaining_width = terminal_width - total_table_width
    padding = min(
        desired_padding, max(min_padding, remaining_width // (num_columns + 1))
    )

    # create the colorscheme table grid
    grid = Table.grid(padding=(0, padding))

    for i in range(0, len(tables), num_columns):
        row = tables[i : i + num_columns]
        grid.add_row(*row)
        if i + num_columns < len(tables):
            grid.add_row()

    console.print(grid)


def get_brightness(color):
    r, g, b = Color.parse(color).get_truecolor()
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def get_contrasting_color(bg_color, colors):
    bg_brightness = get_brightness(bg_color)
    max_contrast = 0
    best_color = "color7"  # default to light gray if no good contrast found

    for name, color in colors.items():
        if name.startswith("color"):
            fg_brightness = get_brightness(color)
            contrast = abs(bg_brightness - fg_brightness)
            if contrast > max_contrast:
                max_contrast = contrast
                best_color = color

    return best_color


def sort_variants_by_brightness(variants):
    def get_variant_brightness(variant):
        bg_color = variant.get_color("background") or variant.get_color("color0")
        return get_brightness(bg_color)

    return sorted(variants.items(), key=lambda x: get_variant_brightness(x[1]))


def parse_scheme_identifier(scheme_identifier: str) -> Tuple[str, Optional[str]]:
    """Parse scheme identifier into scheme name/variant identifier."""
    parts = scheme_identifier.split(":")
    scheme_name = parts[0]
    variant_identifier = parts[1] if len(parts) > 1 else None
    return scheme_name, variant_identifier


@scheme.command("show")
@click.argument("scheme_identifier")
@click.option(
    "--wallpapers",
    is_flag=True,
    help="Show compatible wallpapers, ranked by color similarity",
)
def show_scheme(scheme_identifier, wallpapers):
    """Preview all or a subset of a scheme's variants. Identifier syntax: <scheme_name>:<variant_type|variant_name> (eg 'catppuccin:latte', 'rose-pine:dark')"""
    scheme_name, variant_identifier = parse_scheme_identifier(scheme_identifier)
    scheme = load_scheme(scheme_name)

    if variant_identifier:
        if variant_identifier in scheme.variants:
            variants_to_show = [scheme.variants[variant_identifier]]
        elif variant_identifier in ["dark", "light"]:
            variants_to_show = [
                v for v in scheme.variants.values() if v.type == variant_identifier
            ]
        else:
            raise click.UsageError(
                f"Variant '{variant_identifier}' not found in scheme '{scheme.name}'"
            )
    else:
        variants_to_show = scheme.variants.values()

    terminal_width = shutil.get_terminal_size().columns
    stack_tables = terminal_width < 80 and wallpapers
    console.print()

    if not wallpapers:
        # side-by-side
        variant_tables = [create_variant_table(variant) for variant in variants_to_show]
        columns = Columns(variant_tables, equal=True, expand=True)
        console.print(columns)
    else:
        for i, variant in enumerate(variants_to_show):
            if i > 0:
                console.print()

            variant_table = create_variant_table(variant)
            compatible_wallpapers = get_compatible_wallpapers(scheme, variant)
            wallpaper_table = create_wallpaper_table(compatible_wallpapers)

            if stack_tables:
                console.print(Group(variant_table, wallpaper_table))
            else:
                combined_table = Table.grid(padding=1)
                combined_table.add_row(variant_table, wallpaper_table)
                console.print(combined_table)


def create_variant_table(variant):
    table = Table(
        title=f"{variant.name} ({variant.type})", box=box.ROUNDED, show_header=False
    )
    table.add_column("color", style="bold")
    table.add_column("hex")

    for color_name, color_value in variant.colors.items():
        color_square = create_color_squares([color_value])
        hex_value = color_value[1:]
        table.add_row(color_name, f"{color_square} {hex_value}")

    return table


def create_wallpaper_table(wallpapers):
    table = Table(title=" wallpapers", box=box.ROUNDED, title_justify="left")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Type", style="cyan")
    table.add_column("Colors", justify="center")

    for wallpaper in wallpapers[:8]:
        color_squares = create_color_squares(
            get_varying_colors(wallpaper["colors"], n=4)
        )
        table.add_row(
            wallpaper["id"][:6],
            wallpaper["name"][:20],
            wallpaper["type"],
            color_squares,
        )

    return table


@scheme.command("import")
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--analyze",
    "-a",
    is_flag=True,
    help="Analyze the scheme and create a color profile",
)
def import_scheme(file_path, analyze):
    """Import a new scheme from a JSON file."""
    with open(file_path, "r") as f:
        scheme_data = json.load(f)

    scheme_name = scheme_data["name"]
    output_path = os.path.join(SCHEMES_DIR, f"{scheme_name}.json")

    with open(output_path, "w") as f:
        json.dump(scheme_data, f, indent=2)

    if analyze:
        analyze_scheme(scheme_name)
        click.echo(f"Created color profile for scheme '{scheme_name}'")

    click.echo(f"Imported scheme '{scheme_name}' successfully.")


@scheme.command("analyze")
@click.argument("scheme_name")
def analyze_existing_scheme(scheme_name):
    """Analyze an existing scheme's variants to create a color profile."""
    analyze_scheme(scheme_name)
    click.echo(f"Created color profile for scheme '{scheme_name}'")


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
    palette_output = generate_palette(colors, model)

    with open("palette.txt", "w") as f:
        f.write(palette_output)

    click.echo("Palette generated successfully.")


@generate.command("wallpaper")
@click.argument("image_path", type=click.Path(exists=True))
def generate_wallpaper_cmd(image_path):
    """Generate a wallpaper based on an image."""
    colors = infer_palette(image_path, n=6)
    named_colors = estimate_colors(colors)
    colors_str = ", ".join(str(color) for color in named_colors if color is not None)
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
@click.option(
    "--analyze",
    "-a",
    is_flag=True,
    help="Extract/record colors on import",
)
def import_wallpaper_cmd(path, name, type, analyze):
    """Import a new wallpaper."""
    try:
        wallpaper_id = import_wallpaper(path, name, type)
        click.echo(f"Imported wallpaper with ID: {wallpaper_id}")
        if analyze:
            colors = analyze_wallpaper(wallpaper_id)
            click.echo(f"Analyzed wallpaper. Extracted colors: {colors}")
    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)


@wallpaper.command("analyze")
@click.argument("wallpaper_id")
def analyze_existing_wallpaper(wallpaper_id):
    """Extract colors from an existing wallpaper and store in metadata."""
    try:
        colors = analyze_wallpaper(wallpaper_id)
        click.echo(f"Extracted colors for wallpaper {wallpaper_id}: {colors}")
    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)


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

    columns = ["id", "name", "type", "colors", "resolution", "filesize"]

    table = Table(show_header=True, box=box.ROUNDED)
    for col in columns:
        justify = "center" if col == "colors" else "left"
        table.add_column(col, no_wrap=True, justify=justify)

    for wallpaper in wallpapers:
        row = []
        for key in columns:
            if key == "id":
                value = wallpaper["id"][:6]
            elif key == "name":
                value = wallpaper["name"][:20]
            elif key == "filesize":
                value = f"{wallpaper['filesize'] / 1024 / 1024:.2f} MB"
            elif key == "colors":
                if "colors" in wallpaper:
                    top_colors = get_varying_colors(wallpaper["colors"], n=4)
                    # sort colors based on wallpaper type
                    if wallpaper["type"] == "light":
                        top_colors = sort_colors(top_colors, reverse=True)
                    else:  # "dark" or "both"
                        top_colors = sort_colors(top_colors)
                    value = create_color_squares(top_colors)
                else:
                    value = "N/A"
            else:
                value = wallpaper.get(key, "")
            row.append(value)
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
        table = Table(box=box.ROUNDED, show_header=False)
        table.add_column("key", style="bold")
        table.add_column("value")

        for key, value in wallpaper.items():
            if key == "id":
                value = value
            elif key == "filesize":
                value = f"{value / 1024 / 1024:.2f} MB"
            elif key == "colors":
                color_squares = []
                for color in value:
                    color_squares.append(f"[{color}]■[/] {color[1:]}")
                value = "  ".join(color_squares)

            table.add_row(key, str(value))

        console.print(table)

        if open:
            path = get_wallpaper_path(wallpaper)
            click.echo(f"Opening wallpaper: {path}")
            if sys.platform == "darwin":
                subprocess.run(["open", path], check=True)
            else:
                subprocess.run(["xdg-open", path], check=True)
    else:
        click.echo("Wallpaper not found.")


@scheme.command("apply")
@click.argument("scheme_identifier")
def set_scheme(scheme_identifier):
    """Apply a color scheme variant. Identifier syntax: <scheme_name>:<variant_type|variant_name> (eg 'catppuccin:mocha', 'rose-pine:light')"""
    scheme_name, variant_identifier = parse_scheme_identifier(scheme_identifier)
    scheme = load_scheme(scheme_name)

    if variant_identifier:
        if variant_identifier in scheme.variants:
            variant_to_apply = scheme.variants[variant_identifier]
        elif variant_identifier in ["dark", "light"]:
            variants = [
                v for v in scheme.variants.values() if v.type == variant_identifier
            ]
            if not variants:
                raise click.UsageError(
                    f"No {variant_identifier} variant found in scheme '{scheme.name}'"
                )
            variant_to_apply = variants[0]
        else:
            raise click.UsageError(
                f"Variant '{variant_identifier}' not found in scheme '{scheme.name}'"
            )
    else:
        variant_to_apply = next(iter(scheme.variants.values()))

    variant_to_apply.apply()
    click.echo(
        f"Applied {scheme.name} - {variant_to_apply.name} ({variant_to_apply.type})"
    )


if __name__ == "__main__":
    cli()
