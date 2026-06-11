[Back to README](../../../README.md)

# IFF Format (`.iff`)

> **Status:** Documented — verified against all 6 IGI 1 animation files
> (`common/anims/000.iff`, `001`, `002`, `003`, `005`, `006`; `004` does not ship).

IGI 1 `.iff` files are **skeletal animation libraries**: one shared skeleton plus
many animation clips for a character. They are **not** the same format as IGI 2
`.iff` (which is an `ILFF` container, little-endian, content type `ANIM` — stored
on disk reversed as `MINA`). The two games share the extension but nothing else.

> **010 Editor template:** a binary template that decodes this format lives at
> `templates/igi1/iff.bt`. In 010 Editor, open a `.iff` file (file mask `*.iff`)
> and run *Templates → Run Template* on it to get a fully labelled, navigable
> tree of the skeleton and every animation clip.

## Container: EA IFF 85 (`FORM`)

IGI 1 `.iff` uses the classic **Electronic Arts IFF-85** container:

- Every chunk is `tag (4 ASCII bytes) + size (uint32, BIG-ENDIAN) + data[size]`.
- Chunks are word-aligned: when `size` is odd, a single `0x00` pad byte follows.
- `FORM` chunks are containers; their data begins with a 4-byte form type, then
  child chunks.

> **Endianness split (important):** chunk *sizes* are **big-endian** (EA IFF
> convention), but all *payload* fields (ints, floats) are **little-endian**
> (the game ran on x86). A parser must read `>I` for chunk sizes and `<...` for
> everything inside a chunk.

### The 12-byte grouping-FORM quirk

The two *grouping* forms `BOBJ` and `BOAL` declare a `size` that is **12 bytes
short** — it covers their real children plus only the 12-byte header of the
*next* sibling form, not that sibling's body. Concretely, in `002.iff`:

```
@0x000 FORM BOBJ  size=588      (claims to end at 0x254)
@0x00c FORM BOBH  size=564      (skeleton — correct; full span 572 = 8-byte header + 564, ends at 0x248)
@0x248 FORM BOAL  size=155228   (BOAL header sits inside BOBJ's claimed range!)
```

`BOBJ.size` (588) = `BOBJ` type (4) + full `BOBH` (572) + just the 12-byte
`BOAL` header. **Do not rely on `BOBJ`/`BOAL` sizes to find the end of their
content.** Walk children by *their own* sizes instead; the leaf chunks and the
`BOBH`/`BOAN` form sizes are all correct and tile perfectly to EOF. This quirk is
consistent across every file.

## Chunk tree

```
FORM "BOBJ"                              root body object
├─ FORM "BOBH"                           body header (skeleton, size reliable)
│  ├─ BOSH   8 B                         skeleton header: {object_id, bone_count}
│  ├─ PLST   4 * bone_count B            parent index per bone (-1 = root)
│  └─ TLST   12 * bone_count B           bind-pose translation per bone (3 * f32)
└─ FORM "BOAL"                           animation list (size unreliable — walk to EOF)
   ├─ BALH   8 B                         {animation_count, animation_id_capacity}
   └─ FORM "BOAN" * animation_count      one animation clip each (size reliable)
      ├─ BOAH  12 B                      clip header: {duration, flags, animation_id}
      ├─ BOTH  4 B                       translation keyframe count  (root motion track)
      ├─ BOTD  40 * count B              translation keyframes
      ├─ ( BORH 4 B + BORD 52*count B ) * bone_count   one rotation track per bone
      ├─ BOEH  4 B                       event count
      └─ BOED  24 * count B              events (may be empty)
```

Per-file shape (verified):

| File      | object_id | bone_count | animations (`BALH[0]`) | `BALH[1]` |
|-----------|-----------|------------|------------------------|-----------|
| `000.iff` | 0         | 33         | 122                    | 247       |
| `001.iff` | 1         | 33         | 95                     | 212       |
| `002.iff` | 2         | 33         | 18                     | 20        |
| `003.iff` | 3         | 33         | 47                     | 50        |
| `005.iff` | 5         | 56         | 78                     | 81        |
| `006.iff` | 6         | 33         | 16                     | 18        |

`bone_count` is 33 for the standard human skeleton and 56 for `005.iff`.

