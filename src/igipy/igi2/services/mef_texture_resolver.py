"""Resolve a MEF model's per-render-group diffuse textures through the level material table.

The MEF binary does not store texture filenames. Texture binding is external and
**level-scoped**: every level / location / "common" directory holds a material/texture
table that exists in two equivalent forms — the binary "<level>.mtp" and a machine-generated
text sibling "<level>.dat". The ".dat" is a plain-text table::

    398                       <- model count
    <model_name>
    <texture_count>
    <texture_name> x texture_count
    ...

Each MEF render group carries a "group_index" that selects an entry in its model's texture
list::

    texture_name = dat_textures[model_name][ render_group.group_index ]

This was verified against the reverse-engineered text ".MEF" sources: "group_index" is a
valid index into the ".dat" list for 7485 / 7497 models (99 %), and the ".dat" list matches
the text-source diffuse textures (in material order). The ".dat" is preferred over the binary
".mtp" "INST" chunk because it is clean text (the "INST" packing is drift-prone).

Models that do not resolve ("group_index" out of range, model absent from the table, missing
".dat", or missing a texture file) fall back to no texture for that render group.

See "docs/igi2/formats/mef.md" (DNER render groups) and "docs/igi2/formats/dat_mtp.md".
"""

import logging
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from io import BytesIO
from pathlib import Path, PurePosixPath

import numpy as np

from igipy.core.formats.tex import TEX
from igipy.igi1.services.tex_to_tga import tex_to_tga
from igipy.igi2.formats.mef import MEF

logger = logging.getLogger(__name__)

# Texture names sometimes carry a pixel-format suffix (e.g. "407_03_1_argb8888"). The display
# name strips it; the on-disk file may keep it ("glass_argb8888.tex") or not ("407_12_1.tex").
PIXEL_FORMAT_SUFFIXES = ("_argb8888", "_argb1555", "_argb4444")

# Shared texture directory searched when a texture is not found beside the model's own level.
COMMON_TEXTURES_DIRECTORY = PurePosixPath("common/textures")

TEXTURE_SOURCE_SUFFIX = ".tex"
TEXTURE_OUTPUT_SUFFIX = ".tga"

# TGA header byte offsets used to classify alpha (see "core.formats.tga.TGAHeader").
_TGA_PIXEL_DEPTH_OFFSET = 16
_TGA_IMAGE_DESCRIPTOR_OFFSET = 17
_TGA_PIXEL_DATA_OFFSET = 18
_OPAQUE_ALPHA = 255
_DEPTH_ARGB1555 = 16
_ALPHA_BITS_ARGB1555 = 1
_DEPTH_ARGB8888 = 32
_ALPHA_BITS_ARGB8888 = 8


class TextureTransparency(StrEnum):
    """How a diffuse texture's alpha channel should be rendered.

    Decided from the texture's actual alpha content (not its name), because IGI2 cutout
    textures (fences/foliage/grates) are often 16-bit ARGB1555 with no "_argb*" name suffix.
    See "classify_texture_transparency" and the project material-transparency research notes.
    """

    OPAQUE = "opaque"
    ALPHA_TEST = "alpha_test"  # hard 1-bit cutout (fences, foliage) — usually two-sided in-game
    ALPHA_BLEND = "alpha_blend"  # smooth 8-bit alpha (glass, decals)


