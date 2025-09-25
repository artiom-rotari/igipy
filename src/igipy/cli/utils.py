from collections import defaultdict
from itertools import chain

import typer

from igipy.config import GameConfig


def extensions(config: GameConfig) -> None:
    counter = defaultdict(lambda: {"game_count": 0, "extracted_count": 0})

    for path, group in chain(
        ((path, "game_count") for path in config.game_dir.glob("**/*")),
        ((path, "extracted_count") for path in config.extracted_dir.glob("**/*")),
    ):
        if not path.is_file():
            continue

        if path.suffix != ".dat":
            format_name = f"`{path.suffix}`"
        elif path.with_suffix(".mtp").exists():
            format_name = "`.dat` (mtp)"
        else:
            format_name = "`.dat` (graph)"

        counter[format_name][group] += 1

    results: list[tuple[str, int, int, int]] = [
        (extension, counts["game_count"] + counts["extracted_count"], counts["game_count"], counts["extracted_count"])
        for extension, counts in sorted(
            counter.items(), key=lambda item: item[1]["game_count"] + item[1]["extracted_count"], reverse=True
        )
    ]

    typer.echo(
        f"| {'Extension':<15} | {'Total':<15} | {'Game':<15} | {'Extracted':<15} |\n"
        f"|-{'-' * 15}-|-{'-' * 15}-|-{'-' * 15}-|-{'-' * 15}-|"
    )

    for extension, total_count, game_count, extracted_count in results:
        typer.echo(f"| {extension:<15} | {total_count:<15} | {game_count:<15} | {extracted_count:<15} |")


def files(config: GameConfig, patterns: list[str]) -> None:
    for pattern in patterns:
        for path in chain(
            config.game_dir.glob(pattern),
            config.extracted_dir.glob(pattern),
        ):
            if not path.is_file():
                continue

            typer.echo(path.absolute().as_posix())
