[Back to Project README](../../../README.md) · [Docs Index](../../README.md)

# IGI 2 Script Reference (QSC by category)

Deep-dive companion to [formats/qvm.md](../formats/qvm.md). Each page below documents one **category**
of IGI 2 script (decompiled from `.qvm` to `.qsc`), explaining what the scripts in that category
define — the real function signatures, what each argument means, and concrete examples pulled from the
game files.

> **Source:** examples are copied from the decompiled `.qsc` (`igi2 convert-qvm-to-qsc`). The QSC
> language and the binary container are described in [core/formats/qvm.md](../../core/formats/qvm.md).
> Argument **names** are not stored in the bytecode for most calls — where a meaning is inferred from
> values/context rather than an explicit `Task_DeclareParameters` schema, it is marked *(inferred)*.

## Pages

| # | Page | Covers | Example of what it answers |
|---|------|--------|----------------------------|
| 1 | [Engine & global config](engine-config.md) | `config`, `lod`, `magicobjconfig`, `editormagicobjconfig` | "At what distance does a model drop to a lower LOD?" |
| 2 | [Player & combat](player-combat.md) | `humanplayer`, `weapon`, `ammo`, `animtrigger`, `material` | "On an AK-47 reload, which animation and sound play?" |
| 3 | [AI behavior](ai.md) | `default`, `settings`, `squaddefault`, per-level `NNN`/`Squad_NNN` | "How does a squad react when it detects the player?" |
| 4 | [Sound definitions](sounds.md) | global + per-level `sounds` | "How is a looping alarm or a 3D bullet impact defined?" |
| 5 | [Menu UI](menu.md) | `mainmenu`, `ingamemenu` | "What does the Gamma slider in the options menu call?" |
| 6 | [Physics objects](physics-objects.md) | `physicsobj` + per-vehicle | "What is the T-80's mass, engine power, and wheel grip?" |
| 7 | [Missions & level scene](missions.md) | `igi2`, `mission`, `objects` | "How is an enemy soldier placed, armed, and given AI?" |

## See Also

- [QVM Scripts (categories overview)](../formats/qvm.md) — the one-page map these deep-dives expand on.
- [Game Structure](../game_structure.md) — where these files live on disk.
- [Level](../level.md) — the `objects.qsc` scene-graph object types in detail.
