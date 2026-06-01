[Back to README](../../../README.md)

# TEX Format (`.tex`)

Texture image format used by both IGI 1 and IGI 2. Parsed by the shared `core` TEX reader
(`core/formats/tex.py`) and converted to `.tga` (`core/services/tex_to_tga.py`). The `.spr`
([SPR](spr.md)) and `.pic` ([PIC](pic.md)) extensions are the same container under a different
name and are read by the same parser.

Every TEX file starts with the ASCII signature `LOOP` followed by a `uint32` version. The version
selects one of four layouts.

## Versions

| Version | Class    | Layout                                                                   | Seen in |
|---------|----------|--------------------------------------------------------------------------|---------|
| 2       | `TEX02`  | Single header + one bitmap                                               | IGI 1   |
| 7       | `TEX07`  | Header + per-tile headers + tile bitmaps + `TEX06` tile-grid footer      | IGI 1/2 |
| 9       | `TEX09`  | Same shape as `TEX07`, different header fields                           | IGI 2   |
| 11      | `TEX11`  | Header + a mip-level chain (base level first)                            | IGI 2   |

Many header fields are still reverse-engineered and are kept as `unknown_NN` so the file can be
written back byte-for-byte (`model_dump_stream`).

## Pixel modes

The `mode` field selects the pixel layout. It is the single source of truth in `PIXEL_MODES`
(`core/formats/tex.py`):

| `mode` | Pixel format | Bits | Bytes/pixel | numpy dtype |
|--------|--------------|------|-------------|-------------|
| 2      | ARGB1555     | 16   | 2           | `uint16`    |
| 3      | ARGB8888     | 32   | 4           | `uint32`    |
| 67     | ARGB8888     | 32   | 4           | `uint32`    |

Mode `67` is `0x43` — i.e. mode `3` with an extra `0x40` usage flag. The flag does not change the
on-disk pixel layout, so modes `3` and `67` decode identically.

## Tiles vs. mip levels

The multi-image versions store their extra images for two different reasons:

- **`TEX07` / `TEX09` store tiles.** The trailing `TEX06` footer carries a `count_x × count_y`
  grid. Each item is a full-resolution tile, and `TEX07.bitmap` reassembles them row-major into one
  image. All tiles are read at the parent header's `width`/`height`.
- **`TEX11` stores a mip chain.** Up to ten levels follow the header, each half the dimensions of
  the previous one (level *n* is `width >> n` × `height >> n`). Level 0 is the full-resolution base
  image.

## TGA conversion

`core/services/tex_to_tga.py` exposes two layers:

- `tex_to_tga_image(instance: TEX) -> TGA` — pure conversion of an already-parsed `TEX` into a
  `TGA` model (`core/formats/tga.py`). Used by callers that already hold a parsed texture (e.g. the IGI 2
  `mef_texture_resolver`, which inspects the alpha channel to classify material transparency).
- `tex_to_tga(source_io, source_path) -> (BytesIO, Path | None)` — the stream-in/stream-out wrapper
  that matches the shared `convert` pipeline contract (`core/utils/pipeline.py`). This is what the
  `convert-tex-to-tga` CLI commands use for both games.

### Fidelity — what is and isn't preserved

- **Base image: lossless.** The source pixel bytes are copied into the TGA verbatim — no
  recompression, resampling, or channel reordering. TEX's little-endian ARGB1555 / ARGB8888 byte
  order already matches what a 16-/32-bit true-color TGA expects, so the copy is byte-exact. Rows
  are emitted bottom-to-top (the TGA descriptor's bottom-to-top bit is set) to match TEX's
  orientation.
- **`TEX11` higher mip levels: dropped.** Only the base level is exported. The smaller levels are
  downscaled copies and can be regenerated on demand, so no source detail is lost.
- **Container metadata: not represented in TGA.** The `TEX06` tile-grid footer and the
  reverse-engineered `unknown_NN` header fields have no TGA equivalent. They are preserved only
  through the TEX → TEX round-trip (`model_dump_stream`), not through the TGA export.

In short, the TGA carries the full base image exactly; everything dropped is either regenerable
(mip levels) or TEX-container bookkeeping with no image content.
