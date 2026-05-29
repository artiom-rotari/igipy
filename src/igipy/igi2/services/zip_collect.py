import json
import zipfile
from fnmatch import fnmatch
from io import BytesIO
from pathlib import Path, PurePosixPath

import typer

from igipy.core.base import FileIgnored
from igipy.core.formats.res import RES

GAME_EXTENSIONS: set[str] = {
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

ROOT_EXTENSIONS: set[str] = {".qvm"}

EXPORT_PATTERNS: dict[str, str] = {
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

LANGUAGE_PATTERNS: dict[str, str] = {
    "language/*/menusystem.res": "language/*/",
    "language/*/messages.res": "language/*/",
    "language/*/missions.res": "language/*/",
    "language/*/computer.res": "language/*/",
    "language/*/objectives.res": "language/*/",
}


def _resolve_merge_prefix(
    resource_key: str,
    pattern_value: str,
    patterns: dict[str, str],
) -> PurePosixPath:
    if not pattern_value:
        return PurePosixPath(".")

    wildcard_count = pattern_value.count("*")
    if wildcard_count == 0:
        return PurePosixPath(pattern_value.rstrip("/"))

    resource_parts = PurePosixPath(resource_key).parts

    for pattern_key in patterns:
        if not fnmatch(resource_key, pattern_key):
            continue

        pattern_parts = PurePosixPath(pattern_key).parts
        fills = [
            real_part
            for pattern_part, real_part in zip(pattern_parts, resource_parts, strict=False)
            if pattern_part == "*"
        ]

        result = pattern_value
        for fill in fills:
            result = result.replace("*", fill, 1)

        return PurePosixPath(result.rstrip("/"))

    return PurePosixPath(pattern_value.replace("*", "_").rstrip("/"))


def _write_entry(
    zip_file: zipfile.ZipFile | None,
    seen_paths: set[str],
    archive_path: str,
    data: bytes,
    collision_path: str,
) -> bool:
    if archive_path in seen_paths:
        if zip_file is not None:
            zip_file.writestr(collision_path, data)
        return True

    seen_paths.add(archive_path)
    if zip_file is not None:
        zip_file.writestr(archive_path, data)
    return False


def _match_pattern(resource_key: str, patterns: dict[str, str]) -> str | None:
    for pattern_key, pattern_value in patterns.items():
        if fnmatch(resource_key, pattern_key):
            return pattern_value
    return None


def _copy_non_resource_files(
    game_dir: Path,
    zip_file: zipfile.ZipFile | None,
    seen_paths: set[str],
) -> tuple[int, int]:
    typer.secho("\n=== Phase A: Copy non-resource files ===", fg="green")

    copied = 0
    collisions = 0

    for item in sorted(game_dir.rglob("*")):
        if not item.is_file():
            continue

        relative_parts = item.relative_to(game_dir).parts
        suffix = item.suffix.lower()
        if suffix in {".res", ".mtp"}:
            continue
        if suffix not in GAME_EXTENSIONS:
            continue
        if len(relative_parts) == 1 and suffix not in ROOT_EXTENSIONS:
            continue
        if suffix == ".dat" and item.with_suffix(".mtp").exists():
            continue

        relative_path = item.relative_to(game_dir)
        parts = relative_path.parts
        lowered_parents = [p.lower() for p in parts[:-1]]
        archive_path = PurePosixPath(*lowered_parents, parts[-1]).as_posix() if lowered_parents else parts[-1]

        copied += 1
        collision_path = f"_collision/copy/{archive_path}"
        collision = _write_entry(zip_file, seen_paths, archive_path, item.read_bytes(), collision_path)
        source = typer.style(relative_path.as_posix(), fg="green")
        if collision:
            collisions += 1
            typer.echo(f'Collision [{copied:>05}]: "{source}" -> "{typer.style(collision_path, fg="magenta")}"')
        else:
            typer.echo(f'Copy [{copied:>05}]: "{source}" -> "{typer.style(archive_path, fg="yellow")}"')

    typer.secho(f"Phase A: {copied} files copied, {collisions} collisions.", fg="green")
    return copied, collisions


def _export_res_archives(
    game_dir: Path,
    zip_file: zipfile.ZipFile | None,
    seen_paths: set[str],
) -> tuple[int, int]:
    typer.secho("\n=== Phase B: Export .res archives ===", fg="green")

    exported = 0
    collisions = 0

    for resource_file in sorted(game_dir.rglob("*.res")):
        resource_path = PurePosixPath(*resource_file.relative_to(game_dir).parts)
        resource_key = resource_path.as_posix().lower()

        matched_value = _match_pattern(resource_key, EXPORT_PATTERNS)
        if matched_value is None:
            continue

        try:
            resource = RES.model_validate_stream(BytesIO(resource_file.read_bytes()))
        except (ValueError, FileIgnored):
            continue

        if not resource.content_pairs or resource.content_pairs[0][1].header.fourcc != b"BODY":
            continue

        merge_prefix = _resolve_merge_prefix(resource_key, matched_value, EXPORT_PATTERNS)

        for chunk_name, chunk_body in resource.content_pairs:
            entry_name = chunk_name.get_cleaned_content().removeprefix("LOCAL:")
            entry_path = PurePosixPath(entry_name.replace("\\", "/"))
            destination_path = entry_path if str(merge_prefix) == "." else merge_prefix / entry_path
            archive_path = destination_path.as_posix().lower()

            exported += 1
            collision_path = PurePosixPath("_collision", resource_key, *entry_path.parts).as_posix().lower()
            collision = _write_entry(zip_file, seen_paths, archive_path, chunk_body.content, collision_path)
            source = typer.style(resource_path.as_posix(), fg="red")
            entry = typer.style(entry_name, fg="green")
            if collision:
                collisions += 1
                dest = typer.style(collision_path, fg="magenta")
                typer.echo(f'Collision [{exported:>05}]: "{source}" "{entry}" -> "{dest}"')
            else:
                dest = typer.style(archive_path, fg="yellow")
                typer.echo(f'Export [{exported:>05}]: "{source}" "{entry}" -> "{dest}"')

    typer.secho(f"Phase B: {exported} files exported.", fg="green")
    return exported, collisions


def _export_language_res(
    game_dir: Path,
    zip_file: zipfile.ZipFile | None,
    seen_paths: set[str],
) -> tuple[int, int]:
    typer.secho("\n=== Phase C: Export language .res to JSON ===", fg="green")

    language_exported = 0
    collisions = 0

    for resource_file in sorted(game_dir.rglob("*.res")):
        resource_path = PurePosixPath(*resource_file.relative_to(game_dir).parts)
        resource_key = resource_path.as_posix().lower()

        matched_value = _match_pattern(resource_key, LANGUAGE_PATTERNS)
        if matched_value is None:
            continue

        try:
            resource = RES.model_validate_stream(BytesIO(resource_file.read_bytes()))
        except (ValueError, FileIgnored):
            continue

        if not resource.content_pairs or resource.content_pairs[0][1].header.fourcc != b"CSTR":
            continue

        content = [
            {
                "key": chunk_name.get_cleaned_content().removeprefix("LOCAL:"),
                "value": chunk_cstr.get_cleaned_content(),
            }
            for chunk_name, chunk_cstr in resource.content_pairs
        ]

        json_bytes = json.dumps(content, indent=4, ensure_ascii=False).encode("utf-8")

        merge_prefix = _resolve_merge_prefix(resource_key, matched_value, LANGUAGE_PATTERNS)
        json_filename = PurePosixPath(resource_path.name).with_suffix(".json")

        if str(merge_prefix) == ".":
            archive_path = json_filename.as_posix().lower()
        else:
            archive_path = (merge_prefix / json_filename).as_posix().lower()

        language_exported += 1
        collision_path = PurePosixPath("_collision", resource_key, json_filename).as_posix().lower()
        collision = _write_entry(zip_file, seen_paths, archive_path, json_bytes, collision_path)
        source = typer.style(resource_path.as_posix(), fg="red")
        if collision:
            collisions += 1
            dest = typer.style(collision_path, fg="magenta")
            typer.echo(f'Collision [{language_exported:>05}]: "{source}" -> "{dest}"')
        else:
            dest = typer.style(archive_path, fg="yellow")
            typer.echo(f'Language [{language_exported:>05}]: "{source}" -> "{dest}"')

    typer.secho(f"Phase C: {language_exported} language files exported.", fg="green")
    return language_exported, collisions


def zip_collect(game_dir: Path, output_path: Path, dry: bool = True) -> None:
    seen_paths: set[str] = set()

    if dry:
        typer.secho("DRY RUN — no files will be written.", fg="yellow")

    zip_file = None if dry else zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED)

    try:
        copied, copy_collisions = _copy_non_resource_files(game_dir, zip_file, seen_paths)
        exported, export_collisions = _export_res_archives(game_dir, zip_file, seen_paths)
        language_exported, lang_collisions = _export_language_res(game_dir, zip_file, seen_paths)
    finally:
        if zip_file is not None:
            zip_file.close()

    total = copied + exported + language_exported
    total_collisions = copy_collisions + export_collisions + lang_collisions
    dry_suffix = " (dry run)" if dry else ""
    typer.secho(
        f"\nTotal: {total} files, {total_collisions} collisions{dry_suffix}.",
        fg="green",
    )

    if not dry:
        typer.secho(f"Output: {output_path}", fg="green")
