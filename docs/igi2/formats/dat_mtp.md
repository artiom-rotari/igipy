[Back to README](../../../README.md)

# Material / Texture Table (`.mtp` + `.dat`)

> **Status:** Decoded — the model→texture mapping consumed by the textured MEF→FBX exporter.

IGI 2 stores a **level-scoped material/texture table** that records which textures each model uses.
It exists in two equivalent forms that sit side by side in every level / location / `common`
directory:

| File          | Form   | Role                                                                   |
|---------------|--------|------------------------------------------------------------------------|
| `<level>.mtp` | binary | FORM container (parsed by `igi2/formats/mtp.py`)                       |
| `<level>.dat` | text   | machine-generated dump of the same model→texture table (easy to parse) |

The MEF binary itself does **not** store texture filenames (see [mef.md](mef.md) → DNER). The table
is what binds a model's render groups to textures, so it is the key input for textured model export.

## Why the `.dat` is the practical source

The **textured MEF→FBX exporter** reads the **`.dat`** rather than the binary `.mtp` `INST` chunk.
Both hold the same per-model texture lists; the `.dat` is line-oriented text and trivially parsed,
so it stays the canonical input for `mef_texture_resolver.py`.

The binary `INST` chunk is nonetheless **fully decoded** by `igi2/formats/mtp.py` (see
[Binary `.mtp` chunks](#binary-mtp-chunks-igi2formatsmtppy) below) and is the source for the
`convert-mtp-to-json` export. The two tables are equivalent for 99 % of models — see
[INST ↔ `.dat` equivalence](#inst--dat-equivalence).

## `.dat` format

```
*** This file is machine generated
*** DO NOT EDIT!

398                       <- model count
comms                     <- model name
1                         <- texture count
100_04_1_argb8888         <- texture name × count
helmet
5
102_01_1_argb8888
desk2
101_01_1_argb8888
glass_argb8888
ref1
...
```

After the comment header and a blank line: a model count, then for each model a `name`, a
`texture_count`, and that many `texture_name` lines (textures in material order). A count of `0`
(e.g. `none`, `killbox`) means the model has no textures.

Texture names may carry a pixel-format suffix (`_argb8888` / `_argb1555` / `_argb4444`). The texture
file on disk keeps whatever stem the table uses — `glass_argb8888.tex` but `407_12_1.tex` — and lives
in `<level>/textures/` or the shared `common/textures/`.

## Model → render-group → texture mapping

Each MEF render group carries a `group_index` (see [mef.md](mef.md) → DNER) that indexes its model's
texture list in the table:

```
texture_name = table[model_name][ render_group.group_index ]
```

**Validation:** `group_index` is a valid index into the `.dat` list for **7485 / 7497 models (99 %)**,
and the resolved textures match the reverse-engineered text `.MEF` sources (`DiffuseTMap`, in material
order). The remaining ~1 % (plus models absent from the table or with a missing `.tex`) export
untextured. The table is **level-specific**, so the same model can use different textures in different
levels (e.g. winter-map variants).

## Binary `.mtp` chunks (`igi2/formats/mtp.py`)

The `.mtp` is a FORM container with these chunks:

| Chunk                          | Content                                                                            |
|--------------------------------|------------------------------------------------------------------------------------|
| `MODS`                         | model-name string table (the table's model order)                                  |
| `TEXF`                         | texture-name string table                                                          |
| `INST`                         | per-model records `[model_index, texture_count, texture_index x count]` (→ `TEXF`) |
| `GTT `                         | texture-table descriptor — `(index, -1)` pairs parallel to `TEXF` (not a map)      |
| `VNAM`                         | variant-name string table with offsets                                             |
| `BANM`, `SNDS`, `SVOL`, `PALF` | name/sound/palette tables (not used for texture export)                            |

`INST` is the binary equivalent of the `.dat` table; `GTT ` and `material_flags` are **not** needed
for diffuse texturing.

### `INST` record layout

`INST` is a flat little-endian record stream, one record per model in `MODS` order, consuming the
chunk exactly:

```
Offset  Size  Type          Field
0       4     uint32        model_index          -> MODS.names[model_index]
4       4     uint32        texture_count
8       4×N   uint32[N]     texture_indices      -> TEXF.names[i] (N = texture_count, material order)
```

`MTP.model_texture_table()` joins these against `MODS`/`TEXF` and returns
`{model_name: [texture_name, ...]}`. Texture names are returned **as stored** — a few carry a
trailing-space padding (e.g. `412_06_1_argb8888 `) that the text `.dat` strips.

### INST ↔ `.dat` equivalence

The binary `INST` table and the text `.dat` table were compared across all 32 IGI 2 `.mtp`/`.dat`
pairs (7,528 model entries):

| Result                          | Models | Share  |
|---------------------------------|--------|--------|
| Identical                       | 7,415  | 98.5 % |
| Trailing-whitespace difference  | 41     | 0.5 %  |
| **Equivalent (above combined)** | 7,456  | 99.0 % |
| Real difference (variant skin)  | 72     | 1.0 %  |

The 72 real differences are **variant skins** — the binary and text tables captured different
variant snapshots of the same model (e.g. `jones_2` → `[jones_jungle, jones-jungleface]` in `INST`
vs `[jones_blue, jones_1]` in `.dat`; `resg_*` → winter vs default; `005_01_1` arms variant). The
`.mtp` `VNAM` chunk enumerates these variants. This is a genuine data difference, not a parser
artifact, and does not affect FBX export (which resolves through the `.dat`).

## JSON export (`convert-mtp-to-json`)

`igi2 convert-mtp-to-json` parses every `.mtp` in the collect source and writes a `.json` sibling in
the convert destination (also part of `convert-all`). The output is a purpose-shaped document built
from the decoded chunks — not a raw model dump:

```json
{
  "model_count": 271,
  "texture_count": 214,
  "variants": ["good_sc_1", "good_sc_2", "..."],
  "model_textures": {
    "good_sc_1": ["ch_gsci_01", "ch_gsci_00", "ch_gci_03_argb8888", "bci_02_argb8888"],
    "...": ["..."]
  }
}
```

`model_textures` is `MTP.model_texture_table()` (the `INST`/`MODS`/`TEXF` join); `variants` is the
`VNAM` table. Texture names are kept exactly as stored, so the JSON is a faithful reference for the
binary table.

## Used by

- `igi2/services/mtp_to_json.py` (`convert-mtp-to-json`) — exports the binary `.mtp` table to JSON.
- `igi2/services/mef_texture_resolver.py` — parses the `.dat`, resolves each render group's texture.
- `igi2/services/mef_to_fbx.py` (`convert-mef-to-fbx`) — exports textured FBX using the resolver.
