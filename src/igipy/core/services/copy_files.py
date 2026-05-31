import shutil
from pathlib import Path

import typer


def copy_files(source: Path, destination: Path, dry: bool = False) -> None:
    if not source.is_dir():
        typer.secho(f"Error: '{source}' is not a directory.", fg="red")
        raise typer.Exit(1)

    if not destination.is_dir():
        typer.secho(f"Error: '{destination}' is not a directory.", fg="red")
        raise typer.Exit(1)

    number = 0

    excluded_extensions = {".res", ".mtp"}

    for item in sorted(source.rglob("*")):
        if not item.is_file():
            continue

        if item.suffix.lower() in excluded_extensions:
            continue

        if item.suffix.lower() == ".dat" and item.with_suffix(".mtp").exists():
            continue

        relative_path = item.relative_to(source)
        parts = relative_path.parts
        lowered_parents = [part.lower() for part in parts[:-1]]
        destination_path = (
            destination.joinpath(*lowered_parents, parts[-1]) if lowered_parents else destination / parts[-1]
        )

        number += 1
        typer.echo(
            f'Copy [{number:>05}]: "{typer.style(relative_path.as_posix(), fg="green")}" '
            f'to "{typer.style(destination_path.as_posix(), fg="yellow")}"'
        )

        if not dry:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination_path)

    typer.secho(f"Total: {number} files {'(dry run)' if dry else 'copied'}.", fg="green")
