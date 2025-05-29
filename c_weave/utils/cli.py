from rich import box
from rich.console import Console
from rich.table import Table

from c_weave.utils.color import get_varying_colors

console = Console()


def create_color_squares(colors):
    return " ".join(f"[{color}]■[/]" for color in colors)


def create_variant_table(variant, show_title=True):
    title = f"{variant.name} ({variant.type})" if show_title else ""
    table = Table(title=title, box=box.ROUNDED, show_header=False)
    table.add_column("color", style="bold")
    table.add_column("hex")

    for color_name, color_value in variant.colors.items():
        color_square = create_color_squares([color_value])
        table.add_row(color_name, f"{color_square} {color_value[1:]}")

    return table


def create_wallpaper_table(wallpapers, show_title=True):
    table = Table(
        title=" wallpapers" if show_title else "",
        box=box.ROUNDED,
        title_justify="left",
    )
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
