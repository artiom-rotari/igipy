import functools
from collections.abc import Callable
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
from igipy.igi2.services.collect import collect
from igipy.igi2.services.copy_raw import RAW_PATTERNS, copy_raw
from igipy.igi2.services.dat_forest_to_json import dat_forest_to_json
from igipy.igi2.services.dat_graph_to_json import dat_graph_to_json
from igipy.igi2.services.dat_graphcover_to_json import dat_graphcover_to_json
from igipy.igi2.services.fnt_to_zip import fnt_to_zip
from igipy.igi2.services.iff_to_fbx import iff_to_fbx
from igipy.igi2.services.iff_to_qsc import iff_to_qsc
from igipy.igi2.services.mef_to_fbx import mef_to_fbx
from igipy.igi2.services.mef_to_qsc import mef_to_qsc
from igipy.igi2.services.mtp_to_json import mtp_to_json
from igipy.igi2.services.objects_to_json import objects_to_json
from igipy.igi2.services.olm_to_tga import olm_to_tga
from igipy.igi2.services.syn_to_json import syn_to_json
from igipy.igi2.services.thm_to_tga import thm_to_tga
from igipy.igi2.services.tlm_to_tga import tlm_to_tga
from igipy.igi2.services.tmm_to_tga import tmm_to_tga

igi2_app = typer.Typer(add_completion=False)


def _run_convert(
    converter: Callable[[BytesIO, Path | None], tuple[BytesIO, Path | None]],
    patterns: list[str],
    dry: bool,
) -> None:
    config = Config.model_validate_file()
    convert(
        collect_path=config.igi2.collect_path,
        collect_is_zip=config.igi2.collect_is_zip,
        convert_path=config.igi2.convert_path,
        convert_is_zip=config.igi2.convert_is_zip,
        converter=converter,
        patterns=patterns,
        dry=dry,
    )


# noinspection DuplicatedCode
@igi2_app.callback(invoke_without_command=True)
def igi2_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


@igi2_app.command(
    name="collect",
    short_help="Collect all game resources into the collect zip archive or directory",
)
def igi2_collect(
    game_dir: Annotated[Path | None, typer.Option(help="Game install directory (default from config)")] = None,
    output: Annotated[Path | None, typer.Option(help="Output zip/dir path (default from config)")] = None,
    dry: bool = False,
) -> None:
    config = Config.model_validate_file()
    collect(
        game_dir=game_dir or config.igi2.game_dir,
        output_path=output or config.igi2.collect_path,
        collect_is_zip=config.igi2.collect_is_zip,
        dry=dry,
    )


@igi2_app.command(
    name="convert-all",
    short_help="Run all converters (collect source to convert destination)",
)
def igi2_convert_all(dry: bool = False) -> None:
    config = Config.model_validate_file()
    typer.secho(f"Collect: {config.igi2.collect_path}", fg="cyan")
    typer.secho(f"Convert: {config.igi2.convert_path}", fg="cyan")

    typer.secho("Copying raw files (.mp3, .bmp, .jpg, .tga, .json)...", fg="green")
    igi2_convert_raw(dry=dry)

    typer.secho("Converting .qvm to .qsc...", fg="green")
    igi2_convert_qvm_to_qsc(dry=dry)

    typer.secho("Converting .wav to standard .wav...", fg="green")
    igi2_convert_wav_to_wav(dry=dry)

    typer.secho("Converting .tex/.spr/.pic to .tga...", fg="green")
    igi2_convert_tex_to_tga(dry=dry)

    typer.secho("Converting .fnt to BMFont zip...", fg="green")
    igi2_convert_fnt_to_zip(dry=dry)

    typer.secho("Converting .thm to .tga heightmap...", fg="green")
    igi2_convert_thm_to_tga(dry=dry)

    typer.secho("Converting .tmm to .tga material map...", fg="green")
    igi2_convert_tmm_to_tga(dry=dry)

    typer.secho("Converting .syn to .json...", fg="green")
    igi2_convert_syn_to_json(dry=dry)

    typer.secho("Converting .tlm to .tga lightmap...", fg="green")
    igi2_convert_tlm_to_tga(dry=dry)

    typer.secho("Converting forest_*.dat to .json...", fg="green")
    igi2_convert_dat_forest_to_json(dry=dry)

    typer.secho("Converting graph*.dat to .json...", fg="green")
    igi2_convert_dat_graph_to_json(dry=dry)

    typer.secho("Converting graphcover*.dat to .json...", fg="green")
    igi2_convert_dat_graphcover_to_json(dry=dry)

    typer.secho("Converting .mtp to .json material/texture table...", fg="green")
    igi2_convert_mtp_to_json(dry=dry)

    typer.secho("Converting .olm to .tga object lightmap...", fg="green")
    igi2_convert_olm_to_tga(dry=dry)

    typer.secho("Converting .iff to .fbx skeleton animation...", fg="green")
    igi2_convert_iff_to_fbx(dry=dry)

    typer.secho("All conversions complete.", fg="green", bold=True)


