[Back to README](../../../README.md)

# IFF Format — Skeletal Animation

IFF files store skeletal animation clips for character and object animations. They are located in `common/anims/` inside
`.res` archives and contain bone hierarchy data, keyframe channels, and optional attachment points. Despite the `.iff`
extension, these files use IGI's ILFF container format (not the standard EA IFF 85).

## Structure Overview

```
+---------------------------------------------------+
|  ILFF Header (content_type = "ANIM")              |
+---------------------------------------------------+
|  DHNA -- Animation Header (57-109 bytes)          |
|  version, duration, bone count, name              |
+---------------------------------------------------+
|  REIH -- Bone Hierarchy (404 or 612 bytes)        |
|  BFS child counts + parent-relative offsets       |
+---------------------------------------------------+
|  TNVE -- Keyframe Data (bulk of file)             |
|  variable-size entries: pos, rot, transforms      |
+---------------------------------------------------+
|  ATTA -- Attachment Points (optional, N x 80B)    |
|  named bone attachments (weapon, helmet, etc.)    |
+---------------------------------------------------+
```

## Statistics

| Metric             | Value                                                                                                           |
|--------------------|-----------------------------------------------------------------------------------------------------------------|
| Total files        | 1,244                                                                                                           |
| Location           | `common/anims/` (inside `.res` archives)                                                                        |
| Size range         | 2,800-360,624 bytes                                                                                             |
| Median size        | 7,558 bytes                                                                                                     |
| Skeleton types     | 31-bone (990 files), 47-bone (254 files)                                                                        |
| Chunk combinations | `DHNA+REIH+TNVE` (154 files), `DHNA+REIH+TNVE+ATTA` (1,090 files)                                               |
| Naming             | Descriptive (`crawl.iff`, `civilian_walk.iff`), numbered (`005_02.iff`), and first-person (`fire_ak47_1st.iff`) |

## DHNA -- Animation Header

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

| Example            | Duration | Bone count | Entries | Looping | Root motion |
|--------------------|----------|------------|---------|---------|-------------|
| `corpse.iff`       | 160      | 31         | 33      | No      | No          |
| `crawl.iff`        | 7,680    | 31         | 142     | Yes     | Yes         |
| `generic_walk.iff` | 32,800   | 31         | 5,018   | No      | No          |
| `anya_talking.iff` | 448,000  | 31         | 4,006   | Yes     | No          |

## REIH -- Bone Hierarchy

The chunk fourcc `REIH` is `HIER` reversed (Hierarchy). Size depends on bone count: 31 bones = 404 bytes, 47 bones = 612
bytes. Formula: `bone_count + 1 + bone_count * 12`.

```
Offset          Size              Type       Field
0               bone_count        byte[]     BFS child counts (one per bone)
bone_count      1                 byte       Padding (0x00)
bone_count + 1  bone_count * 12   float3[]   Rest-pose offsets (3 floats per bone)
```

### BFS Child Counts (Bone Hierarchy Reconstruction)

The first `bone_count` bytes encode the skeleton hierarchy as a **BFS-ordered child count** (out-degree) per bone. The
bones are listed in breadth-first traversal order, and each byte tells how many direct children that bone has.

**Proof:** For any tree with N nodes, the sum of all child counts equals N-1 (every node except the root has exactly one
parent). For the 31-bone skeleton: sum = 30 = 31-1. For the 47-bone skeleton: sum = 46 = 47-1.

**Reconstruction algorithm** (BFS queue):

```
1. Read bone 0 (root). Push it to a FIFO queue with its child count.
2. For each subsequent bone (index 1..N-1):
   a. Peek at the front of the queue -- this is the current parent.
   b. Assign this bone as a child of the current parent.
   c. Decrement the parent's remaining child count.
   d. If the parent's count reaches 0, pop it from the queue.
   e. If this bone's child count > 0, push it to the back of the queue.
```

This algorithm works for both 31-bone and 47-bone skeletons with no hardcoded hierarchy.

### 31-Bone Skeleton Hierarchy

Child counts and bone names (from MEF MANB chunk):

