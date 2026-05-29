import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath

import typer


def zip_extensions(zip_path: Path) -> None:
    if not zip_path.is_file():
        typer.secho(f"File not found: {zip_path}", fg="red")
        raise typer.Exit(1)

    counter: dict[str, int] = defaultdict(int)
    total_files = 0

    with zipfile.ZipFile(zip_path, "r") as zip_file:
        for file_info in zip_file.infolist():
            if file_info.filename.endswith("/"):
                continue

            extension = PurePosixPath(file_info.filename).suffix.lower()
            if not extension:
                extension = "(no ext)"

            counter[extension] += 1
            total_files += 1

    results = sorted(counter.items(), key=lambda item: item[1], reverse=True)

    typer.echo(f"| {'Extension':<15} | {'Count':<10} |\n|-{'-' * 15}-|-{'-' * 10}-|")

    for extension, count in results:
        typer.echo(f"| {extension:<15} | {count:<10} |")

    typer.secho(f"\nTotal: {total_files} files, {len(results)} extensions.", fg="green")
