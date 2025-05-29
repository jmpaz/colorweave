import click

from c_weave.commands.generate_cmds import generate
from c_weave.commands.scheme_cmds import scheme
from c_weave.commands.wallpaper_cmds import wallpaper
from c_weave.config import ensure_directories
from c_weave.utils.logging import configure_logging


@click.group()
@click.option(
    "--debug",
    "-D",
    "logging_level",
    type=click.IntRange(0, 2),
    default=0,
    help="Set logging level: 0=WARNING (default), 1=INFO, 2=DEBUG",
)
@click.pass_context
def cli(ctx, logging_level):
    ensure_directories()
    configure_logging(logging_level)
    if logging_level > 0:
        click.echo(f"Logging level: {['WARNING', 'INFO', 'DEBUG'][logging_level]}")
    ctx.ensure_object(dict)
    ctx.obj["DEBUG"] = logging_level


cli.add_command(scheme)
cli.add_command(wallpaper)
cli.add_command(generate)


if __name__ == "__main__":
    cli()

