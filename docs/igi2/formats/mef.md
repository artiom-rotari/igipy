[Back to README](../../../README.md)

# MEF Format — 3D Mesh Model

MEF files store 3D mesh models for characters, objects, buildings, and vehicles. They are located in `models/`
directories inside `.res` archives and use IGI's ILFF container format with content type `OCEM` (MECO reversed). Two
structural variants exist: **standard** (7,526 files) with full render mesh data in three model types (0, 1, 3), and *
*SEMS** (82 files) containing only a simplified collision mesh.

## Structure Overview

### Standard Variant (7,526 files)

```
+---------------------------------------------------+
|  ILFF Header (content_type = "OCEM")              |
+---------------------------------------------------+
|  HSEM - Mesh Header (176 bytes, always present)   |
+---------------------------------------------------+
|  REIH - Bone Hierarchy (type 1 only)              |
|  MANB - Bone Names (type 1 only)                  |
+---------------------------------------------------+
|  ATTA - Attachment Points (72 bytes per entry)     |
|  XTVM - MagicVertex Positions (16 bytes per entry) |
|  TROP - Portal descriptors (5 uint32 per entry)   |
|  XVTP - Vertex Positions (float3 per entry)       |
|  CFTP - Face Properties (3 uint32 per entry)      |
+---------------------------------------------------+
|  WOLG - Glow Points (optional, before D3DR)       |
+---------------------------------------------------+
|  D3DR - Render State (36/40/44 bytes by type)     |
|  ECAF - Render Faces (uint16 triangle indices)    |
|  DNER - Render Groups (28 or 32 bytes per entry)  |
|  XTRV - Vertices (28/32/40 bytes by type)         |
+---------------------------------------------------+
|  PMTL - Lightmap params / LTMP (type 3 only)      |
+---------------------------------------------------+
|  HSMC - Collision Header (optional)               |
|  XTVC - Collision Vertices (repeated ×2)          |
|  ECFC - Collision Faces (repeated ×2)             |
|  TAMC - Collision Materials (repeated ×2)         |
|  HPSC - Collision Spheres (repeated ×2)           |
+---------------------------------------------------+
|  HPRM - Morph Targets (optional, after collision) |
|  TXAN - Texture Animation (1 file only)           |
+---------------------------------------------------+
```

### SEMS Variant — Simplified Collision Mesh (82 files)

```
+---------------------------------------------------+
|  ILFF Header (content_type = "OCEM")              |
+---------------------------------------------------+
|  SEMS - Submesh Header (28 bytes per entry)       |
|  XTVS - Simplified Vertices (12 bytes per entry)  |
|  CAFS - Simplified Faces (28 bytes per entry)     |
|  EGDE - Edge List (8 bytes per entry)             |
+---------------------------------------------------+
```

All chunk fourccs are reversed names: HSEM=MESH, ECAF=FACE, DNER=REND, XTRV=VRTX, XTVM=MVTX, TROP=PORT, XVTP=PTVX,
CFTP=PTFC, ATTA=ATTA, WOLG=GLOW, HPRM=MRPH, PMTL=LTMP, HSMC=CMSH, XTVC=CVTX, ECFC=CFCE, TAMC=CMAT, HPSC=CSPH, REIH=HIER,
MANB=BNAM, SEMS=SMES, XTVS=SVTX, CAFS=SFAC, EGDE=EDGE.

## Statistics

| Metric                 | Value                                                 |
|------------------------|-------------------------------------------------------|
| Total files            | 7,609                                                 |
| Valid OCEM files       | 7,608 (1 non-ILFF: `menusystem/models/minefield.mef`) |
| Standard variant       | 7,526 files (HSEM-based render mesh)                  |
| SEMS variant           | 82 files (simplified collision mesh only)             |
| Location               | `models/` directories inside `.res` archives          |
| Size range             | 416 -- 1,663,236 bytes                                |
| Type 0 (static)        | 1,853 files                                           |
| Type 1 (skeletal)      | 240 files                                             |
| Type 3 (static + PMTL) | 5,433 files                                           |

## Model Types

| Property        | Type 0       | Type 1              | Type 3                    |
|-----------------|--------------|---------------------|---------------------------|
| Files           | 1,853        | 240                 | 5,433                     |
| Vertex size     | 32 bytes     | 40 bytes            | 28 bytes                  |
| D3DR size       | 36 bytes     | 40 bytes            | 44 bytes                  |
| DNER entry size | 32 bytes     | 32 bytes            | 28 bytes                  |
| Has REIH+MANB   | No           | Yes (always)        | No                        |
| Has PMTL        | No           | No                  | Yes (always)              |
| Has WOLG        | 106 files    | Never               | 885 files                 |
| Has HPRM        | 178 files    | 37 files            | Never                     |
| Description     | Static props | Characters/vehicles | Buildings/terrain objects |