# noinspection DuplicatedCode
@igi2_app.command(
    name="extensions-of-game",
    short_help="Print file counts by extension from the game install directory",
)
def igi2_extensions_of_game() -> None:
    config = Config.model_validate_file()
    count_extensions(path=config.igi2.game_dir, is_zip=False)


@igi2_app.command(
    name="extensions-of-collect",
    short_help="Print file counts by extension from the collect source",
)
def igi2_extensions_of_collect() -> None:
    config = Config.model_validate_file()
    count_extensions(path=config.igi2.collect_path, is_zip=config.igi2.collect_is_zip)


@igi2_app.command(
    name="extensions-of-convert",
    short_help="Print file counts by extension from the convert destination",
)
def igi2_extensions_of_convert() -> None:
    config = Config.model_validate_file()
    count_extensions(path=config.igi2.convert_path, is_zip=config.igi2.convert_is_zip)


@igi2_app.command(
    name="convert-raw",
    short_help="Copy .mp3, .bmp, .jpg, .tga, .json files as-is from collect source to convert destination",
)
def igi2_convert_raw(dry: bool = False) -> None:
    _run_convert(converter=copy_raw, patterns=RAW_PATTERNS, dry=dry)


@igi2_app.command(
    name="convert-qvm-to-qsc",
    short_help="Convert .qvm files from collect source to .qsc files in convert destination",
)
def igi2_convert_qvm_to_qsc(dry: bool = False) -> None:
    _run_convert(converter=qvm_to_qsc, patterns=["*.qvm"], dry=dry)


@igi2_app.command(
    name="convert-wav-to-wav",
    short_help="Convert .wav files from collect source to regular .wav files in convert destination",
)
def igi2_convert_wav_to_wav(dry: bool = False) -> None:
    _run_convert(converter=wav_to_wav, patterns=["*.wav"], dry=dry)


@igi2_app.command(
    name="convert-tex-to-tga",
    short_help="Convert .tex, .spr, .pic files from collect source to .tga files in convert destination",
)
def igi2_convert_tex_to_tga(dry: bool = False) -> None:
    _run_convert(converter=tex_to_tga, patterns=["*.tex", "*.spr", "*.pic"], dry=dry)


@igi2_app.command(
    name="convert-fnt-to-zip",
    short_help="Convert .fnt files from collect source to BMFont (.fnt + .tga) in convert destination",
)
def igi2_convert_fnt_to_zip(dry: bool = False) -> None:
    _run_convert(converter=fnt_to_zip, patterns=["*.fnt"], dry=dry)


@igi2_app.command(
    name="convert-thm-to-tga",
    short_help="Convert .thm files from collect source to grayscale .tga heightmap images in convert destination",
)
def igi2_convert_thm_to_tga(dry: bool = False) -> None:
    _run_convert(converter=thm_to_tga, patterns=["*.thm"], dry=dry)


@igi2_app.command(
    name="convert-tmm-to-tga",
    short_help="Convert .tmm files from collect source to palette-colored .tga material maps in convert destination",
)
def igi2_convert_tmm_to_tga(dry: bool = False) -> None:
    _run_convert(converter=tmm_to_tga, patterns=["*.tmm"], dry=dry)


@igi2_app.command(
    name="convert-syn-to-json",
    short_help="Convert .syn files from collect source to .json files in convert destination",
)
def igi2_convert_syn_to_json(dry: bool = False) -> None:
    _run_convert(converter=syn_to_json, patterns=["*.syn"], dry=dry)


@igi2_app.command(
    name="convert-tlm-to-tga",
    short_help="Convert .tlm files from collect source to .tga lightmap images in convert destination",
)
def igi2_convert_tlm_to_tga(dry: bool = False) -> None:
    _run_convert(converter=tlm_to_tga, patterns=["*.tlm"], dry=dry)


