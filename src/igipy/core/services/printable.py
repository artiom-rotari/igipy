import string
from pathlib import Path

import typer


def printable(source: Path, min_length: int = 5, charset: str = string.printable) -> None:
    data = source.read_bytes()
    word = bytearray()

    charset_bytes = charset.encode()

    for byte in data:
        if byte in charset_bytes:
            word.append(byte)
        else:
            if len(word) >= min_length:
                typer.echo(word.decode())
            word.clear()
