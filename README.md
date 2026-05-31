# igipy

> Reverse engineering tools for *Project I.G.I* and *Project I.G.I 2: Covert Strike* game files.

**igipy** is a Python CLI tool for converting proprietary game file formats from IGI 1 and IGI 2 into standard, open formats. It is a direct successor and refactor of the tool published at [https://github.com/NEWME0/Project-IGI/](https://github.com/NEWME0/Project-IGI/).

## Installation

Requires **Python 3.13**.

```bash
pip install --upgrade igipy
```

## Quick Start

1. Run `igipy` once to generate the configuration file:

   ```bash
   igipy
   ```

2. Edit `igipy.json` — point each game's `game_dir` at your installation. The generated file has a
   block per game (`igi1` and `igi2`). Each pipeline endpoint can be a directory
   (`*_is_zip: false`) or a single `.zip` archive (`*_is_zip: true`, path must end in `.zip`):

   ```json
   {
     "igi1": {
       "collect_is_zip": false,
       "convert_is_zip": false,
       "game_dir": "C:/Games/ProjectIGI",
       "collect_path": "igi1_collected.zip",
       "convert_path": "igi1_converted.zip"
     },
     "igi2": {
       "collect_is_zip": false,
       "convert_is_zip": false,
       "game_dir": "C:/Games/ProjectIGI2",
       "collect_path": "igi2_collected.zip",
       "convert_path": "igi2_converted.zip"
     }
   }
   ```

3. Collect the game files, then convert them — use the `igi1` or `igi2` command group for the game
   you want:

   ```bash
   igipy igi1 collect              # gather IGI 1 files into collect_path
   igipy igi1 convert-tex-to-tga   # run an IGI 1 converter into convert_path

   igipy igi2 collect              # gather IGI 2 files into collect_path
   igipy igi2 convert-all          # convert everything into convert_path
   ```

## Commands

The workflow is two-stage: **`collect`** gathers raw game files from `game_dir` into the collect
endpoint (copying loose files and unpacking `.res` archives), then the **`convert-*`** commands read
from the collect endpoint and write converted assets to the convert endpoint. Both endpoints are a
directory or a `.zip` depending on `collect_is_zip` / `convert_is_zip`. Every `convert-*` command
accepts `--dry` to preview without writing.

### `igipy igi1 …`

| Command | Description |
|---------|-------------|
| `collect` | Gather IGI 1 game files into the collect endpoint (loose files + unpacked `.res`, language `.res` → JSON). |
| `convert-qvm-to-qsc` | Decompile `.qvm` bytecode to `.qsc` script source. |
| `convert-tex-to-tga` | Convert `.tex` / `.spr` / `.pic` textures to `.tga`. |
| `convert-wav-to-wav` | Decode ADPCM `.wav` audio to standard PCM `.wav`. |
| `res-to-zip <file.res>` | Convert a single `.res` file to `.zip` (binary) or `.json` (strings). |
| `extensions-of-game` | Print a file-type count table for the game install directory. |
| `extensions-of-collect` | Print a file-type count table for the collect endpoint. |
| `extensions-of-convert` | Print a file-type count table for the convert endpoint. |

### `igipy igi2 …`

| Command | Description |
|---------|-------------|
| `collect` | Gather IGI 2 game files into the collect endpoint (loose files + unpacked `.res`, language `.res` → JSON). |
| `convert-all` | Run every IGI 2 converter below in sequence. |
| `convert-raw` | Copy raw assets (`.mp3`, `.bmp`, `.jpg`, `.tga`, `.json`) through unchanged. |
| `convert-qvm-to-qsc` | Decompile `.qvm` → `.qsc`. |
| `convert-wav-to-wav` | Decode ADPCM `.wav` → standard `.wav`. |
| `convert-tex-to-tga` | `.tex` / `.spr` / `.pic` → `.tga`. |
| `convert-fnt-to-zip` | `.fnt` bitmap font → BMFont (`.fnt` + `.tga`) zip. |
| `convert-thm-to-tga` | `.thm` terrain heightmaps → grayscale `.tga`. |
| `convert-tmm-to-tga` | `.tmm` terrain material maps → palette `.tga`. |
| `convert-tlm-to-tga` | `.tlm` terrain lightmaps → `.tga`. |
| `convert-olm-to-tga` | `.olm` object lightmaps → `.tga`. |
| `convert-syn-to-json` | `.syn` lip-sync envelopes → `.json`. |
| `convert-dat-forest-to-json` | `forest_*.dat` vegetation placement → `.json`. |
| `convert-dat-graph-to-json` | `graph*.dat` AI navigation graphs → `.json`. |
| `convert-dat-graphcover-to-json` | `graphcover*.dat` AI cover/visibility data → `.json`. |
| `convert-iff-to-fbx` | `.iff` skeletal animation → FBX. |
| `convert-iff-to-qsc` | `.iff` skeletal animation → `.bef` text source. |
| `convert-mef-to-fbx` | `.mef` 3D model → FBX. |
| `convert-mef-to-qsc` | `.mef` 3D model → text source. |
| `res-to-zip <file.res>` | Convert a single `.res` file to `.zip` / `.json`. |
| `extensions-of-game` | Print a file-type count table for the game install directory. |
| `extensions-of-collect` | Print a file-type count table for the collect endpoint. |
| `extensions-of-convert` | Print a file-type count table for the convert endpoint. |

### `igipy core …`

| Command | Description |
|---------|-------------|
| `count-extensions <path>` | Count files by extension in a directory or `.zip`. |
| `copy-files <src> <dst>` | Copy filtered game files between directories (skips `.res` / `.mtp` and `.dat` paired with `.mtp`). |
| `printable <file>` | Print printable ASCII strings found in a binary file. |
| `gconv [args…]` | Run the bundled `gconv.exe`. |

## Documentation

Full documentation is split by scope — shared **core** formats, **igi1**, and **igi2**. See the
documentation table of contents:

- **[docs/README.md](docs/README.md)** — index of all format references, game structure notes,
  and per-game file extension inventories.

## License

MIT
