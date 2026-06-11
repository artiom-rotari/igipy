[← Physics objects](physics-objects.md) · [Scripts Index](README.md) · [Back to Project README](../../../README.md)

# 7. Missions & level scene

These scripts tie everything together into playable levels: the mission roster, each mission's
descriptor, and the full per-level scene graph.

| File | Scope | Defines |
|------|-------|---------|
| `missions/igi2.qsc` | global | The mission list |
| `<loc>/<lvl>/mission.qsc` | per level | One mission descriptor (id → paths) |
| `<loc>/<lvl>/objects.qsc` | per level | The entire level scene graph (largest QVM) |

## `igi2.qsc` — the mission list

A flat list of `DefineMissionListItem(id)` registering the campaign missions:

```c
DefineMissionListItem(11);  // location1/level1
DefineMissionListItem(12);
…
DefineMissionListItem(36);  // location3/level6
```

IDs **11–17, 21–26, 31–36** = 19 single-player missions (location.level encoded in the id; see
[game_structure.md → Mission Numbering](../game_structure.md#mission-numbering)). Multiplayer maps are
listed separately.

## `mission.qsc` — mission descriptor

A single `DefineMission(…)` per level. The real location1/level1 line:

```c
DefineMission(11, "S", "N", "G", "L", "Mission 11 Name", "Mission 11 Desc", "",
  "missions/location1/level1", "missions/location1/common", "missions/location1/level1",
  "location1", "level1", "mission11.spr");
```

| Position | Field | Meaning |
|----------|-------|---------|
| 1 | mission id | matches `igi2.qsc` (`11`) |
| 2–5 | flags | four single-char flags (`"S"`/`"N"`/`"G"`/`"L"`); `"S"` marks single-player, `"M"` multiplayer — the rest are mode/variant flags whose exact meaning is *unconfirmed* |
| 6–7 | name / description | mission name and briefing (or localization keys) |
| 8 | — | empty in shipped files |
| 9–11 | path triple | level dir, location-`common` dir, level data dir |
| 12–13 | location / level | symbolic names (`"location1"`, `"level1"`) |
| 14 | sprite | briefing sprite (`mission11.spr`) |

Multiplayer descriptors use `"M"` and point into `missions/multiplayer/…`, e.g.
`DefineMission(8, "M", "U", "L", "T", "Jungle", "…", "", "missions/multiplayer/jungle", …)`.

## `objects.qsc` — the level scene graph

The biggest script per level (102–395 KB decompiled). Two phases:

1. **Schema** — a block of `Task_DeclareParameters("Type", "field", "fieldType", …)` declaring every
   object type used.
2. **Instances** — a deeply nested tree of `Task_New(id, "Type", …)` building the actual scene.

Around 43–65 distinct types appear per level (89 across all levels), including: `Terrain`, `TerrainMap`, `TerrainMaterial`, `Water`,
`Forest`, `Building`, `EditRigidObj`, `EditBoneObj`, `AIGraph`, `AISquad`, `HumanSoldier`, `HumanAI`,
`HumanPlayer`, `Door`, `Switch`, `Lift`, `SCamera`, `AlarmControl`, `AreaActivate`, `EditVariable`,
`PatrolPath`, `CutScene`, `LevelFlow`, `LevelTimer`, `DefineComputerObjective`, `GunPickup`,
`MineField`, `SoundGenerator`, plus `Container`/`ConditionalContainer`/`Dynamic` grouping nodes.

### Nesting = ownership

A child `Task_New` is a sub-component of its parent. Enemies are built squad → soldier → AI:

```c
Task_New(700, "AISquad", "Main Gates", 4, AIType_Defensive, 102, 100, -1, 30, 5, 60,
  Task_New(400, "HumanSoldier", "", -449419.15625, 2079701.125, -29049.6953125, -3.769911,
    "rsg3_1", 1,
    "//Normal Guard\nHuman_AddWeapon(\"WEAPON_ID_MAKAROV\");\n…",
    1, -1,
    Task_New(500, "HumanAI", "", "HUMANAI_TYPE_C1_NORMAL_SOLDIER", "HUMANAI_ANIMTYPE_SOLDIER_PISTOL", 1)))
```

This single nest places a defensive squad, a guard at a world position with the `rsg3_1` model, gives
him a Makarov via an **embedded weapon script** (`Human_AddWeapon(...)` — a `VarString` run at spawn),
and attaches a C1 soldier AI bound to graph 1.

### Key object types

**`AISquad`** — id, label, formation distance (m), squad type, alarm trigger/control ids, stationary
gun id (`-1` none), max-run distance, target timeout, tense timeout; children are its soldiers.

**`HumanSoldier`** — id, label, X/Y/Z, facing (rad), model stem, team, weapon script (`VarString`),
bone-hierarchy id, stand-anim id; child is its `HumanAI`.

**`HumanAI`** — id, label, archetype (`HUMANAI_TYPE_*` from [settings.qsc](ai.md#commonaisettingsqsc--archetype-tuning)),
animation set (`HUMANAI_ANIMTYPE_*`), and the graph id it patrols.

**`Door`** — position, open displacement, orientation matrix, model, max swing angle, open time,
pickable flag, locked/open/close `VarString` expressions, and open/close/loop/activate sounds.

**`Forest`** — center, tree model, area size, tree count, scale ranges, view cutoff (LOD), wind-LOD
count. The per-tree placement lives in the sibling `forest_<id>.dat`.

**`Water`** — center, size, detail, alpha, UV/env scale, texture + reflection map paths, diffuse/
specular colours.

**`EditRigidObj`** — a static prop: position, orientation, model, render group, shadow/clip flags.

**`AIGraph`** — id, origin, link/cover tuning; the navigation topology itself is the binary
`graphs/graph<id>.dat`.

### How ids link to external files

`objects.qsc` is the master index — a `Task_New` id names its associated data/script files (see
[game_structure.md → Task ID naming](../game_structure.md#task-id-file-naming-convention)):

| Task | File |
|------|------|
| `HumanAI` id 500 | `ai/500.qvm` ([per-soldier script](ai.md#per-level-ainnnqsc--one-soldier)) |
| `AISquad` id 700 | `ai/Squad_700.qvm` ([per-squad script](ai.md#per-level-aisquad_nnnqsc--one-squad)) |
| `AIGraph` id 1 | `graphs/graph1.dat` |
| `Forest` id 2540 | `forest_2540.dat` |

The full field-by-field object-type catalog is in [level.md](../level.md).

## Multiplayer differences

Multiplayer `objects.qsc` has **no AI** (`AISquad`/`HumanSoldier`/`HumanAI` absent) and instead uses
networked types: `Network_Mission`, `Network_Objective` (team-scoped goals), `SpawnArea`/`SpawnPoint`
(per-team respawns), `C4BombArea`, `Terminal`. It also pulls model LOD from a sibling
[`lod.qsc`](engine-config.md#lodqsc--model-lod-switch-distances) via a
`LocalModelLODSettingsContainer`, where single-player bakes LOD into each object.

## See Also

- [AI behavior](ai.md) — the `ai/NNN` and `Squad_NNN` scripts these tasks name.
- [Level](../level.md) — the complete `objects.qsc` object-type reference.
- [Game Structure](../game_structure.md) — mission numbering and on-disk layout.
