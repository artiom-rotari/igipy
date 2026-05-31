import string
from pathlib import Path
from typing import Annotated

import typer

from igipy.core.services.copy_files import copy_files
from igipy.core.services.count_extensions import count_extensions
from igipy.core.services.printable import printable
from igipy.core.utils.gconv import gconv

core_app = typer.Typer(add_completion=False)


@core_app.callback(invoke_without_command=True)
def core_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


@core_app.command(
    name="count-extensions",
    short_help="Count files by extension in a directory or .zip archive",
)
def core_count_extensions(path: Path) -> None:
    count_extensions(path=path, is_zip=path.suffix == ".zip")


@core_app.command(
    name="copy-files",
    short_help="Copy files from source to destination, excluding .res/.mtp/.dat(with .mtp)",
)
def core_copy_files(
    source: Annotated[Path, typer.Argument(help="Source directory")],
    destination: Annotated[Path, typer.Argument(help="Destination directory")],
    dry: bool = False,
) -> None:
    copy_files(source=source, destination=destination, dry=dry)


@core_app.command(
    name="printable",
    short_help="Search printable series in binary files",
)
def core_printable(source: Path, min_length: int = 5, charset: str = string.printable) -> None:
    printable(source=source, min_length=min_length, charset=charset)


@core_app.command(
    name="gconv",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    short_help="Run gconv.exe",
)
def core_gconv(ctx: typer.Context) -> None:
    gconv(ctx)
