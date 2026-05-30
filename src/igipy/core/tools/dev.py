import shutil
from collections import defaultdict
from pathlib import Path
from typing import Annotated

import typer

dev_app = typer.Typer(add_completion=False)


@dev_app.callback(invoke_without_command=True)
def dev_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


@dev_app.command(
    name="count-extensions",
    short_help="Count files by extension in a directory",
)
def dev_count_extensions(path: Path) -> None:
    if not path.is_dir():
        typer.secho(f"Error: '{path}' is not a directory.", fg="red")
        raise typer.Exit(1)

    counter: dict[str, int] = defaultdict(int)

    for item in path.rglob("*"):
        if not item.is_file():
            continue
        ext = item.suffix if item.suffix else "(no extension)"
        counter[ext] += 1

    results = sorted(counter.items(), key=lambda x: x[1], reverse=True)

    typer.echo(f"| {'Extension':<20} | {'Count':<10} |")
    typer.echo(f"|-{'-' * 20}-|-{'-' * 10}-|")

    for ext, count in results:
        typer.echo(f"| {ext:<20} | {count:<10} |")


@dev_app.command(
    name="copy-files",
    short_help="Copy files from source to destination, excluding .res/.mtp/.dat(with .mtp)",
)
def dev_copy_files(
    source: Annotated[Path, typer.Argument(help="Source directory")],
    destination: Annotated[Path, typer.Argument(help="Destination directory")],
    dry: bool = False,
) -> None:
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

        rel = item.relative_to(source)
        parts = rel.parts
        lowered_parents = [p.lower() for p in parts[:-1]]
        destination_path = (
            destination.joinpath(*lowered_parents, parts[-1]) if lowered_parents else destination / parts[-1]
        )

        number += 1
        typer.echo(
            f'Copy [{number:>05}]: "{typer.style(rel.as_posix(), fg="green")}" '
            f'to "{typer.style(destination_path.as_posix(), fg="yellow")}"'
        )

        if not dry:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination_path)

    typer.secho(f"Total: {number} files {'(dry run)' if dry else 'copied'}.", fg="green")
