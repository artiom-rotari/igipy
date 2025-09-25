from pathlib import Path
from typing import Annotated, Self

from pydantic import BaseModel, Field, PlainSerializer

JsonPrettyPath = Annotated[Path, PlainSerializer(lambda value: value.as_posix(), return_type=str, when_used="json")]


class GameConfig(BaseModel):
    game_dir: JsonPrettyPath
    work_dir: JsonPrettyPath

    @property
    def gconv(self) -> Path:
        return Path(__file__).parent / "bin" / "gconv.exe"

    @property
    def scripts_dir(self) -> Path:
        return self.work_dir / "scripts"

    @property
    def build_dir(self) -> Path:
        return self.work_dir / "build"

    @property
    def decoded_dir(self):
        return self.work_dir / "decoded"

    @property
    def extracted_dir(self):
        return self.work_dir / "extracted"


class IGI1Config(GameConfig):
    game_dir: JsonPrettyPath = Path("C:/Games/ProjectIGI")
    work_dir: JsonPrettyPath = Path.cwd() / "igi1"


class IGI2Config(GameConfig):
    game_dir: JsonPrettyPath = Path("C:/Program Files (x86)/GOG Galaxy/Games/IGI 2 - Covert Strike")
    work_dir: JsonPrettyPath = Path.cwd() / "igi2"


class Config(BaseModel):
    debug: bool = False
    igi1: IGI1Config = Field(default_factory=IGI1Config)
    igi2: IGI2Config = Field(default_factory=IGI2Config)

    @classmethod
    def model_validate_file(cls, path: Path = None) -> Self:
        path = path or Path("igipy.json")

        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(cls.model_construct().model_dump_json(indent=2))

        if not path.is_file(follow_symlinks=False):
            raise FileNotFoundError(f"{path.as_posix()} isn't a file")

        return cls.model_validate_json(path.read_text())
