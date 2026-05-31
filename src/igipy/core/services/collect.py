import json
from fnmatch import fnmatch
from io import BytesIO
from pathlib import Path, PurePosixPath

import typer

from igipy.core.base import FileIgnored
from igipy.core.formats.res import RES
from igipy.core.utils.archive import ArchiveWriter


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
    writer: ArchiveWriter,
    seen_paths: set[str],
    archive_path: str,
    data: bytes,
    collision_path: str,
) -> bool:
    if archive_path in seen_paths:
        writer.write(collision_path, data)
        return True

    seen_paths.add(archive_path)
    writer.write(archive_path, data)
    return False


def _match_pattern(resource_key: str, patterns: dict[str, str]) -> str | None:
    for pattern_key, pattern_value in patterns.items():
        if fnmatch(resource_key, pattern_key):
            return pattern_value
    return None


def _collect_raw(
    game_dir: Path,
    writer: ArchiveWriter,
    seen_paths: set[str],
    raw_extensions: set[str],
    raw_root_extensions: set[str],
) -> tuple[int, int]:
    typer.secho("\n=== Phase A: Copy non-resource files ===", fg="green")

    copied = 0
    collisions = 0

    for item in sorted(game_dir.rglob("*")):
        if not item.is_file():
            continue

        relative_parts = item.relative_to(game_dir).parts
        suffix = item.suffix.lower()
        if suffix == ".res":
            continue
        if suffix not in raw_extensions:
            continue
        if len(relative_parts) == 1 and suffix not in raw_root_extensions:
            continue

        relative_path = item.relative_to(game_dir)
        parts = relative_path.parts
        lowered_parents = [p.lower() for p in parts[:-1]]
        archive_path = PurePosixPath(*lowered_parents, parts[-1]).as_posix() if lowered_parents else parts[-1]

        copied += 1
        collision_path = f"_collision/copy/{archive_path}"
        collision = _write_entry(writer, seen_paths, archive_path, item.read_bytes(), collision_path)
        source = typer.style(relative_path.as_posix(), fg="green")
        if collision:
            collisions += 1
            typer.echo(f'Collision [{copied:>05}]: "{source}" -> "{typer.style(collision_path, fg="magenta")}"')
        else:
            typer.echo(f'Copy [{copied:>05}]: "{source}" -> "{typer.style(archive_path, fg="yellow")}"')

    typer.secho(f"Phase A: {copied} files copied, {collisions} collisions.", fg="green")
    return copied, collisions


def _collect_res_file(
    game_dir: Path,
    writer: ArchiveWriter,
    seen_paths: set[str],
    res_file_patterns: dict[str, str],
) -> tuple[int, int]:
    typer.secho("\n=== Phase B: Export .res archives ===", fg="green")

    exported = 0
    collisions = 0

    for resource_file in sorted(game_dir.rglob("*.res")):
        resource_path = PurePosixPath(*resource_file.relative_to(game_dir).parts)
        resource_key = resource_path.as_posix().lower()

        matched_value = _match_pattern(resource_key, res_file_patterns)
        if matched_value is None:
            continue

        try:
            resource = RES.model_validate_stream(BytesIO(resource_file.read_bytes()))
        except (ValueError, FileIgnored):
            continue

        if not resource.content_pairs or resource.content_pairs[0][1].header.fourcc != b"BODY":
            continue

        merge_prefix = _resolve_merge_prefix(resource_key, matched_value, res_file_patterns)

        for chunk_name, chunk_body in resource.content_pairs:
            entry_name = chunk_name.get_cleaned_content().removeprefix("LOCAL:")
            entry_path = PurePosixPath(entry_name.replace("\\", "/"))
            destination_path = entry_path if str(merge_prefix) == "." else merge_prefix / entry_path
            archive_path = destination_path.as_posix().lower()

            exported += 1
            collision_path = PurePosixPath("_collision", resource_key, *entry_path.parts).as_posix().lower()
            collision = _write_entry(writer, seen_paths, archive_path, chunk_body.content, collision_path)
            source = typer.style(resource_path.as_posix(), fg="red")
            entry = typer.style(entry_name, fg="green")
            if collision:
                collisions += 1
                destination = typer.style(collision_path, fg="magenta")
                typer.echo(f'Collision [{exported:>05}]: "{source}" "{entry}" -> "{destination}"')
            else:
                destination = typer.style(archive_path, fg="yellow")
                typer.echo(f'Export [{exported:>05}]: "{source}" "{entry}" -> "{destination}"')

    typer.secho(f"Phase B: {exported} files exported, {collisions} collisions.", fg="green")
    return exported, collisions


