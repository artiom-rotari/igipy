from collections import defaultdict
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

import typer


def _iter_member_names(path: Path, is_zip: bool) -> list[str]:
    if is_zip:
        if not path.is_file():
            typer.secho(f"File not found: {path}", fg="red")
            raise typer.Exit(1)
        with ZipFile(path, "r") as zip_file:
            return [info.filename for info in zip_file.infolist() if not info.is_dir()]

    if not path.is_dir():
        typer.secho(f"Directory not found: {path}", fg="red")
        raise typer.Exit(1)
    return [item.relative_to(path).as_posix() for item in path.rglob("*") if item.is_file()]


def _classify_dat(name: PurePosixPath, member_names: set[str]) -> str:
    """Classify a ``.dat`` member into a more specific bucket.

    The ``.mtp`` companion check works for both zip and directory sources because it tests
    membership in the collected member-name set rather than touching the filesystem.
    """
    if name.with_suffix(".mtp").as_posix() in member_names:
        return ".dat (mtp)"
    if name.match("forest_*.dat"):
        return ".dat (forest)"
    if name.match("graph[0-9]*.dat"):
        return ".dat (graph)"
    if name.match("graphcover*.dat"):
        return ".dat (graphcover)"
    return ".dat"


def count_extensions(path: Path, is_zip: bool) -> None:
    member_names = _iter_member_names(path, is_zip)
    member_name_set = set(member_names)

    counter: dict[str, int] = defaultdict(int)
    total_files = 0

    for member_name in member_names:
        name = PurePosixPath(member_name)
        extension = name.suffix.lower() or "(no ext)"
        if extension == ".dat":
            extension = _classify_dat(name, member_name_set)
        counter[extension] += 1
        total_files += 1

    results = sorted(counter.items(), key=lambda item: item[1], reverse=True)

    typer.echo(f"| {'Extension':<20} | {'Count':<10} |\n|-{'-' * 20}-|-{'-' * 10}-|")

    for extension, count in results:
        typer.echo(f"| {extension:<20} | {count:<10} |")

    typer.secho(f"\nTotal: {total_files} files, {len(results)} extensions.", fg="green")
