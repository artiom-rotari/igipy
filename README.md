# igipy

> Reverse engineering tools for *Project I.G.I* and *Project I.G.I 2: Covert Strike* game files.

**igipy** is a Python CLI tool for converting proprietary game file formats from IGI 1 and IGI 2 into standard, open formats. It is a direct successor and refactor of the tool published at [https://github.com/NEWME0/Project-IGI/](https://github.com/NEWME0/Project-IGI/).

## Installation

Requires **Python 3.13**.

```bash
pip install --upgrade igipy
```

## Quick Start

1. Create a working directory and run `igipy` to generate the configuration file:

   ```bash
   igipy
   ```

2. Edit `igipy.json` — set `source_dir` to your game installation path:

   ```json
   {
     "igi1": {
       "source_dir": "C:/Games/ProjectIGI",
       "unpack_dir": "./unpack",
       "target_dir": "./target"
     }
   }
   ```

3. Convert all supported formats at once:

   ```bash
   igipy igi1 convert-all
   ```

## Key Features

- **IGI 1:** Convert `.res` archives, `.qvm` scripts, `.wav` audio (ADPCM), `.tex`/`.spr`/`.pic` textures
- **IGI 2:** ZIP-based pipeline — collect game files, then batch-convert all supported formats
- **Formats:** `.res` → `.zip`/`.json`, `.qvm` → `.qsc`, `.wav` → standard `.wav`, `.tex` → `.tga`, `.thm`/`.tmm`/`.tlm` → `.tga`, `.fnt` → BMFont, `.syn` → `.json`, `.dat` (forest/graph/graphcover) → `.json`

## Usage

### IGI 1

```bash
igipy igi1 convert-all          # Convert all supported formats
igipy igi1 convert-all-res      # .res → .zip/.json
igipy igi1 convert-all-wav      # .wav → standard .wav
igipy igi1 convert-all-qvm      # .qvm → .qsc
igipy igi1 convert-all-tex      # .tex/.spr/.pic → .tga
```

### IGI 2

```bash
igipy igi2 zip-collect           # Collect game files into a single zip
igipy igi2 zip-convert-all       # Convert all formats in the collected zip
igipy igi2 convert-all-res       # .res → .zip/.json (directory-based)
```

All commands support `--dry` flag for preview without writing files.

## Documentation

| Guide | Description |
|-------|-------------|
| [Game Structure](docs/game_structure.md) | IGI 2 directory layout, mission numbering, QSC script types |
| [File Extensions](docs/extensions.md) | Full file type inventory with conversion status |
| [QVM Format](docs/format_qvm.md) | Bytecode script format |
| [FNT Format](docs/format_fnt.md) | Bitmap font format |
| [Terrain System](docs/format_terrain.md) | THM/TMM/TLM terrain formats overview |
| [Forest DAT](docs/format_forest_dat.md) | Vegetation placement format |
| [Graph DAT](docs/format_graph_dat.md) | AI navigation graph format |
| [Graphcover DAT](docs/format_graphcover_dat.md) | AI cover/visibility format |
| [SYN Format](docs/format_syn.md) | Lip-sync envelope format |
| [IFF Format](docs/format_iff.md) | Skeletal animation format |
| [MEF Format](docs/format_mef.md) | 3D mesh model format |
| [objects.qsc](docs/format_objects_qsc.md) | Level scene graph — all 88 object type declarations |
| [Model Naming](docs/model_naming.md) | MEF model filename convention and category prefixes |

## Supported Game File Formats

Below is a summary of the file formats in *Project I.G.I*, including their locations and conversion support:

| Extension       | Total           | Source          | Unpack          | Support         |
|-----------------|-----------------|-----------------|-----------------|-----------------|
| `.olm`          | 25337           | 0               | 25337           | Not now         |
| `.tex`          | 7225            | 26              | 7199            | Yes             |
| `.mef`          | 6794            | 0               | 6794            | Not now         |
| `.qvm`          | 997             | 997             | 0               | Yes             |
| `.wav`          | 740             | 394             | 346             | Yes             |
| `.dat` (graph)  | 300             | 300             | 0               | Yes             |
| `.spr`          | 158             | 0               | 158             | Yes             |
| `.res`          | 92              | 92              | 0               | Yes             |
| `.dat` (mtp)    | 17              | 17              | 0               | Not now         |
| `.mtp`          | 17              | 17              | 0               | Not now         |
| `.fnt`          | 11              | 2               | 9               | Yes             |
| `.hmp`          | 6               | 6               | 0               | Not now         |
| `.pic`          | 5               | 0               | 5               | Yes             |

## License

MIT
