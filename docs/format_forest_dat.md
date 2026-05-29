[← Terrain System](format_terrain.md) · [Back to README.md](../README.md#supported-game-file-formats) · [Graph DAT →](format_graph_dat.md)

# Forest DAT Format

Forest DAT files (`forest_*.dat`) store vegetation instance placement data — positions, rotations, scales, and pre-baked light colors for trees and bushes in each level. There are 109 files total (67 unique after deduplication across locations). Each file corresponds to a `Forest` task in the level's `objects.qsc` — the numeric suffix in the filename is the task ID (e.g. `forest_2540.dat` corresponds to `Task_New(2540, "Forest", ...)`).

## Correlation with objects.qsc

The `Forest` task in `objects.qsc` declares per-forest parameters:

```
Task_New(2540, "Forest", "",
    43643.95, 1736414.38, 155616.58,  # Position (ObjectPos)
    "900_16_1",                        # Model (base vegetation model name)
    250,                               # Area size (meters)
    FALSE,                             # Randomize area (PushButton)
    FALSE,                             # Update (PushButton)
    FALSE,                             # Calculate light (PushButton)
    0,                                 # Density of trees [1/m^2]
    1,                                 # Random rotation range
    0.2, 0.2, 0.2,                    # Random X/Y/Z-scale range
    FALSE,                             # Isotropic scaling
    34,                                # Number of trees
    1,                                 # Brush size (m)
    TRUE,                              # Brush draw/delete
    500,                               # View cutoff (m)
    FALSE,                             # Normalize objects to ground
    2)                                 # Number of LODs affected by wind
```

The `Number of trees` parameter matches the record count in the corresponding `.dat` file exactly. Verified across all 19 single-player levels.

## Location

```
missions/location*/level*/forest_*.dat
```

## Structure Overview

```
┌──────────────────────────────────────┐
│ Header (14 bytes)                    │
│   uint32 (value = 10)               │
│   newline (0x0A)                     │
│   ASCII "Ver. 3.0"                   │
│   newline (0x0A)                     │
├──────────────────────────────────────┤
│ Record 0 (40 bytes)                  │
├──────────────────────────────────────┤
│ Record 1 (40 bytes)                  │
├──────────────────────────────────────┤
│ ...                                  │
├──────────────────────────────────────┤
│ Record N-1 (40 bytes)               │
└──────────────────────────────────────┘
```

## Header

14 bytes. A uint32 value followed by a version string.

| Offset | Size | Type   | Value      | Description             |
|--------|------|--------|------------|-------------------------|
| 0      | 4    | uint32 | 10         | Unknown constant        |
| 4      | 1    | byte   | 0x0A       | Newline separator       |
| 5      | 8    | ASCII  | `Ver. 3.0` | Format version string   |
| 13     | 1    | byte   | 0x0A       | Newline separator       |

## Record Layout

Each record is 40 bytes, little-endian:

| Offset | Type    | Field      | Description                              |
|--------|---------|------------|------------------------------------------|
| 0      | 3×f32   | position   | World XYZ coordinates                    |
| 12     | f32     | rotation_x | Tilt angle in radians, usually 0         |
| 16     | f32     | rotation_y | Usually −0.0 (`0x80000000`), sometimes non-zero |
| 20     | f32     | rotation_z | Yaw rotation in radians (0–2π)           |
| 24     | 3×f32   | scale      | XYZ scale, usually uniform               |
| 36     | uint8   | color_r    | Pre-baked light color, red component      |
| 37     | uint8   | color_g    | Pre-baked light color, green component     |
| 38     | uint8   | color_b    | Pre-baked light color, blue component      |
| 39     | uint8   | color_a    | Unused (always 0)                          |

## Record Count

The number of records is calculated from the file size:

```
record_count = (file_size - 14) / 40
```

All 67 unique files have exact 40-byte record alignment with zero remainder. Record counts range from 1 to 3,585 trees per file.

## Field Notes

### Position

Three float32 values representing world-space XYZ coordinates where the vegetation instance is placed.

### Rotation

- **rotation_x** — tilt angle, usually 0.0. Range: 0–2π when non-zero.
- **rotation_y** — usually negative zero (`0x80000000`). Occasionally non-zero across files.
- **rotation_z** — yaw (heading) rotation in radians, range 0–2π.

### Scale

Three float32 values for XYZ scale. Usually uniform (same value for all three axes), but occasionally non-uniform scaling is used.

### Color

Four bytes storing a pre-baked per-instance light color (RGB + unused alpha). The model for all instances in a file is determined by the parent `Forest` task in `objects.qsc`, not stored per-record.

- **color_r, color_g, color_b** — RGB components (0–255) of the lighting color at this vegetation instance's position.
- **color_a** — Always 0 (unused padding byte).

The color tint varies by location climate: location1 (warm) shows R > G > B (brownish), while location3 (colder) shows B > G > R (bluish). These values correspond to the "Calculate light" button in the Forest task's QSC parameters.

## File Naming

Files are named `forest_<task_id>.dat` where `<task_id>` is the numeric ID from the `Task_New(id, "Forest", ...)` call in the level's `objects.qsc`. A level can have 0–5 forest files (one per Forest task). The same task IDs appear in multiple levels when locations share geometry.

```
missions/
  location1/
    level1/
      forest_3140.dat     # Task_New(3140, "Forest", "Grass", ...) — 1,897 trees
      forest_3141.dat     # Task_New(3141, "Forest", "Bushes", ...) — 918 trees
      forest_3663.dat     # Task_New(3663, "Forest", "small pine", ...) — 204 trees
      forest_3826.dat     # Task_New(3826, "Forest", "Birch", ...) — 213 trees
      forest_3827.dat     # Task_New(3827, "Forest", "2ak", ...) — 91 trees
  location2/
    level1/
      forest_2540.dat     # Task_New(2540, "Forest", "", ...) — 34 trees
  ...
```

## Parser

```python
from igipy.igi2.formats import DATForest
```

`DATForest.model_validate_stream(stream)` returns a model with `header_value`, `version`, and `records: list[ForestRecord]`. Each `ForestRecord` has `position_x/y/z`, `rotation_x/y/z`, `scale_x/y/z`, and `color_r/g/b/a`.

## See Also

- [Terrain System](format_terrain.md) — terrain height, material, and light maps
- [Graph DAT Format](format_graph_dat.md) — AI navigation graph format
- [File extensions overview](extensions.md) — full list of game file formats
