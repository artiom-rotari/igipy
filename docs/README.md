# igipy Documentation

> Table of contents for all igipy documentation, grouped by scope: **core** (shared),
> **igi1** (*Project I.G.I*), and **igi2** (*Project I.G.I 2: Covert Strike*).

Shared formats live under `core/`, game-specific notes under `igi1/` and `igi2/`. Per-format
pages live in each scope's `formats/` subfolder. For project setup and CLI usage, see the
[root README](../README.md).

## Core (shared)

Formats parsed by shared `core` code and used by both games.

| Page | Description |
|------|-------------|
| [QVM Format](core/formats/qvm.md) | Compiled bytecode script format |
| [TEX Format](core/formats/tex.md) | Texture image format (stub) |
| [SPR Format](core/formats/spr.md) | Sprite texture, TEX variant (stub) |
| [PIC Format](core/formats/pic.md) | Picture texture, TEX variant (stub) |
| [WAV Format](core/formats/wav.md) | Audio format incl. ADPCM (stub) |

## IGI 1

### Overview

| Page | Description |
|------|-------------|
| [File Extensions](igi1/extensions.md) | IGI 1 file type inventory with conversion status |

IGI 1 reuses the shared `core` formats (QVM scripts, TEX/SPR/PIC textures, WAV audio). The pages
below cover IGI 1-specific types and are stubs to be filled in as they are reverse-engineered.

### Formats

| Page | Description |
|------|-------------|
| [MEF Format](igi1/formats/mef.md) | 3D mesh model format (stub) |
| [IFF Format](igi1/formats/iff.md) | Skeletal animation / ILFF container (stub) |
| [FNT Format](igi1/formats/fnt.md) | Bitmap font format (stub) |
| [DAT Graph](igi1/formats/dat_graph.md) | AI navigation graph format (stub) |
| [DAT MTP](igi1/formats/dat_mtp.md) | Material/texture properties (stub) |
| [HMP Format](igi1/formats/hmp.md) | Heightmap resource (stub) |
| [BIT Format](igi1/formats/bit.md) | `.bit` resource (stub) |
| [CMD Format](igi1/formats/cmd.md) | `.cmd` resource (stub) |
| [CTR Format](igi1/formats/ctr.md) | `.ctr` resource (stub) |
| [LMP Format](igi1/formats/lmp.md) | `.lmp` resource (stub) |

## IGI 2

### Overview

| Page | Description |
|------|-------------|
| [Game Structure](igi2/game_structure.md) | Directory layout, mission numbering, QSC script types |
| [File Extensions](igi2/extensions.md) | Full file type inventory with conversion status |
| [Model Naming](igi2/model_naming.md) | MEF model filename convention and category prefixes |
| [Terrain System](igi2/terrain.md) | THM/TMM/TLM terrain formats overview |
| [Level](igi2/level.md) | Level scene graph (objects.qsc) — object type declarations |

### Formats

| Page | Description |
|------|-------------|
| [FNT Format](igi2/formats/fnt.md) | Bitmap font format |
| [DAT Forest](igi2/formats/dat_forest.md) | Vegetation placement format |
| [DAT Graph](igi2/formats/dat_graph.md) | AI navigation graph format |
| [DAT Graphcover](igi2/formats/dat_graphcover.md) | AI cover/visibility format |
| [DAT MTP](igi2/formats/dat_mtp.md) | Material/texture properties (stub) |
| [SYN Format](igi2/formats/syn.md) | Lip-sync envelope format |
| [IFF Format](igi2/formats/iff.md) | Skeletal animation format |
| [MEF Format](igi2/formats/mef.md) | 3D mesh model format |
| [OLM Format](igi2/formats/olm.md) | Object lightmap format |
| [THM Format](igi2/formats/thm.md) | Terrain heightmap format |
| [TMM Format](igi2/formats/tmm.md) | Terrain material map format |
| [TLM Format](igi2/formats/tlm.md) | Terrain lightmap format |
