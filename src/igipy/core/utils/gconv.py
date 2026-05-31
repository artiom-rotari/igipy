import subprocess
from pathlib import Path

import typer


def gconv(ctx: typer.Context) -> None:
    # core/utils/gconv.py is two levels under the package root, so parents[2] resolves to
    # src/igipy where the bundled bin/gconv.exe lives.
    executable = Path(__file__).parents[2].joinpath("bin/gconv.exe").as_posix()
    arguments = ctx.args or ["--help"]
    command = [executable, *arguments]
    subprocess.run(command, check=True)  # noqa: S603
