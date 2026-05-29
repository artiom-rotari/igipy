from io import BytesIO
from pathlib import Path

from igipy.core.formats.qsc import QSC
from igipy.core.formats.qvm import QVM


def qvm_to_qsc(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:
    target_path: Path | None = source_path.with_suffix(".qsc") if source_path is not None else None
    qvm_instance = QVM.model_validate_stream(source_io)
    qsc_instance = QSC(content=qvm_instance.rebuild_block())
    target_io, _ = qsc_instance.model_dump_stream()
    return target_io, target_path
