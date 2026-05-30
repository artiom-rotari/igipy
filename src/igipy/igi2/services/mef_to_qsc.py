"""Convert binary MEF mesh to text source format using QSC AST.

Produces a text representation of the MEF model matching the original 3ds Max
export format used by gconv.exe. The output uses the QSC AST infrastructure
(function calls as ExprStatements) but saves with a .mef extension.

Not all binary data maps back to text commands. Material definitions, texture
paths, and render state (D3DR) are not stored in the binary format and cannot
be reconstructed. Collision mesh data (HSMC/XTVC/ECFC/TAMC/HPSC) is also
compiler-generated and has no text equivalent.
"""

from io import BytesIO
from pathlib import Path

from igipy.core.formats.qsc import (
    QSC,
    BlockStatement,
    Call,
    ExprStatement,
    Literal,
)
from igipy.igi2.formats.mef import MEF

MODEL_TYPE_STATIC = 0
MODEL_TYPE_SKELETAL = 1
MODEL_TYPE_BUILDING = 3


def _call(name: str, *args: float | str | bool) -> ExprStatement:
    """Build an ExprStatement wrapping a Call node."""
    return ExprStatement(expression=Call(function=name, arguments=[Literal(value=a) for a in args]))


def mef_to_qsc(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:
    target_path: Path | None = source_path.with_suffix(".mef") if source_path is not None else None
    mef = MEF.model_validate_stream(source_io)

    statements = _build_sems_statements(mef) if mef.is_sems_variant else _build_standard_statements(mef)

    qsc = QSC(content=BlockStatement(statements=statements), indent_width=0, indent_char="")
    target_io, _ = qsc.model_dump_stream()
    target_io.seek(0)
    return target_io, target_path


def _build_bone_statements(mef: MEF) -> list[ExprStatement]:
    """Build Bone() and BuildHierarchy() calls from REIH + MANB chunks."""
    if mef.reih is None or mef.manb is None:
        return []

    rest_offsets = mef.reih.bones_offsets
    bone_count = len(mef.reih.content)
    parents = mef.reih.bones_parents
    names = mef.manb.content[:bone_count]

    statements = [
        _call("Bone", i, names[i], parents[i], rest_offsets[i][0], rest_offsets[i][1], rest_offsets[i][2])
        for i in range(bone_count)
    ]
    statements.append(_call("BuildHierarchy"))
    return statements


def _build_vertex_statements(mef: MEF, model_type: int) -> list[ExprStatement]:
    """Build Vertex() calls from XVTP (preferred) or XTRV (fallback)."""
    if mef.xvtp is not None and mef.xvtp.content:
        return [
            _call("Vertex", i, vertex.position_x, vertex.position_y, vertex.position_z)
            for i, vertex in enumerate(mef.xvtp.content)
        ]

    if mef.xtrv is None:
        return []

    content_map = {
        MODEL_TYPE_STATIC: mef.xtrv.content_0,
        MODEL_TYPE_SKELETAL: mef.xtrv.content_1,
        MODEL_TYPE_BUILDING: mef.xtrv.content_3,
    }
    vertices = content_map.get(model_type)
    if vertices is None:
        return []

    return [
        _call("Vertex", i, vertex.position_x, vertex.position_y, vertex.position_z) for i, vertex in enumerate(vertices)
    ]


def _build_vertex_influence_statements(mef: MEF, model_type: int) -> list[ExprStatement]:
    """Build VertexInfluenceRigid() calls from XTRV bone data (type 1 only)."""
    if model_type != MODEL_TYPE_SKELETAL or mef.xtrv is None:
        return []

    return [
        _call(
            "VertexInfluenceRigid",
            vertex.bone_index,
            vertex.vertex_index,
            vertex.position_x,
            vertex.position_y,
            vertex.position_z,
            vertex.bone_weight,
        )
        for vertex in mef.xtrv.content_1
    ]


def _build_normal_statements(mef: MEF, model_type: int) -> list[ExprStatement]:
    """Build Normal() calls from XTRV (type 0 and 1 only)."""
    if mef.xtrv is None:
        return []

    content_map = {
        MODEL_TYPE_STATIC: mef.xtrv.content_0,
        MODEL_TYPE_SKELETAL: mef.xtrv.content_1,
    }
    vertices = content_map.get(model_type)
    if vertices is None:
        return []

    return [_call("Normal", i, vertex.normal_x, vertex.normal_y, vertex.normal_z) for i, vertex in enumerate(vertices)]


def _build_face_statements(mef: MEF, model_type: int) -> list[ExprStatement]:
    """Build Face() calls from ECAF + DNER with material assignment."""
    if mef.ecaf is None or mef.dner is None:
        return []

    if model_type in (MODEL_TYPE_STATIC, MODEL_TYPE_SKELETAL):
        groups = mef.dner.content_0 if model_type == MODEL_TYPE_STATIC else mef.dner.content_1
    else:
        groups = mef.dner.content_3

    face_materials: list[int] = []
    for group in groups:
        face_materials.extend([group.group_index] * group.face_count)

    return [
        _call(
            "Face",
            i,
            face.index_a,
            face.index_b,
            face.index_c,
            face.index_a,
            face.index_b,
            face.index_c,
            face_materials[i] if i < len(face_materials) else 0,
        )
        for i, face in enumerate(mef.ecaf.content)
    ]


def _build_uv_statements(mef: MEF, model_type: int) -> list[ExprStatement]:
    """Build UV() calls from XTRV per-face vertex data."""
    if mef.ecaf is None or mef.xtrv is None:
        return []

    content_map = {
        MODEL_TYPE_STATIC: mef.xtrv.content_0,
        MODEL_TYPE_SKELETAL: mef.xtrv.content_1,
    }
    vertices = content_map.get(model_type)
    if vertices is None:
        return []

    statements: list[ExprStatement] = []
    for i, face in enumerate(mef.ecaf.content):
        vertex_0, vertex_1, vertex_2 = vertices[face.index_a], vertices[face.index_b], vertices[face.index_c]
        statements.append(
            _call(
                "UV",
                i,
                vertex_0.uv_u,
                vertex_0.uv_v,
                vertex_1.uv_u,
                vertex_1.uv_v,
                vertex_2.uv_u,
                vertex_2.uv_v,
            )
        )

    return statements


def _build_attachment_statements(mef: MEF) -> list[ExprStatement]:
    """Build AttachObject() and AttachObjectBoneID() calls from ATTA."""
    if mef.atta is None:
        return []

    statements: list[ExprStatement] = []
    for item in mef.atta.content:
        name = item.name.rstrip(b"\x00").decode("ascii", errors="replace")
        statements.append(
            _call(
                "AttachObject",
                name,
                item.attach_index,
                item.m00,
                item.m01,
                item.m02,
                item.m10,
                item.m11,
                item.m12,
                item.m20,
                item.m21,
                item.m22,
                item.position_x,
                item.position_y,
                item.position_z,
            )
        )
        statements.append(_call("AttachObjectBoneID", item.attach_index, item.bone_index))

    return statements


def _build_magic_vertex_statements(mef: MEF) -> list[ExprStatement]:
    """Build MagicVertex() calls from XTVM."""
    if mef.xtvm is None:
        return []

    return [
        _call("MagicVertex", i, 0, item.position_x, item.position_y, item.position_z, item.param)
        for i, item in enumerate(mef.xtvm.content)
    ]


def _build_glow_statements(mef: MEF) -> list[ExprStatement]:
    """Build Glow() calls from WOLG."""
    if mef.wolg is None:
        return []

    return [
        _call(
            "Glow",
            item.position_x,
            item.position_y,
            item.position_z,
            item.radius,
            item.color_red,
            item.color_green,
            item.color_blue,
        )
        for item in mef.wolg.content
    ]


def _build_standard_statements(mef: MEF) -> list[ExprStatement]:
    model_type = mef.hsem.model_type

    statements: list[ExprStatement] = [_call("NewObject", ""), _call("BreakScript")]
    statements.extend(_build_bone_statements(mef))
    statements.extend(_build_vertex_statements(mef, model_type))
    statements.extend(_build_vertex_influence_statements(mef, model_type))
    statements.extend(_build_normal_statements(mef, model_type))
    statements.extend(_build_face_statements(mef, model_type))
    statements.extend(_build_uv_statements(mef, model_type))
    statements.extend(_build_attachment_statements(mef))
    statements.extend(_build_magic_vertex_statements(mef))
    statements.extend(_build_glow_statements(mef))

    return statements


def _build_sems_statements(mef: MEF) -> list[ExprStatement]:
    """Build text representation for SEMS variant (simplified collision mesh)."""
    statements: list[ExprStatement] = [_call("NewObject", ""), _call("BreakScript")]

    if mef.xtvs is not None:
        statements.extend(
            _call("Vertex", i, vertex.position_x, vertex.position_y, vertex.position_z)
            for i, vertex in enumerate(mef.xtvs.content)
        )

    if mef.cafs is not None:
        statements.extend(
            _call("Face", i, face.index_a, face.index_b, face.index_c, face.index_a, face.index_b, face.index_c, 0)
            for i, face in enumerate(mef.cafs.content)
        )

    return statements
