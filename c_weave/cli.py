import importlib

import click

from c_weave.config import ensure_directories
from c_weave.utils.logging import configure_logging


class LazyGroup(click.Group):
    lazy_commands = {
        "scheme": ("c_weave.commands.scheme_cmds", "scheme"),
        "wallpaper": ("c_weave.commands.wallpaper_cmds", "wallpaper"),
        "generate": ("c_weave.commands.generate_cmds", "generate"),
    }

    def list_commands(self, ctx):
        return sorted(set(super().list_commands(ctx)) | self.lazy_commands.keys())

    def get_command(self, ctx, name):
        if name in self.lazy_commands:
            module_name, attr = self.lazy_commands[name]
            module = importlib.import_module(module_name)
            cmd = getattr(module, attr)
            self.add_command(cmd)
            return cmd
        return super().get_command(ctx, name)


@click.group(cls=LazyGroup)
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


if __name__ == "__main__":
    cli()
