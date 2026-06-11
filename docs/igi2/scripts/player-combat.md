[← Engine & config](engine-config.md) · [Scripts Index](README.md) · [Back to Project README](../../../README.md) · [AI behavior →](ai.md)

# 2. Player & combat definitions

Global definitions for the player character and everything combat-related: weapons, ammo, the
animation→sound bridge, and surface physics. Argument meanings marked *(inferred)* are deduced from
values, not an explicit schema.

| File | Location | Defines |
|------|----------|---------|
| `animtrigger.qsc` | `animtrigger/` | Which sound fires on a given animation event (reload, footstep, melee) |
| `weapon.qsc` | `weapons/` | 44 weapon types (33 guns + knife/grenades/mines): ballistics, accuracy, animations, sounds, fire modes |
| `ammo.qsc` | `weapons/` | Ammo types: tracer colour, casing, shop price |
| `humanplayer.qsc` | `humanplayer/` | Player movement, per-body-part damage, weapon cycle, ammo caps |
| `material.qsc` | `material/` | Surface physics: footsteps, bullet impacts, penetration, decals |

---

## `animtrigger.qsc` — "on this animation, play this sound"

This is the file behind *"on a weapon reload, this animation plays this sound."* Each animation
trigger id is mapped to a sound (or to a pure logic event):

```c
DefineAnimTrigger(triggerId, TASKTYPE, "soundId", looping)
```

| Position | Field | Meaning |
|----------|-------|---------|
| 1 | trigger id | numeric id, or a named `HUMANANIM_TRIGGER_*` constant |
| 2 | task type | `TASKTYPE_ANIMSOUND` (plays a sound) or `TASKTYPE_HUMAN`/`HUMANPLAYER`/`HUMANSOLDIER` (logic only) |
| 3 | sound id | sound to play (a [sounds.qsc](sounds.md) id); `""` for logic-only triggers |
| 4 | looping | `TRUE` = loops while the animation plays; `FALSE` = one-shot |

**Glock reload — three staged sounds across the reload animation:**

```c
DefineAnimTrigger(1000, TASKTYPE_ANIMSOUND, "glock_reload_1", TRUE);
DefineAnimTrigger(1001, TASKTYPE_ANIMSOUND, "glock_reload_2", TRUE);
DefineAnimTrigger(1002, TASKTYPE_ANIMSOUND, "glock_reload_3", TRUE);
```

**AK-47 reload, footstep on a fence, melee, body fall:**

```c
DefineAnimTrigger(1033, TASKTYPE_ANIMSOUND, "ak47_reload_1", TRUE);
DefineAnimTrigger(1025, TASKTYPE_ANIMSOUND, "walk_fence_1",  FALSE);
DefineAnimTrigger(1052, TASKTYPE_ANIMSOUND, "gunpunch_01",   TRUE);
DefineAnimTrigger(1040, TASKTYPE_ANIMSOUND, "bodyfall_9",    TRUE);
```

**Logic-only triggers (no sound — they drive code, e.g. footstep dispatch, grenade release):**

```c
DefineAnimTrigger(HUMANANIM_TRIGGER_FEETSOUND, TASKTYPE_HUMAN);
DefineAnimTrigger(HUMANANIM_TRIGGER_THROWGRENADE, TASKTYPE_HUMANPLAYER);
```

The animation frame that fires each trigger id lives in the model/animation data, not here — this
file is purely the trigger-id → sound/event table. Named constants seen: `HUMANANIM_TRIGGER_FEETSOUND`,
`_THROWGRENADE`, `_THROWGRENADE_RELEASE`, `_STOPANIMATION`, `_OPENDRAWER`, `_CLOSEDRAWER`,
`_CLOSECOMBAT_DEALDAMAGE`, `_DEADBODY_SOUND`.

---

## `weapon.qsc` — weapon definitions

Each weapon is a `Task_New("WeaponType", …)` whose long argument list covers identity, per-stance
accuracy (degrees), draw/holster animations and sounds, the tracer texture/velocity, and which
**primary** and **secondary** task types it uses. The actual ballistics live in nested parameter
blocks: `Gun`, `Zoom`, `Knife`, `ProjectileLauncher`, `C4Bomb`, `ProximityMine`, `RemoteMine`,
`Medipack`, `LaserDesignator`, `FireMode`, `PullPin`.

The **`Gun`** block is where fire/reload behaviour is set. Its key positions *(inferred from values)*:
ammo type, display type, bullets-per-round, rounds-per-clip, rounds-per-minute, range (m), reload
time (s), muzzle velocity (m/s), muzzle-flash sprites/size, recoil (alpha/gamma kickback degrees),
gunshot task type, casing model, then the **1st- and 3rd-person fire and reload animation names**,
then up to three **fire sounds** with loop flags, the AI detection-range constant, and `TagItemReal32`
damage/penetration tags.

**AK-47** — primary `Gun` + secondary `Knife` (stock bash). Note the reload animation
`reload_ak47_1st` and the looped fire sound `ak74_loop`:

