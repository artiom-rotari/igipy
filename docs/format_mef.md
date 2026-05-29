[Back to README](../README.md)

# MEF Format — 3D Mesh Model

MEF files store 3D mesh models for characters, objects, buildings, and vehicles. They are located in `models/` directories inside `.res` archives and use IGI's ILFF container format with content type `OCEM` (MECO reversed). Three model types exist: static geometry (type 0), skeletal meshes with bone weights (type 1), and static geometry with per-material data (type 3).

## Structure Overview

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
|  XTVM - Material Positions                        |
|  TROP - Unknown (5 uint32 per entry)              |
|  XVTP - Vertex Positions (float3 per entry)       |
|  CFTP - Face Properties (3 uint32 per entry)      |
+---------------------------------------------------+
|  D3DR - Render State (36/40/44 bytes by type)     |
|  ECAF - Render Faces (uint16 triangle indices)    |
|  DNER - Render Groups (28 or 32 bytes per entry)  |
|  XTRV - Vertices (28/32/40 bytes by type)         |
+---------------------------------------------------+
|  PMTL - Material Table (type 3 only)              |
|  WOLG - Glow Points (type 0/3 only, optional)     |
|  HPRM - Morph Targets (type 0/1 only, optional)   |
|  TXAN - Texture Animation (1 file only)           |
+---------------------------------------------------+
|  HSMC - Collision Header (optional)               |
|  XTVC - Collision Vertices (repeated per submesh) |
|  ECFC - Collision Faces (repeated per submesh)    |
|  TAMC - Collision Materials (repeated per submesh)|
|  HPSC - Collision Spheres (repeated per submesh)  |
+---------------------------------------------------+
```

All chunk fourccs are reversed names: HSEM=MESH, ECAF=FACE, DNER=REND, XTRV=VRTX, XTVM=MVTX, TROP=PORT, XVTP=PTVX, CFTP=PTFC, ATTA=ATTA, WOLG=GLOW, HPRM=MRPH, PMTL=LTMP, HSMC=CMSH, XTVC=CVTX, ECFC=CFCE, TAMC=CMAT, HPSC=CSPH, REIH=HIER, MANB=BNAM.

## Statistics

| Metric | Value |
|--------|-------|
| Total files | 7,609 |
| Valid OCEM files | 7,608 (1 non-OCEM: `menusystem/models/minefield.mef`) |
| Location | `models/` directories inside `.res` archives |
| Size range | 416 -- 1,663,236 bytes |
| Type 0 (static) | 1,853 files |
| Type 1 (skeletal) | 240 files |
| Type 3 (static + PMTL) | 5,433 files |

## Model Types

| Property | Type 0 | Type 1 | Type 3 |
|----------|--------|--------|--------|
| Files | 1,853 | 240 | 5,433 |
| Vertex size | 32 bytes | 40 bytes | 28 bytes |
| D3DR size | 36 bytes | 40 bytes | 44 bytes |
| DNER entry size | 32 bytes | 32 bytes | 28 bytes |
| Has REIH+MANB | No | Yes (always) | No |
| Has PMTL | No | No | Yes (always) |
| Has WOLG | 106 files | Never | 885 files |
| Has HPRM | 178 files | 37 files | Never |
| Description | Static props | Characters/vehicles | Buildings/terrain objects |

## HSEM — Mesh Header

The chunk fourcc `HSEM` is `MESH` reversed. Always 176 bytes. The first 156 bytes are parsed as `<12I12f6If6H5I`; the remaining 20 bytes are zeros.

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

The chunk fourcc `XTRV` is `VRTX` reversed. Contains all render vertices as a flat array. Vertex format depends on model type.

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

Weight of 1.0 means fully influenced by the referenced bone. Values less than 1.0 indicate blending with a parent or adjacent bone (the complement weight is implicit).

### Type 3 — Compact Static Vertex (28 bytes)

```
Offset  Size  Type     Field
0       12    float3   Position (x, y, z)
12      4     float    Unknown (range -0.27 to 6.25)
16      4     float    Unknown (range -3.0 to 1.0, likely U coordinate)
20      4     float    Unknown (range 0.0 to 1.0, likely V coordinate)
24      4     float    Unknown (range 0.0 to 1.0, few unique values per model)
```

The existing codebase incorrectly defines `XTRVItem3` as `Struct("<10f")` (40 bytes). The actual type-3 vertex is 28 bytes, validated across all 5,433 type-3 files.

## ECAF — Render Faces

The chunk fourcc `ECAF` is `FACE` reversed. Contains triangle indices as a flat array of little-endian `uint16` values. Each triangle uses 3 consecutive indices (6 bytes per face).

```
face_count = len(ECAF) / 6
max_index  = render_vertex_count - 1
```

This chunk is present in all 7,608 valid MEF files but is **missing from the code's `chunk_mapping`** — the parser does not handle it.

## DNER — Render Groups

The chunk fourcc `DNER` is `REND` reversed. Partitions the mesh into render groups (draw calls). Each group references a contiguous range of vertices and indices from XTRV and ECAF.

**Validated across 7,499 files with zero failures.** The cumulative index/vertex offsets always sum to the totals from HSEM.

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
12      2     uint16   Unknown (material reference?)
14      2     uint16   Unknown (flags?)
16      2     uint16   Index start (offset into ECAF, in uint16 elements)
18      2     uint16   Face count (number of triangles)
20      2     uint16   Vertex start (offset into XTRV)
22      2     uint16   Vertex count
24      2     uint16   Group index (sequential: 0, 1, 2, ...)
26      2     uint16   Reserved (always 0)
```