## HSEM — Mesh Header

The chunk fourcc `HSEM` is `MESH` reversed. Always 176 bytes. The first 156 bytes are parsed as `<12I12f6If6H5I`; the
remaining 20 bytes are zeros.

```
Offset  Size  Type     Field
0       4     uint32   Unknown (varies)
4       4     uint32   Created year
8       4     uint32   Created month
12      4     uint32   Created day
16      4     uint32   Created hour
20      4     uint32   Created minute
24      4     uint32   Created second
28      4     uint32   Created millisecond
32      4     uint32   Model type (0, 1, or 3)
36      4     uint32   Unknown
40      4     uint32   Unknown
44      4     uint32   Unknown
48      48    float[12] Bounding box (two sets of min/max float3)
96      4     uint32   Render face count
100     4     uint32   Render vertex count (XTRV)
104     4     uint32   Unknown
108     4     uint32   Collision face count total (ECFC)
112     4     uint32   Collision vertex count total (XTVC)
116     4     uint32   Unknown
120     4     float    Unknown (bounding radius?)
124     4     uint32   XTVM entry count
128     4     uint32   ATTA entry count (in entries, not bytes)
132     2     uint16   XVTP entry count
134     2     uint16   CFTP entry count
136     2     uint16   TROP entry count
138     2     uint16   Zero
140     2     uint16   Zero
142     2     uint16   Zero
144     20    uint32[5] Zeros (padding)
156     20    -        Zeros (padding)
```

## XTRV — Vertices

The chunk fourcc `XTRV` is `VRTX` reversed. Contains all render vertices as a flat array. Vertex format depends on the
model
type.

### Type 0 — Static Vertex (32 bytes)

```
Offset  Size  Type     Field
0       12    float3   Position (x, y, z)
12      12    float3   Normal (x, y, z)
24      8     float2   Texture UV (u, v)
```

### Type 1 — Skeletal Vertex (40 bytes)

```
Offset  Size  Type     Field
0       12    float3   Position (x, y, z)
12      12    float3   Normal (x, y, z)
24      8     float2   Texture UV (u, v)
32      4     float    Bone weight (0.0 to 1.0)
36      2     uint16   Vertex index (self-reference)
38      2     uint16   Bone index
```

Weight of 1.0 means fully influenced by the referenced bone. Values less than 1.0 indicate blending with a parent or
adjacent bone (the complement weight is implicit).

### Type 3 — Compact Static Vertex (28 bytes)

Type-3 (lightmapped static) vertices store **two UV sets and no per-vertex normal** — for
lightmapped geometry, lighting is baked into the lightmap, so runtime normals are unnecessary.

```
Offset  Size  Type     Field
0       12    float3   Position (x, y, z)
12      4     float    Diffuse U          (may exceed [0,1] for tiling)
16      4     float    Diffuse V, stored pre-flipped as (1 - source_v)
20      4     float    Lightmap U         (second UV set, [0,1])
24      4     float    Lightmap V         (second UV set, [0,1])
```

Validated as 28 bytes across all 5,433 type-3 files. **Decoded** against the IGI2 Map Editor's
text-MEF sources (see *Provenance & Methodology*): the diffuse UV matches the text `UV()` command
exactly across **128,869 / 128,869 type-3 vertices (100%)** in 174 paired models, with V stored
already flipped (`1 - source_v`). The parser exposes `uv_u`/`diffuse_v`/`lightmap_u`/`lightmap_v`
plus a `uv_v` property (`1 - diffuse_v`) so all XTRV variants share the same `uv_u`/`uv_v`
semantics and the `(uv_u, 1.0 - uv_v)` export convention applies uniformly.

## ECAF — Render Faces

The chunk fourcc `ECAF` is `FACE` reversed. Contains triangle indices as a flat array of little-endian `uint16` values.
Each triangle uses 3 consecutive indices (6 bytes per face).

```
face_count = len(ECAF) / 6
max_index  = render_vertex_count - 1
```

Present in all 7,526 standard variant files.

## DNER — Render Groups

The chunk fourcc `DNER` is `REND` reversed. Partitions the mesh into render groups (draw calls). Each group references a
contiguous range of vertices and indices from XTRV and ECAF.

**Validated across 7,499 files with zero failures.** The cumulative index/vertex offsets always sum to the totals from
HSEM.

### Type 0 and Type 1 — 32 bytes per entry

```
Offset  Size  Type     Field
0       4     uint32   Material flags
4       12    float3   Group center (bounding center)
16      2     uint16   Index start (offset into ECAF, in uint16 elements)
18      2     uint16   Face count (number of triangles)
20      2     uint16   Vertex start (offset into XTRV)
22      2     uint16   Vertex count
24      2     uint16   Group index (sequential: 0, 1, 2, ...)
26      2     int16    Sentinel (-1 typically)
28      2     int16    Unknown (-1 or small value)
30      2     int16    Unknown (0 or small value)
```

