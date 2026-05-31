[Back to README](../../../README.md)

# OLM — Object Lightmap

## Overview

`.olm` files store per-object lightmap data in *Project I.G.I 2: Covert Strike*. Each file contains one or more RGBA lightmap layers associated with a specific game object. Unlike most IGI 2 formats, OLM is **not** ILFF-based — it uses a flat binary layout similar to `.tlm` (Terrain Light Map).

**Statistics (IGI 2):**

- 32,532 files total
- All located under `missions/<location>/<level>/lightmaps/`
- 32,530 single-layer files, 2 files with 3 layers
- File sizes range from 116 bytes (1x1 pixel) to 6,578,392 bytes (1024x1024 with 3 layers)

**Filename convention:** `XXXX_YYYY_Z.olm`

- `XXXX` — object/tile ID
- `YYYY` — sub-index
- `Z` — layer type indicator

## Binary Structure

### Main Header (88 bytes)

| Offset | Type | Field | Description |
|--------|------|-------|-------------|
| 0x00 | float32 | `version1` | Always `0.12` |
| 0x04 | float32 | `version2` | Always `0.16` |
| 0x08 | uint32 | `year` | Creation year (e.g. 2002, 2003) |
| 0x0C | uint32 | `month` | Creation month (1-12) |
| 0x10 | uint32 | `day` | Creation day (1-31) |
| 0x14 | uint32 | `hour` | Creation hour (0-23) |
| 0x18 | uint32 | `minute` | Creation minute (0-59) |
| 0x1C | uint32 | `second` | Creation second (0-59) |
| 0x20 | uint32 | `millisecond` | Creation millisecond (0-999) |
| 0x24 | uint32 | `unknown_0` | Always 0 |
| 0x28 | uint32 | `count1` | Unknown flag (0 or 1) |
| 0x2C | uint32 | `layer_count` | Number of lightmap layers (1 or 3) |
| 0x30 | uint32x4 | `reserved` | Always zero |
| 0x40 | uint16 | `width` | Grid/block width |
| 0x42 | uint16 | `height` | Grid/block height |
| 0x44 | uint16 | `total_stride` | Related to perimeter/edge count |
| 0x46 | uint16 | `format` | Pixel format indicator (always 3 = RGBA) |
| 0x48 | uint32 | `pad` | Always 0 |
| 0x4C | float32 | `uv_scale_u` | UV coordinate scale (U axis) |
| 0x50 | float32 | `uv_scale_v` | UV coordinate scale (V axis) |
| 0x54 | float32 | `zero` | Always 0.0 |

### Layer Descriptor (24 bytes per layer)

After the main header, each layer has a 24-byte sub-header:

| Offset | Type | Field | Description |
|--------|------|-------|-------------|
| +0x00 | uint32 | `flags` | Always `0x20000001` |
| +0x04 | uint32 | `ptr1` | Runtime pointer (not meaningful on disk) |
| +0x08 | uint32 | `ptr2` | Runtime pointer (not meaningful on disk) |
| +0x0C | uint32 | `val` | Always 21 |
| +0x10 | uint32 | `pad` | Always 0 |
| +0x14 | uint16 | `pixel_width` | Actual pixel width of this layer |
| +0x16 | uint16 | `pixel_height` | Actual pixel height of this layer |

### Extra Block (28 bytes, between layers only)

For multi-layer files, a 28-byte block appears between consecutive layer descriptors (not after the last one):

| Offset | Type | Field | Description |
|--------|------|-------|-------------|
| +0x00 | uint32 | `pad` | Always 0 |
| +0x04 | uint16 | `block_width` | Block dimensions for next level |
| +0x06 | uint16 | `block_height` | Block dimensions for next level |
| +0x08 | uint16 | `block_stride` | Stride value |
| +0x0A | uint16 | `block_format` | Format (always 3) |
| +0x0C | uint32 | `pad` | Always 0 |
| +0x10 | float32 | `block_uv_u` | UV scale U for this block |
| +0x14 | float32 | `block_uv_v` | UV scale V for this block |
| +0x18 | uint32 | `pad` | Always 0 |

### Pixel Data

After all layer descriptors, pixel data is stored sequentially for each layer. Each pixel is 4 bytes in **RGBA** order (red, green, blue, alpha). The pixel count for each layer is `pixel_width * pixel_height`.

Total pixel data size = sum of (`pixel_width * pixel_height * 4`) for all layers.

## Layout Diagram

```
Single-layer file (layer_count=1):
  [88 bytes] Main Header
  [24 bytes] Layer 0 Descriptor
  [W*H*4 bytes] Layer 0 Pixel Data (RGBA)

Multi-layer file (layer_count=3):
  [88 bytes] Main Header
  [24 bytes] Layer 0 Descriptor
  [28 bytes] Extra Block 0
  [24 bytes] Layer 1 Descriptor
  [28 bytes] Extra Block 1
  [24 bytes] Layer 2 Descriptor
  [W0*H0*4 bytes] Layer 0 Pixel Data (RGBA)
  [W1*H1*4 bytes] Layer 1 Pixel Data (RGBA)
  [W2*H2*4 bytes] Layer 2 Pixel Data (RGBA)
```

## Notes

- The `width`/`height` fields in the main header represent grid or block dimensions. The actual pixel dimensions are in the layer descriptors (`pixel_width`, `pixel_height`). For single-layer files, `pixel_width` is often slightly smaller than `width` (e.g. width=4 but pixel_width=3).
- The `version1` (0.12) and `version2` (0.16) floats are constant across all 32,532 files — likely format version identifiers.
- Multi-layer files contain lightmap cascades at decreasing resolutions (e.g. 1024x774, 768x768, 512x512).
- Pixel data uses the same RGBA byte order as `.tlm` files and must be swapped to BGRA for TGA output.
