from pathlib import Path

from igipy.core.services.collect import collect as collect_resources

RAW_EXTENSIONS: set[str] = {
    ".qvm",
    ".dat",
    ".mtp",
    ".res",
    ".avi",
    ".fnt",
    ".wav",
    ".bit",
    ".cmd",
    ".ctr",
    ".hmp",
    ".lmp",
    ".tex",
    ".iff",
}

RAW_ROOT_EXTENSIONS: set[str] = {".qvm"}

RES_FILE_PATTERNS: dict[str, str] = {
    "common/sounds/sounds.res": "",
    "common/sprites/sprites.res": "",
    "common/textures/common.res": "",
    "common/textures/textures.res": "",
    "computer/computer.res": "",
    "menusystem/sound/sounds.res": "",
    "menusystem/ingamemenu.res": "",
    "menusystem/loadingscreen.res": "",
    "menusystem/menusystem.res": "",
    "menusystem/missionsprites.res": "",
    "missions/location0/common/models/location0.res": "missions/location0/common/",
    "missions/location0/common/textures/location0.res": "missions/location0/common/",
    "missions/location0/*/lightmaps/lightmaps.res": "",
    "missions/location0/*/models/*.res": "missions/location0/*/",
    "missions/location0/*/textures/*.res": "missions/location0/*/",
    "screens/game/status/status.res": "",
}

RES_TEXT_PATTERNS: dict[str, str] = {
    "language/*/computer.res": "language/*/",
    "language/*/menusystem.res": "language/*/",
    "language/*/messages.res": "language/*/",
    "language/*/missions.res": "language/*/",
    "language/*/movies.res": "language/*/",
    "language/*/objectives.res": "language/*/",
    "menusystem/english.res": "menusystem/",
}


def collect(game_dir: Path, output_path: Path, collect_is_zip: bool, dry: bool = False) -> None:
    collect_resources(
        game_dir=game_dir,
        output_path=output_path,
        collect_is_zip=collect_is_zip,
        raw_extensions=RAW_EXTENSIONS,
        raw_root_extensions=RAW_ROOT_EXTENSIONS,
        res_file_patterns=RES_FILE_PATTERNS,
        res_text_patterns=RES_TEXT_PATTERNS,
        dry=dry,
    )
