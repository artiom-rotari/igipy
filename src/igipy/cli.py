import typer
from pydantic import ValidationError

from . import __version__
from .config import Config
from .core.tools.dev import dev_app
from .core.tools.gconv import gconv
from .core.tools.printable import printable
from .igi1.app import igi1_app
from .igi2.app import igi2_app

app = typer.Typer(add_completion=False)
app.add_typer(igi1_app, name="igi1", short_help="Convertors for IGI 1 game")
app.add_typer(igi2_app, name="igi2", short_help="Convertors for IGI 2 game")
app.add_typer(dev_app, name="dev", short_help="Developer utilities")
app.command(name="printable", short_help="Search printable series in binary files", hidden=True)(printable)
app.command(
    name="gconv",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    short_help="Run gconv.exe",
    hidden=True,
)(gconv)


@app.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
    version: bool = typer.Option(None, "--version", is_eager=True, help="Show version."),
) -> None:
    if version:
        typer.echo(f"Version: {typer.style(__version__, fg='green')}")
        raise typer.Exit(0)

    try:
        Config.model_validate_file()
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
