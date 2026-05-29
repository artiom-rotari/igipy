[Back to README](../README.md)

# IFF Format — Skeletal Animation

IFF files store skeletal animation clips for character and object animations. They are located in `common/anims/` inside `.res` archives and contain bone hierarchy data, keyframe channels, and optional attachment points. Despite the `.iff` extension, these files use IGI's ILFF container format (not the standard EA IFF 85).

## Structure Overview

```
┌───────────────────────────────────────────────────┐
│  ILFF Header (content_type = "ANIM")              │
├───────────────────────────────────────────────────┤
│  DHNA — Animation Header (57–109 bytes)           │
│  version, duration, bone count, name              │
├───────────────────────────────────────────────────┤
│  REIH — Bone Hierarchy (404 or 612 bytes)         │
│  per-bone type flags + rest-pose offsets           │
├───────────────────────────────────────────────────┤
│  TNVE — Keyframe Data (bulk of file)              │
│  variable-size entries: pos, rot, transforms      │
├───────────────────────────────────────────────────┤
│  ATTA — Attachment Points (optional, N × 80B)     │
│  named bone attachments (weapon, helmet, etc.)    │
└───────────────────────────────────────────────────┘
```

## Statistics

| Metric | Value |
|--------|-------|
| Total files | 1,244 |
| Location | `common/anims/` (inside `.res` archives) |
| Size range | 2,800–360,624 bytes |
| Median size | 7,558 bytes |
| Skeleton types | 31-bone (1,158 files), 47-bone (86 files) |
| Chunk combinations | `DHNA+REIH+TNVE` (154 files), `DHNA+REIH+TNVE+ATTA` (1,090 files) |
| Naming | Descriptive (`crawl.iff`, `civilian_walk.iff`) and numbered (`005_02.iff`) |

## DHNA — Animation Header

The chunk fourcc `DHNA` is `ANHD` reversed (Animation Header). Variable size due to the embedded animation name string.

```
Offset  Size  Type     Field
0       8     -        Padding (0xAB bytes)
8       4     uint32   Version (always 4)
12      4     uint32   Looping (0 = one-shot, 1 = looping)
16      4     uint32   Duration (time units, see Timing below)
20      4     uint32   Bone count (31 or 47)
24      4     -        Padding (0xAB bytes)
28      4     uint32   Entry count (exact count of TNVE entries)
32      4     uint32   Unknown (always 0)
36      4     uint32   Has root motion (0 or 1)
40      4     uint32   Unknown (always 0)
44      8     -        Padding (0xAB bytes)
52      var   string   Animation name (null-terminated ASCII)
```

| Example | Duration | Bone count | Entries | Looping | Root motion |
|---------|----------|------------|---------|---------|-------------|
| `corpse.iff` | 160 | 31 | 33 | No | No |
| `crawl.iff` | 7,680 | 31 | 142 | Yes | Yes |
| `generic_walk.iff` | 32,800 | 31 | 5,018 | No | No |
| `anya_talking.iff` | 448,000 | 31 | 4,006 | Yes | No |

## REIH — Bone Hierarchy

The chunk fourcc `REIH` is `HIER` reversed (Hierarchy). Size depends on bone count: 31 bones = 404 bytes, 47 bones = 612 bytes. Formula: `bone_count + 1 + bone_count × 12`.

```
Offset          Size              Type       Field
0               bone_count        byte[]     Bone type flags (one per bone)
bone_count      1                 byte       Padding (0x00)
bone_count + 1  bone_count × 12   float3[]   Rest-pose offsets (3 floats per bone)
```

### Bone Type Flags

| Flag | Meaning | TNVE entry types used | Count (31-bone) | Count (47-bone) |
|------|---------|-----------------------|-----------------|-----------------|
| 0 | End effector (no animation) | None | 5 | 10 |
| 1 | Rotation-only bone | `0x04` (ROT) | 24 | 34 |
| 2 | Full transform (47-bone root) | `0x01`, `0x07` | - | 1 |
| 3 | Position + rotation (31-bone root) | `0x03`/`0x06` + `0x04` | 2 | - |
| 5 | Special (47-bone only) | varies | - | 2 |

31-bone skeleton type layout:

```
Index:  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30
Type:   3  1  1  1  1  1  1  3  1  1  1  1  1  1  1  1  1  1  0  0  0  1  1  1  1  1  1  1  1  0  0
        ^                       ^                                      ^ ^ ^                       ^ ^
        root                    root2                                  end effectors               end
```

## TNVE — Keyframe Data

The chunk fourcc `TNVE` is `EVNT` reversed (Events). This is the bulk of the file, containing all animation channel data as a flat sequence of variable-size entries.

### Entry Size Rule

Every entry starts with a 4-byte header where bytes 2–3 are a `uint16` descriptor. **The entry size in bytes = `descriptor × 4`**. This rule was validated across all 1,244 files with zero failures.

### Common Entry Header (12 bytes)

```
Offset  Size  Type     Field
0       1     byte     Entry type (0x01, 0x03, 0x04, 0x06, 0x07, 0xFF)
1       1     byte     Bone index
2       2     uint16   Size descriptor (entry_size = descriptor × 4)
4       4     uint32   Frame offset (time position in duration units)
8       4     uint32   Reserved (usually 0)
```