### Type 3 — 28 bytes per entry

```
Offset  Size  Type     Field
0       12    float3   Group center (bounding center)
12      4     float    Bounding radius? (uint16 pair at 12/14 reads as a positive float;
                       NOT a material index — see material mapping below)
16      2     uint16   Index start (offset into ECAF, in uint16 elements)
18      2     uint16   Face count (number of triangles)
20      2     uint16   Vertex start (offset into XTRV)
22      2     uint16   Vertex count
24      2     uint16   Group index (sequential: 0, 1, 2, ...)
26      2     uint16   Reserved (always 0)
```

**Group ↔ material/texture mapping (decoded).** Each DNER render group is one draw call for one
*renderable* material — a material that has a `DiffuseTMap`. Collision-only materials (no
`DiffuseTMap`, e.g. `collision01_*`) get no render group. The groups are emitted in source
material-id order, so the group ordinal maps to the N-th renderable material → its texture. Verified
by matching per-group `face_count` to the text per-material face counts (e.g. `407_18_1` groups
`[183,209,13,6,9,288,20,10,60]` exactly equal the renderable-material face counts in id order,
skipping the texture-less collision material). This is a strong heuristic, **not absolute** — the
compiler can split or reorder groups (observed in `631_04_2`: same total faces, different partition).
The texture *filename* is not stored in the binary mesh; resolving it needs the model/texture naming
convention and the MTP material system.

### Offset Rule

Index and vertex ranges are contiguous and non-overlapping:

```
group[i].index_start  = group[i-1].index_start + group[i-1].face_count * 3
group[i].vertex_start = group[i-1].vertex_start + group[i-1].vertex_count
sum(face_count)       = HSEM.render_face_count
sum(vertex_count)     = HSEM.render_vertex_count (type 0/3) or D3DR[4] (type 1)
```

## D3DR — Render State

The chunk fourcc `D3DR` is `RD3D` reversed. A single entry containing a render configuration. Size depends on the model
type.

### Type 0 — 36 bytes (9 uint32)

```
Index  Field
[0]    Flags (always 4)
[1]    Total face count
[2]    Render group count (DNER entry count)
[3]    Total vertex count
[4-8]  Zeros
```

### Type 1 — 40 bytes (10 uint32)

```
Index  Field
[0]    Flags (always 4)
[1]    Total face count
[2]    Render group count (DNER entry count)
[3]    Unknown
[4]    DNER total vertex count (sum of DNER vertex counts)
[5]    XTRV total vertex count (may exceed [4] for skeletal meshes)
[6-9]  Zeros
```

For skeletal meshes, the XTRV vertex buffer may contain more vertices than the DNER render groups reference. The ECAF
indices reference only the first `D3DR[4]` vertices.

### Type 3 — 44 bytes (11 uint32)

```
Index  Field
[0]    Flags (always 4)
[1]    Unknown
[2]    Total face count
[3]    Render group count (DNER entry count)
[4]    Total vertex count
[5-10] Zeros
```

## REIH — Bone Hierarchy (Type 1 Only)

The chunk fourcc `REIH` is `HIER` reversed. Present in all 240 type-1 files. Same format as the IFF animation REIH
chunk.

```
Offset          Size              Type       Field
0               bone_count        byte[]     Bone type flags (one per bone)
bone_count      1                 byte       Padding (0x00)
bone_count + 1  bone_count * 12   float3[]   Rest-pose offsets (3 floats per bone)
```

Size = `bone_count + 1 + bone_count * 12`. Three skeleton sizes are observed:

| Bones | REIH size | Files |
|-------|-----------|-------|
| 31    | 404 bytes | 237   |
| 47    | 612 bytes | 1     |
| 28    | 364 bytes | 2     |

The 31-bone skeleton is the standard humanoid skeleton. Bone type flags match IFF animation types (0 = end effector, 1 =
rotation, 2 = full transform, 3 = position + rotation).

## MANB — Bone Names (Type 1 Only)

The chunk fourcc `MANB` is `BNAM` reversed. Contains `bone_count` fixed 16-byte null-padded ASCII strings.

```
Total size = bone_count * 16
```

31-bone skeleton names:

