[Back to README](../../../README.md)

# QVM Scripts (IGI 2) — File Categories

> **Status:** Decoded — all 1,786 IGI 2 `.qvm` files decompile to readable `.qsc` source via
> `igi2 convert-qvm-to-qsc`.

Every `.qvm` in IGI 2 is compiled bytecode for the engine's scripting VM. This page does **not**
describe the binary container or opcode set — that lives in [core/formats/qvm.md](../../core/formats/qvm.md).
Here we catalog the **categories** of QVM/QSC files shipped in the IGI 2 game tree and describe what
each category actually defines, with the function and `Task_New` patterns you will see inside.

QSC is a C-like language: tab-indented, semicolon-terminated, with `if/else`/`while` control flow.
Two idioms dominate every file:

- **`Task_DeclareParameters("Type", "field", "fieldType", ...)`** — declares the schema of an object type.
- **`Task_New(id, "Type", ...)`** — instantiates one object of that type with positional arguments;
  calls nest to form a tree (e.g. a squad containing soldiers containing AI).

For the on-disk directory layout (which `.res` archives, MTP/DAT pairing, `.qsc` decompile pipeline),
see [game_structure.md](../game_structure.md). For the level scene graph specifically, see
[level.md](../level.md). For a **deep, per-category walkthrough** with real decoded examples and
argument-by-argument signatures, see the [Script Reference](../scripts/README.md) — each category
below links to its detailed page.

## Categories at a glance

