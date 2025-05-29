import json
import os
import shutil
from typing import Optional, Tuple

import click
from rich import box
from rich.color import Color
from rich.columns import Columns
from rich.console import Console, Group
from rich.table import Table
from rich.text import Text

from c_weave.config import SCHEMES_DIR
from c_weave.scheme import (
    analyze_scheme,
    get_schemes_without_profiles,
    load_scheme,
)
from c_weave.utils.cli import (
    create_color_squares,
    create_variant_table,
    create_wallpaper_table,
)
from c_weave.wallpaper import (
    determine_wallpapers_to_set,
    get_compatible_wallpapers,
    get_displays,
    get_wallpaper,
    set_wallpapers,
)

console = Console()


def get_brightness(color):
    r, g, b = Color.parse(color).get_truecolor()
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def get_contrasting_color(bg_color, colors):
    bg_brightness = get_brightness(bg_color)
    max_contrast = 0
    best_color = "color7"

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
    parts = scheme_identifier.split(":")
    scheme_name = parts[0]
    variant_identifier = parts[1] if len(parts) > 1 else None
    return scheme_name, variant_identifier


@click.group()
def scheme():
    """manage color schemes"""


@scheme.command("list")
def list_schemes():
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

    num_columns = 1
    for cols in [3, 2]:
        if (column_width + min_padding * 2) * cols <= terminal_width:
            num_columns = cols
            break

    total_table_width = column_width * num_columns
    remaining_width = terminal_width - total_table_width
    padding = min(
        desired_padding, max(min_padding, remaining_width // (num_columns + 1))
    )

    grid = Table.grid(padding=(0, padding))

    for i in range(0, len(tables), num_columns):
        row = tables[i : i + num_columns]
        grid.add_row(*row)
        if i + num_columns < len(tables):
            grid.add_row()

    console.print(grid)


@scheme.command("show")
@click.argument("scheme_identifier")
@click.option(
    "--wallpapers",
    is_flag=True,
    help="Show compatible wallpapers, ranked by color similarity",
)
def show_scheme(scheme_identifier, wallpapers):
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


@scheme.command("import")
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--analyze",
    "-a",
    is_flag=True,
    help="Analyze the scheme and create a color profile",
)
def import_scheme(file_path, analyze):
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
@click.argument("scheme_name", required=False)
@click.option(
    "--missing", is_flag=True, help="Analyze all schemes without color profiles"
)
def analyze_existing_scheme(scheme_name, missing):
    if missing:
        schemes_to_analyze = get_schemes_without_profiles()
        if not schemes_to_analyze:
            click.echo("No schemes found without color profiles.")
            return
        for scheme in schemes_to_analyze:
            analyze_scheme(scheme)
            click.echo(f"Created color profile for scheme '{scheme}'")
    elif scheme_name:
        analyze_scheme(scheme_name)
        click.echo(f"Created color profile for scheme '{scheme_name}'")
    else:
        click.echo("Please provide a scheme name or use --missing flag")


@scheme.command("apply")
@click.argument("scheme_identifier")
@click.option(
    "--wallpapers",
    "-w",
    is_flag=True,
    help="Set matching wallpapers for connected displays",
)
@click.option("--random", "-r", is_flag=True, help="Randomly select wallpapers")
@click.option(
    "--filter-threshold",
    "-f",
    type=float,
    default=0.2,
    help="Filter threshold for random selection",
)
def set_scheme(scheme_identifier, wallpapers, random, filter_threshold):
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
    console.print()
    console.print(
        f"Applied {scheme.name} - {variant_to_apply.name} ({variant_to_apply.type})"
    )

    variant_table = create_variant_table(variant_to_apply, show_title=False)

    if wallpapers:
        try:
            displays = get_displays()
            compatible_wallpapers = get_compatible_wallpapers(
                scheme, variant_to_apply, 1.0
            )
            wallpapers_to_set = determine_wallpapers_to_set(
                compatible_wallpapers, displays, random, filter_threshold
            )
            if wallpapers_to_set:
                set_wallpapers(wallpapers_to_set)

                set_wallpaper_list = []
                for wallpaper_info in wallpapers_to_set:
                    wallpaper_id = os.path.basename(wallpaper_info["wallpaper"]).split(
                        "."
                    )[0]
                    wallpaper = get_wallpaper(wallpaper_id)
                    if wallpaper:
                        set_wallpaper_list.append(wallpaper)

                if set_wallpaper_list:
                    wallpaper_table = create_wallpaper_table(
                        set_wallpaper_list, show_title=False
                    )

                    grid = Table.grid(padding=1)
                    grid.add_row(variant_table, wallpaper_table)
                    console.print(grid)
                else:
                    click.echo("No wallpaper information available for display")
            else:
                click.echo("No suitable wallpapers found for any display")
        except Exception as e:
            click.echo(f"Error setting wallpapers: {str(e)}", err=True)
    else:
        console.print()
        console.print(variant_table)