| Index | Name            | Index | Name               |
|-------|-----------------|-------|--------------------|
| 0     | center          | 16    | upper left arm     |
| 1     | lower body      | 17    | upper right arm    |
| 2     | upper left leg  | 18    | left toe end       |
| 3     | upper right leg | 19    | right toe end      |
| 4     | upper body      | 20    | head end           |
| 5     | lower left leg  | 21    | lower left arm     |
| 6     | lower right leg | 22    | lower right arm    |
| 7     | shoulders       | 23    | left hand          |
| 8     | left foot       | 24    | right hand         |
| 9     | right foot      | 25    | upper left finger  |
| 10    | rotate_head     | 26    | upper right finger |
| 11    | rotate_left     | 27    | lower left finger  |
| 12    | rotate_right    | 28    | lower right finger |
| 13    | left toe        | 29    | left fingers end   |
| 14    | right toe       | 30    | right fingers end  |
| 15    | head            |       |                    |

Names are truncated to 16 characters (e.g., "upper left finge" for "upper left finger").

## ATTA — Attachment Points

72 bytes per entry. Defines named attachment slots on the model. Corresponds to the `AttachObject()` and
`AttachObjectBoneID()` commands in the text source format.

```
Offset  Size  Type      Field
0       16    char[16]  Attachment name (null-padded ASCII)
16      36    float[9]  3×3 rotation matrix (m00, m01, m02, m10, m11, m12, m20, m21, m22)
52      12    float[3]  Position (x, y, z)
64      4     int32     Attachment index (sequential: 0, 1, 2, ...)
68      4     int32     Bone index (-1 = world space, ≥0 = attached to bone)
```

Common attachment names: `shadow_1`, `weapon`, `helmet`, model-specific references (e.g., `100_02_1` for submodel
attachments).

| Entry count    | Files |
|----------------|-------|
| 0 (empty ATTA) | 6,748 |
| 1              | 248   |
| 2              | 138   |
| 3              | 72    |
| 4              | 72    |
| 5+             | 248   |

## WOLG — Glow Points (Optional)

The chunk fourcc `WOLG` is `GLOW` reversed. Present in 991 files (type 0 and type 3 only). Each entry is 32 bytes
defining a light-emitting point on the model.

```
Offset  Size  Type     Field
0       12    float3   Position (x, y, z)
12      4     float    Radius
16      4     float    Color R (0.0 to 1.0)
20      4     float    Color G (0.0 to 1.0)
24      4     float    Color B (0.0 to 1.0)
28      4     -        Padding (0xABABABAB)
```

## HPRM — Morph Targets (Optional)

The chunk fourcc `HPRM` is `MRPH` reversed. Present in 215 files (type 0 and type 1 only). Contains morph target vertex
displacements for facial animation or deformation.

```
Offset  Size  Type     Field
0       4     uint32   Morph vertex count
4       60    -        Padding (zeros)
64      var   -        Morph entries (variable-size, structure varies)
```

The internal entry format varies between files (16 to 44+ bytes per entry observed). Each entry appears to contain a
vertex index followed by position deltas, but the exact structure depends on context and is not fully decoded.

## PMTL — Lightmap Parameters (Type 3 Only)

The chunk fourcc `PMTL` is `LTMP` reversed — **`LightMaP`**, not a material table. Present as a
single entry in all 5,433 type-3 (lightmapped) files. This reclassification is consistent with
type-3 being lightmapped (it also carries the lightmap UV set in XTRV). Each entry is 8 bytes.

```
Offset  Size  Type     Field
0       2     uint16   Lightmap count? (small, 2..41; near-equal to offset 2)
2       2     uint16   Lightmap count? (small, 2..41)
4       2     uint16   Reserved (always 0)
6       2     uint16   Reserved (always 0)
```

The two leading uint16 are small, near-equal counts (lightmap pieces / atlas metadata); the
trailing two are always zero. The exact meaning of the two counts is not yet pinned down — see the
MTP material/texture work.

## Collision Mesh

Optional collision data is present in 3,205 files (42%). Always structured as 2 submeshes: HSMC contains 2 entries, the
second submesh is always empty (zero counts). Each submesh has its own XTVC/ECFC/TAMC/HPSC chunk set.

### HSMC — Collision Header

```
Offset  Size  Type     Field
0       4     uint32   ECFC entry count (collision faces)
4       4     uint32   XTVC entry count (collision vertices)
8       4     uint32   TAMC entry count (collision materials)
12      4     uint32   HPSC entry count (collision spheres)
16      16    uint32[4] Zeros
```

One HSMC item per collision submesh (always 2). The counts match the number of entries in the corresponding
XTVC/ECFC/TAMC/HPSC chunks for that submesh.

### XTVC — Collision Vertices (20 bytes per entry)

```
Offset  Size  Type     Field
0       20    float[5] Position + unknown (x, y, z, w, unknown)
```

### ECFC — Collision Faces (12 bytes per entry)

```
Offset  Size  Type     Field
0       12    uint16[6] Triangle indices + material/flags
```

### TAMC — Collision Materials (16 bytes per entry)

