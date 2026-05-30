from collections import deque
from io import BytesIO
from pathlib import Path

from igipy.core.formats.qsc import QSC, BlockStatement, Call, ExprStatement, Literal
from igipy.igi2.formats.iff import (
    IFF,
    TNVEFullTransform,
    TNVEFullTransformTangent,
    TNVEPosition,
    TNVERotation,
    TNVESeparator,
    TNVETrigger,
)

# BEF positions = IFF game-unit positions / 40.96 (where 40.96 = 4096/100)
_POSITION_SCALE = 4096 / 100
# Trigger bones with index >= this threshold are world-space (no bone attachment)
_WORLD_SPACE_BONE = 0xFFFF_0000


def _scale_position(v: float) -> float:
    return v / _POSITION_SCALE


def _call(name: str, *args: float | str) -> ExprStatement:
    arguments = []
    for arg in args:
        if isinstance(arg, str):
            arguments.append(Literal(value=arg))
        else:
            arguments.append(Literal(value=arg))
    return ExprStatement(expression=Call(function=name, arguments=arguments))


# noinspection DuplicatedCode
def _build_parent_map(child_counts: list[int]) -> list[int]:
    n = len(child_counts)
    parents = [-1] * n
    if n <= 1:
        return parents
    queue: deque[list[int]] = deque()
    queue.append([0, child_counts[0]])
    bone_idx = 1
    while queue and bone_idx < n:
        front = queue[0]
        if front[1] == 0:
            queue.popleft()
            continue
        parents[bone_idx] = front[0]
        front[1] -= 1
        if child_counts[bone_idx] > 0:
            queue.append([bone_idx, child_counts[bone_idx]])
        bone_idx += 1
    return parents


# noinspection DuplicatedCode
def iff_to_qsc(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:  # noqa: C901
    target_path: Path | None = source_path.with_suffix(".bef") if source_path is not None else None
    iff = IFF.model_validate_stream(source_io)

    # noinspection PyListCreation
    statements: list[ExprStatement] = []

    # AnimInit(name, version, duration+1, looping)  # noqa: ERA001
    statements.append(_call("AnimInit", iff.dhna.name, iff.dhna.unknown_01, iff.dhna.duration + 1, iff.dhna.looping))
    statements.append(_call("BreakScript"))

    # Bone(id, "Bone # XX", parent_id, x, y, z)  # noqa: ERA001
    parent_map = _build_parent_map(iff.reih.bone_child_counts)
    for i in range(iff.dhna.bone_count):
        x, y, z = iff.reih.rest_pose_offsets[i]
        sx, sy, sz = _scale_position(x), _scale_position(y), _scale_position(z)
        statements.append(_call("Bone", i, f"Bone # {i:02d}", parent_map[i], sx, sy, sz))
    statements.append(_call("BuildHierarchy"))

    # AnimAttachObject + AnimAttachObjectBoneID (optional)  # noqa: ERA001
    if iff.atta:
        for i, item in enumerate(iff.atta.content):
            name = item.name.rstrip(b"\x00").decode("ascii", errors="replace")
            statements.append(
                _call(
                    "AnimAttachObject",
                    name,
                    i,
                    item.orientation_x,
                    item.orientation_y,
                    item.orientation_z,
                    item.orientation_w,
                    item.secondary_x,
                    item.secondary_y,
                    item.secondary_z,
                    item.secondary_w,
                    item.unknown_float,
                    _scale_position(item.position_x),
                    _scale_position(item.position_y),
                    _scale_position(item.position_z),
                )
            )
            statements.append(_call("AnimAttachObjectBoneID", i, item.bone_index))

    statements.append(_call("BreakScript"))

    # TNVE keyframe entries
    trigger_index = 0
    for entry in iff.tnve.content:
        if isinstance(entry, TNVESeparator):
            continue

        if isinstance(entry, TNVEPosition):
            statements.append(
                _call(
                    "TranslationKeyFrameData",
                    entry.bone_index,
                    0,
                    entry.frame_offset,
                    _scale_position(entry.position_x),
                    _scale_position(entry.position_y),
                    _scale_position(entry.position_z),
                )
            )

        elif isinstance(entry, TNVERotation):
            statements.append(
                _call(
                    "RotationKeyFrameData",
                    entry.bone_index,
                    0,
                    entry.frame_offset,
                    entry.quaternion_x,
                    entry.quaternion_y,
                    entry.quaternion_z,
                    entry.quaternion_w,
                    entry.in_tangent_x,
                    entry.in_tangent_y,
                    entry.in_tangent_z,
                    entry.in_tangent_w,
                    entry.out_tangent_x,
                    entry.out_tangent_y,
                    entry.out_tangent_z,
                    entry.out_tangent_w,
                )
            )

        elif isinstance(entry, TNVETrigger):
            event_code = entry.event_code & 0xFFFF
            trigger_bone = entry.trigger_bone if entry.trigger_bone < _WORLD_SPACE_BONE else -1
            statements.append(
                _call(
                    "TriggerData",
                    trigger_index,
                    event_code,
                    entry.frame_offset,
                    trigger_bone,
                    _scale_position(entry.position_x),
                    _scale_position(entry.position_y),
                    _scale_position(entry.position_z),
                )
            )
            trigger_index += 1

        elif isinstance(entry, TNVEFullTransform):
            statements.append(
                _call(
                    "TranslationKeyFrameData",
                    entry.bone_index,
                    0,
                    entry.frame_offset,
                    _scale_position(entry.position_x),
                    _scale_position(entry.position_y),
                    _scale_position(entry.position_z),
                )
            )
            statements.append(
                _call(
                    "RotationKeyFrameData",
                    entry.bone_index,
                    0,
                    entry.frame_offset,
                    entry.quaternion_x,
                    entry.quaternion_y,
                    entry.quaternion_z,
                    entry.quaternion_w,
                    entry.quaternion_x,
                    entry.quaternion_y,
                    entry.quaternion_z,
                    entry.quaternion_w,
                    entry.quaternion_x,
                    entry.quaternion_y,
                    entry.quaternion_z,
                    entry.quaternion_w,
                )
            )

        elif isinstance(entry, TNVEFullTransformTangent):
            statements.append(
                _call(
                    "TranslationKeyFrameData",
                    entry.bone_index,
                    0,
                    entry.frame_offset,
                    _scale_position(entry.position_x),
                    _scale_position(entry.position_y),
                    _scale_position(entry.position_z),
                )
            )
            statements.append(
                _call(
                    "RotationKeyFrameData",
                    entry.bone_index,
                    0,
                    entry.frame_offset,
                    entry.quaternion_a_x,
                    entry.quaternion_a_y,
                    entry.quaternion_a_z,
                    entry.quaternion_a_w,
                    entry.quaternion_a_x,
                    entry.quaternion_a_y,
                    entry.quaternion_a_z,
                    entry.quaternion_a_w,
                    entry.quaternion_a_x,
                    entry.quaternion_a_y,
                    entry.quaternion_a_z,
                    entry.quaternion_a_w,
                )
            )

    block = BlockStatement(statements=statements)
    qsc = QSC(content=block, max_line_length=10000)
    target_io, _ = qsc.model_dump_stream()
    return target_io, target_path
