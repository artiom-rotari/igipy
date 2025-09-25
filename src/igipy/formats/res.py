import subprocess
from io import BytesIO
from pathlib import Path
from typing import ClassVar, Literal, Self

import typer
from pydantic import Field

from igipy.config import GameConfig
from igipy.formats import ilff, qsc

ENCODING = "latin1"


class NAMEChunk(ilff.RawChunk):
    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"NAME")

    def get_cleaned_content(self) -> str:
        return self.content.removesuffix(b"\x00").decode(ENCODING)


class BODYChunk(ilff.RawChunk):
    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"BODY")


class CSTRChunk(ilff.RawChunk):
    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"CSTR")

    def get_cleaned_content(self) -> str:
        content = self.content.removesuffix(b"\x00").decode(ENCODING)
        content = content.replace("\\", r"\\")
        content = content.replace(r'"', r"\"")
        content = "".join(character if ord(character) < 128 else f"\\x{ord(character):02X}" for character in content)
        return content  # noqa: RET504


class PATHChunk(ilff.RawChunk):
    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"PATH")

    def get_cleaned_content(self) -> str:
        return self.content.removesuffix(b"\x00").decode(ENCODING)


class RES(ilff.ILFF):
    chunk_mapping: ClassVar[dict[bytes, type[ilff.Chunk]]] = {
        b"NAME": NAMEChunk,
        b"BODY": BODYChunk,
        b"CSTR": CSTRChunk,
        b"PATH": PATHChunk,
    }

    content_type: Literal[b"IRES"] = Field(description="Content type")
    content_pairs: list[tuple[NAMEChunk, BODYChunk | CSTRChunk]]
    content_paths: tuple[NAMEChunk, PATHChunk] | None = None

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        header, content_type, chunks = super().model_validate_chunks(stream)

        if content_type != b"IRES":
            raise ValueError(f"Unknown content type: {content_type}")

        content_pairs = list(zip(chunks[::2], chunks[1::2], strict=True))
        content_paths = (
            content_pairs.pop(-1) if content_pairs and content_pairs[-1][1].header.fourcc == b"PATH" else None
        )

        # noinspection PyTypeChecker
        return cls(
            header=header,
            content_type=content_type,
            content_pairs=content_pairs,
            content_paths=content_paths,
        )

    @classmethod
    def cli_decode_all(cls, config: GameConfig, patterns: list[str] | None = None, **kwargs) -> None:
        patterns = patterns or ["**/*.res"]

        encode_qsc_model = qsc.QSC(content=qsc.BlockStatement(statements=[]))

        for pattern in patterns:
            for res_path in config.game_dir.glob(pattern):
                dir_path = config.extracted_dir / res_path.relative_to(config.game_dir)
                dir_path.mkdir(parents=True, exist_ok=True)
                dst_path = config.build_dir / res_path.relative_to(config.game_dir)

                typer.secho(f"Extracting: {res_path.as_posix()}", fg=typer.colors.YELLOW)
                res_model = cls.model_validate_file(res_path)

                encode_qsc_model.content.statements.append(
                    qsc.ExprStatement(
                        expression=qsc.Call(
                            function="BeginResource",
                            arguments=[
                                qsc.Literal(value=dst_path.relative_to(config.work_dir).as_posix()),
                            ],
                        ),
                    ),
                )

                for chunk_a, chunk_b in res_model.content_pairs:
                    if isinstance(chunk_b, CSTRChunk):
                        encode_qsc_model.content.statements.append(
                            qsc.ExprStatement(
                                expression=qsc.Call(
                                    function="AddStringResource",
                                    arguments=[
                                        qsc.Literal(value=chunk_a.get_cleaned_content()),
                                        qsc.Literal(value=chunk_b.get_cleaned_content()),
                                    ],
                                ),
                            ),
                        )

                        continue

                    if isinstance(chunk_b, BODYChunk):
                        content_path = dir_path.joinpath(chunk_a.get_cleaned_content().removeprefix("LOCAL:"))
                        content_path.parent.mkdir(parents=True, exist_ok=True)
                        content_path.write_bytes(chunk_b.content)

                        typer.secho(f"Extracted: {content_path.as_posix()}", fg=typer.colors.GREEN)

                        encode_qsc_model.content.statements.append(
                            qsc.ExprStatement(
                                expression=qsc.Call(
                                    function="AddResource",
                                    arguments=[
                                        qsc.Literal(value=content_path.relative_to(config.work_dir).as_posix()),
                                        qsc.Literal(value=chunk_a.get_cleaned_content()),
                                        qsc.Literal(value=chunk_b.header.alignment),
                                    ],
                                ),
                            ),
                        )

                        continue

                if res_model.content_paths:
                    encode_qsc_model.content.statements.append(
                        qsc.ExprStatement(
                            expression=qsc.Call(
                                function="AddDirectoryResource",
                                arguments=[
                                    qsc.Literal(value=res_model.content_paths[0].get_cleaned_content()),
                                ],
                            ),
                        )
                    )

                encode_qsc_model.content.statements.append(
                    qsc.ExprStatement(
                        expression=qsc.Call(
                            function="EndResource",
                            arguments=[],
                        ),
                    ),
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
        return config.scripts_dir / "encode-all-res.qsc"