```
Offset  Size  Type     Field
0       16    int16[8] Material properties
```

### HPSC — Collision Spheres (24 bytes per entry)

```
Offset  Size  Type     Field
0       16    float[4] Sphere center + radius (x, y, z, r)
16      8     int16[4] Hierarchy indices
```

## SEMS Variant — Simplified Collision Mesh

82 files use a simplified collision-only format with no render mesh data. The first chunk is `SEMS` instead of `HSEM`.
These files contain collision geometry as convex submeshes with face plane equations and edge lists.

### SEMS — Submesh Header (28 bytes per entry)

The chunk fourcc `SEMS` is `SMES` reversed. Each entry defines offsets and counts into the XTVS, CAFS, and EGDE arrays
for one convex submesh.

```
Offset  Size  Type    Field
0       4     int32   CAFS start index
4       4     int32   XTVS start index
8       4     int32   EGDE start index
12      4     int32   CAFS count (faces in this submesh)
16      4     int32   XTVS count (vertices in this submesh)
20      4     int32   EGDE count (edges in this submesh)
24      4     int32   Sentinel (always -1)
```

### XTVS — Simplified Vertices (12 bytes per entry)

The chunk fourcc `XTVS` is `SVTX` reversed. Float3 vertex positions.

```
Offset  Size  Type     Field
0       12    float3   Position (x, y, z)
```

### CAFS — Simplified Faces (28 bytes per entry)

The chunk fourcc `CAFS` is `SFAC` reversed. Each face stores 3 vertex indices and a plane equation (normal + distance).

```
Offset  Size  Type     Field
0       4     uint32   Vertex index A
4       4     uint32   Vertex index B
8       4     uint32   Vertex index C
12      4     float    Normal X
16      4     float    Normal Y
20      4     float    Normal Z
24      4     float    Distance (plane equation d)
```

### EGDE — Edge List (8 bytes per entry)

The chunk fourcc `EGDE` is `EDGE` reversed. Each edge connects two vertices.

```
Offset  Size  Type     Field
0       4     uint32   Vertex index A
4       4     uint32   Vertex index B
```

## Other Chunks

| Chunk | Reversed | Entry size        | Description                                                                                                                                                                                                                                                                                                                                                                   |
|-------|----------|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| XTVM  | MVTX     | 16 bytes (`<3fi`) | MagicVertex positions (position_x, position_y, position_z, param) — special vertices for glow, damage areas, or attachment helpers                                                                                                                                                                                                                                            |
| TROP  | PORT     | 20 bytes (`<5I`)  | **Portal descriptors** — `(range_a_start, range_a_count, range_b_start, range_b_count, reference_index)`. The two `*_start` fields are cumulative (running sum of the preceding `*_count`), verified across all 13 TROP-bearing editor samples. Counts are typically 4 + 2 → a portal quad (4 vertices + 2 triangles); `reference_index` points at an external group/zone id. |
| XVTP  | PTVX     | 12 bytes (`<3f`)  | Source vertex positions (position_x, position_y, position_z) — original mesh vertices before D3D compilation                                                                                                                                                                                                                                                                  |
| CFTP  | PTFC     | 12 bytes (`<3I`)  | Source face indices (index_a, index_b, index_c) — original triangle connectivity before D3D compilation                                                                                                                                                                                                                                                                       |
| TXAN  | NAXT     | varies            | Texture animation (only 1 file in entire dataset)                                                                                                                                                                                                                                                                                                                             |

## Chunk Presence by Model Type

### Standard Variant (7,526 files)

| Chunk | Type 0 (1,853) | Type 1 (240) | Type 3 (5,433) |
|-------|----------------|--------------|----------------|
| HSEM  | Always         | Always       | Always         |
| ATTA  | Always         | Always       | Always         |
| XTVM  | Always         | Always       | Always         |
| TROP  | Always         | Always       | Always         |
| XVTP  | Always         | Always       | Always         |
| CFTP  | Always         | Always       | Always         |
| D3DR  | Always         | Always       | Always         |
| ECAF  | Always         | Always       | Always         |
| DNER  | Always         | Always       | Always         |
| XTRV  | Always         | Always       | Always         |
| REIH  | Never          | Always       | Never          |
| MANB  | Never          | Always       | Never          |
| PMTL  | Never          | Never        | Always         |
| WOLG  | 106 files      | Never        | 885 files      |
| HPRM  | 178 files      | 37 files     | Never          |
| HSMC+ | 750 files      | 99 files     | 2,356 files    |
| TXAN  | 1 file         | Never        | Never          |

### SEMS Variant (82 files)

| Chunk | Present |
|-------|---------|
| SEMS  | Always  |
| XTVS  | Always  |
| CAFS  | Always  |
| EGDE  | Always  |

