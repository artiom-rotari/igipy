import zipfile
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

import typer

RAW_EXTENSIONS: set[str] = {".mp3", ".bmp", ".jpg", ".tga", ".json"}


def zip_convert_raw(
    collect_path: Path,
    convert_path: Path,
    dry: bool = True,
) -> None:
    if dry:
        typer.secho("DRY RUN — no files will be written.", fg="yellow")

    number = 0
    skipped = 0

    existing_names: set[str] = set()
    if convert_path.exists():
        with ZipFile(convert_path, "r") as existing_zip:
            existing_names = set(existing_zip.namelist())

    mode = "a" if convert_path.exists() else "w"
    zip_file = None if dry else ZipFile(convert_path, mode, zipfile.ZIP_DEFLATED)

    try:
        with ZipFile(collect_path, "r") as src_zip:
            entries = [
                info
                for info in src_zip.infolist()
                if not info.is_dir() and PurePosixPath(info.filename).suffix.lower() in RAW_EXTENSIONS
            ]

            for info in entries:
                number += 1
                src_path = PurePosixPath(info.filename)
                dst_name = src_path.as_posix()

                if dst_name in existing_names:
                    skipped += 1
                    typer.echo(
                        f'Skip  [{number:>05}]: "{typer.style(src_path.as_posix(), fg="green")}" (already exists)'
                    )
                    continue

                existing_names.add(dst_name)
                typer.echo(f'Copy  [{number:>05}]: "{typer.style(src_path.as_posix(), fg="green")}"')

                if zip_file is not None:
                    zip_file.writestr(dst_name, src_zip.read(info))
    finally:
        if zip_file is not None:
            zip_file.close()

    dry_suffix = " (dry run)" if dry else ""
    skipped_suffix = f", {skipped} skipped" if skipped > 0 else ""
    typer.secho(
        f"Total: {number} files{skipped_suffix}{dry_suffix}.",
        fg="green",
    )
