[Back to README](../README.md)

# TMM Format — Terrain Material Map

TMM files store per-vertex material assignments for terrain patches. Each byte maps a grid cell to one of up to 8 `TerrainMaterial` definitions in the level's `objects.qsc`.

## Structure Overview

```
┌────────────────────────────────────┐
│ Common Header (32 bytes)           │
│   terrain_scale, timestamp, etc.   │
├────────────────────────────────────┤
│ TMM Extra Fields (12 bytes)        │
│   type=0, width, height            │
├────────────────────────────────────┤
│ Material Data (width × height)     │
│   uint8 per vertex (0–7)           │
└────────────────────────────────────┘
```

## Header (44 bytes)

All fields are little-endian.

| Offset | Type    | Field         | Description                         |
|--------|---------|---------------|-------------------------------------|
| 0      | float32 | terrain_scale | Always 0.01                         |
| 4      | uint32  | year          | Creation year (2002–2003)           |
| 8      | uint32  | month         | Creation month (1–12)               |
| 12     | uint32  | day           | Creation day (1–31)                 |
| 16     | uint32  | hour          | Creation hour (0–23)                |
| 20     | uint32  | minute        | Creation minute (0–59)              |
| 24     | uint32  | second        | Creation second (0–59)              |
| 28     | uint32  | unknown       | Varies (possibly milliseconds)      |
| 32     | uint32  | type          | Always 0                            |
| 36     | uint32  | width         | Grid width (64, 128, 256, or 512)   |
| 40     | uint32  | height        | Grid height (64, 128, 256, or 512)  |

The first 32 bytes are the common terrain header shared with THM and TLM formats.

## Body — Material Indices

`width × height` bytes. Each byte is a material index (0–7) referencing a `TerrainMaterial` object defined in the level's `objects.qsc`.

### Size Formula

```
body_size = width × height
total_file_size = 44 + body_size
```

### Observed Dimensions

| Width × Height | Body size   | File size |
|----------------|-------------|-----------|
| 64 × 64        | 4,096       | 4,140     |
| 128 × 128      | 16,384      | 16,428    |
| 256 × 256      | 65,536      | 65,580    |
| 512 × 512      | 262,144     | 262,188   |

## Material Semantics

Each byte value maps to a `TerrainMaterial` definition in `objects.qsc`. Example from `missions/location1/level1/objects.qsc`:

| Index | Material name        | Texture                                |
|-------|----------------------|----------------------------------------|
| 0     | Grass                | `MISSION:textures/k_grass.jpg`         |
| 1     | Dirt                 | `MISSION:textures/dirtgrey.jpg`        |
| 2     | Rock                 | `MISSION:textures/k_rock.jpg`          |
| 3     | Muddy Road           | `MISSION:textures/muddyroad.jpg`       |
| 4     | Snow                 | `MISSION:textures/k_snow.jpg`          |
| 5     | Snowy Rocks          | `MISSION:textures/k_snowrocks.jpg`     |
| 6     | Distant snowy rocks  | `MISSION:textures/k_snow02.jpg`        |

Each `TerrainMaterial` also defines:
- **Detail texture** — a secondary texture for close-up detail
- **Texture scale** — UV scaling factor (typically 8)
- **Detail texture scale** — scaling for the detail layer (typically 2)
- **Mapping style** — texture mapping mode (0 = planar)

## Export

The TMM loader maps material indices to a fixed color palette and exports as a 32-bit TGA image:

| Index | Color   | Typical material |
|-------|---------|------------------|
| 0     | Green   | Grass            |
| 1     | Brown   | Dirt             |
| 2     | Gray    | Rock             |
| 3     | Tan     | Sand             |
| 4     | White   | Snow             |
| 5     | Dark gray | Stone          |
| 6     | Forest green | Vegetation  |
| 7     | Sienna  | Mud              |

## See Also

- [THM Format](format_thm.md) — terrain height map documentation
- [TLM Format](format_tlm.md) — terrain light map documentation
- [Terrain System](format_terrain.md) — how THM/TMM/TLM work together
- [File extensions overview](extensions.md) — full list of game file formats