## Chunk Combinations

15 unique chunk sequences observed across 7,608 OCEM files. Collision data (HSMC+) always has exactly 2 submeshes (the
second is empty).

| #  | Sequence                                               | Count  |
|----|--------------------------------------------------------|--------|
| 1  | HSEM→ATTA→XTVM→TROP→XVTP→CFTP→D3DR→ECAF→DNER→XTRV→PMTL | 2,534  |
| 2  | …→XTRV→PMTL→HSMC→(XTVC→ECFC→TAMC→HPSC)×2               | 2,014  |
| 3  | …→XTRV (base only, no optional chunks)                 | 976    |
| 4  | …→XTRV→HSMC→(XTVC→ECFC→TAMC→HPSC)×2                    | 592    |
| 5  | …→WOLG→D3DR→…→XTRV→PMTL                                | 543    |
| 6  | …→WOLG→…→PMTL→HSMC→(collision)×2                       | 342    |
| 7  | HSEM→REIH→MANB→ATTA→…→XTRV                             | 141    |
| 8  | …→XTRV→HSMC→(collision)×2→HPRM                         | 110    |
| 9  | **SEMS→XTVS→CAFS→EGDE**                                | **82** |
| 10 | …→XTRV→HPRM                                            | 68     |
| 11 | HSEM→REIH→MANB→…→HSMC→(collision)×2                    | 62     |
| 12 | …→WOLG→…→XTRV                                          | 59     |
| 13 | …→WOLG→…→HSMC→(collision)×2                            | 47     |
| 14 | HSEM→REIH→MANB→…→HSMC→(collision)×2→HPRM               | 37     |
| 15 | …→HSMC→(collision)×2→TXAN                              | 1      |

## Parser Status

The `mef.py` parser successfully parses all 7,608 valid MEF files (100% coverage). Both the standard variant (7,526
files) and the SEMS variant (82 files) are supported.

Previously fixed issues: ECAF handler, XTRVItem3 size, ATTA entry size, REIH/MANB/WOLG/HPRM handlers, DNERItem0 format,
collision chunk sizes (XTVC 16→20, ECFC 8→12, TAMC 12→16).

## Source Format (Text MEF)

Binary MEF files are compiled from text source files using the `gconv.exe` tool (originally from a 3ds Max export
pipeline). A set of 1,495 reverse-engineered text `.MEF` files provides the original source format, confirming the
purpose of many binary chunks.

### Compilation Pipeline

```
3ds Max → Text .MEF (source) → gconv.exe → Binary .mef (ILFF/OCEM)
```

The compiler script (`.qsc` file) specifies settings:

```
SetScale(40.96);
SetTargetPlatform("PC");
SetModelDirectory("models");
SetTextureDirectory("textures");
```

### Text MEF Commands (22 total)

**Material Section** (before `BreakScript()`):

| Command                                                           | Args | Binary Target                 |
|-------------------------------------------------------------------|------|-------------------------------|
| `NewObject(name)`                                                 | 1    | Object name metadata          |
| `Material(id, name, r,g,b, amb_r,g,b, spec_r,g,b, unk, unk, unk)` | 14   | Material properties           |
| `MaterialShininess(id, value)`                                    | 2    | Material shininess            |
| `DiffuseTMap(id, path, u_tile, v_tile)`                           | 4    | Diffuse texture reference     |
| `OpacityTMap(id, path, u_tile, v_tile)`                           | 4    | Opacity texture (365 files)   |
| `ReflectionTMap(id, path, u_tile, v_tile)`                        | 4    | Reflection texture (23 files) |
| `BumpTMap(id, path, u_tile, v_tile)`                              | 4    | Bump texture (4 files)        |
| `MaterialTransparencyType(id, type)`                              | 2    | Transparency mode             |
| `BreakScript()`                                                   | 0    | Section separator             |

**Bone Section** (type 1 only):

| Command                              | Args | Binary Target                   |
|--------------------------------------|------|---------------------------------|
| `Bone(id, name, parent_id, x, y, z)` | 6    | REIH (hierarchy) + MANB (names) |
| `BuildHierarchy()`                   | 0    | End of bone definitions         |

**Geometry Section:**

| Command                                                  | Args | Binary Target                                |
|----------------------------------------------------------|------|----------------------------------------------|
| `Vertex(id, x, y, z)`                                    | 4    | XVTP (source positions) + compiled into XTRV |
| `Normal(id, nx, ny, nz)`                                 | 4    | Compiled into XTRV                           |
| `Face(id, v0, v1, v2, n0, n1, n2, mat_id)`               | 8    | CFTP (source indices) + ECAF + DNER          |
| `UV(id, u0, v0, u1, v1, u2, v2)`                         | 7    | Compiled into XTRV                           |
| `VertexInfluenceRigid(bone_id, vtx_id, x, y, z, weight)` | 6    | Compiled into XTRV type 1                    |

