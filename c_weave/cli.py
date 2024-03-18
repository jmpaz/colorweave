import click
from c_weave.generate import generate_wallpaper
from c_weave.utils.color import infer_palette, estimate_colors, parse_output
from c_weave.design import generate_palette
from c_weave.theme import Scheme, Variant


@click.group()
def cli():
    pass


@cli.command()
@click.argument("image_path", type=click.Path(exists=True))
@click.option(
    "--model",
    type=click.Choice(["instant", "haiku", "sonnet"]),
    default="haiku",
    help="Claude model to use for palette generation",
)
def generate(image_path, model):
    colors = infer_palette(image_path, n=6)
    named_colors = estimate_colors(colors)
    palette_output = generate_palette(colors, named_colors, model)
    parsed_colors = parse_output(palette_output)

    colors_str = ", ".join(named_colors)
    wallpaper = generate_wallpaper(colors_str)

    # Save wallpaper and palette to disk
    with open("palette.txt", "w") as f:
        f.write(palette_output)

    with open("wallpaper.png", "wb") as f:
        f.write(wallpaper)
