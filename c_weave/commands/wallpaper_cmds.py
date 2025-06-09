import json
import subprocess
import sys

import click
from rich import box
from rich.console import Console
from rich.table import Table

from c_weave.utils.cli import create_color_squares

console = Console()


@click.group()
def wallpaper():
    """manage wallpapers"""


@wallpaper.command("import")
@click.argument("path", type=click.Path(exists=True))
@click.option("--name", help="Optional name for the wallpaper")
@click.option(
    "--type",
    type=click.Choice(["dark", "light", "both"]),
    required=True,
    help="Wallpaper type",
)
@click.option("--analyze", "-a", is_flag=True, help="Extract/record colors on import")
def import_wallpaper_cmd(path, name, type, analyze):
    from c_weave.wallpaper import analyze_wallpaper, import_wallpaper

    try:
        wallpaper_id = import_wallpaper(path, name, type)
        click.echo(f"Imported wallpaper with ID: {wallpaper_id}")
        if analyze:
            colors = analyze_wallpaper(wallpaper_id)
            click.echo(f"Analyzed wallpaper. Extracted colors: {colors}")
    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)


@wallpaper.command("analyze")
@click.argument("wallpaper_id", required=False)
@click.option(
    "--missing", is_flag=True, help="Analyze all wallpapers without extracted colors"
)
def analyze_existing_wallpaper(wallpaper_id, missing):
    from c_weave.wallpaper import (
        analyze_wallpaper,
        get_wallpaper,
        get_wallpapers_missing_metadata,
    )

    def process_wallpaper(wallpaper_id: str):
        try:
            wallpaper = get_wallpaper(wallpaper_id)
            if not wallpaper:
                click.echo(
                    f"Error: Wallpaper not found for provided ID {wallpaper_id}",
                    err=True,
                )
                return

            colors = analyze_wallpaper(wallpaper_id)
            wallpaper = get_wallpaper(wallpaper_id)

            color_display = "  ".join(f"[{color}]■[/] {color[1:]}" for color in colors)
            table = Table(show_header=False, box=box.ROUNDED)
            table.add_column("Colors")
            table.add_column("Orientation")
            table.add_row(color_display, wallpaper.get("orientation", "N/A"))
            click.echo(f"Analyzed wallpaper {wallpaper_id}:")
            console.print(table)
        except ValueError as e:
            click.echo(f"Error analyzing wallpaper {wallpaper_id}: {str(e)}", err=True)

    if missing:
        wallpapers_to_analyze = get_wallpapers_missing_metadata()
        if not wallpapers_to_analyze:
            click.echo("No unanalyzed wallpapers found.")
            return
        for i, wallpaper in enumerate(wallpapers_to_analyze):
            process_wallpaper(wallpaper["id"])
            if i < len(wallpapers_to_analyze) - 1:
                click.echo()
    elif wallpaper_id:
        process_wallpaper(wallpaper_id)
    else:
        click.echo("Please provide a wallpaper id or use --missing flag")


@wallpaper.command("list")
@click.option(
    "--format",
    type=click.Choice(["stdout", "json"]),
    default="stdout",
    help="Output format",
)
def list_wallpapers_cmd(format):
    from c_weave.utils.color import get_varying_colors, sort_colors
    from c_weave.wallpaper import list_wallpapers

    wallpapers = list_wallpapers()

    if format == "json":
        # For JSON output, we want to include all data without visual formatting
        json_wallpapers = []
        for wallpaper in wallpapers:
            json_wallpaper = wallpaper.copy()
            # Convert filesize to MB for consistency
            json_wallpaper["filesize_mb"] = wallpaper["filesize"] / 1024 / 1024
            json_wallpapers.append(json_wallpaper)

        click.echo(json.dumps(json_wallpapers, indent=2))
        return

    columns = ["id", "name", "type", "colors", "resolution", "orientation", "filesize"]

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
                    if wallpaper["type"] == "light":
                        top_colors = sort_colors(top_colors, reverse=True)
                    else:
                        top_colors = sort_colors(top_colors)
                    value = create_color_squares(top_colors)
                else:
                    value = "N/A"
            else:
                value = wallpaper.get(key, "N/A")
            row.append(value)
        table.add_row(*row)

    console.print(table)


@wallpaper.command("show")
@click.argument("identifier", type=str)
@click.option(
    "--open", is_flag=True, help="Open the wallpaper in the system image viewer"
)
@click.option(
    "--format",
    type=click.Choice(["stdout", "json"]),
    default="stdout",
    help="Output format",
)
def show_wallpaper(identifier, open, format):
    from c_weave.wallpaper import (
        fuzzy_match_wallpaper,
        get_random_wallpaper,
        get_wallpaper,
        get_wallpaper_path,
    )

    if identifier in ["random", "dark", "light"]:
        wallpaper = get_random_wallpaper(identifier if identifier != "random" else None)
    else:
        wallpaper = get_wallpaper(identifier) or fuzzy_match_wallpaper(identifier)

    if wallpaper:
        if format == "json":
            # For JSON output, include all data with some formatting for consistency
            json_wallpaper = wallpaper.copy()
            # Convert filesize to MB for consistency
            if "filesize" in json_wallpaper:
                json_wallpaper["filesize_mb"] = json_wallpaper["filesize"] / 1024 / 1024
            # Add the full path for convenience
            from c_weave.wallpaper import get_wallpaper_path

            json_wallpaper["path"] = get_wallpaper_path(wallpaper)

            click.echo(json.dumps(json_wallpaper, indent=2))
        else:
            table = Table(box=box.ROUNDED, show_header=False)
            table.add_column("key", style="bold")
            table.add_column("value")

            for key, value in wallpaper.items():
                if key == "id":
                    value = value
                elif key == "filesize":
                    value = f"{value / 1024 / 1024:.2f} MB"
                elif key == "colors":
                    color_squares = [f"[{color}]■[/] {color[1:]}" for color in value]
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
