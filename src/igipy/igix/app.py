import functools
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

import typer

from igipy.config import Config
from igipy.core.services.tex_to_tga import tex_to_tga
from igipy.core.utils import convert
from igipy.igix.services.mef_to_fbx import mef_to_fbx

igix_app = typer.Typer(add_completion=False)


def _run_convert(
    converter: Callable[[BytesIO, Path | None], tuple[BytesIO, Path | None]],
    patterns: list[str],
    dry: bool,
) -> None:
    config = Config.model_validate_file()
    convert(
        collect_path=config.igix.collect_path,
        collect_is_zip=config.igix.collect_is_zip,
        convert_path=config.igix.convert_path,
        convert_is_zip=config.igix.convert_is_zip,
        converter=converter,
        patterns=patterns,
        dry=dry,
    )


# noinspection DuplicatedCode
@igix_app.callback(invoke_without_command=True)
def igix_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


@igix_app.command(
    name="convert-mef-to-fbx",
    short_help="Convert .mef files from collect source to textured .fbx 3D model in convert destination",
)
def igix_convert_mef_to_fbx(dry: bool = False) -> None:
    """Export igix .mef models to .fbx with per-render-group diffuse textures.

    Textures are resolved through the level material table (".dat"); run
    "convert-tex-to-tga" so the referenced ".tga" files exist in the convert destination.
    """
    config = Config.model_validate_file()
    # Bind the collect-source root so mef_to_fbx can read the level .dat and resolve textures.
    converter = functools.partial(mef_to_fbx, collect_path=config.igix.collect_path)
    _run_convert(converter=converter, patterns=["*.mef"], dry=dry)


@igix_app.command(
    name="convert-tex-to-tga",
    short_help="Convert .tex files from collect source to .tga images in convert destination",
)
def igix_convert_tex_to_tga(dry: bool = False) -> None:
    _run_convert(converter=tex_to_tga, patterns=["*.tex", "*.spr", "*.pic"], dry=dry)
