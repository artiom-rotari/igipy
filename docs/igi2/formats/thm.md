[Back to README](../../../README.md)

# THM Format — Terrain Height Map

THM files store terrain elevation data as a grid of float32 height values. Each file represents one terrain patch within a game level.

## Structure Overview

```
┌────────────────────────────────────┐
│ Common Header (32 bytes)           │
│   terrain_scale, timestamp, etc.   │
├────────────────────────────────────┤
│ THM Extra Fields (20 bytes)        │
│   type=2, padding, height_scale,   │
│   width, height                    │
├────────────────────────────────────┤
│ Height Data (width × height × 4)   │
│   float32 per vertex               │
├────────────────────────────────────┤
│ Mipmaps (optional)                 │
│   Progressively smaller levels     │
└────────────────────────────────────┘
```

## Header (52 bytes)

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
| 32     | uint32  | type          | Always 2                            |
| 36     | uint32  | padding       | Always 0                            |
| 40     | float32 | height_scale  | Always 1.0                          |
| 44     | uint32  | width         | Grid width (64, 128, 256, or 512)   |
| 48     | uint32  | height        | Grid height (64, 128, 256, or 512)  |

The first 32 bytes are the common terrain header shared with TMM and TLM formats.

## Body — Height Data

`width × height × 4` bytes of float32 values. Each value is a raw terrain height in fixed-point game units. To convert to meters, **divide by 4096** (the engine's 12-bit fixed-point convention; see [Terrain → Unity Export](../terrain_to_unity.md)).

> **Do not use `terrain_scale` for this.** The on-disk `terrain_scale` field (always `0.01`) is *not* the real-world conversion factor — multiplying raw heights by `0.01` yields values far off the map. The verified conversion is `÷ 4096`, corroborated by the IFF fixed-point convention ("4096 game units = 1 meter") and the map editor's `SetScale(40.96)`.

Values are stored row by row from the top-left corner of the terrain patch.

### Size Formula

```
body_size = width × height × 4
total_file_size = 52 + body_size [+ mipmap_size]
```

### Observed Dimensions

| Width × Height | Body size   | File size (no mipmaps) |
|----------------|-------------|------------------------|
| 64 × 64        | 16,384      | 16,436                 |
| 128 × 128      | 65,536      | 65,588                 |
| 256 × 256      | 262,144     | 262,196                |
| 512 × 512      | 1,048,576   | 1,048,628              |

## Mipmaps

2 of the 50 THM files in the game include a full mipmap chain after the top-level data. All levels down to 1×1 are included.

Body size for a 256×256 mipmapped map — the body holds the **full mip chain, top level first**, so the sum includes the 256² top level:

```
256² + 128² + 64² + 32² + 16² + 8² + 4² + 2² + 1² = 87,381 pixels
87,381 × 4 = 349,524 bytes (all mip levels, top level included)
```

Total file size: 52 (header) + 349,524 (all levels) = **349,576 bytes**, matching the observed size.

The loader reads only the top-level (`width × height × 4` bytes) and skips any remaining mipmap data.

## Export

### TGA (grayscale heightmap)

The THM loader normalizes float32 heights to 0–255 grayscale and exports as a 32-bit TGA image:

- **B = G = R** = normalized height (0 = lowest, 255 = highest)
- **A** = 255

```
igipy igi2 convert-thm-to-tga   # writes <name>.thm.tga
```

### JSON (raw height grid)

The THM loader can also export the raw, unnormalized heights as JSON (`<name>.thm.json`):

```
igipy igi2 convert-thm-to-json
```

```json
{
  "width": 64,
  "height": 64,
  "content": [ /* width × height float32 heights, row-major */ ]
}
```

`content` is a **flat** row-major list of all `width × height` float32 values (full precision, unnormalized). Reconstruct any cell as `content[row * width + column]`. Only the top-level grid is exported; mipmaps are skipped.