@igi2_app.command(
    name="convert-dat-forest-to-json",
    short_help="Convert forest_*.dat files from collect source to .json files in convert destination",
)
def igi2_convert_dat_forest_to_json(dry: bool = False) -> None:
    _run_convert(converter=dat_forest_to_json, patterns=["forest_*.dat"], dry=dry)


@igi2_app.command(
    name="convert-dat-graph-to-json",
    short_help="Convert graph*.dat files from collect source to .json files in convert destination",
)
def igi2_convert_dat_graph_to_json(dry: bool = False) -> None:
    _run_convert(converter=dat_graph_to_json, patterns=["graph[0-9]*.dat"], dry=dry)


@igi2_app.command(
    name="convert-dat-graphcover-to-json",
    short_help="Convert graphcover*.dat files from collect source to .json files in convert destination",
)
def igi2_convert_dat_graphcover_to_json(dry: bool = False) -> None:
    _run_convert(converter=dat_graphcover_to_json, patterns=["graphcover*.dat"], dry=dry)


@igi2_app.command(
    name="convert-olm-to-tga",
    short_help="Convert .olm files from collect source to .tga object lightmap images in convert destination",
)
def igi2_convert_olm_to_tga(dry: bool = False) -> None:
    _run_convert(converter=olm_to_tga, patterns=["*.olm"], dry=dry)


@igi2_app.command(
    name="convert-iff-to-fbx",
    short_help="Convert .iff files from collect source to .fbx skeleton animation in convert destination",
)
def igi2_convert_iff_to_fbx(dry: bool = False) -> None:
    _run_convert(converter=iff_to_fbx, patterns=["*.iff"], dry=dry)


@igi2_app.command(
    name="convert-iff-to-qsc",
    short_help="Convert .iff files from collect source to .bef animation source in convert destination",
)
def igi2_convert_iff_to_qsc(dry: bool = False) -> None:
    _run_convert(converter=iff_to_qsc, patterns=["*.iff"], dry=dry)


@igi2_app.command(
    name="convert-mef-to-fbx",
    short_help="Convert .mef files from collect source to textured .fbx 3D model in convert destination",
)
def igi2_convert_mef_to_fbx(dry: bool = False) -> None:
    """Export .mef models to .fbx with per-render-group diffuse textures.

    Textures are resolved through each level's .mtp and referenced as sibling .tga files,
    so run "convert-tex-to-tga" first to produce those images. Models without a usable
    .mtp entry still export untextured.
    """
    config = Config.model_validate_file()
    # Bind the collect-source root so mef_to_fbx can read the level .mtp and resolve textures.
    converter = functools.partial(mef_to_fbx, collect_path=config.igi2.collect_path)
    _run_convert(converter=converter, patterns=["*.mef"], dry=dry)


@igi2_app.command(
    name="convert-mef-to-qsc",
    short_help="Convert .mef files from collect source to .mef text source in convert destination",
)
def igi2_convert_mef_to_qsc(dry: bool = False) -> None:
    _run_convert(converter=mef_to_qsc, patterns=["*.mef"], dry=dry)


@igi2_app.command(
    name="convert-mtp-to-json",
    short_help="Convert .mtp material/texture tables from collect source to .json in convert destination",
)
def igi2_convert_mtp_to_json(dry: bool = False) -> None:
    _run_convert(converter=mtp_to_json, patterns=["*.mtp"], dry=dry)


@igi2_app.command(
    name="convert-objects-to-json",
    short_help="[temporary] Export every level objects.qvm to a readable .json scene tree",
)
def igi2_convert_objects_to_json(dry: bool = False) -> None:
    """Temporary helper: decode each level objects.qvm into a named JSON task tree.

    Reads the declarations to name the positional Task_New values, drops the declarations,
    and writes the remaining task tree as objects.json. Not part of "convert-all".
    """
    _run_convert(converter=objects_to_json, patterns=["objects.qvm"], dry=dry)


@igi2_app.command(
    name="res-to-zip",
    short_help="Convert a .res file to .zip (binary) or .json (strings)",
)
def igi2_res_to_zip(
    source: Annotated[Path, typer.Argument(help="Path to a .res file")],
    output: Annotated[Path | None, typer.Option(help="Output file path (default: same dir, new suffix)")] = None,
) -> None:
    source_stream = BytesIO(source.read_bytes())
    target_stream, target_path = res_to_zip(source_stream, source)
    output_path = output or target_path
    output_path.write_bytes(target_stream.getvalue())
    typer.secho(f"{source} -> {output_path}", fg="green")
