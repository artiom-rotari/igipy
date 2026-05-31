[Back to README](../../README.md)

# Terrain System Overview

IGI2 uses three file formats that work together to define terrain geometry, texturing, and lighting. All three are stored in `missions/locationN/levelN/heightmaps/` and share a naming convention based on `TerrainMap` IDs from the level's `objects.qsc`.

## File Types

| Format | Extension | Body data | Purpose |
|--------|-----------|-----------|---------|
| [THM](formats/thm.md) | `.thm` | float32 per vertex | Elevation/height data |
| [TMM](formats/tmm.md) | `.tmm` | uint8 per vertex | Material/texture assignment |
| [TLM](formats/tlm.md) | `.tlm` | RGBA per pixel | Baked lighting and shadows |

## Common Header

All three formats share a 32-byte header prefix:

| Offset | Type    | Field         | Notes                          |
|--------|---------|---------------|--------------------------------|
| 0      | float32 | terrain_scale | Always 0.01                    |
| 4      | uint32  | year          | 2002–2003                      |
| 8      | uint32  | month         | 1–12                           |
| 12     | uint32  | day           | 1–31                           |
| 16     | uint32  | hour          | 0–23                           |
| 20     | uint32  | minute        | 0–59                           |
| 24     | uint32  | second        | 0–59                           |
| 28     | uint32  | unknown       | Varies (possibly milliseconds) |

After the common header, a `type` field (uint32) differentiates the format:

| Type value | Format |
|------------|--------|
| 0          | TMM    |
| 2          | THM    |
| 3          | TLM    |

## QSC Terrain Objects

Terrain is defined in `objects.qsc` via three object types:

### Terrain (root object)

Defines global terrain properties:

```
Task_New(<id>, "Terrain", "",
    <x>, <y>, <z>,           // Position
    <world_width>,            // World width in game units
    <world_height>,           // World height in game units
    <detail>, <adaption>,     // LOD parameters
    ...
    Task_New(..., "TerrainMap", ...),
    Task_New(..., "TerrainMaterial", ...),
);
```

### TerrainMap

Defines a heightmap grid. The `ID` field maps to the filename:

```
Task_New(<id>, "TerrainMap", "<name>",
    <map_id>,                 // ID → heightmapNNN.thm/tmm/tlm
    <map_width>, <map_height>,// Grid dimensions (e.g. 128, 256)
    <x>, <y>, <z>,           // Position offset
    <world_width>,            // Covered world width
    <world_height>,           // Covered world height
    <soften_edge_size>,       // Edge blending size
    "<dem_filename>",         // Optional DEM file reference
);
```

**ID to filename mapping:** `TerrainMap` ID `0` → `heightmap000.*`, ID `2` → `heightmap002.*`

### TerrainMaterial

Defines texture layers referenced by TMM material indices:

```
Task_New(<id>, "TerrainMaterial", "<name>",
    <material_id>,            // ID matching TMM byte values (0-7)
    <game_material>,          // Physics material type
    "<texture>",              // Primary texture path
    "<detail_texture>",       // Detail texture path
    <texture_scale>,          // UV scale (typically 8)
    <detail_texture_scale>,   // Detail UV scale (typically 2)
    <mapping_style>,          // 0 = planar mapping
);
```

## Multi-Resolution Terrain

Levels can have multiple TerrainMaps at different resolutions. Example from `location1/level1`:

| TerrainMap   | ID | Dimensions | World coverage |
|--------------|----|------------|----------------|
| Low Res      | 0  | 128 × 128  | 3000 × 3000    |
| Hi Res       | 2  | 256 × 256  | 750 × 750      |

The Hi Res map covers a smaller area at higher detail, typically centered on the playable region.

## File Organization

```
missions/
  location1/
    level1/
      heightmaps/
        heightmap000.thm    # Low Res heightmap (128×128)
        heightmap000.tmm    # Low Res material map
        heightmap000.tlm    # Low Res light map
        heightmap002.thm    # Hi Res heightmap (256×256)
        heightmap002.tmm    # Hi Res material map
        heightmap002.tlm    # Hi Res light map
      objects.qsc           # Level definitions (decompiled from .qvm)
```
