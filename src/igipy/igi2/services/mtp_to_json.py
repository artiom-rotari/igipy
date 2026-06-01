"""Export an IGI 2 ``.mtp`` material/texture table to JSON.

The binary ``.mtp`` (FORM container) holds the level-scoped model -> texture table that binds each
MEF render group to a texture (the MEF binary stores no texture filenames). This converter parses
the binary table directly (``MODS`` model names + ``TEXF`` texture names joined through the decoded
``INST`` records) and emits a clean, purpose-shaped JSON document.

The whole ``MTP`` model is **not** dumped verbatim: it would expose chunk headers and raw bytes that
do not serialise meaningfully. Texture names are kept exactly as stored in ``TEXF`` (including any
``_argb8888`` pixel-format suffix and the occasional trailing-space padding), so the JSON is a
faithful reference for the binary table. See ``docs/igi2/formats/dat_mtp.md``.
"""

import json
from io import BytesIO
from pathlib import Path

from igipy.igi2.formats.mtp import MTP


def mtp_to_json(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:
    target_io: BytesIO = BytesIO()
    target_path: Path | None = source_path.with_suffix(".json") if source_path is not None else None

    instance = MTP.model_validate_stream(source_io)

    document = {
        "model_count": instance.mods.count,
        "texture_count": instance.texf.count,
        "variants": instance.vnam.names,
        "model_textures": instance.model_texture_table(),
    }

    target_io.write(json.dumps(document, indent=2).encode("utf-8"))
    target_io.seek(0)
    return target_io, target_path
