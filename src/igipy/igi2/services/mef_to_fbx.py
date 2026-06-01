"""Export MEF 3D model to FBX 7.5 ASCII format.

Produces a triangle mesh with positions, normals, and UVs. Skeletal models
(type 1) include bone hierarchy, skinning weights, and a bind pose. The
result can be imported into Unity, Blender, Maya, or any FBX-compatible tool.
"""

import logging
import math
from collections import defaultdict
from io import BytesIO
from pathlib import Path

from igipy.core.base import FileIgnored
from igipy.core.formats.fbx import (
    FBX,
    FBXCluster,
    FBXConnection,
    FBXGeometry,
    FBXMaterial,
    FBXModel,
    FBXNodeAttribute,
    FBXPose,
    FBXPoseNode,
    FBXSkin,
    FBXTexture,
    FBXVideo,
    IdGenerator,
)
from igipy.igi2.formats.mef import (
    ATTA_NO_BONE,
    MEF,
    MODEL_TYPE_BUILDING,
    MODEL_TYPE_SKELETAL,
)
from igipy.igi2.services.iff_to_fbx import _position_to_fbx
from igipy.igi2.services.mef_texture_resolver import (
    RenderGroupTexture,
    TextureTransparency,
    resolve_render_group_textures,
)
from igipy.igi2.services.mesh_normals import compute_vertex_normals

logger = logging.getLogger(__name__)