```
Index:  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30
Count:  3  1  1  1  1  1  1  3  1  1  1  1  1  1  1  1  1  1  0  0  0  1  1  1  1  1  1  1  1  0  0
```

Reconstructed tree:

```
center (3 children)
+-- lower body (1)
|   +-- upper body (1)
|       +-- shoulders (3)
|           +-- rotate_head (1)
|           |   +-- head (1)
|           |       +-- head end (0)
|           +-- rotate_left (1)
|           |   +-- upper left arm (1)
|           |       +-- lower left arm (1)
|           |           +-- left hand (1)
|           |               +-- upper left finger (1)
|           |                   +-- lower left finger (1)
|           |                       +-- left fingers end (0)
|           +-- rotate_right (1)
|               +-- upper right arm (1)
|                   +-- lower right arm (1)
|                       +-- right hand (1)
|                           +-- upper right finger (1)
|                               +-- lower right finger (1)
|                                   +-- right fingers end (0)
+-- upper left leg (1)
|   +-- lower left leg (1)
|       +-- left foot (1)
|           +-- left toe (1)
|               +-- left toe end (0)
+-- upper right leg (1)
    +-- lower right leg (1)
        +-- right foot (1)
            +-- right toe (1)
                +-- right toe end (0)
```

The center (pelvis) has 3 children: the spine chain (lower body) and both hip joints (upper left/right leg). The
shoulders node branches into 3 chains: head and both arms. Bones with count 0 are leaf/end effectors.

### Rest-Pose Offsets

The float3 values after the child counts are **parent-relative translations** (bone-local offsets from parent bone
position), NOT absolute world positions.

Evidence:

- Bones 10-12 (rotate_head, rotate_left, rotate_right) have offset `(0, 0, 0)` -- they are co-located with their
  parent (shoulders). This only makes sense as parent-relative.
- Offsets for bones 1-30 are nearly identical across all 990 animations of the same skeleton type, while bone 0 (root)
  varies per animation.
- TNVE position keyframes for bone 0 at frame 0 always match the REIH offset for bone 0 exactly, confirming they share
  the same coordinate space.

