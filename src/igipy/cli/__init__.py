from pathlib import Path

import typer
from pydantic import ValidationError

from igipy import __version__
from igipy.cli.dev import dev_app
from igipy.cli.igi1 import igi1_app
from igipy.cli.igi2 import igi2_app
from igipy.config import Config

app = typer.Typer(add_completion=False)

app.add_typer(dev_app, name="dev", short_help="Development tools")
app.add_typer(igi1_app, name="igi1", short_help="Convertors for IGI 1 game")
app.add_typer(igi2_app, name="igi2", short_help="Convertors for IGI 2 game")


@app.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
    version: bool = typer.Option(None, "--version", is_eager=True, help="Show version."),
    config: Path = typer.Option("igipy.json", "--config", is_eager=True, help="Path to configuration file."),
) -> None:
    if version:
        typer.echo(f"Version: {typer.style(__version__, fg='green')}")
        raise typer.Exit(0)

    try:
        ctx.obj = Config.model_validate_file(path=config)
    except FileNotFoundError:
        typer.echo(
            f"{typer.style('An error occurred!', fg='yellow')}\n"
            f"This application expects to find a configuration file at "
            f"{typer.style('`./igipy.json`', fg='yellow')}.\n"
            f"But it seems that this location already exists and is not a file.\n"
            f"Please move object somewhere else and then execute `igipy` command again.\n"
        )
        raise typer.Exit(0)  # noqa: B904
    except ValidationError as e:
        typer.echo(
            f"{typer.style('An error occurred!', fg='yellow')}\n"
            f"Configuration file {typer.style('`./igipy.json`', fg='yellow')} exists,"
            f"but it seems that it is not valid.\n"
            f"Open {typer.style('`./igipy.json`', fg='yellow')} using a text editor and fix errors:\n"
        )

        for error in e.errors(include_url=False):
            typer.secho(f"Error at: {'.'.join(error['loc'])}", fg="red")
            typer.secho(error["msg"])

        raise typer.Exit(0)  # noqa: B904

    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


def main() -> None:
    app()
