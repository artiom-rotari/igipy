import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Annotated

import typer

from igipy.config import Config
from igipy.core.formats import RES
from igipy.core.services.qvm_to_qsc import qvm_to_qsc
from igipy.core.services.tex_to_tga import tex_to_tga
from igipy.core.services.wav_to_wav import wav_to_wav
from igipy.core.utils import convert_all, convert_zip
from igipy.igi2.services.dat_forest_to_json import dat_forest_to_json
from igipy.igi2.services.dat_graph_to_json import dat_graph_to_json
from igipy.igi2.services.dat_graphcover_to_json import dat_graphcover_to_json
from igipy.igi2.services.fnt_to_zip import fnt_to_zip
from igipy.igi2.services.iff_to_gltf import iff_to_gltf
from igipy.igi2.services.iff_to_json import iff_to_json
from igipy.igi2.services.olm_to_tga import olm_to_tga
from igipy.igi2.services.syn_to_json import syn_to_json
from igipy.igi2.services.thm_to_tga import thm_to_tga
from igipy.igi2.services.tlm_to_tga import tlm_to_tga
from igipy.igi2.services.tmm_to_tga import tmm_to_tga
from igipy.igi2.services.zip_collect import zip_collect
from igipy.igi2.services.zip_convert_raw import zip_convert_raw
from igipy.igi2.services.zip_extensions import zip_extensions

igi2_app = typer.Typer(add_completion=False)


@igi2_app.callback(invoke_without_command=True)
def igi2_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