The engine uses fixed-point precision: **4096 game units = 1 meter** (2^12, enabling fast bit-shift division). The
31-bone skeleton measures ~7319 units from foot to head end, yielding 1.787m (5'10") — the industry-standard default
male character height.

The coordinate system is **Z-up, left-handed**: X = right, Y = forward, Z = up. When exporting to FBX (Y-up,
right-handed), positions transform as `(x, y, z) → (x, z, -y)` and quaternions as
`(qx, qy, qz, qw) → (qx, qz, -qy, qw)`.

### Child Count Values by Skeleton Type

| Count | Meaning                   | 31-bone                     | 47-bone  |
|-------|---------------------------|-----------------------------|----------|
| 0     | Leaf / end effector       | 5 bones                     | 10 bones |
| 1     | Chain bone (single child) | 24 bones                    | 34 bones |
| 2     | Two-way branch            | -                           | 1 bone   |
| 3     | Three-way branch          | 2 bones (center, shoulders) | -        |
| 5     | Five-way branch           | -                           | 2 bones  |

The child count values are consistent across all animations of the same skeleton type (all 990 files with 31 bones share
the same child counts, and all 254 files with 47 bones share the same child counts).

### 47-Bone Skeleton — First-Person Hand Model

The 47-bone skeleton is used for `005_01_1.mef`, a first-person hand model with detailed individual finger bones. Its
254 animations are all in `common/anims/`.

#### Identifying 47-Bone Animations by Filename

All 47-bone animations can be identified by these filename patterns:

| Pattern                | Count   | Description                                                                 |
|------------------------|---------|-----------------------------------------------------------------------------|
| `005_*.iff`            | 61      | Numbered hand pose/gesture animations                                       |
| `*_1st.iff`            | 189     | First-person weapon animations (fire, reload, walk, run, weaponraise, etc.) |
| `*_1st_pers.iff`       | 2       | `pistolwhip_1st_pers.iff`, `push_button_1st_pers.iff`                       |
| `arm_blank.iff`        | 1       | Blank/default arm pose                                                      |
| `fire_mapcomputer.iff` | 1       | Map computer interaction (no `_1st` suffix)                                 |
| **Total**              | **254** |                                                                             |

The `*_1st.iff` animations break down by action:

| Action prefix    | Count | Examples                                                            |
|------------------|-------|---------------------------------------------------------------------|
| `fire_*`         | 40    | `fire_ak47_1st`, `fire_grenade_1st`, `fire_pullpin_flashbang_1st`   |
| `reload_*`       | 34    | `reload_m16_1st`, `reload_loop_spas_1st`, `reload_finish_m1014_1st` |
| `walk_*`         | 30    | `walk_knife_1st`, `walk_pistol_1st`, `walk_irgoggles_1st`           |
| `run_*`          | 30    | `run_ak47_1st`, `run_binoculars_1st`, `run_laserdesignator_1st`     |
| `weaponraise_*`  | 30    | `weaponraise_g36_1st`, `weaponraise_knife_1st`                      |
| `pistolwhip_*`   | 7     | `pistolwhip_gloc_1st`, `pistolwhip_uzi_1st`                         |
| `hitwithstock_*` | 3     | `hitwithstock_ak47_1st`, `hitwithstock_m1014_1st`                   |
| Other            | 15    | `swim_1st`, `push_button_1st`                                       |

All remaining IFF files (any name not matching the patterns above) use the 31-bone skeleton.

## TNVE -- Keyframe Data

The chunk fourcc `TNVE` is `EVNT` reversed (Events). This is the bulk of the file, containing all animation channel data
as a flat sequence of variable-size entries.

### Entry Size Rule

Every entry starts with a 4-byte header where bytes 2-3 are a `uint16` descriptor. **The entry size in
bytes = `descriptor * 4`**. This rule was validated across all 1,244 files with zero failures.

### Common Entry Header (12 bytes)

```
Offset  Size  Type     Field
0       1     byte     Entry type (0x01, 0x03, 0x04, 0x06, 0x07, 0xFF)
1       1     byte     Bone index
2       2     uint16   Size descriptor (entry_size = descriptor * 4)
4       4     uint32   Frame offset (time position in duration units)
8       4     uint32   Reserved (usually 0)
```

### Entry Types

| Type   | Desc | Size | Data layout                                                      | Description                                                  | Frequency           |
|--------|------|------|------------------------------------------------------------------|--------------------------------------------------------------|---------------------|
| `0x03` | 6    | 24B  | header(12) + position(12)                                        | Position keyframe (3 floats)                                 | Common              |
| `0x04` | 18   | 72B  | header(12) + 3x[quat(16) + pad(4)]                               | Rotation with tangents                                       | ~98% of all entries |
| `0x06` | 8    | 32B  | header(12) + trigger_bone(4) + event_code(4) + position(12)     | Trigger event (sound, FX, etc.)                              | 322 files           |
| `0x07` | 11   | 44B  | header(12) + position(12) + quat(16) + pad(4)                    | Full transform (pos + rot)                                   | 47-bone only        |
| `0x01` | 17   | 68B  | header(12) + int(4) + 2x[quat(16)] + pad(4) + pos(12) + float(4) | Full transform with tangents                                 | 47-bone only        |
| `0xFF` | 3    | 12B  | header only                                                      | Section separator (loop boundary)                            | 0 or 1 per file     |

The `pad` bytes are always `0xAB AB AB AB`.

### Rotation Entry Detail (Type 0x04)

The dominant entry type stores three quaternions per keyframe: the rotation value plus in/out tangents for Hermite
spline interpolation.

```
Offset  Size  Content
0       12    Common header (type=0x04, bone_idx, desc=18, frame_offset, reserved)
12      16    Quaternion value (4 x float32: x, y, z, w)
28      4     Padding (0xAB x 4)
32      16    In-tangent quaternion (4 x float32)
48      4     Padding (0xAB x 4)
52      16    Out-tangent quaternion (4 x float32)
68      4     Padding (0xAB x 4)
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

Non-looping animations have no separator -- just a flat sequence of keyframe entries.

**Important for exporters:** Only Section 1 entries (before the separator) should be used as animation keyframes.
Section 2 provides the wrap-around pose for the game engine's loop blending and should be excluded from exported
animation data.

### Type 0x06 Entries (Trigger Events)

Type `0x06` entries are **trigger events** (sound effects, particle FX, etc.), not animation keyframes. Present in 322 of
1,244 files. Their `bone_index` field is always 0; the actual bone reference is in the `trigger_bone` field.

```
Offset  Size  Content
0       12    Common header (type=0x06, bone_idx=0, desc=8, frame_offset, reserved)
12      4     Trigger bone (uint32; 0xFFFF0000+ = no bone / world-space)
16      4     Event code (uint32; upper 16 bits = 0xABAB sentinel, lower 16 bits = event ID)
20      12    Position (3 x float32; world-space trigger location, NOT bone-space)
```

The position values are world-space coordinates for the trigger location, not bone-local offsets. For example, in
`civilian_walk.iff`, bone 0 has rest position `(0.4, 3.9, 3805.5)` but type `0x06` entries show
`(752.5, 1622.4, -3041.8)` — these are spatial trigger points for footstep sounds, not bone poses.

The event code encodes as `0xABAB0000 | event_id`. To extract the BEF-visible event code: `event_code & 0xFFFF`.
The trigger bone field uses values ≥ `0xFFFF0000` as a sentinel for "no bone" (world-space trigger).

### Delta Compression

Not every bone has a keyframe at every time offset. Only bones whose values change get new entries. A static pose (like
`corpse.iff`) has just 1 position + 31 rotations = 32 entries. A complex walk cycle (`generic_walk.iff`) has 5,018
entries spread across many time offsets.

## ATTA -- Attachment Points

Present in 1,090 of 1,244 files (87.5%). Each attachment is 80 bytes.

```
Offset  Size  Type      Field
0       16    char[16]  Attachment name (null-padded ASCII)
16      12    float3    Position (3 x float32)
28      16    float4    Orientation quaternion (4 x float32)
44      16    float4    Secondary quaternion (4 x float32)
60      4     float     Unknown float
64      4     -         Padding (0xAB x 4)
68      4     uint32    Bone index (0xABABABAB = no bone / unlinked)
72      8     -         Reserved (zeros)
```

The bone index value `0xABABABAB` is the MSVC debug heap fill pattern, used here as a sentinel meaning "not attached to
any bone". These attachments exist as independent scene objects.

### Attachment Count Distribution

| Attachments | Files |
|-------------|-------|
| 0           | 154   |
| 1           | 883   |
| 2           | 143   |
| 3           | 53    |
| 4+          | 11    |

### Common Attachment Names

Most files have a single `weapon` attachment. The 85 unique names include:

- **Equipment**: `weapon`, `helmet`, `halo`, `halo2`, `mapcomputer`, `o2`, `primary`, `chutehandle`, `wire2`
- **Numbered IDs**: Reference model object IDs (e.g., `107_02_1`, `502_01_1`)

## Skeleton Types

Two distinct skeleton types exist across all 1,244 files:

| Property         | 31-bone                               | 47-bone                                                                                    |
|------------------|---------------------------------------|--------------------------------------------------------------------------------------------|
| Files            | 990                                   | 254                                                                                        |
| REIH size        | 404 bytes                             | 612 bytes                                                                                  |
| Naming           | Descriptive (`walk.iff`, `crawl.iff`) | Numbered (`005_XX.iff`, 61 files) and first-person weapon (`fire_ak47_1st.iff`, 193 files) |
| Root children    | 3 (spine + both legs)                 | 2                                                                                          |
| Entry types used | `0x03`, `0x04`, `0x06`                | `0x01`, `0x04`, `0x07`                                                                     |
| End effectors    | 5 (bones 18-20, 29-30)                | 10 (bones 37-46)                                                                           |
| Bone names       | Known (from MEF MANB)                 | Known (from MEF `005_01_1.mef` MANB — detailed hand/finger skeleton)                       |

### Skeleton Compatibility with MEF Models

For an animation to be applied to a model, both must share the same skeleton (bone count and hierarchy). Only MEF
type-1 (skeletal) models have skeletons — the remaining 7,369 MEFs are static geometry with no animation support.

| Bone Count | IFF Animations | MEF Models | Compatible                                                          |
|------------|----------------|------------|---------------------------------------------------------------------|
| 31         | 990            | 237        | Yes — REIH hierarchy and MANB bone names confirmed matching         |
| 47         | 254            | 1          | Yes — 254 first-person hand/weapon animations target `005_01_1.mef` |
| 28         | 0              | 2          | No matching animations exist                                        |

The REIH chunk format is identical in both IFF and MEF files. Child counts are consistent across all files of the same
bone count, confirming the skeleton topology is fixed per type. The 2 MEF files with 28-bone skeletons have no
corresponding IFF animations and may represent articulated objects (e.g., vehicles) that use a different animation
system or are non-animated.

## Bone Names (MANB Reference)

Bone names are stored in the MEF MANB chunk as 16-byte null-padded ASCII strings. Names longer than 15 characters are
truncated. The values below are exact MANB strings as they appear in the binary data.

### 31-Bone Skeleton (from `jones_1.mef`)

| Index | MANB string       | Index | MANB string        |
|-------|-------------------|-------|--------------------|
| 0     | `center`          | 16    | `upper left arm`   |
| 1     | `lower body`      | 17    | `upper right arm`  |
| 2     | `upper left leg`  | 18    | `left toe end`     |
| 3     | `upper right leg` | 19    | `right toe end`    |
| 4     | `upper body`      | 20    | `head end`         |
| 5     | `lower left leg`  | 21    | `lower left arm`   |
| 6     | `lower right leg` | 22    | `lower right arm`  |
| 7     | `shoulders`       | 23    | `left hand`        |
| 8     | `left foot`       | 24    | `right hand`       |
| 9     | `right foot`      | 25    | `upper left finge` |
| 10    | `rotate_head`     | 26    | `upper right fing` |
| 11    | `rotate_left`     | 27    | `lower left finge` |
| 12    | `rotate_right`    | 28    | `lower right fing` |
| 13    | `left toe`        | 29    | `left fingers end` |
| 14    | `right toe`       | 30    | `right fingers en` |
| 15    | `head`            |       |                    |

### 47-Bone Skeleton (from `005_01_1.mef`)

| Index | MANB string        | Index | MANB string        |
|-------|--------------------|-------|--------------------|
| 0     | `center shoulders` | 24    | `lower right midd` |
| 1     | `upper left arm`   | 25    | `lower right ring` |
| 2     | `upper right arm`  | 26    | `lower right thum` |
| 3     | `lower left arm`   | 27    | `left forefinger ` |
| 4     | `lower right arm`  | 28    | `left little fing` |
| 5     | `left hand`        | 29    | `left middle fing` |
| 6     | `right hand`       | 30    | `left ring finger` |
| 7     | `upper left foref` | 31    | `left thumb tip`   |
| 8     | `upper left littl` | 32    | `right forefinger` |
| 9     | `upper left middl` | 33    | `right little fin` |
| 10    | `upper left ring ` | 34    | `right middle fin` |
| 11    | `upper left thumb` | 35    | `right ring finge` |
| 12    | `upper right fore` | 36    | `right thumb tip`  |
| 13    | `upper right litt` | 37    | `none09`           |
| 14    | `upper right midd` | 38    | `none07`           |
| 15    | `upper right ring` | 39    | `none06`           |
| 16    | `upper right thum` | 40    | `none08`           |
| 17    | `lower left foref` | 41    | `none10`           |
| 18    | `lower left littl` | 42    | `none02`           |
| 19    | `lower left middl` | 43    | `none05`           |
| 20    | `lower left ring ` | 44    | `none03`           |
| 21    | `lower left thumb` | 45    | `none04`           |
| 22    | `lower right fore` | 46    | `none01`           |
| 23    | `lower right litt` |       |                    |

### 28-Bone Skeleton (from `pat_2.mef`)

| Index | MANB string       | Index | MANB string        |
|-------|-------------------|-------|--------------------|
| 0     | `center`          | 14    | `right toe`        |
| 1     | `lower body`      | 15    | `head end`         |
| 2     | `upper left leg`  | 16    | `lower left arm`   |
| 3     | `upper right leg` | 17    | `lower right arm`  |
| 4     | `upper body`      | 18    | `left toe end`     |
| 5     | `lower left leg`  | 19    | `right toe end`    |
| 6     | `lower right leg` | 20    | `left hand`        |
| 7     | `shoulders`       | 21    | `right hand`       |
| 8     | `left foot`       | 22    | `upper left finge` |
| 9     | `right foot`      | 23    | `upper right fing` |
| 10    | `head`            | 24    | `lower left finge` |
| 11    | `upper left arm`  | 25    | `lower right fing` |
| 12    | `upper right arm` | 26    | `left fingers end` |
| 13    | `left toe`        | 27    | `right fingers en` |

The 28-bone skeleton is the 31-bone humanoid with 3 rotation helper bones removed: `rotate_head`, `rotate_left`,
`rotate_right`. Used only in `pat_2.mef` (location 2 common, location 3 level 6). No IFF animations exist for this
skeleton.

## Timing

Frame offsets in TNVE entries use the same time unit as `DHNA.duration`. Empirically, every observed duration is a
multiple of **160 ticks**, which corresponds to **one frame at 30 fps** -- i.e. **4,800 ticks per second**. Dividing a
tick count by 4,800 gives seconds, producing natural clip lengths across the corpus (single weapon shot ~0.5 s, run
cycle ~1.0 s, walk cycle ~2.0 s, rifle reload ~3.4 s, C4 plant ~5.0 s). The exporter uses this factor
(`ANIMATION_TICKS_PER_SECOND = 4800` in `iff_to_fbx.py`) to set the real FBX timeline length instead of normalizing
every clip to 1 second.

The frame rate is the single empirically-fitted value; if in-game playback is uniformly ~2x off, the engine runs at
60 fps and the factor is 9,600. Relative clip lengths are correct regardless of frame rate.

## Playback Direction and the `fo=0` Ready Anchor (first-person clips)

For 47-bone first-person weapon clips (`*_1st`), frame offset 0 holds a **single canonical "weapon ready" pose shared by
every clip of that weapon**. This was verified by comparing bone 0 at `fo=0` across `fire_ak47_1st`, `reload_ak47_1st`,
and `weaponraise_ak47_1st` -- all three share the same ready pose `(-0.88, -12.58, ~2.6)` with rotation `~(0, -26, 0)`.

- **Symmetric clips** (`fire_*`, `reload_*`, `walk_*`, `run_*`) start and end at this ready pose, so playback direction
  is not visually observable.
- **`weaponraise_*` clips are stored one-way: ready (`fo=0`) -> lowered/away (last frame).** There is no separate
  `lower`/`holster` clip. The engine plays `weaponraise` **in reverse** when selecting a weapon, so it finishes at the
  ready pose. Played forward (as the IFF stores it, and as the exporter faithfully emits it) the weapon appears to
  *lower*, not raise.

The exporter does **not** reverse these clips -- it reads the binary as authored. To get a correct "raise" in a DCC tool
or game engine, play the exported `weaponraise_*` clips backward (e.g. reverse the clip / set negative speed in the
animation controller). This reverse-on-select behavior is a playback-layer decision in the original engine and is not
encoded anywhere in the IFF binary.

## BEF Source Format

BEF files are the reverse-engineered text-based source format from which IFF binary animations were compiled. 1,244 BEF
files exist in 1:1 correspondence with IFF files. They use a C-like syntax of semicolon-terminated function calls,
identical to QSC script files.

### Structure

```
AnimInit(name, 0, duration, looping);
BreakScript();
Bone(id, "Bone # XX", parent_id, x, y, z);  // × bone_count
BuildHierarchy();
AnimAttachObject(name, index, ox,oy,oz,ow, sx,sy,sz,sw, uf, px,py,pz);  // optional
AnimAttachObjectBoneID(index, bone_id);                                    // optional
BreakScript();
TranslationKeyFrameData(bone, 0, tick, x, y, z);
RotationKeyFrameData(bone, 0, tick, qx,qy,qz,qw, ix,iy,iz,iw, ox,oy,oz,ow);
TriggerData(id, event_code, tick, bone, x, y, z);  // optional
```

### Field Mapping (BEF → IFF Binary)

| BEF Function | IFF Location | Field Mapping |
|---|---|---|
| `AnimInit` arg0 | DHNA | Animation name (string) |
| `AnimInit` arg1 | DHNA `unknown_01` | Always 0 (NOT `version`, which is always 4) |
| `AnimInit` arg2 | DHNA `duration` | BEF value = IFF value + 1 |
| `AnimInit` arg3 | DHNA `looping` | 0 = one-shot, 1 = looping |
| `Bone` parent_id | REIH | BEF stores explicit parent indices; REIH encodes as BFS child counts |
| `Bone` x,y,z | REIH offsets | Rest-pose parent-relative translations |
| `AnimAttachObject` 12 floats | ATTA | orientation(4) + secondary(4) + unknown_float(1) + position(3) |
| `AnimAttachObjectBoneID` | ATTA `bone_index` | Attachment index is implicit (sequential order) |
| `TranslationKeyFrameData` | TNVE 0x03 | bone, 0, frame_offset, position xyz |
| `RotationKeyFrameData` | TNVE 0x04 | bone, 0, frame_offset, 3× quaternion (value + in_tangent + out_tangent) |
| `TriggerData` | TNVE 0x06 | sequential_id, event_code & 0xFFFF, frame_offset, trigger_bone, position xyz |

### Statistics

- AnimInit arg1: always 0 across all 1,244 files
- AnimInit arg3: 839 files = 0 (non-looping), 405 files = 1 (looping)
- TriggerData present in 322/1,244 files

### TNVE Entry Type to BEF Function Mapping

| TNVE Entry | Type | BEF Function(s) | Notes |
|---|---|---|---|
| `TNVEPosition` | 0x03 | `TranslationKeyFrameData(bone, 0, tick, x, y, z)` | Direct 1:1 mapping |
| `TNVERotation` | 0x04 | `RotationKeyFrameData(bone, 0, tick, qx,qy,qz,qw, ix,iy,iz,iw, ox,oy,oz,ow)` | 3 quaternions: value + in_tangent + out_tangent |
| `TNVETrigger` | 0x06 | `TriggerData(seq_id, event_code & 0xFFFF, tick, trigger_bone, x, y, z)` | `bone_index` is always 0; real bone is `trigger_bone` |
| `TNVEFullTransform` | 0x07 | `TranslationKeyFrameData(...)` + `RotationKeyFrameData(...)` | Split into 2 calls; quaternion duplicated for all 3 tangent slots |
| `TNVEFullTransformTangent` | 0x01 | `TranslationKeyFrameData(...)` + `RotationKeyFrameData(...)` | Split into 2 calls; `quaternion_a` used for all 3 tangent slots |
| `TNVESeparator` | 0xFF | *(not emitted)* | Loop boundary marker — skipped in BEF output |

Types 0x07 and 0x01 only appear in 47-bone animations. BEF has no combined transform function, so the converter emits
separate translation + rotation calls. The rotation call duplicates the quaternion value into the in/out tangent slots
since these types store no separate tangent data.

### Converter

The `iff_to_qsc` converter reconstructs BEF source from IFF binary data using the QSC AST infrastructure. Output files
use the `.bef` extension. Available as the `convert-iff-to-qsc` CLI command.

## Open Questions

- **Time units**: The exact conversion from duration units to seconds/frames needs verification against in-game
  playback.
- **Interpolation scheme**: The three quaternions per rotation entry (value + 2 tangents) suggest Hermite spline
  interpolation, but the exact formulation needs confirmation.
- **Secondary ATTA quaternion**: The second quaternion in each ATTA entry may be a tangent, inverse bind pose, or
  interpolation endpoint.
- **47-bone `noneXX` bones**: The 47-bone skeleton has 10 end effectors named `none01`–`none10`. Their purpose is
  unclear — they may be fingertip end effectors, IK targets, or attachment points.
