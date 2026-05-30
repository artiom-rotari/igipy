import zipfile
from collections.abc import Callable, Generator
from fnmatch import fnmatch
from io import BytesIO
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

import typer

from igipy.core.base import FileIgnored, FileModel


def convert_all(
    reader: Generator[tuple[BytesIO, Path, Path | None]],
    parser: type[FileModel],
    router: dict[str, Path],
    converter: Callable[[FileModel], tuple[BytesIO, str]] | None = None,
    dry: bool = True,
) -> None:
    for number, (source_stream, source_path, zip_path) in enumerate(reader, start=1):
        try:
            instance = parser.model_validate_stream(source_stream)
            destination_stream, destination_suffix = converter(instance) if converter else instance.model_dump_stream()
        except FileIgnored:
            continue

        destination_path = (
            zip_path.joinpath(source_path).with_suffix(destination_suffix)
            if zip_path
            else source_path.with_suffix(destination_suffix)
        )

        for pattern, target_dir in router.items():
            if destination_path.match(pattern):
                destination_path = target_dir.joinpath(destination_path)
                break

        if not zip_path:
            typer.echo(
                f'Convert [{number:>05}]: "{typer.style(source_path.as_posix(), fg="green")}" '
                f'to "{typer.style(destination_path.as_posix(), fg="yellow")}"'
            )
        else:
            typer.echo(
                f'Convert [{number:>05}]: "{typer.style(source_path.as_posix(), fg="green")}" '
                f'from "{typer.style(zip_path.as_posix(), fg="red")}" '
                f'to "{typer.style(destination_path.as_posix(), fg="yellow")}"'
            )

        if not dry:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            destination_path.write_bytes(destination_stream.getvalue())


def convert_zip(  # noqa: C901
    collect_path: Path,
    convert_path: Path,
    converter: Callable[[BytesIO, Path | None], tuple[BytesIO, Path | None]],
    patterns: list[str],
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
                if not info.is_dir() and any(fnmatch(PurePosixPath(info.filename).name, p) for p in patterns)
            ]

            for info in entries:
                number += 1
                source_path = PurePosixPath(info.filename)

                try:
                    source_stream = BytesIO(source_zip.read(info))
                    destination_stream, destination_path_obj = converter(source_stream, Path(info.filename))
                except FileIgnored:
                    continue
                except Exception as exc:  # noqa: BLE001
                    errors += 1
                    failed_files.append((source_path.as_posix(), str(exc)))
                    typer.echo(f'Error [{number:>05}]: "{typer.style(source_path.as_posix(), fg="red")}" — {exc}')
                    continue

                destination_path = PurePosixPath(destination_path_obj) if destination_path_obj else source_path
                destination_name = destination_path.as_posix()

                if destination_name in existing_names:
                    skipped += 1
                    typer.echo(
                        f'Skip  [{number:>05}]: "{typer.style(source_path.as_posix(), fg="green")}" '
                        f'-> "{typer.style(destination_path.as_posix(), fg="cyan")}" (already exists)'
                    )
                    continue

                existing_names.add(destination_name)
                typer.echo(
                    f'Convert [{number:>05}]: "{typer.style(source_path.as_posix(), fg="green")}" '
                    f'-> "{typer.style(destination_path.as_posix(), fg="yellow")}"'
                )

                if zip_file is not None:
                    zip_file.writestr(destination_name, destination_stream.getvalue())
    finally:
        if zip_file is not None:
            zip_file.close()

    dry_suffix = " (dry run)" if dry else ""
    skipped_suffix = f", {skipped} skipped" if skipped > 0 else ""
    typer.secho(
        f"Total: {number} files, {errors} errors{skipped_suffix}{dry_suffix}.",
        fg="green",
    )

    if failed_files:
        typer.secho(f"\nFailed files ({len(failed_files)}):", fg="red", bold=True)
        for path, reason in failed_files:
            typer.echo(f"  {typer.style(path, fg='red')} — {reason}")


def copy_files(
    reader: Generator[tuple[BytesIO, Path, None]],
    target_dir: Path,
    dry: bool = True,
) -> None:
    for number, (source_stream, source_path, _) in enumerate(reader, start=1):
        parts = source_path.parts
        lowered_parents = [p.lower() for p in parts[:-1]]
        destination_path = (
            target_dir.joinpath(*lowered_parents, parts[-1]) if lowered_parents else target_dir / parts[-1]
        )

        typer.echo(
            f'Copy [{number:>05}]: "{typer.style(source_path.as_posix(), fg="green")}" '
            f'to "{typer.style(destination_path.as_posix(), fg="yellow")}"'
        )

        if not dry:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            destination_path.write_bytes(source_stream.getvalue())