```c
Task_New(-1, "WeaponType", "WEAPON_ID_AK47", "WEAPON_ID_AK47", "AK-47", "ak47", "WEAPONS:ak47.spr",
  WEAPONTYPE_GUN, WEAPONCATEGORY_PRIMARY, SIGHTDISPLAYTYPE_ASSAULTRIFLE, "107_01_1",
  1, 30, 1, 1, "", "", "", 0, 0, 0, 0.70, 3.40, 2.40, 0.5, 2.40, 0.40, 6, 2, 1, 0.15, 0.60,
  /* … draw anims/sounds … */ "greenglow", 300,
  TASKTYPE_GUN, FALSE, FALSE, TASKTYPE_KNIFE, TRUE, FALSE, TRUE, "WEAPONS:ak47_pickup.spr",
  FALSE, FALSE, 2900, TRUE, FALSE, 3, 1, 0.04, TRUE,

  Task_New(-1, "WeaponTypeParameterContainer", "Primary Parameters", 0,
    Task_New(-1, "Gun", "", AMMO_ID_AK74CLIP, AMMODISPLAYTYPE_CLIP,
      1,        /* bullets per round   */
      30,       /* rounds per clip     */
      600,      /* rounds per minute   */
      300,      /* range (m)           */
      2.70,     /* reload time (s)     */
      710,      /* muzzle velocity m/s */
      "flash_round.tex", "flash_side2.tex", 0.20, 2.70, 2.90, -1, -1.10, 1, 5, 10, 0.125, 0.125,
      TASKTYPE_GUNSHOT, "1123_04_1",
      "fire_ak47_1st", "", "", "reload_ak47_1st", "", "",   /* 1st-person fire/reload anims */
      "", "", "", "", "", "",                                /* 3rd-person anims            */
      "ak74_loop", "", "", TRUE, FALSE, FALSE, "ak74_loop_e", /* fire sounds + loop flags   */
      HUMANAI_DETECTIONEVENT_GUNSHOT_RANGE, FALSE, 0,
        Task_New(-1, "TagItemReal32", "Damage Factor", "Damage Factor", 0.43),
        Task_New(-1, "TagItemReal32", "Penetration Power", "Penetration Power", 12))),

  Task_New(-1, "WeaponTypeParameterContainer", "Secondary Parameters", 1,
    Task_New(-1, "Knife", "", 3, 30, 0.5, 0.40, "hitwithstock_ak47_1st", "", "",
      "fire_hitwithstock_ak47", "gunpunch_01")));
```

So for the AK-47: pulling the trigger plays `fire_ak47_1st` + looped sound `ak74_loop`; reloading
plays `reload_ak47_1st` and takes 2.7 s; each shot does damage factor 0.43 with penetration 12.

Other block types follow the same idea with their own fields:

- **`Zoom`** (sniper secondary): min/max FOV degrees, scope-overlay task type, zoom sound, and
  per-stance breath-sway offsets. The Barrett uses `Task_New(-1, "Zoom", "", 3, 20, 2, TASKTYPE_SNIPEROVERLAY, FALSE, "sniper_zoom", 0.4, 0.3, 0.2, …)`.
- **`Knife`**: trace count, melee cone (deg), startup delay (s), damage factor, combo anims, hit sound.
- **`ProjectileLauncher`** (grenades): velocity, range, fuse time, throw anims/sounds, plus explosion
  `TagItem*` (radius, falloff, damage). The frag grenade: 23 m/s, 5 s fuse, 4 m radius.
- **`Medipack`** / **`C4Bomb`** / **`ProximityMine`** / **`RemoteMine`** / **`LaserDesignator`**: heal
  factor / arming + blast radius / trigger radius / max range respectively.

Key constant families: `WEAPON_ID_*` (AK47, GLOCK, BARRET, MP5SD, RPG7, …), `WEAPONTYPE_*`,
`WEAPONCATEGORY_*`, `SIGHTDISPLAYTYPE_*`, `AMMODISPLAYTYPE_*`, `TASKTYPE_GUN/GUNSHOT/KNIFE/ZOOM/…`,
`HUMANAI_DETECTIONEVENT_GUNSHOT_RANGE` / `_SILENCED_RANGE` / `_PISTOL_RANGE`.

---

## `ammo.qsc` — ammunition types

```c
Task_New(-1, "AmmoType", "AMMO_ID_*", "displayName", "casingModel", "pickupModel",
  enableTracer, scoredForAccuracy, sR, sG, sB, eR, eG, eB, shopPrice, shopAmount, "resourceId")
```

`sR,sG,sB`/`eR,eG,eB` are the tracer start/end colours (0–255); `shopAmount` of `-1` means "use the
weapon/player default". The AK clip — tracer on, 80 credits:

