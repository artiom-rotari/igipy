import subprocess

import typer

from igipy import formats
from igipy.cli import utils

igi2_app = typer.Typer(add_completion=False)


@igi2_app.callback(invoke_without_command=True)
def igi1_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


@igi2_app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    short_help="Run gconv.exe",
)
def gconv(ctx: typer.Context):
    executable = ctx.obj.igi2.gconv.absolute().as_posix()
    arguments = ctx.args or ["-help"]
    subprocess.run([executable] + arguments, check=True)


# noinspection DuplicatedCode
@igi2_app.command(short_help="Shows counts of files by extension in {game_dir} and {work_dir}/extracted}")
def extensions(ctx: typer.Context) -> None:
    utils.extensions(config=ctx.obj.igi2)


# noinspection DuplicatedCode
@igi2_app.command(short_help="Shows files with provided extension in {work_dir} and {work_dir}/extracted}")
def files(ctx: typer.Context, patterns: list[str]) -> None:
    utils.files(config=ctx.obj.igi2, patterns=patterns)


@igi2_app.command(short_help="Decode all .res files found in {game_dir}")
def decode_all_res(
    ctx: typer.Context,
    patterns: list[str] = typer.Option(default=["**/*.res"], help="List of items (space-separated)"),  # noqa: B008
) -> None:
    formats.RES.cli_decode_all(config=ctx.obj.igi2, patterns=patterns)
