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
    errors = 0
    skipped = 0
    failed_files: list[tuple[str, str]] = []

    existing_names: set[str] = set()
    if convert_path.exists():
        with ZipFile(convert_path, "r") as existing_zip:
            existing_names = set(existing_zip.namelist())

    mode = "a" if convert_path.exists() else "w"
    zip_file = None if dry else ZipFile(convert_path, mode, zipfile.ZIP_DEFLATED)

    try:
        with ZipFile(collect_path, "r") as source_zip:
            entries = [
                info
                for info in source_zip.infolist()
                if not info.is_dir() and PurePosixPath(info.filename).suffix.lower() in RAW_EXTENSIONS
            ]

            for info in entries:
                number += 1
                source_path = PurePosixPath(info.filename)
                destination_name = source_path.as_posix()

                if destination_name in existing_names:
                    skipped += 1
                    typer.echo(
                        f'Skip  [{number:>05}]: "{typer.style(source_path.as_posix(), fg="green")}" (already exists)'
                    )
                    continue

                existing_names.add(destination_name)

                try:
                    data = source_zip.read(info)
                except Exception as exc:  # noqa: BLE001
                    errors += 1
                    failed_files.append((source_path.as_posix(), str(exc)))
                    typer.echo(f'Error [{number:>05}]: "{typer.style(source_path.as_posix(), fg="red")}" — {exc}')
                    continue

                typer.echo(f'Copy  [{number:>05}]: "{typer.style(source_path.as_posix(), fg="green")}"')

                if zip_file is not None:
                    zip_file.writestr(destination_name, data)
    finally:
        if zip_file is not None:
            zip_file.close()

    dry_suffix = " (dry run)" if dry else ""
    errors_suffix = f", {errors} errors" if errors > 0 else ""
    skipped_suffix = f", {skipped} skipped" if skipped > 0 else ""
    typer.secho(
        f"Total: {number} files{errors_suffix}{skipped_suffix}{dry_suffix}.",
        fg="green",
    )

    if failed_files:
        typer.secho(f"\nFailed files ({len(failed_files)}):", fg="red", bold=True)
        for path, reason in failed_files:
            typer.echo(f"  {typer.style(path, fg='red')} — {reason}")
