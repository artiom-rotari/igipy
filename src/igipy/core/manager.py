from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, PlainSerializer

PosixPath = Annotated[Path, PlainSerializer(lambda value: value.as_posix(), return_type=str, when_used="json")]


class BaseManager(BaseModel):
    pass
