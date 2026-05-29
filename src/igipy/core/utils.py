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
    for number, (src_stream, src_path, zip_path) in enumerate(reader, start=1):
        try:
            instance = parser.model_validate_stream(src_stream)
            dst_stream, dst_suffix = converter(instance) if converter else instance.model_dump_stream()
        except FileIgnored:
            continue

        dst_path = zip_path.joinpath(src_path).with_suffix(dst_suffix) if zip_path else src_path.with_suffix(dst_suffix)

        for pattern, target_dir in router.items():
            if dst_path.match(pattern):
                dst_path = target_dir.joinpath(dst_path)
                break

        if not zip_path:
            typer.echo(
                f'Convert [{number:>05}]: "{typer.style(src_path.as_posix(), fg="green")}" '
                f'to "{typer.style(dst_path.as_posix(), fg="yellow")}"'
            )
        else:
            typer.echo(
                f'Convert [{number:>05}]: "{typer.style(src_path.as_posix(), fg="green")}" '
                f'from "{typer.style(zip_path.as_posix(), fg="red")}" '
                f'to "{typer.style(dst_path.as_posix(), fg="yellow")}"'
            )

        if not dry:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            dst_path.write_bytes(dst_stream.getvalue())


def convert_zip(
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
                if not info.is_dir() and any(fnmatch(PurePosixPath(info.filename).name, p) for p in patterns)
            ]

            for info in entries:
                number += 1
                src_path = PurePosixPath(info.filename)

                try:
                    src_stream = BytesIO(src_zip.read(info))
                    dst_stream, dst_path_obj = converter(src_stream, Path(info.filename))
                except FileIgnored:
                    continue
                except Exception as exc:  # noqa: BLE001
                    errors += 1
                    typer.echo(f'Error [{number:>05}]: "{typer.style(src_path.as_posix(), fg="red")}" — {exc}')
                    continue

                dst_path = PurePosixPath(dst_path_obj) if dst_path_obj else src_path
                dst_name = dst_path.as_posix()

                if dst_name in existing_names:
                    skipped += 1
                    typer.echo(
                        f'Skip  [{number:>05}]: "{typer.style(src_path.as_posix(), fg="green")}" '
                        f'-> "{typer.style(dst_path.as_posix(), fg="cyan")}" (already exists)'
                    )
                    continue

                existing_names.add(dst_name)
                typer.echo(
                    f'Convert [{number:>05}]: "{typer.style(src_path.as_posix(), fg="green")}" '
                    f'-> "{typer.style(dst_path.as_posix(), fg="yellow")}"'
                )

                if zip_file is not None:
                    zip_file.writestr(dst_name, dst_stream.getvalue())
    finally:
        if zip_file is not None:
            zip_file.close()

    dry_suffix = " (dry run)" if dry else ""
    skipped_suffix = f", {skipped} skipped" if skipped > 0 else ""
    typer.secho(
        f"Total: {number} files, {errors} errors{skipped_suffix}{dry_suffix}.",
        fg="green",
    )


def copy_files(
    reader: Generator[tuple[BytesIO, Path, None]],
    target_dir: Path,
    dry: bool = True,
) -> None:
    for number, (src_stream, src_path, _) in enumerate(reader, start=1):
        parts = src_path.parts
        lowered_parents = [p.lower() for p in parts[:-1]]
        dst_path = target_dir.joinpath(*lowered_parents, parts[-1]) if lowered_parents else target_dir / parts[-1]

        typer.echo(
            f'Copy [{number:>05}]: "{typer.style(src_path.as_posix(), fg="green")}" '
            f'to "{typer.style(dst_path.as_posix(), fg="yellow")}"'
        )

        if not dry:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            dst_path.write_bytes(src_stream.getvalue())
