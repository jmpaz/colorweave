import click


@click.group()
def generate():
    """generate content"""


@generate.command("palette")
@click.argument("image_path", type=click.Path(exists=True))
@click.option(
    "--model",
    type=click.Choice(["instant", "haiku", "sonnet"]),
    default="haiku",
    help="Claude model to use for palette generation",
)
def generate_palette_cmd(image_path, model):
    from c_weave.design import generate_palette
    from c_weave.utils.color import infer_palette

    colors = infer_palette(image_path, n=6)
    palette_output = generate_palette(colors, model)

    with open("palette.txt", "w") as f:
        f.write(palette_output)

    click.echo("Palette generated successfully.")


@generate.command("wallpaper")
@click.argument("image_path", type=click.Path(exists=True))
def generate_wallpaper_cmd(image_path):
    from c_weave.generate import generate_wallpaper
    from c_weave.utils.color import estimate_colors, infer_palette

    colors = infer_palette(image_path, n=6)
    named_colors = estimate_colors(colors)
    colors_str = ", ".join(str(color) for color in named_colors if color is not None)
    wallpaper = generate_wallpaper(colors_str)

    with open("wallpaper.png", "wb") as f:
        f.write(wallpaper)

    click.echo("Wallpaper generated successfully.")