def _normal_to_fbx(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Convert normal from IGI2 Z-up to FBX Y-up (no scale)."""
    return x, z, -y


def reverse_triangle_winding(faces: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    """Swap the 2nd and 3rd index of every triangle to flip its front/back face.

    IGI2 winds front faces clockwise (left-handed / DirectX convention; the
    authored normals match "(c - a) x (b - a)" of the stored winding). The
    Z-up -> Y-up swizzle in "_position_to_fbx" is a pure rotation (determinant
    +1), so it preserves that clockwise winding. FBX / Unity treat counter-clockwise as front-facing,
    so every camera-facing triangle would otherwise be
    culled as a back face (you see the far wall through the near one). Reversing
    the winding makes the camera-facing side render. Vertices are not moved, so
    the geometry is not mirrored; only the front/back convention changes.
    """
    return [(index_a, index_c, index_b) for index_a, index_b, index_c in faces]


def _rotation_matrix_to_euler(  # noqa: PLR0913
    m00: float,
    m01: float,
    m02: float,
    m10: float,
    m11: float,
    m12: float,
    m20: float,
    m21: float,
    m22: float,
) -> tuple[float, float, float]:
    """Convert 3x3 rotation matrix (IGI2 Z-up) to FBX Y-up Euler XYZ degrees.

    Applies coordinate system conversion P * R * P^T where
    P = [[1,0,0],[0,0,1],[0,-1,0]] (Z-up -> Y-up).
    """
    r00, r01, r02 = m00, m02, -m01  # noqa: F841
    r10, r11, r12 = m20, m22, -m21
    r20, r21, r22 = -m10, -m12, m11

    if abs(r20) < 0.99999:  # noqa: PLR2004
        pitch = math.asin(max(-1.0, min(1.0, -r20)))
        roll = math.atan2(r21, r22)
        yaw = math.atan2(r10, r00)
    else:
        pitch = math.copysign(math.pi / 2, -r20)
        roll = math.atan2(-r12, r11)
        yaw = 0.0

    return math.degrees(roll), math.degrees(pitch), math.degrees(yaw)


# ---------------------------------------------------------------------------
# Skinning helpers
# ---------------------------------------------------------------------------


def _accumulate_bone_offsets(
    bone_offsets: list[tuple[float, float, float]],
    bone_parents: list[int],
) -> list[tuple[float, float, float]]:
    """Accumulate REIH bone offsets down the parent chain into absolute model-space positions.

    REIH stores each bone's offset RELATIVE to its parent (verified: summing the chain
    reconstructs a correctly proportioned standing humanoid ~1.8 m tall — feet at z~0,
    head at the top — while the raw offsets do not). A bone's world position is therefore
    the running sum of its own offset plus every ancestor's offset. REIH bones are ordered
    parent-before-child (the parent index is always smaller than the child index), so a
    single forward pass can read the parent's already-accumulated position.
    """
    accumulated: list[tuple[float, float, float]] = []
    for index, (offset_x, offset_y, offset_z) in enumerate(bone_offsets):
        parent_index = bone_parents[index] if index < len(bone_parents) else -1
        if 0 <= parent_index < len(accumulated):
            parent_x, parent_y, parent_z = accumulated[parent_index]
        else:
            parent_x, parent_y, parent_z = 0.0, 0.0, 0.0
        accumulated.append((parent_x + offset_x, parent_y + offset_y, parent_z + offset_z))
    return accumulated


def _compute_world_transforms(
    bone_count: int,
    rest_offsets: list[tuple[float, float, float]],
) -> list[list[float]]:
    """Compute each bone's 4x4 row-major world transform.

    "rest_offsets" are ABSOLUTE model-space bone positions (the accumulated REIH offsets
    from "_accumulate_bone_offsets"), so they are used directly as the translation of a
    translation-only world transform (REIH carries no per-bone rotation).
    """
    world_transforms: list[list[float]] = []
    for i in range(bone_count):
        if i < len(rest_offsets):
            translation_x, translation_y, translation_z = _position_to_fbx(*rest_offsets[i])
        else:
            translation_x, translation_y, translation_z = 0.0, 0.0, 0.0
        world_transforms.append([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, translation_x, translation_y, translation_z, 1])
    return world_transforms


def _mat4_mul_row(a: list[float], b: list[float]) -> list[float]:
    """Multiply two 4x4 row-major matrices."""
    r = [0.0] * 16
    for row in range(4):
        for col in range(4):
            s = 0.0
            for k in range(4):
                s += a[row * 4 + k] * b[k * 4 + col]
            r[row * 4 + col] = s
    return r


def _mat4_inverse_row(m: list[float]) -> list[float]:
    """Invert a 4x4 row-major matrix. Falls back to identity on singular."""
    inv = [0.0] * 16

    inv[0] = (
        m[5] * m[10] * m[15]
        - m[5] * m[11] * m[14]
        - m[9] * m[6] * m[15]
        + m[9] * m[7] * m[14]
        + m[13] * m[6] * m[11]
        - m[13] * m[7] * m[10]
    )
    inv[4] = (
        -m[4] * m[10] * m[15]
        + m[4] * m[11] * m[14]
        + m[8] * m[6] * m[15]
        - m[8] * m[7] * m[14]
        - m[12] * m[6] * m[11]
        + m[12] * m[7] * m[10]
    )
    inv[8] = (
        m[4] * m[9] * m[15]
        - m[4] * m[11] * m[13]
        - m[8] * m[5] * m[15]
        + m[8] * m[7] * m[13]
        + m[12] * m[5] * m[11]
        - m[12] * m[7] * m[9]
    )
    inv[12] = (
        -m[4] * m[9] * m[14]
        + m[4] * m[10] * m[13]
        + m[8] * m[5] * m[14]
        - m[8] * m[6] * m[13]
        - m[12] * m[5] * m[10]
        + m[12] * m[6] * m[9]
    )

    det = m[0] * inv[0] + m[1] * inv[4] + m[2] * inv[8] + m[3] * inv[12]
    if abs(det) < 1e-15:  # noqa: PLR2004
        return [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

    inv[1] = (
        -m[1] * m[10] * m[15]
        + m[1] * m[11] * m[14]
        + m[9] * m[2] * m[15]
        - m[9] * m[3] * m[14]
        - m[13] * m[2] * m[11]
        + m[13] * m[3] * m[10]
    )
    inv[5] = (
        m[0] * m[10] * m[15]
        - m[0] * m[11] * m[14]
        - m[8] * m[2] * m[15]
        + m[8] * m[3] * m[14]
        + m[12] * m[2] * m[11]
        - m[12] * m[3] * m[10]
    )
    inv[9] = (
        -m[0] * m[9] * m[15]
        + m[0] * m[11] * m[13]
        + m[8] * m[1] * m[15]
        - m[8] * m[3] * m[13]
        - m[12] * m[1] * m[11]
        + m[12] * m[3] * m[9]
    )
    inv[13] = (
        m[0] * m[9] * m[14]
        - m[0] * m[10] * m[13]
        - m[8] * m[1] * m[14]
        + m[8] * m[2] * m[13]
        + m[12] * m[1] * m[10]
        - m[12] * m[2] * m[9]
    )

    inv[2] = (
        m[1] * m[6] * m[15]
        - m[1] * m[7] * m[14]
        - m[5] * m[2] * m[15]
        + m[5] * m[3] * m[14]
        + m[13] * m[2] * m[7]
        - m[13] * m[3] * m[6]
    )
    inv[6] = (
        -m[0] * m[6] * m[15]
        + m[0] * m[7] * m[14]
        + m[4] * m[2] * m[15]
        - m[4] * m[3] * m[14]
        - m[12] * m[2] * m[7]
        + m[12] * m[3] * m[6]
    )
    inv[10] = (
        m[0] * m[5] * m[15]
        - m[0] * m[7] * m[13]
        - m[4] * m[1] * m[15]
        + m[4] * m[3] * m[13]
        + m[12] * m[1] * m[7]
        - m[12] * m[3] * m[5]
    )
    inv[14] = (
        -m[0] * m[5] * m[14]
        + m[0] * m[6] * m[13]
        + m[4] * m[1] * m[14]
        - m[4] * m[2] * m[13]
        - m[12] * m[1] * m[6]
        + m[12] * m[2] * m[5]
    )

    inv[3] = (
        -m[1] * m[6] * m[11]
        + m[1] * m[7] * m[10]
        + m[5] * m[2] * m[11]
        - m[5] * m[3] * m[10]
        - m[9] * m[2] * m[7]
        + m[9] * m[3] * m[6]
    )
    inv[7] = (
        m[0] * m[6] * m[11]
        - m[0] * m[7] * m[10]
        - m[4] * m[2] * m[11]
        + m[4] * m[3] * m[10]
        + m[8] * m[2] * m[7]
        - m[8] * m[3] * m[6]
    )
    inv[11] = (
        -m[0] * m[5] * m[11]
        + m[0] * m[7] * m[9]
        + m[4] * m[1] * m[11]
        - m[4] * m[3] * m[9]
        - m[8] * m[1] * m[7]
        + m[8] * m[3] * m[5]
    )
    inv[15] = (
        m[0] * m[5] * m[10]
        - m[0] * m[6] * m[9]
        - m[4] * m[1] * m[10]
        + m[4] * m[2] * m[9]
        + m[8] * m[1] * m[6]
        - m[8] * m[2] * m[5]
    )

    inverse_determinant = 1.0 / det
    return [x * inverse_determinant for x in inv]


# ---------------------------------------------------------------------------
# Geometry extraction helpers
# ---------------------------------------------------------------------------


def _extract_static(
    mef: MEF,
) -> tuple[
    list[tuple[float, float, float]],
    list[tuple[int, int, int]],
    list[tuple[float, float, float]] | None,
    list[tuple[float, float]] | None,
]:
    """Extract positions, faces, normals, uvs for static model (type 0)."""
    vertices = mef.render_vertices
    positions = [_position_to_fbx(vertex.position_x, vertex.position_y, vertex.position_z) for vertex in vertices]
    normals = [_normal_to_fbx(vertex.normal_x, vertex.normal_y, vertex.normal_z) for vertex in vertices]
    uvs = [(vertex.uv_u, 1.0 - vertex.uv_v) for vertex in vertices]
    return positions, mef.render_faces, normals, uvs


def _extract_skeletal(
    mef: MEF,
    accumulated_bone_offsets: list[tuple[float, float, float]],
) -> tuple[
    list[tuple[float, float, float]],
    list[tuple[int, int, int]],
    list[tuple[float, float, float]] | None,
    list[tuple[float, float]] | None,
]:
    """Extract positions, faces, normals, uvs for a skeletal model (type 1).

    Type-1 vertices are stored in BONE-LOCAL space — each position is relative to the
    frame of its own "bone_index". To place them in the model space for the bind pose, add
    the bone's absolute offset ("accumulated_bone_offsets", summed down the REIH
    hierarchy). Without this every limb stays at its bone-local origin, and the whole mesh
    collapses onto the hip/origin (the "all parts inside the chest" symptom). Bone frames
    are translation-only here, so the per-vertex normals are unaffected and stay as stored.
    When the skeleton is absent the local positions are emitted unchanged.
    """
    vertices = mef.render_vertices
    normals = [_normal_to_fbx(vertex.normal_x, vertex.normal_y, vertex.normal_z) for vertex in vertices]
    uvs = [(vertex.uv_u, 1.0 - vertex.uv_v) for vertex in vertices]
    bone_count = len(accumulated_bone_offsets)
    if bone_count:
        positions = []
        for vertex in vertices:
            bone_index = vertex.bone_index
            if 0 <= bone_index < bone_count:
                offset_x, offset_y, offset_z = accumulated_bone_offsets[bone_index]
            else:
                offset_x, offset_y, offset_z = 0.0, 0.0, 0.0
            positions.append(
                _position_to_fbx(
                    vertex.position_x + offset_x,
                    vertex.position_y + offset_y,
                    vertex.position_z + offset_z,
                )
            )
    else:
        positions = [_position_to_fbx(vertex.position_x, vertex.position_y, vertex.position_z) for vertex in vertices]
    return positions, mef.render_faces, normals, uvs


def _extract_building(
    mef: MEF,
) -> tuple[
    list[tuple[float, float, float]],
    list[tuple[int, int, int]],
    list[tuple[float, float, float]],
    list[tuple[float, float]] | None,
]:
    """Extract positions, faces, and diffuse UVs for a building model (type 3).

    Type-3 vertices carry a diffuse UV set but no per-vertex normal — lighting is baked into
    the lightmap — so normals stay None. "v.uv_v" exposes the diffuse V in the same
    convention as type 0/1, so the shared "(uv_u, 1.0 - uv_v)" flip applies uniformly and
    keeps type-3 texture orientation aligned with type 0/1.
    """
    vertices = mef.render_vertices
    positions = [_position_to_fbx(vertex.position_x, vertex.position_y, vertex.position_z) for vertex in vertices]
    uvs = [(vertex.uv_u, 1.0 - vertex.uv_v) for vertex in vertices]
    faces = mef.render_faces
    # Type-3 stores no per-vertex normal; generate them so Unity does not
    # recalculate (which produces inverted / see-through faces).
    normals = compute_vertex_normals(positions, faces)
    return positions, faces, normals, uvs


# Below this squared length a normal is treated as degenerate (zero-length).
_DEGENERATE_LENGTH_EPSILON = 1e-9


def _normalize_or_fallback(
    normal: tuple[float, float, float],
    triangle: list[tuple[float, float, float]],
) -> tuple[float, float, float]:
    """Normalize "normal"; when it is degenerate, derive a geometric face normal.

    Used for SEMS authored plane normals: a zero-length CAFS plane normal falls back
    to the "(c - a) x (b - a)" cross product (the IGI2 winding convention shared with
    "compute_vertex_normals", computed here in FBX space), and finally to +Z when the
    triangle itself is degenerate.
    """
    length = (normal[0] * normal[0] + normal[1] * normal[1] + normal[2] * normal[2]) ** 0.5
    if length > _DEGENERATE_LENGTH_EPSILON:
        return normal[0] / length, normal[1] / length, normal[2] / length

    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = triangle
    edge_u_x, edge_u_y, edge_u_z = cx - ax, cy - ay, cz - az
    edge_v_x, edge_v_y, edge_v_z = bx - ax, by - ay, bz - az
    geometric_x = edge_u_y * edge_v_z - edge_u_z * edge_v_y
    geometric_y = edge_u_z * edge_v_x - edge_u_x * edge_v_z
    geometric_z = edge_u_x * edge_v_y - edge_u_y * edge_v_x
    geometric_length = (geometric_x * geometric_x + geometric_y * geometric_y + geometric_z * geometric_z) ** 0.5
    if geometric_length > _DEGENERATE_LENGTH_EPSILON:
        return geometric_x / geometric_length, geometric_y / geometric_length, geometric_z / geometric_length
    return 0.0, 0.0, 1.0


def _extract_sems(
    mef: MEF,
) -> tuple[
    list[tuple[float, float, float]],
    list[tuple[int, int, int]],
    list[tuple[float, float, float]],
    None,
]:
    """Extract de-indexed positions, faces, and authored normals for the SEMS variant.

    The SEMS simplified-collision variant stores no per-vertex normal, but each CAFS
    face carries an authored plane normal — the convex-hull outward normal. FBX's
    "LayerElementNormal" maps one normal per VERTEX index, so a hull vertex shared by
    faces with different plane normals could keep only one of them; and emitting no
    normal at all makes Unity recalculate (producing inverted / see-through faces).
    To preserve the authored flat normals the mesh is DE-INDEXED: every triangle gets
    three fresh vertices that each carry its face's plane normal. The plane normal is
    swizzled with the same Z-up -> Y-up "_normal_to_fbx" used for type 0/1 authored
    normals, so it points outward in FBX space; the later winding reversal does not
    move vertices, so the vertex -> normal mapping stays valid.
    """
    if mef.cafs is None or mef.xtvs is None:
        return [], [], [], None

    source_positions = [
        _position_to_fbx(vertex.position_x, vertex.position_y, vertex.position_z) for vertex in mef.xtvs.content
    ]
    vertex_count = len(source_positions)

    positions: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    normals: list[tuple[float, float, float]] = []
    for item in mef.cafs.content:
        indices = (item.index_a, item.index_b, item.index_c)
        if any(not 0 <= index < vertex_count for index in indices):
            continue
        triangle = [source_positions[index] for index in indices]
        normal = _normalize_or_fallback(_normal_to_fbx(item.normal_x, item.normal_y, item.normal_z), triangle)
        base = len(positions)
        positions.extend(triangle)
        normals.extend((normal, normal, normal))
        faces.append((base, base + 1, base + 2))

    return positions, faces, normals, None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


# noinspection DuplicatedCode,PyUnusedLocal
def mef_to_fbx(  # noqa: C901, PLR0912, PLR0915
    source_io: BytesIO,
    source_path: Path | None = None,
    collect_path: Path | None = None,
) -> tuple[BytesIO, Path | None]:
    """Export a MEF model to FBX.

    When "collect_path" (the collect-source root) and "source_path" are both given, each
    render group is bound to its diffuse texture resolved through the level MTP (see
    "mef_texture_resolver"). Without them the mesh exports untextured (one placeholder
    material), preserving the original behavior and backward compatibility.
    """
    target_path: Path | None = source_path.with_suffix(".fbx") if source_path is not None else None
    mef = MEF.model_validate_stream(source_io)

    name = source_path.stem if source_path else "mef_model"
    id_gen = IdGenerator()

    # Determine model type and extract geometry
    is_sems = mef.is_sems_variant
    model_type = mef.model_type
    is_skeletal = not is_sems and model_type == MODEL_TYPE_SKELETAL

    # Skeletal vertices are stored bone-local and REIH offsets are relative; accumulate the
    # offsets down the hierarchy to get each bone's absolute model-space position, then bake
    # those into the vertices so the skeleton stands up instead of collapsing onto the hip.
    accumulated_bone_offsets: list[tuple[float, float, float]] = []
    if is_skeletal and mef.has_skeleton:
        accumulated_bone_offsets = _accumulate_bone_offsets(mef.reih.bones_offsets, mef.reih.bones_parents)

    if is_sems:
        positions, faces, normals, uvs = _extract_sems(mef)
        logger.debug(
            "[FIX] SEMS authored CAFS normals (de-indexed): model=%s faces=%d vertices=%d",
            name,
            len(faces),
            len(positions),
        )
    elif model_type == MODEL_TYPE_SKELETAL:
        positions, faces, normals, uvs = _extract_skeletal(mef, accumulated_bone_offsets)
    elif model_type == MODEL_TYPE_BUILDING:
        positions, faces, normals, uvs = _extract_building(mef)
    else:
        positions, faces, normals, uvs = _extract_static(mef)

    # Some MEFs carry no render geometry — kill/trigger volumes (killbox, killair),
    # control points (ctrl3_01_1), and proxy/reference models (313_03_3, ...) have an
    # empty XTRV (0 vertices / 0 faces). Emitting them produces a degenerate FBX with
    # "Vertices: 0", which Unity imports as an empty mesh and warns "doesn't contain
    # normals" / "can't calculate tangents". They are invisible game-logic volumes with
    # no authored visual mesh, so skip them (matching the FileIgnored skip pattern used
    # for non-ILFF / empty containers) instead of writing an empty FBX.
    if not positions or not faces:
        logger.debug(
            "[FIX] skipping MEF with empty render geometry: model=%s type=%s sems=%s", name, model_type, is_sems
        )
        raise FileIgnored(f"MEF has no render geometry: {name}")

    # IGI2 winds front faces clockwise; FBX/Unity expect counter-clockwise, so the
    # camera-facing triangles get culled (the near wall is invisible, only the far
    # wall shows). Reverse the winding for emission. Normals were already computed
    # from the original winding above and point outward, so they stay unchanged.
    faces = reverse_triangle_winding(faces)
    logger.debug("[FIX] reversed triangle winding for FBX: model=%s type=%s triangles=%d", name, model_type, len(faces))

    # Core objects
    geometry_id = id_gen()
    mesh_model_id = id_gen()

    node_attributes: list[FBXNodeAttribute] = []
    models: list[FBXModel] = [FBXModel(id=mesh_model_id, name=name, type="Mesh")]
    skins: list[FBXSkin] = []
    poses: list[FBXPose] = []
    connections: list[FBXConnection] = []

    # Materials + textures. One material per render group (faces are ordered group-by-group,
    # so the per-face material index is the group ordinal); duplicate textures are shared.
    render_group_textures: list[RenderGroupTexture | None] = []
    if collect_path is not None and source_path is not None:
        render_group_textures = resolve_render_group_textures(mef, source_path, collect_path)

    materials, textures, videos, material_indices, two_sided = _build_materials_and_textures(
        mef, name, mesh_model_id, render_group_textures, len(faces), id_gen, connections
    )
    if two_sided:
        # Transparent groups (glass/fences) are thin surfaces; disable backface culling so they
        # are visible from both sides. FBX culling is per-mesh, so this applies to the whole mesh.
        models[0].culling = True

    geometries = [
        FBXGeometry(
            id=geometry_id,
            name=name,
            positions=positions,
            faces=faces,
            normals=normals,
            uvs=uvs,
            material_indices=material_indices,
        )
    ]

    # Geometry -> Mesh Model, Mesh Model -> scene root (material -> model wired above)
    connections.append(FBXConnection(source=geometry_id, destination=mesh_model_id))
    connections.append(FBXConnection(source=mesh_model_id, destination=0))

    # Skeleton setup
    bone_count = 0
    bone_names: list[str] = []
    bone_ids: list[int] = []
    rest_offsets: list[tuple[float, float, float]] = []
    parents: list[int] = []
    world_transforms: list[list[float]] = []

    if is_skeletal and mef.has_skeleton:
        # Absolute (accumulated) bone positions: world transforms, bind pose, and the
        # per-bone local translation (offset[i] = world[i] - world[parent]) all derive
        # from these, matching the world-space vertices baked in _extract_skeletal.
        rest_offsets = accumulated_bone_offsets
        bone_count = mef.bone_count
        parents = mef.reih.bones_parents
        bone_names = mef.bone_names
        bone_ids = [id_gen() for _ in range(bone_count)]
        bone_attribute_ids = [id_gen() for _ in range(bone_count)]
        world_transforms = _compute_world_transforms(bone_count, rest_offsets)
        logger.debug(
            "[FIX] skeletal world placement: model=%s bones=%d vertices=%d",
            name,
            bone_count,
            len(positions),
        )

        for i in range(bone_count):
            node_attributes.append(
                FBXNodeAttribute(
                    id=bone_attribute_ids[i],
                    name=bone_names[i],
                    type="LimbNode",
                    type_flags="Skeleton",
                )
            )
            # rest_offsets are absolute (accumulated); a bone node's LOCAL translation is
            # its world position minus its parent's (which equals the raw REIH offset), so
            # the node hierarchy reproduces the absolute world (matching transform_link).
            world_translation = _position_to_fbx(*rest_offsets[i]) if i < len(rest_offsets) else (0.0, 0.0, 0.0)
            parent_index = parents[i]
            if 0 <= parent_index < len(rest_offsets):
                parent_translation = _position_to_fbx(*rest_offsets[parent_index])
            else:
                parent_translation = (0.0, 0.0, 0.0)
            translation = (
                world_translation[0] - parent_translation[0],
                world_translation[1] - parent_translation[1],
                world_translation[2] - parent_translation[2],
            )
            models.append(FBXModel(id=bone_ids[i], name=bone_names[i], type="LimbNode", translation=translation))

        # Bone connections: NodeAttribute -> Model, bone hierarchy
        connections.extend(
            FBXConnection(source=bone_attribute_ids[i], destination=bone_ids[i]) for i in range(bone_count)
        )
        for i in range(bone_count):
            parent_id = 0 if parents[i] == -1 else bone_ids[parents[i]]
            connections.append(FBXConnection(source=bone_ids[i], destination=parent_id))

        # Skin deformers
        skin_id = id_gen()
        cluster_ids = [id_gen() for _ in range(bone_count)]

        # Group vertices by bone. IGI2 skeletal influence is RIGID: each vertex
        # binds 100% to its single bone. The stored bone_weight is not a usable
        # skin weight (often < 1.0, sometimes 0.0); feeding it to Unity leaves a
        # vertex's total weight < 1, so the unassigned remainder pulls it toward
        # the origin and the mesh collapses into the chest. Use weight 1.0.
        bone_vertices: dict[int, list[int]] = defaultdict(list)
        for vertex_index, vertex in enumerate(mef.render_vertices):
            bone_vertices[vertex.bone_index].append(vertex_index)

        clusters: list[FBXCluster] = []
        for bi in range(bone_count):
            inverse_bind = _mat4_inverse_row(world_transforms[bi])
            vertex_indexes = bone_vertices.get(bi, [])
            clusters.append(
                FBXCluster(
                    id=cluster_ids[bi],
                    name=bone_names[bi],
                    indexes=vertex_indexes,
                    weights=[1.0] * len(vertex_indexes),
                    transform=inverse_bind,
                    transform_link=world_transforms[bi],
                )
            )

        skins.append(FBXSkin(id=skin_id, name=name, clusters=clusters))

        # Skin connections: Skin -> Geometry, Cluster -> Skin, Bone -> Cluster
        connections.append(FBXConnection(source=skin_id, destination=geometry_id))
        for i in range(bone_count):
            connections.append(FBXConnection(source=cluster_ids[i], destination=skin_id))
            connections.append(FBXConnection(source=bone_ids[i], destination=cluster_ids[i]))

        # Bind pose
        pose_id = id_gen()
        pose_nodes = [FBXPoseNode(node_id=mesh_model_id, matrix=[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])]
        pose_nodes.extend(FBXPoseNode(node_id=bone_ids[i], matrix=world_transforms[i]) for i in range(bone_count))
        poses.append(FBXPose(id=pose_id, name=name, nodes=pose_nodes))

    # Attachments
    if mef.atta is not None:
        attachment_ids = [id_gen() for _ in range(len(mef.atta.content))]
        attachment_attribute_ids = [id_gen() for _ in range(len(mef.atta.content))]

        for i, item in enumerate(mef.atta.content):
            attachment_name = "attach_" + item.name_text
            translation_x, translation_y, translation_z = _position_to_fbx(
                item.position_x, item.position_y, item.position_z
            )
            rotation_x, rotation_y, rotation_z = _rotation_matrix_to_euler(
                item.m00,
                item.m01,
                item.m02,
                item.m10,
                item.m11,
                item.m12,
                item.m20,
                item.m21,
                item.m22,
            )
            node_attributes.append(
                FBXNodeAttribute(id=attachment_attribute_ids[i], name=attachment_name, type="Null", type_flags="Null")
            )
            models.append(
                FBXModel(
                    id=attachment_ids[i],
                    name=attachment_name,
                    type="Null",
                    translation=(translation_x, translation_y, translation_z),
                    rotation=(rotation_x, rotation_y, rotation_z),
                )
            )

        # Attachment connections: NodeAttribute -> Model, Attachment -> parent
        connections.extend(
            FBXConnection(source=attachment_attribute_ids[i], destination=attachment_ids[i])
            for i in range(len(mef.atta.content))
        )
        for i, item in enumerate(mef.atta.content):
            if item.bone_index != ATTA_NO_BONE and bone_ids and 0 <= item.bone_index < bone_count:
                connections.append(FBXConnection(source=attachment_ids[i], destination=bone_ids[item.bone_index]))
            else:
                connections.append(FBXConnection(source=attachment_ids[i], destination=0))

    fbx = FBX(
        name=name,
        geometries=geometries,
        materials=materials,
        videos=videos,
        textures=textures,
        node_attributes=node_attributes,
        models=models,
        skins=skins,
        poses=poses,
        connections=connections,
    )

    target_io, _ = fbx.model_dump_stream()
    return target_io, target_path


def _build_materials_and_textures(  # noqa: PLR0913
    mef: MEF,
    name: str,
    mesh_model_id: int,
    render_group_textures: list[RenderGroupTexture | None],
    face_count: int,
    id_gen: IdGenerator,
    connections: list[FBXConnection],
) -> tuple[list[FBXMaterial], list[FBXTexture], list[FBXVideo], list[int] | None, bool]:
    """Build one material per render group, sharing textures, and the per-face material index.

    Appends the material/texture/video FBX connections to "connections". Returns the
    materials, textures, videos, a per-face material-index list (the group ordinal for each face;
    "None" when there are no render groups — SEMS / no DNER — in which case a single placeholder
    material is emitted and the geometry stays single-material "AllSame"), and a "two_sided" flag
    that is True when any group uses a transparent texture (glass/fences are thin surfaces seen from
    both sides; FBX culling is per-mesh, so the whole mesh is exported two-sided).

    A transparent render group emits FBX material transparency ("TransparencyFactor" + a
    "TransparentColor" texture link) and sets its texture's "alpha_source="Alpha"" so the
    diffuse texture's own alpha drives per-texel opacity (alpha-test cutout vs. alpha-blend is
    finalized at Unity import time).
    """
    render_groups = mef.render_groups
    if not render_groups:
        material_id = id_gen()
        connections.append(FBXConnection(source=material_id, destination=mesh_model_id))
        return [FBXMaterial(id=material_id, name=name)], [], [], None, False

    materials: list[FBXMaterial] = []
    textures: list[FBXTexture] = []
    videos: list[FBXVideo] = []
    material_indices: list[int] = []
    texture_ids_by_name: dict[str, int] = {}
    transparent_group_count = 0

    for ordinal, render_group in enumerate(render_groups):
        resolved = render_group_textures[ordinal] if ordinal < len(render_group_textures) else None
        is_transparent = resolved is not None and resolved.transparency != TextureTransparency.OPAQUE
        if is_transparent:
            transparent_group_count += 1

        material_id = id_gen()
        material_name = resolved.texture_name if resolved is not None else f"{name}_{ordinal}"
        materials.append(
            FBXMaterial(id=material_id, name=material_name, transparency_factor=1.0 if is_transparent else None)
        )
        connections.append(FBXConnection(source=material_id, destination=mesh_model_id))

        if resolved is not None:
            texture_id = texture_ids_by_name.get(resolved.texture_name)
            if texture_id is None:
                texture_id = id_gen()
                video_id = id_gen()
                texture_ids_by_name[resolved.texture_name] = texture_id
                videos.append(
                    FBXVideo(id=video_id, name=resolved.texture_name, relative_filename=resolved.relative_output_path)
                )
                textures.append(
                    FBXTexture(
                        id=texture_id,
                        name=resolved.texture_name,
                        relative_filename=resolved.relative_output_path,
                        alpha_source="Alpha" if is_transparent else "None",
                    )
                )
                connections.append(FBXConnection(source=video_id, destination=texture_id))
            connections.append(FBXConnection(source=texture_id, destination=material_id, property="DiffuseColor"))
            if is_transparent:
                # Texture alpha drives material opacity via the TransparentColor channel.
                connections.append(
                    FBXConnection(source=texture_id, destination=material_id, property="TransparentColor")
                )

        material_indices.extend([ordinal] * render_group.face_count)

    logger.debug(
        "materials for %s: %d groups, %d transparent (two_sided=%s)",
        name,
        len(render_groups),
        transparent_group_count,
        transparent_group_count > 0,
    )

    # Faces are grouped consecutively by render group, so the lengths should match. Guard
    # against any surprise mismatch by dropping back to a single-material ("AllSame") mesh.
    if len(material_indices) != face_count:
        return materials, textures, videos, None, transparent_group_count > 0
    return materials, textures, videos, material_indices, transparent_group_count > 0
