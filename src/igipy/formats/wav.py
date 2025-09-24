import subprocess
import wave
from io import BytesIO
from itertools import chain
from pathlib import Path
from struct import Struct
from typing import ClassVar, Literal, Self

import typer
from pydantic import NonNegativeInt

from igipy.config import GameConfig
from igipy.formats import base, qsc
from igipy.formats.utils import adpcm


class WAVHeader(base.StructModel):
    struct: ClassVar[Struct] = Struct("4s4H2I")

    signature: Literal[b"ILSF"]
    sound_pack: Literal[0, 1, 2, 3]
    sample_width: Literal[16]
    channels: Literal[1, 2]
    unknown: NonNegativeInt
    framerate: Literal[11025, 22050, 44100]
    sample_count: NonNegativeInt


class WAV(base.FileModel):
    header: WAVHeader
    content: bytes

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        header = WAVHeader.model_validate_stream(stream)
        content = stream.read()
        return cls(header=header, content=content)

    @property
    def samples(self) -> bytes:
        if self.header.sound_pack in {0, 1}:
            return self.content
        if self.header.sound_pack in {2, 3}:
            return adpcm.decode(self.content, channels=self.header.channels)

        raise ValueError(f"Unsupported sound pack: {self.header.sound_pack}")

    def to_wav_stream(self) -> BytesIO:
        stream = BytesIO()
        samples = self.samples

        with wave.open(stream, "w") as wave_stream:
            wave_stream.setnchannels(self.header.channels)
            wave_stream.setsampwidth(self.header.sample_width // 8)
            wave_stream.setframerate(self.header.framerate)
            wave_stream.writeframesraw(samples)

        return stream

    def to_wav_file(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.to_wav_stream().getvalue())

    @classmethod
    def cli_decode_all(cls, config: GameConfig, patterns: list[str] | None = None, **kwargs) -> None:
        patterns = patterns or ["**/*.wav"]

        encode_qsc_model = qsc.QSC(content=qsc.BlockStatement(statements=[]))

        for pattern in patterns:
            for src_path, src_dir, decoded_dir, encoded_dir in chain(
                (
                    (src_path, config.game_dir, config.decoded_dir, config.build_dir)
                    for src_path in config.game_dir.glob(pattern)
                    if src_path.is_file(follow_symlinks=False)
                ),
                (
                    (src_path, config.extracted_dir, config.decoded_dir, config.extracted_dir)
                    for src_path in config.extracted_dir.glob(pattern)
                    if src_path.is_file(follow_symlinks=False)
                ),
            ):
                decoded_path = decoded_dir / src_path.relative_to(src_dir)
                encoded_path = encoded_dir / src_path.relative_to(src_dir)

                wav_model = cls.model_validate_file(src_path)

                wav_model.to_wav_file(decoded_path)
                typer.secho(f"Created: {decoded_path.as_posix()}", fg=typer.colors.GREEN)

                encode_qsc_model.content.statements.append(
                    qsc.ExprStatement(
                        expression=qsc.Call(
                            function="ConvertSoundFile",
                            arguments=[
                                qsc.Literal(value=decoded_path.relative_to(config.work_dir).as_posix()),
                                qsc.Literal(value=encoded_path.relative_to(config.work_dir).as_posix()),
                                qsc.Literal(value=wav_model.header.sound_pack),
                            ],
                        )
                    )
                )

        encode_qsc_path = cls.get_encode_qsc_path(config)
        encode_qsc_model.to_file(encode_qsc_path)
        typer.secho(f"QSC script saved: {encode_qsc_path.as_posix()}", fg=typer.colors.YELLOW)

    # noinspection DuplicatedCode
    @classmethod
    def cli_encode_all(cls, config: GameConfig, **kwargs: dict) -> None:  # noqa: ARG003
        encode_qsc_path = cls.get_encode_qsc_path(config)

        if not encode_qsc_path.is_file(follow_symlinks=False):
            typer.secho(f"File not found: {encode_qsc_path.as_posix()}", fg=typer.colors.RED)

        subprocess.run(
            [config.gconv.absolute().as_posix(), encode_qsc_path.relative_to(config.work_dir).as_posix()],
            cwd=config.work_dir.absolute().as_posix(),
            check=False,
        )

    @classmethod
    def get_encode_qsc_path(cls, config: GameConfig) -> Path:
        return config.scripts_dir / "encode-all-wav.qsc"