**Optional Commands:**

| Command                                  | Args | Binary Target         | Frequency |
|------------------------------------------|------|-----------------------|-----------|
| `AttachObject(name, id, 9×rot, 3×pos)`   | 14   | ATTA                  | 96 files  |
| `AttachObjectBoneID(id, bone_id)`        | 2    | ATTA bone_index field | 96 files  |
| `MagicVertex(id, type, x, y, z, param)`  | 6    | XTVM                  | 72 files  |
| `Glow(x, y, z, radius, r, g, b)`         | 7    | WOLG                  | 150 files |
| `MorphChannel(id, name)`                 | 2    | HPRM                  | 35 files  |
| `MorphVertex(ch_id, vtx_id, dx, dy, dz)` | 5    | HPRM                  | 35 files  |

### Compilation Transformations

The compiler merges separate `Vertex`, `Normal`, and `UV` data into per-vertex `XTRV` entries. This involves vertex
splitting: source vertices referenced by multiple faces with different normals or UVs are duplicated in the output. The
`XVTP` and `CFTP` chunks preserve the original source indices.

Material definitions, texture paths, and other metadata are consumed by the compiler to generate `D3DR` render state and
`DNER` render groups but are not stored verbatim in the binary format.

## Open Questions

### Important for Completeness

- **HPRM morph targets**: The text source confirms structure: `MorphChannel(id, name)` defines channels,
  `MorphVertex(ch_id, vtx_id, dx, dy, dz)` defines per-vertex deltas. However, the binary packing within the HPRM chunk
  varies between files and is not fully decoded. *(Not present in the Map Editor sample set — 0/198 models — so it could
  not be decoded via recompiled experiments; remains observational on the full game corpus.)*

- **Type-1 extra vertices**: Skeletal meshes often have `D3DR[5]` (XTRV count) > `D3DR[4]` (DNER-referenced count). The
  extra vertices may be LOD data, morph targets, or collision proxies. *(Not present in the Map Editor sample set —
  0/198 models are type-1 — so this is observational only.)*

- **PMTL (LTMP) lightmap counts**: PMTL is reclassified as lightmap parameters (fourcc `LTMP`), not a material table.
  The two leading `uint16` are small near-equal counts (lightmap pieces / atlas metadata); their exact meaning is not
  yet pinned down.

- **DNER offset 12/14 (type 3)**: the `uint16` pair reads as a plausible positive float (likely a per-group bounding
  radius alongside the center). Confirmed **not** a material index — group→material is positional (see a DNER section).
  The exact meaning is unconfirmed.

### Low Priority / Nice to Have

- **TXAN texture animation**: Only 1 file. Low priority.

### Resolved Questions

These questions were answered by analysis of reverse-engineered text MEF source files and — for
the items marked *(Map Editor)* — by **controlled gconv recompile experiments and 100%-corpus
correlation** using the official IGI2 Map Editor (see *Provenance & Methodology*):

- **Type-3 vertex UV coordinates**: ✅ SOLVED *(Map Editor)* — the 28-byte `XTRVItem3` is
  position + diffuse UV (offset 12 = U, offset 16 = `1 - source_v`) + lightmap UV (offsets 20/24),
  with **no per-vertex normal**. The diffuse UV matches the text `UV()` command exactly across
  128,869 / 128,869 type-3 vertices (174 models). This unblocks textured export for the 5,433
  type-3 files (71% of all MEF). See the XTRV Type-3 section.

- **Material-to-texture mapping in binary**: ✅ PARTIALLY SOLVED *(Map Editor)* — each DNER render
  group corresponds to one renderable (`DiffuseTMap`-bearing) material, in source material-id order
  (a strong heuristic; the compiler may split/reorder groups). The texture **filename** is not
  stored in the binary mesh — resolving it requires the model/texture naming convention and the MTP
  material system. See the DNER Type-3 section.

- **TROP chunk**: ✅ SOLVED *(Map Editor)* — portal descriptors
  `(range_a_start, range_a_count, range_b_start, range_b_count, reference_index)` with cumulative
  start fields (verified 13/13 TROP-bearing models); typically 4 vertices + 2 triangles per portal
  quad. See the Other Chunks table.

- **PMTL chunk identity**: ✅ SOLVED *(Map Editor)* — it is the lightmap-parameters chunk (`LTMP`),
  not a material table. See the PMTL section.

Answered earlier by analysis of reverse-engineered text MEF source files:

- **Material-to-texture mapping (source level)**: ✅ SOLVED — `DiffuseTMap(id, path, u_tile, v_tile)` explicitly maps
  material IDs to texture file paths. Additional texture types: `OpacityTMap`, `ReflectionTMap`, `BumpTMap`.