### Offset Rule

Index and vertex ranges are contiguous and non-overlapping:

```
group[i].index_start  = group[i-1].index_start + group[i-1].face_count * 3
group[i].vertex_start = group[i-1].vertex_start + group[i-1].vertex_count
sum(face_count)       = HSEM.render_face_count
sum(vertex_count)     = HSEM.render_vertex_count (type 0/3) or D3DR[4] (type 1)
```

## D3DR — Render State

The chunk fourcc `D3DR` is `RD3D` reversed. A single entry containing render configuration. Size depends on model type.

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

For skeletal meshes, the XTRV vertex buffer may contain more vertices than the DNER render groups reference. The ECAF indices reference only the first `D3DR[4]` vertices.

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

The chunk fourcc `REIH` is `HIER` reversed. Present in all 240 type-1 files. Same format as the IFF animation REIH chunk.

```
Offset          Size              Type       Field
0               bone_count        byte[]     Bone type flags (one per bone)
bone_count      1                 byte       Padding (0x00)
bone_count + 1  bone_count * 12   float3[]   Rest-pose offsets (3 floats per bone)
```

Size = `bone_count + 1 + bone_count * 12`. Three skeleton sizes observed:

| Bones | REIH size | Files |
|-------|-----------|-------|
| 31 | 404 bytes | 237 |
| 47 | 612 bytes | 1 |
| 28 | 364 bytes | 2 |

The 31-bone skeleton is the standard humanoid skeleton. Bone type flags match IFF animation types (0 = end effector, 1 = rotation, 2 = full transform, 3 = position + rotation).

## MANB — Bone Names (Type 1 Only)

The chunk fourcc `MANB` is `BNAM` reversed. Contains `bone_count` fixed 16-byte null-padded ASCII strings.

```
Total size = bone_count * 16
```

31-bone skeleton names:

| Index | Name | Index | Name |
|-------|------|-------|------|
| 0 | center | 16 | upper left arm |
| 1 | lower body | 17 | upper right arm |
| 2 | upper left leg | 18 | left toe end |
| 3 | upper right leg | 19 | right toe end |
| 4 | upper body | 20 | head end |
| 5 | lower left leg | 21 | lower left arm |
| 6 | lower right leg | 22 | lower right arm |
| 7 | shoulders | 23 | left hand |
| 8 | left foot | 24 | right hand |
| 9 | right foot | 25 | upper left finger |
| 10 | rotate_head | 26 | upper right finger |
| 11 | rotate_left | 27 | lower left finger |
| 12 | rotate_right | 28 | lower right finger |
| 13 | left toe | 29 | left fingers end |
| 14 | right toe | 30 | right fingers end |
| 15 | head | | |

Names are truncated to 16 characters (e.g., "upper left finge" for "upper left finger").

## ATTA — Attachment Points

72 bytes per entry (the existing code incorrectly uses 68). Defines named attachment slots on the model.

```
Offset  Size  Type      Field
0       16    char[16]  Attachment name (null-padded ASCII)
16      48    float[12] Transform data (position + quaternions)
64      4     int32     Index A
68      4     int32     Index B
```

Common attachment names: `shadow_1`, `weapon`, `helmet`, model-specific references.

| Entry count | Files |
|-------------|-------|
| 0 (empty ATTA) | 6,748 |
| 1 | 248 |
| 2 | 138 |
| 3 | 72 |
| 4 | 72 |
| 5+ | 248 |

## WOLG — Glow Points (Optional)

The chunk fourcc `WOLG` is `GLOW` reversed. Present in 991 files (type 0 and type 3 only). Each entry is 32 bytes defining a light-emitting point on the model.

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

The chunk fourcc `HPRM` is `MRPH` reversed. Present in 215 files (type 0 and type 1 only). Contains morph target vertex displacements for facial animation or deformation.

```
Offset  Size  Type     Field
0       4     uint32   Morph vertex count
4       60    -        Padding (zeros)
64      var   -        Morph entries (variable-size, structure varies)
```

The internal entry format varies between files (16 to 44+ bytes per entry observed). Each entry appears to contain a vertex index followed by position deltas, but the exact structure depends on context and is not fully decoded.

## PMTL — Material Table (Type 3 Only)

