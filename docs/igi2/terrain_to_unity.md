[Back to README](../../README.md)

# Terrain → Unity Export (temporary tooling)

This page documents the reverse-engineering assumptions behind
[`scripts/terrain_to_unity_json.py`](../../terrain_to_unity_json.py) and its companion
Unity importer [`scripts/unity/IgiTerrainImporter.cs`](../../scripts/unity/IgiTerrainImporter.cs).
The pipeline merges a level's `.thm` heightmaps into a single Unity `Terrain`.

> **Status: temporary.** These scripts live outside the `igipy` CLI and are throwaway helpers
> for the `igipy-unity` port. The format facts below are the durable part; the scripts may be
> deleted once the C# importer absorbs the logic.

## Pipeline

```
heightmap000.thm (coarse base) ─┐
                                ├─► terrain_to_unity_json.py ─► terrain_unity.json ─► IgiTerrainImporter.cs ─► Unity Terrain
heightmap002.thm (fine detail) ─┘
```

1. The Python script reads both `.thm` files (via the [THM parser](formats/thm.md)).
2. It converts raw values to meters, places each patch in world space, and resamples both onto
   one square grid sized for Unity's `Terrain` component.
3. The C# Editor script (`IGI/Import Terrain JSON...`) reads the JSON and builds a `TerrainData`.

## Where the parameters come from

The level's `objects.qvm` describes the terrain through `Terrain` and `TerrainMap` objects (see
[level.md](level.md)). The values fed to the exporter map directly onto `TerrainMap` fields:

| Exporter argument     | `TerrainMap` field         | location1/level1 value          |
|-----------------------|----------------------------|---------------------------------|
| `--base-path`         | ID 0 (low-res) map         | `heightmap000.thm` (128×128)    |
| `--detail-path`       | ID 2 (hi-res) map          | `heightmap002.thm` (256×256)    |
| `--base-world-size`   | World width / World height | 3000 m                          |
| `--detail-world-size` | World width / World height | 750 m                           |
| `--detail-center`     | Position (3 floats)        | `-1302000, 1386000` (raw units) |
| `--feather-cells`     | Soften edge size           | engine blends the hi-res edge   |

The `Soften edge size` field confirms the engine itself feathers the hi-res patch into the base —
the `--feather-cells` blend band is the Unity-side analogue.

## Divisors

The shared terrain header carries `terrain_scale = 0.01`, but that is **not** the value used here.
Empirically the correct height conversion is a fixed-point **÷4096** (12 fractional bits):

```
height_meters = raw_float / 4096
```

The same ÷4096 divisor applies to **positions**, proven by location1/level1:

```
-1302000 / 4096 = -317.87 m   (Unity X)
 1386000 / 4096 = +338.38 m   (Unity Z)
```

A 750 m patch centered there spans X∈[−692.9, +57.1], Z∈[−36.6, +713.4] — comfortably inside the
3000 m base map (−1500…+1500). The alternative `× 0.01` would give −13020 m, far off the map, so
it is ruled out. Both divisors remain CLI parameters (`--height-divisor`, `--position-divisor`,
default 4096) in case a different level needs re-tuning.

### Measured ranges (location1/level1)

| File               | Grid    | World size | Sample spacing | Raw→m (÷4096) range |
|--------------------|---------|------------|----------------|---------------------|
| `heightmap000.thm` | 128×128 | 3000 m     | ≈23.6 m/sample | −26.4 … 747.2 m     |
| `heightmap002.thm` | 256×256 | 750 m      | ≈2.9 m/sample  | −27.9 … 202.6 m     |

## Coordinate mapping (IGI → Unity)

IGI uses a DirectX-era right-handed system with the heightmap on the horizontal plane and
elevation as the up axis. Unity is left-handed, Y-up. The exporter maps:

```
IGI X (east)  → Unity X (right)
IGI Y (north) → Unity Z (forward)
height        → Unity Y (up)
```

Because the source is right-handed and Unity is left-handed, a **horizontal mirror** is often
needed. Rather than guess, the exporter exposes orientation toggles you correct by eye against the
in-game map editor — no code change required:

- `--flip-rows` — mirror grid rows (world Z)
- `--flip-columns` — mirror grid columns (world X)
- `--swap-axes` — transpose rows/columns
- `--rotate {0,90,180,270}` — rotate the merged terrain clockwise by N degrees (default 0)

The THM grid is stored row-major from the top-left; the working assumption is **row = +Z (north),
column = +X (east)**. If the imported terrain looks mirrored or rotated versus the editor, apply
the toggle that fixes it.

### Rotating the terrain to match already-rotated objects

The rest of a level's geometry (buildings, soldiers, patrol paths exported from `objects.qvm`)
is already rotated into Unity's frame. If the terrain alone lands 90° off, rotate **the terrain to
match the objects** with `--rotate` — do **not** change the global IGI→Unity axis mapping, which
would re-break the already-correct objects.

