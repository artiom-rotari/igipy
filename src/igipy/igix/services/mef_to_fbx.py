"""Export an early/beta IGI2 ("igix") MEF model to FBX 7.5 ASCII.

This mirrors :func:`igipy.igi2.services.mef_to_fbx.mef_to_fbx` and reuses every FBX
and texture-resolution helper from the IGI2 exporter (which is Unity-verified). Only
two things are igix-specific:

* the model is parsed with :class:`igipy.igix.formats.mef.MEF`; and
* **type-3 (building) models route through the static extractor** — the igix type-3
  vertex carries an authored per-vertex normal and a diffuse UV (the retail IGI2
  type-3 vertex dropped the normal, so its exporter computes one instead).

Everything else — the Z-up→Y-up swizzle and FBX-centimeter scale (``SCALE = 100 /
4096``), clockwise→counter-clockwise winding reversal, skeletal bind pose / skinning,
attachments, per-render-group textures and transparency — is imported unchanged.
"""

import logging
from collections import defaultdict
from io import BytesIO
from pathlib import Path

from igipy.core.base import FileIgnored
from igipy.core.formats.fbx import (
    FBX,
    FBXCluster,
    FBXConnection,
    FBXGeometry,
    FBXModel,
    FBXNodeAttribute,
    FBXPose,
    FBXPoseNode,
    FBXSkin,
    IdGenerator,
)
from igipy.igi2.formats.mef import ATTA_NO_BONE, MODEL_TYPE_SKELETAL
from igipy.igi2.services.iff_to_fbx import _position_to_fbx
from igipy.igi2.services.mef_texture_resolver import (
    RenderGroupTexture,
    resolve_render_group_textures,
)
from igipy.igi2.services.mef_to_fbx import (
    _accumulate_bone_offsets,
    _build_materials_and_textures,
    _compute_world_transforms,
    _extract_sems,
    _extract_skeletal,
    _extract_static,
    _mat4_inverse_row,
    _rotation_matrix_to_euler,
    reverse_triangle_winding,
)
from igipy.igix.formats.mef import MEF

logger = logging.getLogger(__name__)


# noinspection DuplicatedCode,PyUnusedLocal
def mef_to_fbx(  # noqa: C901, PLR0912, PLR0915
    source_io: BytesIO,
    source_path: Path | None = None,
    collect_path: Path | None = None,
) -> tuple[BytesIO, Path | None]:
    """Export an igix MEF model to FBX.

    When "collect_path" (the collect-source root) and "source_path" are both given, each
    render group is bound to its diffuse texture resolved through the level material table
    (see "igi2.services.mef_texture_resolver"). Without them the mesh exports untextured
    (one placeholder material), preserving backward compatibility.
    """
    target_path: Path | None = source_path.with_suffix(".fbx") if source_path is not None else None
    mef = MEF.model_validate_stream(source_io)

    name = source_path.stem if source_path else "mef_model"
    id_gen = IdGenerator()

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
    elif model_type == MODEL_TYPE_SKELETAL:
        positions, faces, normals, uvs = _extract_skeletal(mef, accumulated_bone_offsets)
    else:
        # Type 0 (static) and type 3 (building) both use the static extractor: unlike retail
        # IGI2, the igix type-3 vertex carries an authored per-vertex normal and diffuse UV,
        # so its stored normals are emitted directly (no compute_vertex_normals fallback).
        positions, faces, normals, uvs = _extract_static(mef)

    # Some MEFs carry no render geometry (kill/trigger volumes, control points, proxy/reference
    # models with an empty XTRV). Emitting them produces a degenerate FBX ("Vertices: 0") that
    # tools import as an empty mesh; skip them cleanly instead.
    if not positions or not faces:
        logger.debug(
            "[FIX] skipping igix MEF with empty render geometry: model=%s type=%s sems=%s", name, model_type, is_sems
        )
        raise FileIgnored(f"MEF has no render geometry: {name}")

    # IGI2/igix wind front faces clockwise; FBX/Unity expect counter-clockwise, so the
    # camera-facing triangles would otherwise be culled. Reverse winding for emission;
    # normals were computed from the original winding and stay unchanged.
    faces = reverse_triangle_winding(faces)

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
        # Absolute (accumulated) bone positions drive world transforms, bind pose, and the
        # per-bone local translation, matching the world-space vertices baked in _extract_skeletal.
        rest_offsets = accumulated_bone_offsets
        bone_count = mef.bone_count
        parents = mef.reih.bones_parents
        bone_names = mef.bone_names
        bone_ids = [id_gen() for _ in range(bone_count)]
        bone_attribute_ids = [id_gen() for _ in range(bone_count)]
        world_transforms = _compute_world_transforms(bone_count, rest_offsets)

        for i in range(bone_count):
            node_attributes.append(
                FBXNodeAttribute(
                    id=bone_attribute_ids[i],
                    name=bone_names[i],
                    type="LimbNode",
                    type_flags="Skeleton",
                )
            )
            # rest_offsets are absolute (accumulated); a bone node's LOCAL translation is its
            # world position minus its parent's (which equals the raw REIH offset).
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

        # Skin deformers. igix skeletal influence is RIGID: each vertex binds 100% to its single
        # bone (the stored bone_weight is not a usable skin weight); use weight 1.0.
        skin_id = id_gen()
        cluster_ids = [id_gen() for _ in range(bone_count)]

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
