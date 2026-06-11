[← AI behavior](ai.md) · [Scripts Index](README.md) · [Back to Project README](../../../README.md) · [Menu UI →](menu.md)

# 4. Sound definitions

Sound scripts register named, spatialized sound entries grouped by category. There is one global
library and one smaller file per level.

| File | Scope | Defines |
|------|-------|---------|
| `common/sounds/sounds.qsc` | global | The engine sound library (alarms, bullets, footsteps, explosions, …) |
| `<level>/sounds/sounds.qsc` | per level | Level audio (music, cutscene voice, ambience) |

Both use the same two calls: `DefineGroup("NAME", … )` wraps a set of `DefineSound(…)` entries, and
groups can nest (the global `FOOTSTEPS` group contains per-material sub-groups: metals, glass,
concrete, watermix, ground, …).

## `DefineSound` signature

```c
DefineSound("soundId", "SAMPLE", delay, pan, pitch, volume, minDistance, maxDistance, -1, -1, -1, -1, loop)
```

| Position | Field | Meaning |
|----------|-------|---------|
| 1 | sound id | name referenced elsewhere (by [animtrigger](player-combat.md#animtriggerqsc--on-this-animation-play-this-sound), [weapon](player-combat.md), [material](player-combat.md), AI) |
| 2 | sample | audio asset stem (the `.wav`/`.mp3`) |
| 3 | delay | start delay *(inferred: ms)*, usually `0` |
| 4 | pan | stereo pan *(inferred)*, usually `0` |
| 5 | pitch | pitch shift *(inferred)*, usually `0` |
| 6 | volume | `0.0`–`1.0` linear gain |
| 7 | minDistance | full volume within this radius (world units) |
| 8 | maxDistance | inaudible beyond this radius |
| 9–12 | reserved | always `-1` |
| 13 | loop | `TRUE` = loops; `FALSE` = one-shot |

## Examples by group

A looping **alarm** audible across a wide area:

```c
DefineSound("alarm_20", "ALARM_2", 0, 0, 0, 1, 20.0, 1000.0, -1, -1, -1, -1, TRUE);
```

A one-shot **bullet impact** on hard metal, localized:

```c
DefineSound("bul_metal_hrd_1", "BUL_METAL_HRD_1", 0, 0, 0, 1, 4.0, 50.0, -1, -1, -1, -1, FALSE);
```

A looping **ambient generator** and a one-shot **explosion**:

```c
DefineSound("generator_03", "generator_03", 0, 0, 0, 1, 10.0, 60.0, -1, -1, -1, -1, TRUE);
DefineSound("explo_03_l", "EXPLO_03_L", 0, 0, 0, 1, 45.0, 1000.0, -1, -1, -1, -1, FALSE);
```

A per-level **cutscene voice line** (quieter, very wide range so it reads clearly):

```c
DefineSound("cv11_intro_01_white", "cv11_intro_01_white", 0, 0, 0, 0.70, 19.99, 1000.0, -1, -1, -1, -1, FALSE);
```

## Group inventory

- **Global** (`common/sounds/sounds.qsc`): a large set including `ALARMSYSTEM`, `BODYFALLS`,
  `BULLETS`, `DOORS`, `ELEVATOR`, `ENVIRONMENT`, `EXPLOSIONS`, `FOOTSTEPS` (with nested per-material
  sub-groups), `GUN SHOTS`, `GUN RELOAD`, `HIT`, `IMPACT-RELATED`, `PLAYER`, `VEHICLES`,
  `WEAPON-RELATED`, plus per-vehicle and per-material groups (`apc_sounds`, `su27`, `concrete`,
  `glass`, `metals`, `snow`, …).
- **Per level**: a handful of groups — typically `INGAME` (machinery, music), `VOICE` (mission
  dialogue), `CS SFX` (cutscene effects), and `AMBIENTFX`/`AMBFX`/`ENVIRONMENT` (wildlife, weather).

**Looping vs one-shot:** alarms, ambient machinery, wind, elevators and water loop (`TRUE`); footsteps,
gunshots, impacts, explosions and voice lines are one-shot (`FALSE`). Distance ranges scale with
purpose: footsteps ~3–12 units, bullet impacts ~4–50, alarms/explosions up to 1000, wind ambience up
to 10000.

## See Also

- [Player & combat](player-combat.md) — `animtrigger`, `weapon`, and `material` all reference these ids.
- [AI behavior](ai.md) — squads play `AIVoice_*` lines from these groups.
- [Missions & level scene](missions.md) — `SoundGenerator` tasks place level sounds in the world.