- **Direction.** `--rotate` is degrees **clockwise** viewed top-down, implemented as
  `np.rot90(merged_meters, k=-(degrees // 90))` (numpy's positive `k` is counter-clockwise, so a
  clockwise rotation uses a negative `k`). Because the THM row axis runs opposite to world-north on
  screen, array-clockwise can present as world-counter-clockwise — so if `--rotate 90` lands
  mirrored or backwards versus the objects, try `--rotate 270` (optionally combined with a
  `--flip-*` toggle) and keep the one that aligns.
- **Order of operations.** Per-patch flips (`--flip-*`, applied inside `load_patch`) run first, then
  the base + detail patches are merged, then `--rotate` is applied **once** to the merged composite —
  so base and detail rotate together and stay registered.
- **Why the Python exporter, not a Unity transform.** Unity's `Terrain` component ignores
  `transform.rotation` (the heightfield renderer and collider stay axis-aligned), so the rotation
  must be baked into the height data. `IgiTerrainImporter.cs` needs no change: the grid stays a
  square `R×R` and the JSON contract is unchanged.
- **Placement invariant.** For the default square base (`--base-world-size` is one value) centered
  at the origin (`--base-center 0,0`), `worldSizeMeters` is square and `terrainCornerMeters` is
  symmetric about the origin, so both are rotation-invariant and need no fix-up. If you rotate by
  90/270 with a **non-zero** `--base-center`, the corner is not recomputed (rotation about the array
  center ≠ rotation about the world origin); the exporter prints a `WARNING` in that case.

## Combining the two heightmaps (single merged grid)

`location1/level1` shows as one continuous plane in the editor even though two `.thm` files exist.
The exporter reproduces that as a single Unity terrain:

1. Allocate one `R × R` grid (`--resolution`, must be `2ⁿ+1`; default **1025**) spanning the base
   extent. At 1025 over 3000 m the cell size is ≈2.93 m — fine enough to preserve the hi-res patch.
2. Bilinearly sample the **base** everywhere.
3. Where an output cell falls inside the **detail** footprint, sample the detail and override the
   base, linearly feathered over `--feather-cells` near the footprint edge to soften the seam.
4. Normalize the merged heights to `0..1` over the global min/max (what `TerrainData.SetHeights`
   expects) and record the absolute range so the importer can place the terrain at the right height.

## JSON contract

```json
{
  "resolution": 1025,
  "worldSizeMeters": { "x": 3000.0, "z": 3000.0 },
  "heightRangeMeters": { "min": -27.85, "max": 747.1562 },
  "terrainCornerMeters": { "x": -1500.0, "z": -1500.0 },
  "heights": [ /* resolution*resolution floats in 0..1, row-major heights[z][x] */ ],
  "meta": { "...": "sources, divisors, detail footprint, orientation flags, sample spacing" }
}
```

The Unity importer builds `TerrainData` with `heightmapResolution = resolution`,
`size = (worldSizeMeters.x, max−min, worldSizeMeters.z)`, calls `SetHeights`, then places the
terrain GameObject at `(terrainCornerMeters.x, heightRangeMeters.min, terrainCornerMeters.z)` so
absolute elevations line up with the rest of the level.

## Usage

```bash
python scripts/terrain_to_unity_json.py \
  --base-path=.ignore/igi2_collected/missions/location1/level1/heightmaps/heightmap000.thm \
  --base-world-size=3000 --base-center=0,0 \
  --detail-path=.ignore/igi2_collected/missions/location1/level1/heightmaps/heightmap002.thm \
  --detail-world-size=750 --detail-center=-1302000,1386000 \
  --resolution=1025 --rotate=90 --output=terrain_unity.json
```

> **`--rotate` tip:** start with `--rotate=90` and compare against the already-rotated objects in
> Unity; if the terrain lands mirrored or turned the wrong way, switch to `--rotate=270`. See
> [Rotating the terrain to match already-rotated objects](#rotating-the-terrain-to-match-already-rotated-objects).

> **Note:** because `--detail-center` starts with a minus sign, pass it with `=`
> (`--detail-center=-1302000,1386000`); a space-separated value is parsed as a flag.

Then in Unity: copy `IgiTerrainImporter.cs` into an `Editor/` folder, run
**IGI → Import Terrain JSON...**, and pick the JSON.

## Open questions (validate against the editor)

- **Origin vs. center.** The `TerrainMap.Position` field is labeled "world position of map origin",
  but the working assumption here (and the user's editor observation) is that position is the patch
  **center**. The exporter treats it as center. If the hi-res patch lands offset by half its size,
  switch the convention.
- **Handedness mirror.** Confirm the correct `--flip-*` combination by comparing landmark positions
  to the in-game map editor.
- **Vertices vs. cells.** Sample spacing assumes `world_size / (grid − 1)` (samples are vertices).
  If edges are slightly off, the engine may use `world_size / grid` (cells).
- **Soften edge size → feather.** The exact engine blend width is not yet read from `objects.qvm`;
  `--feather-cells` is a manual approximation.
