from collections.abc import Callable
from io import BytesIO
from pathlib import Path, PurePosixPath

import typer

from igipy.core.base import FileIgnored
from igipy.core.utils.archive import ArchiveWriter, existing_destination_names, iter_source_entries
from igipy.core.utils.paths import matches_any_pattern


def convert(  # noqa: PLR0913
    collect_path: Path,
    collect_is_zip: bool,
    convert_path: Path,
    convert_is_zip: bool,
    converter: Callable[[BytesIO, Path | None], tuple[BytesIO, Path | None]],
    patterns: list[str],
    dry: bool = True,
) -> None:
    """Read entries from the collect source and write converted entries to the convert destination.

    Both endpoints honour the zip/directory duality: "collect_is_zip" selects whether the source
    is a zip archive or a directory tree, and "convert_is_zip" selects the destination shape. All
    four combinations are supported through the shared archive layer.
    """
    if dry:
        typer.secho("DRY RUN — no files will be written.", fg="yellow")

    number = 0
    errors = 0
    skipped = 0
    failed_files: list[tuple[str, str]] = []

    existing_names = existing_destination_names(convert_path, convert_is_zip)

    with ArchiveWriter(convert_path, convert_is_zip, dry=dry) as writer:
        for source_path, source_stream in iter_source_entries(collect_path, collect_is_zip):
            if not matches_any_pattern(source_path.as_posix(), patterns):
                continue

            number += 1

            try:
                destination_stream, destination_path_object = converter(source_stream, Path(source_path.as_posix()))
            except FileIgnored:
                continue
            except Exception as exception:  # noqa: BLE001
                errors += 1
                failed_files.append((source_path.as_posix(), str(exception)))
                typer.echo(f'Error [{number:>05}]: "{typer.style(source_path.as_posix(), fg="red")}" — {exception}')
                continue

            destination_path = PurePosixPath(destination_path_object) if destination_path_object else source_path
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

            writer.write(destination_name, destination_stream.getvalue())

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
