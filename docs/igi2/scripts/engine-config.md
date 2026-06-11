[Scripts Index](README.md) · [Back to Project README](../../../README.md) · [Player & combat →](player-combat.md)

# 1. Engine & global configuration

Loose `.qsc` files at the game root that configure the engine and register special objects. They are
read once at startup. Argument meanings marked *(inferred)* are deduced from values, not an explicit
schema.

| File | Defines |
|------|---------|
| `config.qsc` | Player settings: input bindings, video, audio, language, difficulty, mission stats |
| `lod.qsc` | Per-model level-of-detail switch distances |
| `magicobjconfig.qsc` | The "magic object" registry — maps models to special gameplay task types |
| `editormagicobjconfig.qsc` | Editor-only stub (empty container) |

---

## `config.qsc` — settings & key bindings

A flat list of `GO*` and `GfxOptions_*` setter calls (no `Task_New`). This is the file the options
menu writes back to. Distinct calls:

| Call | Meaning |
|------|---------|
| `GOVersion(n)` | Config format version |
| `GOPlayer("David Jones")` | Active player profile name |
| `GOActiveMission(slot, state)` | Mission unlock state per slot *(inferred: 0 locked / 2 unlocked)* |
| `GOInRemap(action, device, key)` | Bind an input action to a device + key |
| `GOInMouSens(0.082…)` | Mouse sensitivity |
| `GOInMouInv(1)` | Invert mouse (1 = inverted) |
| `GOGfxDisp(1920, 1080, 32)` | Resolution width, height, colour depth |
| `GOGfxDevice("nvldumd.dll")` | Direct3D driver DLL |
| `GOGfxGamma(n)` | Gamma level |
| `GoGfxCrossHairColour(r, g, b)` | Crosshair RGB (0–1) |
| `GfxOptions_SetDetailLevelFromConfigFile(GFXOPTIONS_DETAIL_HIGH)` | Object detail preset |
| `GfxOptions_ConfigSetAntialiasingMode(GFXOPTIONS_ANTIALIASING_X6)` | MSAA level |
| `GfxOptions_SetWaterQualityLevel(WATERRENDER_QUALITY_HIGH)` | Water shader quality |
| `GOSoundMusic(1, 0.8)` | Music on/off + volume |
| `GOGameDiff(GD_2)` | Difficulty (`GD_0`…`GD_3`) |
| `GOGameLang(ENGLISH)` | Language |
| `GOPlayerMissionStats(11, 1, …)` | Per-mission saved scores/thresholds |

**Input binding example** — `W` walks forward:

```c
GOInRemap(MoveForwards, INPUTPORT_DEVICE_KEYBOARD, KEY_W);
GOInMouSens(0.08208999782800674);
```

Constants: `INPUTPORT_DEVICE_KEYBOARD` / `_MOUSE`, the `KEY_*` set, `MOUSE_BUTTON_*`,
`GFXOPTIONS_*`, `WATERRENDER_QUALITY_*`, `GD_0`–`GD_3`, `ENGLISH` (+ other languages).

---

## `lod.qsc` — model LOD switch distances

One `Task_New("ModelLODSettings", …)` per model, declared by a single schema header:

```c
Task_DeclareParameters("ModelLODSettings", "Model", "String16",
  "Distance to LOD 2", "Real32", "Distance to LOD 3", "Real32",
  "Distance to LOD 4", "Real32", "Distance to LOD 5", "Real32",
  "Distance to cutoff", "Real32");
```

| Position | Field | Meaning |
|----------|-------|---------|
| 1 | task id | `-1` = auto-assign |
| 2 | type | `"ModelLODSettings"` |
| 3 | label | human-readable name |
| 4 | model | model file stem |
| 5–8 | LOD2/3/4/5 distance | distance (world units) at which the model drops to that lower-detail mesh |
| 9 | cutoff | distance beyond which the model is not drawn |

Example — the AK-47 world model switches detail close up, vanishes at 100 units:

```c
Task_New(-1, "ModelLODSettings", "107_01_1 ak47", "107_01_1", 4, 12, 20, 40, 100);
```

A large structure stays full-detail far out and is visible to 520 units:

```c
Task_New(-1, "ModelLODSettings", "230_03_1 - fucking safe", "230_03_1", 120, 320, 520, 520, 520);
```

Small props get short distances (a grenade pin), large/architectural models get long ones. A
near-identical `lod.qsc` also lives in each multiplayer map directory.

---

## `magicobjconfig.qsc` — special-object registry

Maps a model to a **task type** that gives it special behaviour (breakable, climbable, mountable,
etc.). Everything sits inside one `MagicObjConfigContainer`. The base record:

```c
Task_New(-1, "MagicObjConfig", "<name>", "<model>", "<taskTypeId>", TASKTYPE_*)
```

Positions: id (`-1`), type, object name, model stem, a task-type id string (often the model stem or
`none`), and the `TASKTYPE_*` enum that drives behaviour.

Some types carry extra tuning via nested `TagItemInt32` / `TagItemReal32` children. A car door with
its rotation tuning:

```c
Task_New(-1, "MagicObjConfig", "610_02_1", "610_02_1", "610_02_1", TASKTYPE_CARDOOR,
    Task_New(-1, "TagItemInt32",  "CARDOOR - Rotation axis",          "CARDOOR - Rotation axis", 0),
    Task_New(-1, "TagItemReal32", "CARDOOR - Rotation speed (deg/sec)","CARDOOR - Rotation speed (deg/sec)", 30),
    Task_New(-1, "TagItemReal32", "CARDOOR - Max angle",              "CARDOOR - Max angle", -118)),
```

A destructible hit-zone with a damage threshold:

```c
Task_New(-1, "MagicObjConfig", "709_02_1", "709_02_1", "709_02_1", TASKTYPE_HITZONE,
    Task_New(-1, "TagItemReal32", "HITZONE - Max damage", "HITZONE - Max damage", 5),
    Task_New(-1, "TagItemReal32", "HITZONE - Smoke damage level", "HITZONE - Smoke damage level", 0)),
```

Task types seen: `TASKTYPE_SHADOWVOLUME`, `TASKTYPE_GLASS`, `TASKTYPE_LADDER`,
`TASKTYPE_AISTATIONARYGUN`, `TASKTYPE_WHEEL`, `TASKTYPE_DEATHZONE`, `TASKTYPE_CARDOOR`,
`TASKTYPE_HITZONE`, `TASKTYPE_ROTOR`, `TASKTYPE_GRENADEPIN`, `TASKTYPE_RPGROCKET`,
`TASKTYPE_WEAPONMAGICOBJ`, `TASKTYPE_PRIMARYMAGICOBJ`, `TASKTYPE_BOMBBACKPACK`, `TASKTYPE_DRAWER`.

---

## `editormagicobjconfig.qsc` — editor stub

Two lines. Declares an empty `MagicObjConfigContainer` used by the level editor; defines no objects.

```c
Task_DeclareParameters("MagicObjConfigContainer");
Task_New(-1, "MagicObjConfigContainer", "editormagicobjconfig.qsc");
```

## See Also

- [Physics objects](physics-objects.md) — the `TASKTYPE_*` rigid bodies that magic objects often pair with.
- [Missions & level scene](missions.md) — where placed instances of these models live.
- [QVM Scripts overview](../formats/qvm.md) — all categories at a glance.
