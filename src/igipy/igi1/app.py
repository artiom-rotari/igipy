from io import BytesIO
from pathlib import Path
from typing import Annotated

import typer

from igipy.config import Config
from igipy.core.services.count_extensions import count_extensions
from igipy.core.services.qvm_to_qsc import qvm_to_qsc
from igipy.core.services.res_to_zip import res_to_zip
from igipy.core.services.tex_to_tga import tex_to_tga
from igipy.core.services.wav_to_wav import wav_to_wav
from igipy.core.utils import convert
from igipy.igi1.services.collect import collect

igi1_app = typer.Typer(add_completion=False)


@igi1_app.callback(invoke_without_command=True)
def igi1_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


@igi1_app.command(
    name="collect",
    short_help="Collect all game resources into the collect zip archive or directory",
)
def igi1_collect(
    game_dir: Annotated[Path | None, typer.Option(help="Game install directory (default from config)")] = None,
    output: Annotated[Path | None, typer.Option(help="Output zip/dir path (default from config)")] = None,
    dry: bool = False,
) -> None:
    config = Config.model_validate_file()
    collect(
        game_dir=game_dir or config.igi1.game_dir,
        output_path=output or config.igi1.collect_path,
        collect_is_zip=config.igi1.collect_is_zip,
        dry=dry,
    )


@igi1_app.command(
    name="res-to-zip",
    short_help="Convert a .res file to .zip (binary) or .json (strings)",
)
def igi1_res_to_zip(
    source: Annotated[Path, typer.Argument(help="Path to a .res file")],
    output: Annotated[Path | None, typer.Option(help="Output file path (default: same dir, new suffix)")] = None,
) -> None:
    source_stream = BytesIO(source.read_bytes())
    target_stream, target_path = res_to_zip(source_stream, source)
    output_path = output or target_path
    output_path.write_bytes(target_stream.getvalue())
    typer.secho(f"{source} -> {output_path}", fg="green")


@igi1_app.command(
    name="convert-qvm-to-qsc",
    short_help="Convert .qvm files from the collect source to .qsc files in the convert destination",
)
def igi1_convert_qvm_to_qsc(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert(
        collect_path=config.igi1.collect_path,
        collect_is_zip=config.igi1.collect_is_zip,
        convert_path=config.igi1.convert_path,
        convert_is_zip=config.igi1.convert_is_zip,
        converter=qvm_to_qsc,
        patterns=["*.qvm"],
        dry=dry,
    )


@igi1_app.command(
    name="convert-tex-to-tga",
    short_help="Convert .tex, .spr, .pic files from the collect source to .tga files in the convert destination",
)
def igi1_convert_tex_to_tga(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert(
        collect_path=config.igi1.collect_path,
        collect_is_zip=config.igi1.collect_is_zip,
        convert_path=config.igi1.convert_path,
        convert_is_zip=config.igi1.convert_is_zip,
        converter=tex_to_tga,
        patterns=["*.tex", "*.spr", "*.pic"],
        dry=dry,
    )


@igi1_app.command(
    name="convert-wav-to-wav",
    short_help="Convert .wav files from the collect source to regular .wav files in the convert destination",
)
def igi1_convert_wav_to_wav(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert(
        collect_path=config.igi1.collect_path,
        collect_is_zip=config.igi1.collect_is_zip,
        convert_path=config.igi1.convert_path,
        convert_is_zip=config.igi1.convert_is_zip,
        converter=wav_to_wav,
        patterns=["*.wav"],
        dry=dry,
    )


@igi1_app.command(
    name="extensions-of-game",
    short_help="Print file counts by extension from the game install directory",
)
def igi1_extensions_of_game() -> None:
    config = Config.model_validate_file()
    count_extensions(path=config.igi1.game_dir, is_zip=False)


@igi1_app.command(
    name="extensions-of-collect",
    short_help="Print file counts by extension from the collect source",
)
def igi1_extensions_of_collect() -> None:
    config = Config.model_validate_file()
    count_extensions(path=config.igi1.collect_path, is_zip=config.igi1.collect_is_zip)


@igi1_app.command(
    name="extensions-of-convert",
    short_help="Print file counts by extension from the convert destination",
)
def igi1_extensions_of_convert() -> None:
    config = Config.model_validate_file()
    count_extensions(path=config.igi1.convert_path, is_zip=config.igi1.convert_is_zip)
