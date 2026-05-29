from io import BytesIO

from igipy.core.formats.qsc import QSC
from igipy.core.formats.qvm import QVM


def qvm_to_qsc(instance: QVM) -> tuple[BytesIO, str]:
    """Convert a QVM bytecode instance to QSC source text."""
    return QSC(content=instance.rebuild_block()).model_dump_stream()
