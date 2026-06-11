from pathlib import Path
from typing import ClassVar, Self

from pydantic import BaseModel, Field

from igipy.igi1.manager import IGI1Manager
from igipy.igi2.manager import IGI2Manager
from igipy.igix.manager import IGIxManager


class Config(BaseModel):
    path: ClassVar[Path] = Path("igipy.json")
    igi1: IGI1Manager = Field(default_factory=IGI1Manager)
    igi2: IGI2Manager = Field(default_factory=IGI2Manager)
    igix: IGIxManager = Field(default_factory=IGIxManager)

    @classmethod
    def model_validate_file(cls) -> Self:
        if not cls.path.exists():
            cls.path.parent.mkdir(parents=True, exist_ok=True)
            cls.path.write_text(cls.model_construct().model_dump_json(indent=2))

        if not cls.path.is_file(follow_symlinks=False):
            raise FileNotFoundError(f"{cls.path.as_posix()} isn't a file")

        return cls.model_validate_json(cls.path.read_text())