| Category | Where | Files | What it defines |
|----------|-------|-------|-----------------|
| [Engine & global config](#1-engine--global-configuration) | game root | `config`, `lod`, `magicobjconfig`, `editormagicobjconfig` | Settings, draw-distance tiers, special-object/prop registry |
| [Player & combat](#2-player--combat-definitions) | `humanplayer/`, `weapons/`, `animtrigger/`, `material/` | `humanplayer`, `weapon`, `ammo`, `animtrigger`, `material` | Player physics, weapons, ammo, animation→sound triggers, surface physics |
| [AI behavior](#3-ai-behavior) | `common/ai/`, per-level `ai/` | `default`, `settings`, `squaddefault`, `NNN`, `Squad_NNN` | Soldier/squad event handlers, AI tuning, per-NPC and per-squad scripts |
| [Sound definitions](#4-sound-definitions) | `common/sounds/`, per-level `sounds/` | `sounds` | Spatial sound groups (alarms, bullets, ambience, voice, music) |
| [Menu UI](#5-menu-ui) | `menusystem/` | `mainmenu`, `ingamemenu` | Front-end and pause-menu screen layouts and handlers |
| [Physics objects](#6-physics-objects) | `physicsobj/` | `physicsobj` + per-vehicle | Mass/drag/collision for cars, helis, missiles, planes, trains |
| [Missions & level scene](#7-missions--level-scene) | `missions/` | `igi2`, `mission`, `objects` | Mission list, mission descriptor, full level scene graph |

The single largest, most important QVMs are the per-level `objects.qvm` files (102–395 KB
decompiled); everything else is small (most files are a few hundred bytes to tens of KB).

## 1. Engine & global configuration

Loose `.qvm` files at the game root that configure the engine itself.

| File | Contents | Representative calls |
|------|----------|----------------------|
| `config.qsc` | Player settings: key/mouse bindings, video (resolution, AA, detail), audio, language, difficulty | `GOInRemap()`, `GOGfxDisp()`, `GOSoundMusic()`, `GfxOptions_SetDetailLevelFromScript()` |
| `lod.qsc` | Per-model level-of-detail draw distances — LOD2/3/4/5 thresholds plus a max cull distance for every model in the game | `Task_New(-1, "ModelLODSettings", "model", d2, d3, d4, d5, maxDist)` |
| `magicobjconfig.qsc` | Registry of "magic" / special objects — maps models to gameplay task types: shadow volumes, glass, ladders, gun stations, rotors, car doors, drawers, grenades, explosives | `Task_New(..., TASKTYPE_GLASS \| TASKTYPE_LADDER \| TASKTYPE_SHADOWVOLUME \| ...)` |
| `editormagicobjconfig.qsc` | Editor-only stub — declares an empty `MagicObjConfigContainer` for level-editor tooling | `MagicObjConfigContainer` |

A near-identical `lod.qsc` also appears inside each multiplayer map directory (multiplayer levels
carry their own LOD table).

## 2. Player & combat definitions

Global definitions for the player character and all combat-related tunables.

| File | Location | Contents | Representative calls |
|------|----------|----------|----------------------|
| `humanplayer.qsc` | `humanplayer/` | Player movement physics, per-stance modifiers (stand/run/walk/crouch/lie), jump/throw velocity, peek mechanics, per-body-part damage multipliers, weapon cycle order, ammo caps | `Task_DeclareParameters()`, `DefineHumanPlayerWeaponCycle()`, `DefineHumanPlayerAmmoLimit()` |
| `weapon.qsc` | `weapons/` | 44 weapon types — 33 guns (rifles, pistols, shotguns) plus grenades, C4, mines, knife, medipack, laser designator (see [player-combat.md](../scripts/player-combat.md)). Each: fire modes, ammo type, clip size, ROF, per-stance accuracy, reload time, muzzle velocity, animations, sounds, secondary fire | `Task_New(... "WeaponType" ...)` with nested `Gun` / `Zoom` / `Knife` / `C4Bomb` / `ProximityMine` / `LaserDesignator` blocks |
| `ammo.qsc` | `weapons/` | Ammo types — casing model, tracer color (RGB), accuracy flag, shop price/amount | `Task_New(... "AmmoType", "AMMO_ID_*", "model", useTracer, scored, R, G, B, cost, shopAmount)` |
| `animtrigger.qsc` | `animtrigger/` | Maps animation frames to sound/logic events: weapon reloads, melee hits, footstep surfaces, body sounds | `DefineAnimTrigger(id, TASKTYPE, "sound_id", looping)` |
| `material.qsc` | `material/` | 33 game materials (IDs 0–32: Air, Ground, Water, Wood, Metal variants, Flesh, Glass, Concrete, Rubber, Snow, … — full list in [player-combat.md](../scripts/player-combat.md)). Each: density, friction, footstep/bullet-impact sounds, shell effects, decal textures | `DefineGameMaterial("Name", density, friction, [sounds], [decals], [effects])`, `DefineQMaterial()`, `SetActiveMaterial()` |

## 3. AI behavior

The largest population of QVM files by count. Split into shared defaults under `common/ai/` and
thousands of tiny per-entity scripts under each level's `ai/` folder. Per-level AI scripts are named
by the `Task_New` ID of the `HumanAI` / `AISquad` they belong to in that level's `objects.qsc`
(see [game_structure.md → Task ID naming](../game_structure.md#task-id-file-naming-convention)).

### Shared defaults — `common/ai/`

| File | Contents | Representative calls |
|------|----------|----------------------|
| `default.qsc` | Default single-soldier event handler — sets an event-priority ladder on `AIEVENT_CREATE`, then dispatches IDLE / FLASHBANG / GRENADETHROWN / ENEMYDETECTION / TAKINGDAMAGE to action handlers | `AIFunction_GetCurrentEventType()`, `AIAction_CombatIdle()`, `AIFunction_SetEventPriority()`, `AIFunction_PassEventOnToSquad()` |
| `settings.qsc` | AI archetype tuning — defines soldier types (e.g. `HUMANAI_TYPE_C1_NORMAL_SOLDIER`, tough soldier) with ~50 parameters (detection timeout, range-based accuracy, view angle/range, grenade reaction, fire interval) plus difficulty-scale multipliers (`DIFF_SCALE_GD_*`) | `Task_New(... "HumanAIConfigItem", "AI_TYPE", isBase, p1, p2, ...)` |
| `squaddefault.qsc` | Default squad state machine — handles squad states (Idle, Move, Patrol, SearchArea, Inquire, Danger) and events, coordinating voice/cohesion | `AISquad_GetState()`, `AISquad_SwitchState()`, `AISquad_TriggerAlarm()`, `AISquad_PlaySoundAtReceiversPos()` |

### Per-level — `missions/<location>/<level>/ai/`

| Pattern | Contents | Example |
|---------|----------|---------|
| `NNN.qsc` | One soldier's behavior (~14–24 lines). Responds to `AIEVENT_CREATE` / `AIEVENT_IDLE` with navigation actions, then usually defers to the squad | `500.qsc`: `AIAction_WalkToNode(100, 1)`, `AIAction_LookAtNode(69, 1)`, `AIFunction_PassEventOnToSquad()` |
| `Squad_NNN.qsc` | One squad's reactive routing (~15–40 lines). Reads squad state and area/variable triggers, then assigns patrol routes | `Squad_700.qsc`: `if (AreaActivate_150.nActive) AISquad_Patrol(631); ... else AISquad_DefaultHandler()` |

Single-player levels carry dozens to ~160 of these per level; **multiplayer maps have no `ai/`
folder** (no scripted NPCs).

## 4. Sound definitions

Sound QVMs define named, spatialized sound entries grouped by category. They appear once globally and
once per level.

| File | Scope | Contents |
|------|-------|----------|
| `common/sounds/sounds.qsc` | Global | Engine sound library — `ALARMSYSTEM` (alarm tiers by distance), `BODYFALLS`, `BULLETS` (per-surface impacts + tracer colors), `RICCOCHET`, `WHIZZBY`. ~180+ entries |
| `missions/<location>/<level>/sounds/sounds.qsc` | Per level | Level audio — `INGAME` (machinery, music), `VOICE` (mission voice lines), `CS SFX`, `AMBIENTFX` (wildlife, weather). ~60–70 lines |

Both use the same nesting: `DefineGroup("NAME", DefineSound(id, sample, delay, pan, pitch, volume,
minDist, maxDist, ..., loopFlag), ...)`.

## 5. Menu UI

Front-end UI defined as script in `menusystem/`.

| File | Contents | Representative calls |
|------|----------|----------------------|
| `mainmenu.qsc` | Main-menu screen tree — Main, Single/Multiplayer, Graphics (resolution, gamma, AA, texture detail, LOD, shadows), Sound, Controls rebinding, Credits, ReadMe. Text boxes, sliders, list boxes, button handlers | `Task_New(... "MenuManager" ...)`, `MenuManager_PushScreen()`, `Config_SaveConfig()` |
| `ingamemenu.qsc` | Pause-menu tree — Resume, Load, Restart, Graphics, Sound, Controls, Quit; single-player vs multiplayer variants | `MenuManager_LeaveMenus()`, `LevelFlow_LevelFailed()`, `Game_SetMusicVolume()`, `Game_SetSFXVolume()` |

## 6. Physics objects

`physicsobj/` defines rigid-body parameters for every dynamic/vehicle object. The root
`physicsobj.qsc` holds reusable/base definitions (grenades, sandbags, generic props); each vehicle
subfolder has one `.qsc` for that vehicle. All use `DefinePhysicsObjType(TASKTYPE_*, ...)` with mass,
dimensions, drag/friction, and type-specific sub-components.

| Subfolder | Type | Distinctive fields |
|-----------|------|--------------------|
| `cars/` (apc, buggy, cutscene_truck, limo, t80, truck) | `TASKTYPE_CAR` | Heaviest (mass ~3k–18k); per-wheel `TASKTYPE_WHEEL` sub-objects, suspension, engine power, sound group |
| `helis/` (bell, mil) | `TASKTYPE_HELI` | Mass ~3k; multiple `TASKTYPE_ROTOR` sub-objects with blade mass and angular dynamics |
| `missiles/` (cgm2, hind, rpg18, rpg7) | `TASKTYPE_MISSILE` | Very light (mass ~10); drag, guidance, `MISSILE_SMOKE_*` / `MISSILE_TYPE_*`, smoke sprite |
| `planes/` (cutscenemissile, jsf, su27) | `TASKTYPE_PLANE` | Mass ~10k; wing dimensions, thrust/fuel, pitch stability |
| `trains/` | `TASKTYPE_WHEEL` | Minimal — wheel only (track simulation handles the rest) |
| `weapons/` | `TASKTYPE_GENERICPHYSICSOBJ` | Generic light prop (mass ~3) |

## 7. Missions & level scene

The mission and level-scene QVMs tie everything above into playable levels.

| File | Scope | Contents |
|------|-------|----------|
| `missions/igi2.qsc` | Global | The mission list — `DefineMissionListItem(11..36)` for single-player plus multiplayer IDs (1–5, 8). Maps mission IDs to locations/levels (see [game_structure.md → Mission Numbering](../game_structure.md#mission-numbering)) |
| `missions/<loc>/<lvl>/mission.qsc` | Per level | One `DefineMission(id, ...)` call — mission ID, flags, name/description strings, and the asset path triple (level / location-common / level dirs) plus the mission sprite |
| `missions/<loc>/<lvl>/objects.qsc` | Per level | **The level scene graph** — the single biggest QVM. Declares all object types via `Task_DeclareParameters`, then instantiates the entire scene with nested `Task_New`: terrain, buildings, lights, soldiers, squads, doors, switches, cameras, water, forests, AI graphs, objectives, cutscenes |

Inside `objects.qsc`, entities nest to mirror gameplay structure — an `AISquad` contains its
`HumanSoldier` instances, each of which contains a `HumanAI` child, and weapons are embedded as
script strings (e.g. `"Human_AddWeapon(\"WEAPON_ID_MAKAROV\")"`). The full object-type catalog
(field-by-field) is documented in [level.md](../level.md). Multiplayer `objects.qsc` files are
similar in scale but contain no AI and add a local `lod.qsc`.

## See Also

- [QVM Format (core)](../../core/formats/qvm.md) — binary container, opcode table, decompiler model.
- [Game Structure](../game_structure.md) — directory layout, MTP/DAT pairing, conversion pipeline.
- [Level](../level.md) — `objects.qsc` object-type declarations in detail.