def _collect_res_text(
    game_dir: Path,
    writer: ArchiveWriter,
    seen_paths: set[str],
    res_text_patterns: dict[str, str],
) -> tuple[int, int]:
    typer.secho("\n=== Phase C: Export language .res to JSON ===", fg="green")

    language_exported = 0
    collisions = 0

    for resource_file in sorted(game_dir.rglob("*.res")):
        resource_path = PurePosixPath(*resource_file.relative_to(game_dir).parts)
        resource_key = resource_path.as_posix().lower()

        matched_value = _match_pattern(resource_key, res_text_patterns)
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

        merge_prefix = _resolve_merge_prefix(resource_key, matched_value, res_text_patterns)
        json_filename = PurePosixPath(resource_path.name).with_suffix(".json")

        if str(merge_prefix) == ".":
            archive_path = json_filename.as_posix().lower()
        else:
            archive_path = (merge_prefix / json_filename).as_posix().lower()

        language_exported += 1
        collision_path = PurePosixPath("_collision", resource_key, json_filename).as_posix().lower()
        collision = _write_entry(writer, seen_paths, archive_path, json_bytes, collision_path)
        source = typer.style(resource_path.as_posix(), fg="red")
        if collision:
            collisions += 1
            destination = typer.style(collision_path, fg="magenta")
            typer.echo(f'Collision [{language_exported:>05}]: "{source}" -> "{destination}"')
        else:
            destination = typer.style(archive_path, fg="yellow")
            typer.echo(f'Language [{language_exported:>05}]: "{source}" -> "{destination}"')

    typer.secho(f"Phase C: {language_exported} language files exported, {collisions} collisions.", fg="green")
    return language_exported, collisions


def collect(  # noqa: PLR0913
    game_dir: Path,
    output_path: Path,
    collect_is_zip: bool,
    raw_extensions: set[str],
    raw_root_extensions: set[str],
    res_file_patterns: dict[str, str],
    res_text_patterns: dict[str, str],
    dry: bool = False,
) -> None:
    if dry:
        typer.secho("DRY RUN — no files will be written.", fg="yellow")

    typer.secho(f"Game directory: {game_dir}", fg="cyan")
    typer.secho(f"Output: {output_path} ({'zip' if collect_is_zip else 'directory'})", fg="cyan")

    seen_paths: set[str] = set()

    with ArchiveWriter(output_path, collect_is_zip, dry=dry, overwrite=True) as writer:
        copied, copy_collisions = _collect_raw(game_dir, writer, seen_paths, raw_extensions, raw_root_extensions)
        exported, export_collisions = _collect_res_file(game_dir, writer, seen_paths, res_file_patterns)
        language_exported, language_collisions = _collect_res_text(game_dir, writer, seen_paths, res_text_patterns)

    total = copied + exported + language_exported
    total_collisions = copy_collisions + export_collisions + language_collisions
    dry_suffix = " (dry run)" if dry else ""
    typer.secho(
        f"\nTotal: {total} files, {total_collisions} collisions{dry_suffix}.",
        fg="green",
        bold=True,
    )

    if not dry:
        typer.secho(f"Output: {output_path}", fg="green")