@igi2_app.command(
    name="convert-all-res",
    short_help="Convert all .res files found in source_dir to .zip or .json files",
)
def igi2_convert_all_res(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert_all(
        reader=config.igi2.read_all_res(),
        parser=RES,
        router={"*.zip": config.igi2.unpack_dir, "*.json": config.igi2.target_dir},
        dry=dry,
    )


@igi2_app.command(
    name="convert-all",
    short_help="Convert all known formats found in source_dir",
)
def igi2_convert_all() -> None:
    typer.secho("Converting `.res`...", fg="green")
    igi2_convert_all_res(dry=False)


@igi2_app.command(
    name="extensions",
    short_help="Group files in source_dir and unpack_dir by extension and show counts",
    hidden=True,
)
def igi2_extensions() -> None:
    config = Config.model_validate_file()

    counter = defaultdict(lambda: {"source": 0, "unpack": 0})

    for path in config.igi2.source_dir.glob("**/*"):
        if not path.is_file():
            continue

        if path.suffix != ".dat":
            format_name = f"`{path.suffix}`"
        elif path.with_suffix(".mtp").exists():
            format_name = "`.dat` (mtp)"
        else:
            format_name = "`.dat` (graph)"

        counter[format_name]["source"] += 1

    for path in config.igi2.unpack_dir.glob("**/*.zip"):
        with zipfile.ZipFile(path, "r") as zip_file:
            for file_info in zip_file.infolist():
                format_name = f"`{Path(file_info.filename).suffix}`"
                counter[format_name]["unpack"] += 1

    results: list[tuple[str, int, int, int]] = [
        (extension, counts["source"] + counts["unpack"], counts["source"], counts["unpack"])
        for extension, counts in sorted(
            counter.items(), key=lambda item: item[1]["source"] + item[1]["unpack"], reverse=True
        )
    ]

    typer.echo(
        f"| {'Extension':<15} | {'Total':<15} | {'Source':<15} | {'Unpack':<15} |\n"
        f"|-{'-' * 15}-|-{'-' * 15}-|-{'-' * 15}-|-{'-' * 15}-|"
    )

    for extension, total, source, unpack in results:
        typer.echo(f"| {extension:<15} | {total:<15} | {source:<15} | {unpack:<15} |")


@igi2_app.command(
    name="zip-collect",
    short_help="Collect all game resources into a single zip archive",
)
def igi2_zip_collect(
    game_dir: Annotated[Path | None, typer.Option(help="Game install directory (default from config)")] = None,
    output: Annotated[Path | None, typer.Option(help="Output zip file path (default from config)")] = None,
    dry: bool = False,
) -> None:
    config = Config.model_validate_file()
    zip_collect(
        game_dir=game_dir or config.igi2.source_dir,
        output_path=output or config.igi2.collect_path,
        dry=dry,
    )


@igi2_app.command(
    name="zip-convert-all",
    short_help="Run all zip-based converters (collect zip to convert zip)",
)
def igi2_zip_convert_all(dry: bool = False) -> None:
    config = Config.model_validate_file()
    typer.secho(f"Collect: {config.igi2.collect_path}", fg="cyan")
    typer.secho(f"Convert: {config.igi2.convert_path}", fg="cyan")

    typer.secho("Copying raw files (.mp3, .bmp, .jpg, .tga, .json)...", fg="green")
    igi2_zip_convert_raw(dry=dry)

    typer.secho("Converting .qvm to .qsc...", fg="green")
    igi2_zip_convert_qvm_to_qsc(dry=dry)

    typer.secho("Converting .wav to standard .wav...", fg="green")
    igi2_zip_convert_wav_to_wav(dry=dry)

    typer.secho("Converting .tex/.spr/.pic to .tga...", fg="green")
    igi2_zip_convert_tex_to_tga(dry=dry)

    typer.secho("Converting .fnt to BMFont zip...", fg="green")
    igi2_zip_convert_fnt_to_zip(dry=dry)

    typer.secho("Converting .thm to .tga heightmap...", fg="green")
    igi2_zip_convert_thm_to_tga(dry=dry)

    typer.secho("Converting .tmm to .tga material map...", fg="green")
    igi2_zip_convert_tmm_to_tga(dry=dry)

    typer.secho("Converting .syn to .json...", fg="green")
    igi2_zip_convert_syn_to_json(dry=dry)

    typer.secho("Converting .tlm to .tga lightmap...", fg="green")
    igi2_zip_convert_tlm_to_tga(dry=dry)

    typer.secho("Converting forest_*.dat to .json...", fg="green")
    igi2_zip_convert_dat_forest_to_json(dry=dry)

    typer.secho("Converting graph*.dat to .json...", fg="green")
    igi2_zip_convert_dat_graph_to_json(dry=dry)

    typer.secho("Converting graphcover*.dat to .json...", fg="green")
    igi2_zip_convert_dat_graphcover_to_json(dry=dry)

    typer.secho("Converting .olm to .tga object lightmap...", fg="green")
    igi2_zip_convert_olm_to_tga(dry=dry)

    typer.secho("Converting .iff to .json animation data...", fg="green")
    igi2_zip_convert_iff_to_json(dry=dry)

    typer.secho("Converting .iff to .gltf skeleton animation...", fg="green")
    igi2_zip_convert_iff_to_gltf(dry=dry)

    typer.secho("All zip conversions complete.", fg="green", bold=True)


@igi2_app.command(
    name="zip-collected-extensions",
    short_help="Print file counts by extension from the collect zip",
)
def igi2_zip_collected_extensions(
    path: Annotated[Path | None, typer.Option(help="Path to zip file (default from config)")] = None,
) -> None:
    config = Config.model_validate_file()
    zip_extensions(zip_path=path or config.igi2.collect_path)


@igi2_app.command(
    name="zip-converted-extensions",
    short_help="Print file counts by extension from the convert zip",
)
def igi2_zip_converted_extensions(
    path: Annotated[Path | None, typer.Option(help="Path to zip file (default from config)")] = None,
) -> None:
    config = Config.model_validate_file()
    zip_extensions(zip_path=path or config.igi2.convert_path)


@igi2_app.command(
    name="zip-convert-raw",
    short_help="Copy .mp3, .bmp, .jpg, .tga, .json files as-is from collect zip to convert zip",
)
def igi2_zip_convert_raw(dry: bool = False) -> None:
    config = Config.model_validate_file()
    zip_convert_raw(
        collect_path=config.igi2.collect_path,
        convert_path=config.igi2.convert_path,
        dry=dry,
    )


@igi2_app.command(
    name="zip-convert-qvm-to-qsc",
    short_help="Convert .qvm files from collect zip to .qsc files in convert zip",
)
def igi2_zip_convert_qvm_to_qsc(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert_zip(
        collect_path=config.igi2.collect_path,
        convert_path=config.igi2.convert_path,
        converter=qvm_to_qsc,
        patterns=["*.qvm"],
        dry=dry,
    )


@igi2_app.command(
    name="zip-convert-wav-to-wav",
    short_help="Convert .wav files from collect zip to regular .wav files in convert zip",
)
def igi2_zip_convert_wav_to_wav(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert_zip(
        collect_path=config.igi2.collect_path,
        convert_path=config.igi2.convert_path,
        converter=wav_to_wav,
        patterns=["*.wav"],
        dry=dry,
    )


@igi2_app.command(
    name="zip-convert-tex-to-tga",
    short_help="Convert .tex, .spr, .pic files from collect zip to .tga files in convert zip",
)
def igi2_zip_convert_tex_to_tga(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert_zip(
        collect_path=config.igi2.collect_path,
        convert_path=config.igi2.convert_path,
        converter=tex_to_tga,
        patterns=["*.tex", "*.spr", "*.pic"],
        dry=dry,
    )


@igi2_app.command(
    name="zip-convert-fnt-to-zip",
    short_help="Convert .fnt files from collect zip to BMFont (.fnt + .tga) in convert zip",
)
def igi2_zip_convert_fnt_to_zip(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert_zip(
        collect_path=config.igi2.collect_path,
        convert_path=config.igi2.convert_path,
        converter=fnt_to_zip,
        patterns=["*.fnt"],
        dry=dry,
    )


@igi2_app.command(
    name="zip-convert-thm-to-tga",
    short_help="Convert .thm files from collect zip to grayscale .tga heightmap images in convert zip",
)
def igi2_zip_convert_thm_to_tga(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert_zip(
        collect_path=config.igi2.collect_path,
        convert_path=config.igi2.convert_path,
        converter=thm_to_tga,
        patterns=["*.thm"],
        dry=dry,
    )


@igi2_app.command(
    name="zip-convert-tmm-to-tga",
    short_help="Convert .tmm files from collect zip to palette-colored .tga material map images in convert zip",
)
def igi2_zip_convert_tmm_to_tga(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert_zip(
        collect_path=config.igi2.collect_path,
        convert_path=config.igi2.convert_path,
        converter=tmm_to_tga,
        patterns=["*.tmm"],
        dry=dry,
    )


@igi2_app.command(
    name="zip-convert-syn-to-json",
    short_help="Convert .syn files from collect zip to .json files in convert zip",
)
def igi2_zip_convert_syn_to_json(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert_zip(
        collect_path=config.igi2.collect_path,
        convert_path=config.igi2.convert_path,
        converter=syn_to_json,
        patterns=["*.syn"],
        dry=dry,
    )


@igi2_app.command(
    name="zip-convert-tlm-to-tga",
    short_help="Convert .tlm files from collect zip to .tga lightmap images in convert zip",
)
def igi2_zip_convert_tlm_to_tga(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert_zip(
        collect_path=config.igi2.collect_path,
        convert_path=config.igi2.convert_path,
        converter=tlm_to_tga,
        patterns=["*.tlm"],
        dry=dry,
    )


@igi2_app.command(
    name="zip-convert-dat-forest-to-json",
    short_help="Convert forest_*.dat files from collect zip to .json files in convert zip",
)
def igi2_zip_convert_dat_forest_to_json(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert_zip(
        collect_path=config.igi2.collect_path,
        convert_path=config.igi2.convert_path,
        converter=dat_forest_to_json,
        patterns=["forest_*.dat"],
        dry=dry,
    )


@igi2_app.command(
    name="zip-convert-dat-graph-to-json",
    short_help="Convert graph*.dat files from collect zip to .json files in convert zip",
)
def igi2_zip_convert_dat_graph_to_json(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert_zip(
        collect_path=config.igi2.collect_path,
        convert_path=config.igi2.convert_path,
        converter=dat_graph_to_json,
        patterns=["graph[0-9]*.dat"],
        dry=dry,
    )


@igi2_app.command(
    name="zip-convert-dat-graphcover-to-json",
    short_help="Convert graphcover*.dat files from collect zip to .json files in convert zip",
)
def igi2_zip_convert_dat_graphcover_to_json(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert_zip(
        collect_path=config.igi2.collect_path,
        convert_path=config.igi2.convert_path,
        converter=dat_graphcover_to_json,
        patterns=["graphcover*.dat"],
        dry=dry,
    )


@igi2_app.command(
    name="zip-convert-iff-to-json",
    short_help="Convert .iff files from collect zip to .json animation data in convert zip",
)
def igi2_zip_convert_iff_to_json(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert_zip(
        collect_path=config.igi2.collect_path,
        convert_path=config.igi2.convert_path,
        converter=iff_to_json,
        patterns=["*.iff"],
        dry=dry,
    )


@igi2_app.command(
    name="zip-convert-olm-to-tga",
    short_help="Convert .olm files from collect zip to .tga object lightmap images in convert zip",
)
def igi2_zip_convert_olm_to_tga(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert_zip(
        collect_path=config.igi2.collect_path,
        convert_path=config.igi2.convert_path,
        converter=olm_to_tga,
        patterns=["*.olm"],
        dry=dry,
    )


@igi2_app.command(
    name="zip-convert-iff-to-gltf",
    short_help="Convert .iff files from collect zip to .gltf skeleton animation in convert zip",
)
def igi2_zip_convert_iff_to_gltf(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert_zip(
        collect_path=config.igi2.collect_path,
        convert_path=config.igi2.convert_path,
        converter=iff_to_gltf,
        patterns=["*.iff"],
        dry=dry,
    )
