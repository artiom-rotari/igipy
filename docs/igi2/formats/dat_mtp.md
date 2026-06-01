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

The exporter reads the **`.dat`** rather than the binary `.mtp` `INST` chunk. Both hold the same
per-model texture lists, but the `.mtp` `INST` packing is a flat record stream
(`[model_index, texture_count, texture_index × count]` indexing the `TEXF` name table) that is
error-prone to walk — a single misread record desynchronises the rest. The `.dat` is line-oriented
text and trivially parsed.

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
| `INST`                         | per-model records `[model_index, texture_count, texture_index × count]` (→ `TEXF`) |
| `GTT `                         | texture-table descriptor — `(index, -1)` pairs parallel to `TEXF` (not a map)      |
| `VNAM`                         | variant-name string table with offsets                                             |
| `BANM`, `SNDS`, `SVOL`, `PALF` | name/sound/palette tables (not used for texture export)                            |

`INST` is the binary equivalent of the `.dat` table; `GTT ` and `material_flags` are **not** needed
for diffuse texturing.

## Used by

- `igi2/services/mef_texture_resolver.py` — parses the `.dat`, resolves each render group's texture.
- `igi2/services/mef_to_fbx.py` (`convert-mef-to-fbx`) — exports textured FBX using the resolver.