@lru_cache(maxsize=512)
def classify_texture_transparency(tex_source_path: str) -> TextureTransparency:
    """Classify a source ".tex" as opaque / alpha-test / alpha-blend from its alpha channel.

    Cached by path because one texture is shared across many render groups and models. Any
    parse/decode failure is treated as opaque (the safe default) and logged at DEBUG.
    """
    try:
        tex = TEX.model_validate_stream(BytesIO(Path(tex_source_path).read_bytes()))
        tga_stream, _ = tex_to_tga(tex)
    except Exception as error:  # noqa: BLE001 — never let a bad texture abort the export
        logger.debug("Texture transparency classification failed for %s: %s", tex_source_path, error)
        return TextureTransparency.OPAQUE

    data = tga_stream.getvalue()
    pixel_depth = data[_TGA_PIXEL_DEPTH_OFFSET]
    alpha_bits = data[_TGA_IMAGE_DESCRIPTOR_OFFSET] & 0x0F
    pixels = data[_TGA_PIXEL_DATA_OFFSET:]

    if pixel_depth == _DEPTH_ARGB1555 and alpha_bits == _ALPHA_BITS_ARGB1555:
        # ARGB1555 little-endian: alpha is the top bit of each 16-bit texel.
        values = np.frombuffer(pixels, dtype="<u2")
        has_cutout = bool((((values >> 15) & 1) == 0).any())
        result = TextureTransparency.ALPHA_TEST if has_cutout else TextureTransparency.OPAQUE
    elif pixel_depth == _DEPTH_ARGB8888 and alpha_bits == _ALPHA_BITS_ARGB8888:
        alpha = np.frombuffer(pixels, dtype=np.uint8).reshape(-1, 4)[:, 3]
        if bool((alpha == _OPAQUE_ALPHA).all()):
            result = TextureTransparency.OPAQUE
        elif set(np.unique(alpha).tolist()) <= {0, _OPAQUE_ALPHA}:
            result = TextureTransparency.ALPHA_TEST  # binary alpha → hard cutout
        else:
            result = TextureTransparency.ALPHA_BLEND  # intermediate alpha → smooth blend
    else:
        result = TextureTransparency.OPAQUE

    logger.debug("Texture %s classified as %s (depth=%d)", tex_source_path, result.value, pixel_depth)
    return result


@dataclass(frozen=True)
class RenderGroupTexture:
    """Diffuse texture resolved for a single render group.

    "texture_name" is the suffix-stripped stem, suitable for naming the FBX material and
    texture nodes. "relative_output_path" is the converted ".tga" path **relative to the
    model's FBX file**, suitable for an FBX "RelativeFilename" (the convert tree mirrors the
    collect tree, so the relative path is identical on both sides). "transparency" is the
    alpha classification of the source texture, used to emit FBX material transparency.
    """

    texture_name: str
    relative_output_path: str
    transparency: TextureTransparency = TextureTransparency.OPAQUE


def _strip_pixel_format_suffix(texture_name: str) -> str:
    for suffix in PIXEL_FORMAT_SUFFIXES:
        if texture_name.endswith(suffix):
            return texture_name[: -len(suffix)]
    return texture_name


def _level_directory(model_source_path: PurePosixPath) -> PurePosixPath:
    """Return the level directory that governs a model.

    Models live in "<level>/models/<name>.mef"; the material table and "textures" directory
    are siblings under "<level>". For "common/models/x.mef" this is "common".
    """
    return model_source_path.parent.parent


def _find_material_table_path(collect_path: Path, level_directory: PurePosixPath) -> Path | None:
    """Locate the level's material/texture ".dat" table (the sibling of its ".mtp").

    The level directory also holds unrelated ".dat" files (forest, graph, graphcover), so the
    table is identified as the ".dat" paired with the level's ".mtp" (same stem).
    """
    level_on_disk = collect_path / level_directory.as_posix()
    if not level_on_disk.is_dir():
        return None
    for mtp_path in sorted(level_on_disk.glob("*.mtp")):
        dat_path = mtp_path.with_suffix(".dat")
        if dat_path.is_file():
            return dat_path
    return None


@lru_cache(maxsize=64)
def _parse_material_table(dat_path_text: str) -> dict[str, tuple[str, ...]]:
    """Parse a machine-generated material ".dat" into "{model_name: (texture_name, ...)}".

    Cached by path because one table serves every model in a level (thousands of lookups).
    """
    lines = [line.strip() for line in Path(dat_path_text).read_text(errors="ignore").splitlines()]
    index = 0
    # Skip the leading comment / blank lines up to the first standalone integer (the model count).
    while index < len(lines) and not lines[index].isdigit():
        index += 1
    index += 1  # skip the model count itself

    table: dict[str, tuple[str, ...]] = {}
    while index < len(lines):
        if lines[index] == "":
            index += 1
            continue
        model_name = lines[index]
        index += 1
        if index >= len(lines) or not lines[index].isdigit():
            break
        texture_count = int(lines[index])
        index += 1
        table[model_name] = tuple(lines[index : index + texture_count])
        index += texture_count
    return table


