[← Player & combat](player-combat.md) · [Scripts Index](README.md) · [Back to Project README](../../../README.md) · [Sound definitions →](sounds.md)

# 3. AI behavior

The most numerous category by file count. Shared defaults live in `common/ai/`; each level then has
many tiny per-entity scripts under its own `ai/` folder. A per-level script's filename is the
`Task_New` id of the `HumanAI`/`AISquad` it belongs to in that level's
[objects.qsc](missions.md#objectsqsc--the-level-scene-graph).

| File | Scope | Defines |
|------|-------|---------|
| `common/ai/default.qsc` | global | Default single-soldier event handler |
| `common/ai/settings.qsc` | global | AI archetype tuning + difficulty scales |
| `common/ai/squaddefault.qsc` | global | Default squad state machine |
| `<level>/ai/NNN.qsc` | per level | One soldier's behaviour (id = its `HumanAI` task) |
| `<level>/ai/Squad_NNN.qsc` | per level | One squad's reactive routing (id = its `AISquad` task) |

All AI scripts are **event handlers**: they branch on the current event/state and call actions. The
two dispatch primitives are `AIFunction_GetCurrentEventType()` (per soldier) and
`AISquad_GetState()` / `AISquad_GetEvent()` (per squad).

---

## `common/ai/default.qsc` — default soldier

On `AIEVENT_CREATE` it registers an interrupt priority ladder with ~47 `AIFunction_SetEventPriority(…)`
calls (order = priority), then dispatches the live event to an action. The core actions:

| Event | Action | Meaning |
|-------|--------|---------|
| `AIEVENT_SQUADCOMBATIDLE` | `AIAction_CombatIdle(AIACTIONFLAG_NONE)` | alert idle stance |
| `AIEVENT_IDLE` | `AIAction_Idle(…)` then `AIFunction_PassEventOnToSquad()` | relaxed idle, defer to squad |
| `AIEVENT_FLASHBANG` | `AIAction_Stunned(2, …)` | stunned for 2 s |
| `AIEVENT_GRENADETHROWN` / `…SHOUT` | `AIAction_RunPanicking(10, …)` | flee for 10 s |
| (default) | `AIFunction_PassEventOnToSquad()` | escalate to squad |

`AIFunction_PassEventOnToSquad()` is the key link: most events bubble up to the squad FSM. Other
calls: `AIFunction_HasTarget()`, `AIFunction_UseIdleView()`, `AIFunction_DefaultHandler()`.

---

## `common/ai/settings.qsc` — archetype tuning

One `HumanAIConfigItem` per archetype, with ~50 tuning parameters declared by an explicit schema (so
these names are *not* inferred). The signature:

```c
Task_New(-1, "HumanAIConfigItem", "AI_TYPE", isBaseData,
  dangerTimeout, inquireTimeout, detectionTimeDistanceFactor,
  minRangeAccuracy, medRangeAccuracy, maxRangeAccuracy, accuracyMedRange, accuracyMaxRange,
  animSpeed, closeCombatDamage, combatView1Alpha, combatView1Length, … ,
  minFireInterval, percentFirePerBurst, maxTrackingDist, maxTrackingTime, detectionToAttackTime,
  /* + 16 per-body-part damage multipliers */ …)
```

Selected fields: accuracy is a 0–100 % hit chance that varies by range band; `combatView1Alpha/Length`
is the detection cone angle/range; `grenadeReactionProb`/`grenadeThrowProb` are percentages;
`minFireInterval` is the cooldown between shots.

The six archetypes climb in capability:

| Archetype | minAcc | maxAcc | Notes |
|-----------|--------|--------|-------|
| `HUMANAI_TYPE_C1_NORMAL_SOLDIER` | 50 | 5 | baseline rookie |
| `HUMANAI_TYPE_C1_TOUGH_SOLDIER` | 60 | 6 | +accuracy, faster fire |
| `HUMANAI_TYPE_C2_NORMAL_SOLDIER` | 60 | 10 | longer effective range |
| `HUMANAI_TYPE_C2_TOUGH_SOLDIER` | 65 | 12 | — |
| `HUMANAI_TYPE_C3_NORMAL_SOLDIER` | 65 | 15 | — |
| `HUMANAI_TYPE_C3_TOUGH_SOLDIER` | 70 | 17 | elite |

Three **difficulty scales** multiply the base values (`isBaseData = FALSE`): `DIFF_SCALE_GD_1` (easy —
worse aim, harder to detect player), `DIFF_SCALE_GD_2` (normal), `DIFF_SCALE_GD_3` (hard — fast
reactions, sharp aim). A soldier's archetype is chosen in `objects.qsc` when its `HumanAI` is placed.

---

## `common/ai/squaddefault.qsc` — squad state machine

A finite state machine keyed on `AISquad_GetState()` × `AISquad_GetEvent()`, branching by squad type
(`AIType_Offensive`, `AIType_Defensive`, `AIType_OnVehicle`). States include `AISquadState_Idle`,
`_Patrol`, `_SearchArea`, `_Inquire`, `_Leapfrog`, `_Danger`, `_HoldArea`.

An **offensive** squad that detects the enemy while searching goes loud and assaults:

```c
if(AISquad_nSquadState == AISquadState_SearchArea || … )
{
  if(AISquad_nEvent == AIEVENT_ENEMYDETECTION)
  {
    AISquad_PlaySoundAtReceiversPos(AIVoice_Engaging);
    AISquad_SwitchState(AISquadState_Leapfrog);
    AISquad_TriggerAlarm();
    if(Config_GetActiveDifficultyLevel() > 0) { AISquad_ThrowGrenade(); }
  }
}
```

A **defensive** squad instead falls back to `AISquadState_HoldArea` on detection. Key squad calls:
`AISquad_SwitchState(state)`, `AISquad_PlaySoundAtReceiversPos(AIVoice_*)`,
`AISquad_TriggerEvent(AIEVENT_DISTRESSCALL, 35)` (broadcast within 35 m), `AISquad_TriggerAlarm()`,
`AISquad_ThrowGrenade()`, `AISquad_Patrol(pathId)`, `AISquad_MoveToNode(nodeId)`,
`AISquad_ReceiverLookAtEvent()`, `AISquad_DefaultHandler()` (defer to the per-squad script).

Voice constants: `AIVoice_SearchArea`, `_EnemyDetected`, `_Engaging`, `_ManDown`, `_TakeCover`,
`_HoldArea`, `_GunShotHeard`, etc.

---

## Per-level `ai/NNN.qsc` — one soldier

Tiny scripts (often 10–20 lines). They typically initialise on create, do something on idle, and
otherwise defer to the squad. Soldier **500** walks a patrol and looks at a node:

```c
if(AIFunction_GetCurrentEventType() == AIEVENT_CREATE)
{
  AIFunction_DefaultHandler();
}
if(AIFunction_GetCurrentEventType() == AIEVENT_IDLE)
{
  AIAction_WalkToNode(100, 1);   // walk to graph node 100 (arg2: 0 crouch / 1 walk / 2 run, inferred)
  AIAction_LookAtNode(69, 1);    // face graph node 69
  AIFunction_PassEventOnToSquad();
}
else { AIFunction_DefaultHandler(); }
```

Some are gated by a mission flag — soldier 500 in level 6 only runs to a node when `EditVariable_320`
is set:

```c
if(EditVariable_320.nValue == 1) { AIAction_RunToNode(105, 1); }
else { AIFunction_DefaultHandler(); }
```

Actions: `AIAction_WalkToNode` / `_RunToNode` / `_LookAtNode(nodeId, flag)`. The node ids index the
level's [AIGraph](missions.md#objectsqsc--the-level-scene-graph) (binary `graphs/graphN.dat`).

---

## Per-level `ai/Squad_NNN.qsc` — one squad

Reactive routing layered on top of `squaddefault.qsc`. Squad **700** picks a patrol route from
trigger zones:

```c
if(AISquad_GetState() == AISquadState_Idle && AISquad_GetEvent() == AIEVENT_IDLE)
{
  if(EditVariable_103.nValue == 1)
  {
    if(AreaActivate_150.nActive)                              { AISquad_Patrol(631); }
    else if(AreaActivate_151.nActive || AreaActivate_152.nActive) { AISquad_Patrol(632); }
    else { AISquad_DefaultHandler(); }
  }
  else { AISquad_DefaultHandler(); }
}
else { AISquad_DefaultHandler(); }
```

Camera-aware variants route to an interception node based on which `SCamera` last saw the player:

```c
if(SCamera_109.isLastDetection)      { AISquad_MoveToNode(13); }
else if(SCamera_106.isLastDetection) { AISquad_MoveToNode(42); }
```

`EditVariable_NNN.nValue`, `AreaActivate_NNN.nActive`, and `SCamera_NNN.isLastDetection` all reference
sibling tasks in `objects.qsc` by id — these are the scripted gates between default behaviour and
level-specific tactics. A minimal squad script is just `AISquad_DefaultHandler();`.

## See Also

- [Missions & level scene](missions.md) — where `HumanAI`/`AISquad`/`AIGraph`/`EditVariable` tasks are placed.
- [Player & combat](player-combat.md) — the accuracy/detection values AI archetypes tune.
- [Sound definitions](sounds.md) — the `AIVoice_*` lines squads play.