The chunk fourcc `PMTL` is `LTMP` reversed. Present in all 5,433 type-3 files. Each entry is 8 bytes.

```
Offset  Size  Type     Field
0       2     uint16   Unknown
2       2     uint16   Unknown
4       2     uint16   Unknown
6       2     uint16   Unknown
```

## Collision Mesh

Optional collision data present in approximately 42% of files. Consists of a header chunk (HSMC) followed by paired data chunks that repeat per collision submesh.

### HSMC — Collision Header

```
Offset  Size  Type     Field
0       4     uint32   ECFC entry count (collision faces)
4       4     uint32   XTVC entry count (collision vertices)
8       4     uint32   TAMC entry count (collision materials)
12      4     uint32   HPSC entry count (collision spheres)
16      16    uint32[4] Zeros
```

One HSMC item per collision submesh. The counts index into the following XTVC/ECFC/TAMC/HPSC chunk arrays.

### XTVC — Collision Vertices

```
Offset  Size  Type     Field
0       16    float4   Position (x, y, z, w)
```

### ECFC — Collision Faces

```
Offset  Size  Type     Field
0       8     uint16[4] Triangle indices + material reference
```

### TAMC — Collision Materials

```
Offset  Size  Type     Field
0       12    int16[6] Material properties
```

### HPSC — Collision Spheres

```
Offset  Size  Type     Field
0       16    float4   Sphere center + radius (x, y, z, r)
4       8     int16[4] Hierarchy indices
```

## Other Chunks

| Chunk | Reversed | Entry size | Description |
|-------|----------|------------|-------------|
| XTVM | MVTX | 16 bytes (`<3fi`) | Material vertex positions |
| TROP | PORT | 20 bytes (`<5I`) | Unknown (portal/viewport data?) |
| XVTP | PTVX | 12 bytes (`<3f`) | Vertex positions (subset) |
| CFTP | PTFC | 12 bytes (`<3I`) | Face properties (subset) |
| TXAN | NAXT | varies | Texture animation (only 1 file in entire dataset) |

## Chunk Presence by Model Type

| Chunk | Type 0 | Type 1 | Type 3 |
|-------|--------|--------|--------|
| HSEM | Always | Always | Always |
| ATTA | Always | Always | Always |
| XTVM | Always | Always | Always |
| TROP | Always | Always | Always |
| XVTP | Always | Always | Always |
| CFTP | Always | Always | Always |
| D3DR | Always | Always | Always |
| ECAF | Always | Always | Always |
| DNER | Always | Always | Always |
| XTRV | Always | Always | Always |
| REIH | Never | Always | Never |
| MANB | Never | Always | Never |
| PMTL | Never | Never | Always |
| WOLG | 106 files | Never | 885 files |
| HPRM | 178 files | 37 files | Never |
| HSMC+ | 750 files | 99 files | 2,356 files |
| TXAN | 1 file | Never | Never |

## Known Code Issues

The existing `mef.py` parser has several issues identified during this research:

1. **Missing ECAF handler**: The `chunk_mapping` does not include `b"ECAF"`, so render face data is silently dropped during parsing.
2. **Wrong XTRVItem3 size**: `XTRVItem3 = Struct("<10f")` defines 40 bytes, but type-3 vertices are 28 bytes. This causes parse failures for all 5,433 type-3 files.
3. **Wrong ATTA entry size**: `ATTAItem = Struct("<16s12fi")` defines 68 bytes, but entries are 72 bytes.
4. **Missing REIH/MANB handlers**: Skeletal bone hierarchy and bone name chunks are not in `chunk_mapping`.
5. **Missing WOLG handler**: Glow point data is silently dropped.
6. **Missing HPRM handler**: Morph target data is silently dropped.
7. **DNERItem0 variable-size assumption**: The code treats type-0 DNER as variable-length (`3f+8H` + tail), but entries are fixed 32 bytes.

## Open Questions

- **Type-3 vertex fields**: The 4 fields after position in type-3 vertices are not fully understood. Fields at offsets 16 and 20 are likely UV coordinates, but offset 12 and 24 need more investigation.
- **HPRM internal structure**: Morph target entries have variable sizes across files. The vertex index + delta hypothesis works for some files but not all.
- **DNER material flags**: The `uint32` at offset 0 in type-0/1 DNER entries (and `uint16` pair at offset 12-14 in type-3) likely reference materials or textures, but the mapping is unknown.
- **Type-1 extra vertices**: Skeletal meshes often have more XTRV vertices than DNER/ECAF reference. The purpose of these extra vertices (D3DR[3]) is unclear.
- **Parent-child bone indices**: REIH stores bone type flags and rest-pose offsets but not explicit parent indices. The hierarchy topology may be fixed per skeleton type.

## See Also

- [Game Structure](game_structure.md) -- IGI2 game file organization, including `models/` locations
- [File Extensions](extensions.md) -- full file type inventory with conversion status
- [IFF Format](format_iff.md) -- skeletal animation format (uses same REIH bone hierarchy)
