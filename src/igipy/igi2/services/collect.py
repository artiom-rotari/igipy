from pathlib import Path

from igipy.core.services.collect import collect as collect_resources

RAW_EXTENSIONS: set[str] = {
    ".qvm",
    ".dat",
    ".mtp",
    ".bmp",
    ".jpg",
    ".tga",
    ".mp3",
    ".wav",
    ".fnt",
    ".thm",
    ".tmm",
    ".tlm",
    ".syn",
    ".iff",
}

RAW_ROOT_EXTENSIONS: set[str] = {".qvm"}

RES_FILE_PATTERNS: dict[str, str] = {
    "common/fonts/fonts_*.res": "",
    "common/models/common.res": "common/",
    "common/models/new.res": "common/",
    "common/sounds/*/sounds.res": "",
    "common/sounds/sounds.res": "",
    "common/sprites/sprites.res": "",
    "common/textures/common.res": "common/",
    "common/textures/new.res": "common/",
    "common/textures/textures.res": "",
    "computer/computer.res": "",
    "menusystem/ingamemenu.res": "",
    "menusystem/loadingscreen.res": "",
    "menusystem/menusystem.res": "",
    "menusystem/missionsprites.res": "",
    "menusystem/models/menusystem.res": "",
    "menusystem/sound/sounds.res": "",
    "menusystem/textures/menusystem.res": "",
    "screens/game/status/status.res": "",
    "weapons/weapons.res": "",
    "missions/location2/level2/envmaps/water_3970.res": "missions/location2/level2/envmaps/",
    "missions/multiplayer/jungle/envmaps/water_4000.res": "missions/multiplayer/jungle/envmaps/",
    "missions/multiplayer/sandstorm/envmaps/water_3716.res": "missions/multiplayer/sandstorm/envmaps/",
    "missions/location3/level1/lightmaps/lightmaps.res": "",
    "missions/*/*/models/*.res": "missions/*/*/",
    "missions/*/*/textures/*.res": "missions/*/*/",
    "missions/*/*/envmaps/water_*.res": "",
    "missions/*/*/lightmaps/lightmaps.res": "missions/*/*/",
    "missions/*/*/heightmaps/heightmaps.res": "missions/*/*/heightmaps/",
    "missions/*/*/sounds/sounds.res": "",
    "missions/*/*/sounds/*/sounds.res": "",
}

RES_TEXT_PATTERNS: dict[str, str] = {
    "language/*/menusystem.res": "language/*/",
    "language/*/messages.res": "language/*/",
    "language/*/missions.res": "language/*/",
    "language/*/computer.res": "language/*/",
    "language/*/objectives.res": "language/*/",
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