def _locate_texture(
    collect_path: Path,
    level_directory: PurePosixPath,
    texture_name: str,
) -> tuple[PurePosixPath, str] | None:
    """Locate the texture's ".tex" on disk; return its (directory, on-disk stem) or None.

    The level-local "textures" directory is searched first, then the shared "common" one.
    The table name is probed as-is and suffix-stripped; the matched stem is returned so the
    converted ".tga" path mirrors the actual filename "tex_to_tga" produces.
    """
    stripped = _strip_pixel_format_suffix(texture_name)
    level_textures = level_directory / "textures"
    for candidate_directory in (level_textures, COMMON_TEXTURES_DIRECTORY):
        directory_on_disk = collect_path / candidate_directory.as_posix()
        for stem in (texture_name, stripped):
            if (directory_on_disk / f"{stem}{TEXTURE_SOURCE_SUFFIX}").is_file():
                return candidate_directory, stem
    return None


def _relative_output_path(model_source_path: PurePosixPath, texture_directory: PurePosixPath, texture_stem: str) -> str:
    """Path to the converted ".tga" relative to the model's FBX file (posix, with "..")."""
    from_directory_parts = model_source_path.parent.parts
    to_path_parts = (*texture_directory.parts, f"{texture_stem}{TEXTURE_OUTPUT_SUFFIX}")

    common_length = 0
    for from_part, to_part in zip(from_directory_parts, to_path_parts, strict=False):
        if from_part != to_part:
            break
        common_length += 1

    upward = [".."] * (len(from_directory_parts) - common_length)
    downward = list(to_path_parts[common_length:])
    return PurePosixPath(*upward, *downward).as_posix()


def resolve_render_group_textures(
    mef: MEF,
    model_source_path: Path | PurePosixPath,
    collect_path: Path,
) -> list[RenderGroupTexture | None]:
    """Resolve one diffuse texture per render group, in render-group order.

    Returns a list aligned with "mef.render_groups"; each entry is a
    :class:`RenderGroupTexture` or "None" when no texture could be resolved for that group
    (the caller should then emit an untextured placeholder material for it).
    """
    render_groups = mef.render_groups
    if not render_groups:
        return []

    source_path = PurePosixPath(model_source_path.as_posix())
    fallback: list[RenderGroupTexture | None] = [None] * len(render_groups)

    level_directory = _level_directory(source_path)
    dat_path = _find_material_table_path(collect_path, level_directory)
    if dat_path is None:
        return fallback

    texture_names = _parse_material_table(dat_path.as_posix()).get(source_path.stem)
    if not texture_names:
        return fallback

    return [
        _resolve_single_group(texture_names, render_group.group_index, collect_path, level_directory, source_path)
        for render_group in render_groups
    ]


def _resolve_single_group(
    texture_names: tuple[str, ...],
    group_index: int,
    collect_path: Path,
    level_directory: PurePosixPath,
    model_source_path: PurePosixPath,
) -> RenderGroupTexture | None:
    if not 0 <= group_index < len(texture_names):
        return None

    table_name = texture_names[group_index]
    located = _locate_texture(collect_path, level_directory, table_name)
    if located is None:
        return None

    texture_directory, file_stem = located
    relative_output_path = _relative_output_path(model_source_path, texture_directory, file_stem)
    tex_source_path = collect_path / texture_directory.as_posix() / f"{file_stem}{TEXTURE_SOURCE_SUFFIX}"
    return RenderGroupTexture(
        texture_name=_strip_pixel_format_suffix(table_name),
        relative_output_path=relative_output_path,
        transparency=classify_texture_transparency(tex_source_path.as_posix()),
    )
