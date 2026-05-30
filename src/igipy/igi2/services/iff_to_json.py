import json
from io import BytesIO
from pathlib import Path

from igipy.igi2.formats.iff import IFF


def _sanitize(obj: object) -> object:
    """Recursively convert bytes to strings for JSON serialization."""
    if isinstance(obj, bytes):
        return obj.rstrip(b"\x00").decode("ascii", errors="replace")
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, tuple):
        return [_sanitize(v) for v in obj]
    return obj


def iff_to_json(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:
    target_path: Path | None = source_path.with_suffix(".json") if source_path is not None else None
    iff = IFF.model_validate_stream(source_io)

    data = {
        "header": {
            "version": iff.dhna.version,
            "looping": iff.dhna.looping,
            "duration": iff.dhna.duration,
            "bone_count": iff.dhna.bone_count,
            "entry_count": iff.dhna.entry_count,
            "has_root_motion": iff.dhna.has_root_motion,
            "name": iff.dhna.name,
        },
        "hierarchy": {
            "bone_child_counts": iff.reih.bones_child_counts,
            "rest_pose_offsets": [list(offset) for offset in iff.reih.bones_offsets],
        },
        "keyframes": [_sanitize(entry.model_dump()) for entry in iff.tnve.content],
        "attachments": ([_sanitize(item.model_dump()) for item in iff.atta.content] if iff.atta else []),
    }

    target_io = BytesIO()
    target_io.write(json.dumps(data, indent=2).encode("utf-8"))
    target_io.seek(0)
    return target_io, target_path
