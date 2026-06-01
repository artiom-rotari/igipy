"""Generate smooth vertex normals for MEF meshes that ship without them.

Type-3 (lightmapped) MEF models bake lighting into a lightmap and store no
per-vertex normal. Without normals an engine recalculates them on import — Unity
in particular then renders inverted / see-through faces. This computes
area-weighted smooth normals from the triangle mesh, in the SAME coordinate
space as the supplied positions (so the result is used as-is, no extra swizzle).

Winding: IGI2 triangle winding is opposite to the "(b - a) x (c - a)"
convention — verified across type-0 models that DO carry authored normals
(geometric vs authored agreed for only 3/809 faces, opposed for 806). The face
normal therefore uses "(c - a) x (b - a)" so generated normals match the
authored orientation.
"""


def compute_vertex_normals(
    positions: list[tuple[float, float, float]],
    faces: list[tuple[int, int, int]],
) -> list[tuple[float, float, float]]:
    """Return one unit normal per position, area-weighted across adjacent faces."""
    accumulated: list[list[float]] = [[0.0, 0.0, 0.0] for _ in positions]
    for index_a, index_b, index_c in faces:
        ax, ay, az = positions[index_a]
        bx, by, bz = positions[index_b]
        cx, cy, cz = positions[index_c]
        # (c - a) x (b - a): flipped winding to match IGI2 authored normals.
        # The magnitude equals twice the triangle area, giving area weighting.
        edge_u_x, edge_u_y, edge_u_z = cx - ax, cy - ay, cz - az
        edge_v_x, edge_v_y, edge_v_z = bx - ax, by - ay, bz - az
        normal_x = edge_u_y * edge_v_z - edge_u_z * edge_v_y
        normal_y = edge_u_z * edge_v_x - edge_u_x * edge_v_z
        normal_z = edge_u_x * edge_v_y - edge_u_y * edge_v_x
        for index in (index_a, index_b, index_c):
            accumulated[index][0] += normal_x
            accumulated[index][1] += normal_y
            accumulated[index][2] += normal_z

    normals: list[tuple[float, float, float]] = []
    for normal_x, normal_y, normal_z in accumulated:
        length = (normal_x * normal_x + normal_y * normal_y + normal_z * normal_z) ** 0.5
        if length > 1e-9:  # noqa: PLR2004
            normals.append((normal_x / length, normal_y / length, normal_z / length))
        else:
            normals.append((0.0, 0.0, 1.0))
    return normals
