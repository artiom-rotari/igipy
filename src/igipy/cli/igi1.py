import subprocess

import typer

from igipy import formats

igi1_app = typer.Typer(add_completion=False)


@igi1_app.callback(invoke_without_command=True)
def igi1_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


@igi1_app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    short_help="Run gconv.exe",
)
def gconv(ctx: typer.Context):
    executable = ctx.obj.igi1.gconv.absolute().as_posix()
    arguments = ctx.args or ["-help"]
    subprocess.run([executable] + arguments, check=True)


@igi1_app.command(short_help="Decode all .res files found in {game_dir}")
def decode_all_res(
    ctx: typer.Context,
    patterns: list[str] = typer.Option(default=["*.res"], help="List of items (space-separated)"),
) -> None:
    formats.RES.cli_decode_all(config=ctx.obj.igi1, patterns=patterns)


@igi1_app.command(short_help="Decode all .wav files found in {game_dir} and {work_dir}/extracted")
def decode_all_wav(
    ctx: typer.Context,
    patterns: list[str] = typer.Option(default=["*.wav"], help="List of items (space-separated)"),
) -> None:
    formats.WAV.cli_decode_all(config=ctx.obj.igi1, patterns=patterns)


@igi1_app.command(short_help="Decode all .qvm files found in {game_dir}")
def decode_all_qvm(
    ctx: typer.Context,
    patterns: list[str] = typer.Option(default=["*.qvm"], help="List of items (space-separated)"),
) -> None:
    formats.QVM.cli_decode_all(config=ctx.obj.igi1, patterns=patterns)


@igi1_app.command(short_help="Execute script {work_dir}/scripts/encode-all-res.qsc")
def encode_all_res(ctx: typer.Context) -> None:
    formats.RES.cli_encode_all(config=ctx.obj.igi1)


@igi1_app.command(short_help="Execute script {work_dir}/scripts/encode-all-wav.qsc")
def encode_all_wav(ctx: typer.Context) -> None:
    formats.WAV.cli_encode_all(config=ctx.obj.igi1)


@igi1_app.command(short_help="Execute script {work_dir}/scripts/encode-all-qvm.qsc")
def encode_all_qvm(ctx: typer.Context) -> None:
    formats.QVM.cli_encode_all(config=ctx.obj.igi1)