```c
Task_New(-1, "AmmoType", "AMMO_ID_AK74CLIP", "AMMO_ID_AK74CLIP", "", "AK_clip_model",
  TRUE, TRUE, 255, 128, 0, 255, 255, 0, 80, -1, "AK47CLIP_DESC");
```

A 40 mm grenade round — no tracer, one per purchase, 600 credits:

```c
Task_New(-1, "AmmoType", "AMMO_ID_M203CLIP", "AMMO_ID_M203CLIP", "", "108_05_1",
  FALSE, FALSE, 255, 128, 0, 255, 255, 0, 600, 1, "M203CLIP_DESC");
```

---

## `humanplayer.qsc` — the player character

One `HumanPlayerConfigItem` declared by schema, then instantiated. It carries movement tuning,
**separate single-player and multiplayer damage multipliers per body part**, and two embedded scripts
(the weapon cycle order and the per-ammo carry caps). Selected fields with real values:

| Field | Value | Meaning |
|-------|-------|---------|
| Movement speed scale | `2.5` | walk-speed modifier |
| Forward / upward jump | `7.5` / `22` km/h | jump velocities |
| Throwing base velocity | `15` km/h | grenade throw speed |
| Peek length / time | `1` m / `0.25` s | lean-peek distance and ramp |
| Electric-fence damage scale | `0.5` | fence damage halved |
| Limb multiplier (SP / MP) | `0.175` / `0.55` | arms & legs take less damage |
| Head multiplier (SP / MP) | `0.55` / `1.8` | MP headshots are near-lethal |

The two trailing strings are executable scripts:

```c
"DefineHumanPlayerWeaponCycle(WEAPON_ID_AK47, WEAPON_ID_AUG, WEAPON_ID_BARRET, … WEAPON_ID_MEDIPACK)"
"DefineHumanPlayerAmmoLimit(AMMO_ID_MAKAROVCLIP, 64, AMMO_ID_AK74CLIP, 300, … AMMO_ID_GRENADE, 3)"
```

— the order weapons cycle through, and how much of each ammo the player may carry (M16 300 rounds,
grenades 3, C4 1).

---

## `material.qsc` — surface physics

Each surface is `SetActiveMaterial(id)` + `DefineQMaterial(…)` + `DefineGameMaterial(…)`. The game
material defines penetration, the full set of **footstep walk/run sounds** (up to 8 variants each),
body-fall, **bullet-impact sounds**, and the bullet-hole **decal textures** for entry and exit.

Concrete — Concrete blocks most rounds and spawns entry/exit hole decals:

```c
SetActiveMaterial(11);
DefineQMaterial(0, 0.90, 1, 192, 192, 192);
DefineGameMaterial("Concrete", 4, 25, 0.01, FALSE, 1,
  "concrete_w_01", … "concrete_w_08",        /* 8 walk-step sounds */
  "concrete_r_01", … "concrete_r_08",        /* 8 run-step sounds  */
  "concrete_land_01",
  "bf_hard_01", "bf_hard_02", "bf_hard_03", "rain_2",
  "bul_ground_1", … "bul_ground_6",          /* bullet impact sounds */
  "Hit0", "", "knh_concrete",                /* melee sound */
  TASKTYPE_GUNSHOTEFFECT, TRUE, TRUE, "hole-concrete-inn.tex", "dent-concrete-super.tex", 0.03, "1012_01_1",
  TASKTYPE_GUNSHOTEFFECT, FALSE, FALSE, "hole-concrete-out.tex", "", 0.03, "1012_01_1");
```

`Flesh` uses wet impact sounds (`bul_flesh_1…5`) and red wound decals (`hole-flesh-inn/out.tex`);
`Fence` overrides footsteps to the noisy `walk_fence_1` and has no decals (rounds pass/ricochet).
The first two `DefineGameMaterial` numbers are penetration chance/depth *(inferred)*.

Material id list (from `SetActiveMaterial`): 0 Air, 1 Ground, 2 Water, 3 Wood, 4 Carton,
5 StrongMetal, 6 NormalMetal, 7 SoftMetal, 8 Flesh, 9 BloodyFlesh, 10 Textiles, 11 Concrete,
12 Runway, 13 Rug, 14 Glass, 15 Plastic, 16 Porcelain, 17 Rubber, 18 Fence, 19 Gravel, 20 Snow,
21 HumanCollision, 22 MetalLadder, 23 MetalFence, 24 ConveyorBelt, 25 UnbreakableGlass, 26 Forest,
27 Grass, 28 Sand, 29 ThinConcrete, 30 WoodStrong, 31 Treetrunk, 32 Branches.

There are **33** game materials in total (IDs 0–32), each created by a matching
`DefineGameMaterial` / `SetActiveMaterial` pair in `material.qsc`.

## See Also

- [Sound definitions](sounds.md) — the sound ids that `animtrigger`/`weapon`/`material` reference.
- [AI behavior](ai.md) — how AI uses weapon detection ranges and accuracy.
- [Engine & config](engine-config.md) — the `magicobjconfig` task types weapons attach to.
