import zipfile
from collections import defaultdict
from pathlib import Path

import typer

from igipy.config import Config
from igipy.core.formats import QVM, RES, TEX, WAV
from igipy.core.utils import convert_all
from igipy.igi1.services.qvm_to_qsc import qvm_to_qsc
from igipy.igi1.services.res_to_archive import res_to_archive
from igipy.igi1.services.tex_to_tga import tex_to_tga
from igipy.igi1.services.wav_to_wav import wav_to_wav

igi1_app = typer.Typer(add_completion=False)


@igi1_app.callback(invoke_without_command=True)
def igi1_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


@igi1_app.command(
    name="convert-all-res",
    short_help="Convert all .res files found in source_dir to .zip or .json files",
)
def igi1_convert_all_res(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert_all(
        reader=config.igi1.read_all_res(),
        parser=RES,
        router={"*.zip": config.igi1.unpack_dir, "*.json": config.igi1.target_dir},
        converter=res_to_archive,
        dry=dry,
    )


@igi1_app.command(
    name="convert-all-wav",
    short_help="Convert all .wav files found in source_dir and unpack_dir to regular .wav files",
)
def igi1_convert_all_wav(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert_all(
        reader=config.igi1.read_all_wav(),
        parser=WAV,
        router={"*": config.igi1.target_dir},
        converter=wav_to_wav,
        dry=dry,
    )


@igi1_app.command(
    name="convert-all-qvm",
    short_help="Convert all .qvm files found in source_dir to .qsc file",
)
def igi1_convert_all_qvm(dry: bool = False) -> None:
    config = Config.model_validate_file()
    convert_all(
        reader=config.igi1.read_all_qvm(),
        parser=QVM,
        router={"*": config.igi1.target_dir},
        converter=qvm_to_qsc,
        dry=dry,
    )


@igi1_app.command(
    name="convert-all-tex",
    short_help="Convert all .tex, .spr and .pic files found in source_dir and unpack_dir to .tga files",
)
def igi1_convert_all_tex(dry: bool = False) -> None:
    config = Config.model_validate_file()

    convert_all(
        reader=config.igi1.read_all_tex(),
        parser=TEX,
        router={"*": config.igi1.target_dir},
        converter=tex_to_tga,
        dry=dry,
    )


@igi1_app.command(
    name="convert-all",
    short_help="Convert all known formats found in source_dir",
)
def igi1_convert_all() -> None:
    typer.secho("Converting `.res`...", fg="green")
    igi1_convert_all_res(dry=False)
    typer.secho("Converting `.wav`...", fg="green")
    igi1_convert_all_wav(dry=False)
    typer.secho("Converting `.qvm`...", fg="green")
    igi1_convert_all_qvm(dry=False)
    typer.secho("Converting `.tex`...", fg="green")
    igi1_convert_all_tex(dry=False)


@igi1_app.command(
    name="extensions",
    short_help="Group files in source_dir and unpack_dir by extension and show counts",
    hidden=True,
)
def igi1_extensions() -> None:
    config = Config.model_validate_file()

    counter = defaultdict(lambda: {"source": 0, "unpack": 0})

    for path in config.igi1.source_dir.glob("**/*"):
        if not path.is_file():
            continue

        if path.suffix != ".dat":
            format_name = f"`{path.suffix}`"
        elif path.with_suffix(".mtp").exists():
            format_name = "`.dat` (mtp)"
        else:
            format_name = "`.dat` (graph)"

        counter[format_name]["source"] += 1

    for path in config.igi1.unpack_dir.glob("**/*.zip"):
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
