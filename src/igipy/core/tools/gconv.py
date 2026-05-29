import subprocess
from pathlib import Path

import typer


def gconv(ctx: typer.Context) -> None:
    executable = Path(__file__).parents[2].joinpath("bin/gconv.exe").as_posix()
    arguments = ctx.args or ["--help"]
    command = [executable, *arguments]
    subprocess.run(command, check=True)  # noqa: S603
