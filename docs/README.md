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
| [TEX Format](core/formats/tex.md) | Texture image format, converted to TGA |
| [SPR Format](core/formats/spr.md) | Sprite texture, TEX variant |
| [PIC Format](core/formats/pic.md) | Picture texture, TEX variant |
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
| [IFF Format](igi1/formats/iff.md) | Skeletal animation / EA IFF-85 (FORM) container |
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
| [Terrain → Unity Export](igi2/terrain_to_unity.md) | Merge `.thm` heightmaps into a Unity Terrain (temporary tooling) |
| [Level](igi2/level.md) | Level scene graph (objects.qsc) — object type declarations |

### Formats

| Page | Description |
|------|-------------|
| [QVM Scripts](igi2/formats/qvm.md) | QVM/QSC script file categories and contents |
| [FNT Format](igi2/formats/fnt.md) | Bitmap font format |
| [DAT Forest](igi2/formats/dat_forest.md) | Vegetation placement format |
| [DAT Graph](igi2/formats/dat_graph.md) | AI navigation graph format |
| [DAT Graphcover](igi2/formats/dat_graphcover.md) | AI cover/visibility format |
| [DAT MTP](igi2/formats/dat_mtp.md) | Model→texture table (`.mtp` FORM container + `.dat` text dump) |
| [SYN Format](igi2/formats/syn.md) | Lip-sync envelope format |
| [IFF Format](igi2/formats/iff.md) | Skeletal animation format |
| [MEF Format](igi2/formats/mef.md) | 3D mesh model format |
| [OLM Format](igi2/formats/olm.md) | Object lightmap format |
| [THM Format](igi2/formats/thm.md) | Terrain heightmap format |
| [TMM Format](igi2/formats/tmm.md) | Terrain material map format |
| [TLM Format](igi2/formats/tlm.md) | Terrain lightmap format |

### Script Reference

Deep dives into each QSC script category (decompiled QVM), with real decoded examples.

| Page | Description |
|------|-------------|
| [Scripts Index](igi2/scripts/README.md) | Overview of all script categories |
| [Engine & Config](igi2/scripts/engine-config.md) | `config`, `lod`, `magicobjconfig` |
| [Player & Combat](igi2/scripts/player-combat.md) | Weapons, ammo, animation triggers, materials |
| [AI Behavior](igi2/scripts/ai.md) | Soldier/squad event handlers and tuning |
| [Sound Definitions](igi2/scripts/sounds.md) | Spatial sound groups and entries |
| [Menu UI](igi2/scripts/menu.md) | Main and in-game menu layouts |
| [Physics Objects](igi2/scripts/physics-objects.md) | Vehicle/projectile rigid-body configs |
| [Missions & Level Scene](igi2/scripts/missions.md) | Mission list, descriptors, `objects.qsc` |

### Research

In-depth reverse-engineering notes (background analysis, not a format spec).

| Page | Description |
|------|-------------|
| [GPU Shaders (Direct3D 8)](igi2/research/shaders.md) | Recovered vertex shaders: terrain triplanar blend, water Fresnel, RenderMode registry |