- **Bone parent-child topology**: ✅ SOLVED — `Bone(id, name, parent_id, x, y, z)` explicitly stores parent index. The
  REIH binary format stores BFS-ordered child counts instead, and parent indices are reconstructed via the
  `_build_parent_map()` algorithm in `iff_to_gltf.py`.

- **ATTA fields**: ✅ SOLVED — `AttachObject(name, id, 9×rotation, 3×position)` confirms 3×3 rotation matrix + position.
  `AttachObjectBoneID(id, bone_index)` confirms the bone attachment field.

- **XTVM purpose**: ✅ SOLVED — `MagicVertex(id, type, x, y, z, param)` — special vertex positions with parameter (often
  -1). Used for glow helpers, damage areas, or attachment points.

- **XVTP/CFTP relationship**: ✅ SOLVED — XVTP stores original source vertex positions from `Vertex()` commands, CFTP
  stores original source face indices from `Face()` vertex indices. They represent the pre-compilation mesh before D3D
  vertex splitting and optimization.

- **WOLG fields**: ✅ CONFIRMED — `Glow(x, y, z, radius, r, g, b)` matches the existing parser field names exactly.

## Research Priorities

Ordered by impact on conversion quality:

| Priority | Topic                                | Impact                                   | Status                                                                  |
|----------|--------------------------------------|------------------------------------------|-------------------------------------------------------------------------|
| 1        | Type-3 vertex UVs                    | Unlocks textured export for 71% of files | ✅ Solved (Map Editor)                                                   |
| 2        | Material-to-texture mapping (binary) | Enables textured export for all types    | ✅ Partially solved — group↔material positional; filename via MTP/naming |
| 3        | Bone parent topology                 | Enables skeletal export (glTF/FBX)       | ✅ Solved                                                                |
| 4        | PMTL table                           | Completes type-3 material data           | ✅ Reclassified as LTMP lightmap params                                  |
| 5        | HPRM morph targets                   | Enables facial animation export          | Partially solved (no editor sample)                                     |
| 6        | ATTA fields                          | Attachment point structure               | ✅ Solved                                                                |
| 7        | XTVM/XVTP/CFTP purpose               | Completes format documentation           | ✅ Solved                                                                |
| 8        | TROP chunk                           | Portal/visibility data                   | ✅ Solved (Map Editor)                                                   |

### Conversion Readiness Summary

| Model Type        | Files | Geometry | UVs                               | Normals                    | Skeleton                     | Textures                                           |
|-------------------|-------|----------|-----------------------------------|----------------------------|------------------------------|----------------------------------------------------|
| Type 0 (static)   | 1,853 | Ready    | Ready                             | Ready                      | N/A                          | Source paths known                                 |
| Type 1 (skeletal) | 240   | Ready    | Ready                             | Ready                      | Ready (parent map algorithm) | Source paths known                                 |
| Type 3 (static)   | 5,433 | Ready    | **Ready** (diffuse + lightmap UV) | None (baked into lightmap) | N/A                          | Group↔material positional; filename via MTP/naming |

**Bottom line**: Textured (diffuse-UV) export now works for **all** model types, including type-3
(71% of files), which carries diffuse + lightmap UV sets and no per-vertex normals. Skeletal export
is unblocked (bone parent reconstruction). The per-group material assignment is recoverable from the
binary; the texture **filename** still comes from the naming convention / MTP material system, not
the mesh.

## Provenance & Methodology

The type-3 UV, material-mapping, TROP, and PMTL decoding above were produced using the **official
IGI2 Map Editor** (shipped by the game's creators). For the same models it provides paired assets —
text `.MEF` source, the compiled binary `.mex` (identical `ILFF`/`OCEM` container to game `.mef`),
and 3DS Max sources — plus a runnable `gconv.exe` (byte-identical to the copy bundled in
`src/igipy/bin/`). This enabled two evidence methods:

1. **Recompile validation** — recompiling a text `.MEF` with `gconv` reproduces the shipped `.mex`
   byte-for-byte except the HSEM compile timestamp (and two compiler-version sentinel int16s),
   confirming the toolchain and the meaning of fields.
2. **100%-corpus correlation** — parsing all 198 paired editor models (174 type-3, 24 type-0; 0
   parse failures with the project parser) and matching binary fields against the text command
   stream. The type-3 diffuse UV decoded rests on a 128,869 / 128,869-vertex exact match.

The editor binaries/assets are not vendored into the repository; mining notes are kept at
`.ai-factory/references/igi2-map-editor.md`. *(Note: the Map Editor sample set is static map props,
so it contains no type-1/skeletal or HPRM/morph models — those questions remain observational on the
full game corpus.)*
