import string
import subprocess
import zipfile
from collections import defaultdict
from pathlib import Path

import typer

from igipy.formats import qsc

dev_app = typer.Typer(add_completion=False)


@dev_app.command(
    name="printable",
    short_help="Search printable series in binary files",
    hidden=True,
)
def printable(src: Path, min_length: int = 5, charset: str = string.printable) -> None:
    data = src.read_bytes()
    word = bytearray()

    charset = charset.encode()

    for byte in data:
        if byte in charset:
            word.append(byte)
        else:
            if len(word) >= min_length:
                typer.echo(word.decode())
            word.clear()


@dev_app.command(
    name="extensions",
    short_help="Group files in source_dir and unpack_dir by extension and show counts",
    hidden=True,
)
def igi1_extensions(ctx: typer.Context) -> None:
    counter = defaultdict(lambda: {"source": 0, "unpack": 0})

    for path in ctx.obj.igi1.game_dir.glob("**/*"):
        if not path.is_file():
            continue

        if path.suffix != ".dat":
            format_name = f"`{path.suffix}`"
        elif path.with_suffix(".mtp").exists():
            format_name = "`.dat` (mtp)"
        else:
            format_name = "`.dat` (graph)"

        counter[format_name]["source"] += 1

    for path in ctx.obj.igi1.unpack_dir.glob("**/*.zip"):
        with zipfile.ZipFile(path, "r") as zip_file:
            for file_info in zip_file.infolist():
                format_name = f"`{Path(file_info.filename).suffix}`"
                counter[format_name]["unpack"] += 1

    results: list[tuple[str, int, int, int]] = [
        (extension, counts["source"] + counts["unpack"], counts["source"], counts["unpack"])
        for extension, counts in sorted(
            counter.items(), key=lambda item: item[1]["source"] + item[1]["unpack"], reverse=True
        )
    ]

    typer.echo(
        f"| {'Extension':<15} | {'Total':<15} | {'Source':<15} | {'Unpack':<15} |\n"
        f"|-{'-' * 15}-|-{'-' * 15}-|-{'-' * 15}-|-{'-' * 15}-|"
    )

    for extension, total, source, unpack in results:
        typer.echo(f"| {extension:<15} | {total:<15} | {source:<15} | {unpack:<15} |")


@dev_app.command(hidden=True)
def compare(ctx: typer.Context, pattern: str = "invalid-pattern") -> None:
    for initial_path in ctx.obj.igi1.game_dir.glob(pattern):
        encoded_path = ctx.obj.igi1.build_dir / initial_path.relative_to(ctx.obj.igi1.game_dir)

        if not encoded_path.is_file():
            typer.secho(f"Initial: {initial_path.absolute().as_posix()}", fg="green")
            typer.secho(f"Encoded: doesn't exists {encoded_path.absolute().as_posix()}", fg="yellow")
            continue

        initial_data = initial_path.read_bytes()
        encoded_data = encoded_path.read_bytes()

        if initial_data != encoded_data:
            typer.secho(f"Initial: {initial_path.absolute().as_posix()}", fg="green")
            typer.secho(f"Encoded: doesn't match {encoded_path.absolute().as_posix()}", fg="red")
        else:
            typer.secho(f"Initial: {initial_path.absolute().as_posix()}", fg="green")
            typer.secho(f"Encoded: matches {encoded_path.absolute().as_posix()}", fg="green")


@dev_app.command(hidden=True)
def dump_resources(ctx: typer.Context):
    for encoded_path in ctx.obj.igi1.game_dir.glob("**/*.res"):
        qsc_model = qsc.QSC(
            content=qsc.BlockStatement(
                statements=[
                    qsc.ExprStatement(
                        expression=qsc.Call(
                            function="DumpResource",
                            arguments=[
                                qsc.Literal(value=encoded_path.absolute().as_posix()),
                            ],
                        ),
                    ),
                ]
            )
        )

        qsc_path = ctx.obj.igi1.work_dir / "script.qsc"
        qsc_model.to_file(qsc_path)

        result = subprocess.run(
            args=[ctx.obj.igi1.gconv_path.absolute().as_posix(), qsc_path.absolute().as_posix()],
            cwd=encoded_path.parent.absolute().as_posix(),
            stdout=subprocess.PIPE,
            check=False,
        )

        stdout_lines = result.stdout.decode("latin1").splitlines()

        print(stdout_lines[2], stdout_lines[-5])