### Entry Types

| Type | Desc | Size | Data layout | Description | Frequency |
|------|------|------|-------------|-------------|-----------|
| `0x03` | 6 | 24B | header(12) + position(12) | Position keyframe (3 floats) | Common |
| `0x04` | 18 | 72B | header(12) + 3×[quat(16) + pad(4)] | Rotation with tangents | ~98% of all entries |
| `0x06` | 8 | 32B | header(12) + extra(8) + position(12) | Position with interpolation data | Uncommon |
| `0x07` | 11 | 44B | header(12) + position(12) + quat(16) + pad(4) | Full transform (pos + rot) | 47-bone only |
| `0x01` | 17 | 68B | header(12) + int(4) + 2×[quat(16)] + pad(4) + pos(12) + float(4) | Full transform with tangents | 47-bone only |
| `0xFF` | 3 | 12B | header only | Section separator (loop boundary) | 0 or 1 per file |

The `pad` bytes are always `0xAB AB AB AB`.

### Rotation Entry Detail (Type 0x04)

The dominant entry type stores three quaternions per keyframe: the rotation value plus in/out tangents for Hermite spline interpolation.

```
Offset  Size  Content
0       12    Common header (type=0x04, bone_idx, desc=18, frame_offset, reserved)
12      16    Quaternion value (4 × float32: x, y, z, w)
28      4     Padding (0xAB × 4)
32      16    In-tangent quaternion (4 × float32)
48      4     Padding (0xAB × 4)
52      16    Out-tangent quaternion (4 × float32)
68      4     Padding (0xAB × 4)
```

### Looping Animation Structure

For looping animations (`DHNA.looping = 1`), the TNVE data is split into two sections by a `0xFF` separator entry:

```
Section 1: Keyframes at various time offsets (delta-compressed)
           Only bones that change at a given time get new entries.
           Starts with a full pose at frame offset 0.

0xFF separator: Marks the loop boundary at the animation duration.

Section 2: Wrap-around pose (1 POS + all ROT entries).
           Provides the pose for seamless loop blending.
```

Non-looping animations have no separator — just a flat sequence of keyframe entries.

### Delta Compression

Not every bone has a keyframe at every time offset. Only bones whose values change get new entries. A static pose (like `corpse.iff`) has just 1 position + 31 rotations = 32 entries. A complex walk cycle (`generic_walk.iff`) has 5,018 entries spread across many time offsets.

## ATTA — Attachment Points

Present in 1,090 of 1,244 files (87.5%). Each attachment is 80 bytes.

```
Offset  Size  Type      Field
0       16    char[16]  Attachment name (null-padded ASCII)
16      12    float3    Position (3 × float32)
28      16    float4    Orientation quaternion (4 × float32)
44      16    float4    Secondary quaternion (4 × float32)
60      4     -         Padding (0xAB × 4)
64      4     uint32    Bone index
68      4     uint32    Attachment index
72      8     -         Reserved (zeros)
```

### Attachment Count Distribution

| Attachments | Files |
|-------------|-------|
| 0 | 154 |
| 1 | 883 |
| 2 | 143 |
| 3 | 53 |
| 4+ | 11 |

### Common Attachment Names

Most files have a single `weapon` attachment. The 85 unique names include:

- **Equipment**: `weapon`, `helmet`, `halo`, `halo2`, `mapcomputer`, `o2`, `primary`, `chutehandle`, `wire2`
- **Numbered IDs**: Reference model object IDs (e.g., `107_02_1`, `502_01_1`)

## Skeleton Types

Two distinct skeleton types exist across all 1,244 files:

| Property | 31-bone | 47-bone |
|----------|---------|---------|
| Files | 1,158 | 86 |
| REIH size | 404 bytes | 612 bytes |
| Naming | Descriptive (`walk.iff`) | Numbered (`005_XX.iff`) |
| Root bone type | 3 (pos+rot) | 2 (full transform) |
| Entry types used | `0x03`, `0x04`, `0x06` | `0x01`, `0x04`, `0x07` |
| End effectors | 5 (bones 18–20, 29–30) | 10 (bones 37–46) |

## Timing

Frame offsets in TNVE entries use the same time unit as `DHNA.duration`. Specific frame rate and time-unit-to-seconds conversion factor are not yet determined — this requires cross-referencing with the game engine's animation playback system or QSC script timing values.

## Open Questions

- **Parent indices**: The REIH chunk stores bone type flags and rest-pose offsets, but explicit parent-child bone indices have not been identified. The skeleton topology may be implicit (fixed for each skeleton type) or encoded differently.
- **Time units**: The exact conversion from duration units to seconds/frames needs verification against in-game playback.
- **Interpolation scheme**: The three quaternions per rotation entry (value + 2 tangents) suggest Hermite spline interpolation, but the exact formulation needs confirmation.
- **Secondary ATTA quaternion**: The second quaternion in each ATTA entry may be a tangent, inverse bind pose, or interpolation endpoint.

## See Also

- [Game Structure](game_structure.md) — IGI2 game file organization, including `common/anims/` location
- [File Extensions](extensions.md) — full file type inventory with conversion status
- [SYN Format](format_syn.md) — lip-sync envelope format (related animation data)
