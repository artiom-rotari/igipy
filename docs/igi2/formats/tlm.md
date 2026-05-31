[Back to README](../../../README.md)

# TLM Format — Terrain Light Map

TLM files store baked lighting and shadow information for terrain patches as RGBA pixel data.

## Structure Overview

```
┌────────────────────────────────────┐
│ Common Header (32 bytes)           │
│   terrain_scale, timestamp, etc.   │
├────────────────────────────────────┤
│ TLM Extra Fields (12 bytes)        │
│   type=3, width, height            │
├────────────────────────────────────┤
│ Light Data (width × height × 4)    │
│   RGBA per pixel                   │
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
| 32     | uint32  | type          | Always 3                            |
| 36     | uint32  | width         | Grid width (128, 256, or 512)       |
| 40     | uint32  | height        | Grid height (128, 256, or 512)      |

The first 32 bytes are the common terrain header shared with THM and TMM formats.

## Body — Light Data

`width × height × 4` bytes of RGBA pixel data:

| Channel | Description                       |
|---------|-----------------------------------|
| R       | Red component of baked lighting   |
| G       | Green component of baked lighting |
| B       | Blue component of baked lighting  |
| A       | Alpha (always 255)                |

Colors are earthy tones matching the terrain appearance — the lightmap captures the combined effect of sun direction, ambient occlusion, and terrain color.

### Size Formula

```
body_size = width × height × 4
total_file_size = 44 + body_size
```

### Observed Dimensions

| Width × Height | Body size   | File size   |
|----------------|-------------|-------------|
| 128 × 128      | 65,536      | 65,580      |
| 256 × 256      | 262,144     | 262,188     |
| 512 × 512      | 1,048,576   | 1,048,620   |

## Export

The TLM loader converts RGBA byte order to BGRA (TGA native order) and exports as a 32-bit TGA image.