## Chunk reference

### `BOSH` — skeleton header (8 B)

| Offset | Type      | Field         | Notes                                        |
|--------|-----------|---------------|----------------------------------------------|
| 0      | int32 LE  | `object_id`   | Matches the file number (`000.iff` → 0, …).  |
| 4      | int32 LE  | `bone_count`  | Number of bones; drives `PLST`/`TLST` lengths and the rotation-track count per clip. |

### `PLST` — parent list (`4 * bone_count` B)

`bone_count` × int32 LE. Entry *i* is the parent bone index of bone *i*; the root
bone stores `-1` (`0xFFFFFFFF`). The 33-bone hierarchy is identical across all
33-bone files; `005.iff` has its own 56-bone hierarchy.

### `TLST` — bind translation list (`12 * bone_count` B)

`bone_count` × `(x, y, z)` float32 LE — each bone's rest-pose translation
relative to its parent. Combine with `PLST` to build the bind pose.

### `BALH` — animation-list header (8 B)

| Offset | Type     | Field                   | Notes                                              |
|--------|----------|-------------------------|----------------------------------------------------|
| 0      | int32 LE | `animation_count`       | Exact number of `BOAN` clips that follow.          |
| 4      | int32 LE | `animation_id_capacity` | One past the highest `animation_id` (`BOAH`); a sparse-id range. *(High confidence, not byte-proven.)* |

### `BOAH` — clip header (12 B)

| Offset | Type      | Field          | Notes                                                            |
|--------|-----------|----------------|------------------------------------------------------------------|
| 0      | float32 LE| `duration`     | Clip length in time units (≈ last keyframe time).                |
| 4      | uint32 LE | `flags`        | Bit 31 (`0x80000000`) observed set on looping cycle clips (walk/run). *(Hypothesis.)* |
| 8      | uint32 LE | `animation_id` | Sparse, increasing per file — the ID gameplay scripts reference. |

### `BOTH` / `BOTD` — translation (root-motion) track

`BOTH` is a single int32 LE keyframe `count`. `BOTD` is `count` records of 40 B
(10 × float32 LE), one shared track for the whole clip (root translation):

| Floats | Field          | Notes                          |
|--------|----------------|--------------------------------|
| 0..2   | `position`     | x, y, z                        |
| 3      | `time`         | Keyframe timestamp (time units)|
| 4..6   | `tangent_in`   | Incoming tangent vector (0 when static) |
| 7..9   | `tangent_out`  | Outgoing tangent vector        |

Keyframe counts range from 1 (static root) to 223 (heavy root motion).

### `BORH` / `BORD` — rotation track (one pair per bone)

A clip contains exactly `bone_count` `BORH`+`BORD` pairs, in bone order. `BORH`
is an int32 LE keyframe `count`; `BORD` is `count` records of 52 B (13 ×
float32 LE):

| Floats | Field            | Notes                                            |
|--------|------------------|--------------------------------------------------|
| 0..3   | `rotation`       | Quaternion (x, y, z, w) at the keyframe          |
| 4      | `time`           | Keyframe timestamp (time units)                  |
| 5..8   | `rotation_b`     | Control/tangent quaternion (== `rotation` when static) |
| 9..12  | `rotation_c`     | Control/tangent quaternion (== `rotation` when static) |

The two extra quaternions are interpolation controls (spherical-cubic / squad);
for a constant pose all three quaternions are identical. `BORD.size` always
equals `count * 52`.

### `BOEH` / `BOED` — event track

`BOEH` is an int32 LE event `count` (often 0, in which case `BOED` has size 0).
`BOED` is `count` records of 24 B:

| Offset | Type      | Field        | Notes                                                       |
|--------|-----------|--------------|-------------------------------------------------------------|
| 0      | uint32 LE | `event_id`   | e.g. `1003`, `1010` — same ID space as IGI 2 `animtrigger.qsc` (footstep / reload / sfx triggers). |
| 4      | float32 LE| `time`       | Event timestamp.                                            |
| 8      | float32 LE| `param`      | Secondary scalar (purpose unconfirmed).                     |
| 12..23 | 3× f32 LE | `position`   | x, y, z — where the event fires (e.g. footstep/muzzle).     |

## Parsing strategy (summary)

1. Read root `FORM BOBJ`. Do **not** trust its size.
2. Read child `FORM BOBH` (size reliable); inside it read `BOSH`, `PLST`, `TLST`.
   Take `bone_count` from `BOSH`.
3. Skip to the `FORM BOAL` that follows `BOBH` (its 12-byte header overlaps
   `BOBJ`'s claimed range — see the quirk above). Do **not** trust `BOAL`'s size.
4. Read `BALH` (gives `animation_count`).
5. Read `animation_count` × `FORM BOAN` (each size reliable). Within each:
   `BOAH`, then `BOTH`+`BOTD`, then `bone_count` × (`BORH`+`BORD`), then
   `BOEH`+`BOED`.
6. Stop at EOF; the children tile exactly to the end of the file.

## Animation identity & event naming

Animations carry **no name strings** anywhere in the file — the only printable
runs are the chunk tags themselves. Clips and their events are identified purely
by integers, resolved through two separate mechanisms.

### Clips: a global animation index (`BOAH.animation_id`)

Each clip's `animation_id` (`BOAH`) is a slot in a **global animation index**, not
a per-file counter:

- IDs start at **2** (0 and 1 are never used) and are always stored in ascending
  order within a file.
- IDs are **sparse** in larger sets — e.g. `000.iff` (the player) uses
  `2, 4, 10, 11, 14, 15, 17, 19, 25, … 246` with gaps, while a simple character
  (`002.iff`) uses the dense range `2…19`.
- The same ID means the *same logical action* across every skeleton: a character
  simply omits the IDs it does not need. This is why `BALH[1]`
  (`animation_id_capacity`) tracks the highest ID rather than the clip count.

Gameplay scripts select clips by this same integer. AI behaviour QVMs
(`common/ai/guard.qvm`, `gunner.qvm`, …) call `AIAction_PlayAnimation(<id>, …)`
with the bare `animation_id` — e.g. `AIAction_PlayAnimation(36, 0)` plays the
clip whose `BOAH.animation_id` is 36:

```
AIAction_PlayAnimation(36, 0);   // play global animation slot 36
AIAction_PlayAnimation(37, 0);
AIAction_PlayAnimation(39, 0);
```

The **human-readable meaning of each ID (idle, walk, run, crouch, reload, death,
…) is not stored in the data** — neither the `.iff` nor the scripts name it; it is
a fixed enum in the engine, keyed by `animation_id`. To label a clip you must map
its ID through that engine-side table; the data only tells you *which numbered
slot* a clip fills and *when* it is played.

### Events: named via `animtrigger.qvm`

The per-clip event track (`BOED`) *is* named, through the same animation-trigger
system IGI 2 uses. Each `BOED.event_id` in the `1000…1054` range is defined in
`common/animtrigger/animtrigger.qvm`:

```
DefineAnimTrigger(1003, TASKTYPE_ANIMSOUND, "m16_reload_1", TRUE);
DefineAnimTrigger(1006, TASKTYPE_ANIMSOUND, "mp5_reload_1", TRUE);
DefineAnimTrigger(1025, TASKTYPE_ANIMSOUND, "walk_fence_1", FALSE);
```

So an event with `event_id = 1003` at its `time` means "play the `m16_reload_1`
sound." All 50 trigger IDs defined by `animtrigger.qvm` are referenced by the six
shipped animation files. Clips also contain **low-numbered events (`0…12`)** that
are *not* present in `animtrigger.qvm`; these appear to be generic engine markers
(e.g. footstep left/right) and are not yet identified.

## Open questions

- `BOAH.flags` bit semantics beyond the looping bit (only `0x0` and `0x80000000`
  seen).
- Exact time-unit scale (values such as 1600 / 3360 / 13280 per clip).
- `BOED.param` meaning.
- The engine-side `animation_id` → action-name table (idle/walk/run/…) is not in
  the data; it would need extracting from the executable or inferring by playback.
- Meaning of the low-numbered events (`0…12`) that are absent from
  `animtrigger.qvm` (suspected generic markers such as footstep left/right).
- Cross-confirm `BALH[1]` as `max(animation_id) + 1` against a file with a
  guaranteed-dense id range.
