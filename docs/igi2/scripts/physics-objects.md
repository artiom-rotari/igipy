[← Menu UI](menu.md) · [Scripts Index](README.md) · [Back to Project README](../../../README.md) · [Missions & level scene →](missions.md)

# 6. Physics objects

`physicsobj/` defines rigid-body parameters for every dynamic object: vehicles, aircraft, projectiles,
grenades, and generic props. The root `physicsobj.qsc` holds reusable/base definitions; each vehicle
subfolder has one `.qsc` for that vehicle.

Every entry is `DefinePhysicsObjType(TASKTYPE_*, subtype, mass, width, length, height, "<NAME>",
"<DESC>", "model", … )`. The leading fields are consistent; the trailing fields differ per type. Most
argument meanings below are *(inferred)* from the values — there is no schema header in these files.

| Subfolder | Task type | Distinctive content |
|-----------|-----------|---------------------|
| root `physicsobj.qsc` | `GENERICPHYSICSOBJ`, `GENERICPHYSICSMAGICOBJ`, `GRENADE` | test props, sandbags, grenade variants |
| `cars/` | `CAR` (+ `WHEEL`) | mass, suspension, engine power, steering, per-wheel grip |
| `helis/` | `HELI` (+ `ROTOR`) | lift zones, rotor blade dynamics |
| `missiles/` | `MISSILE` | thrust, guidance, smoke trail |
| `planes/` | `PLANE` | wing lift, stall angle, engine thrust |
| `trains/` | `WHEEL` | rail wheel only |
| `weapons/` | `GENERICPHYSICSOBJ` | generic projectile prop |

## Common leading fields

```c
DefinePhysicsObjType(
  TASKTYPE_*,     // object class
  subtype,        // variant within the type (0 = default)
  mass,           // kg
  width, length, height,   // bounding box (m)
  "<NAME>", "<DESC>",      // localization keys
  "model",        // mesh stem
  … type-specific fields …,
  gravity_scale,  // often 0.7 (inferred)
  air_resistance) // often 0.001 (inferred)
```

## Cars — `cars/t80/car.qsc`

The T-80 tank: heavy, rigid suspension, big engine, defined wheels as nested `TASKTYPE_WHEEL`:

```c
DefinePhysicsObjType(TASKTYPE_CAR, 0, 18000, 2.20, 7.80, 3.0, "<T80>", "<T80DESC>", "614_01_1", …
  /* engine power */ 80000.0, /* steering ~30°, suspension stiffness/damping, max rpm … */ );

DefinePhysicsObjType(TASKTYPE_WHEEL, 1, 3, 0.30, 0.90, 0.90, "<APCWHEEL>", "<APCWHEELDESC>", "614_05_1",
  0, 0.70, 0.001, "614_05_1", 0.449, 0.451);   // trailing pair = tyre friction (lateral, longitudinal)
```

The `truck` is the same chassis box but ~6× lighter (`mass 3000`), softer suspension, sharper steering
(`45°`), higher-grip tyres (`0.75`), and a `"truck_sounds"` channel set.

## Helicopters — `helis/mil/heli.qsc`

Lift-based, with nested `TASKTYPE_ROTOR` sub-objects (main, tail, auxiliary) carrying blade mass and
flap/lead-lag dynamics:

```c
DefinePhysicsObjType(TASKTYPE_HELI, 0, 3000, 2.20, 7.80, 3.0, "<MIL>", "<MILDESC>", "700_01_1", 0, 0.70, 0.001,
  200, 50.0, 0.40, 50.0, 0.40, 50.0, 0.40, 3000, …);  // lift zones + max rotor power 3000

DefinePhysicsObjType(TASKTYPE_ROTOR, 1, 200, 0.5, 0.40, 0.30, "<ROTOR>", "<ROTORDESC>", "700_03_1", …); // main
DefinePhysicsObjType(TASKTYPE_ROTOR, 2, 100, 0.10, 7,   0.40, "<ROTOR>", "<ROTORDESC>", "700_04_1", …); // tail (long)
```

## Missiles — `missiles/rpg7/missile.qsc`

Very light, direct-thrust projectile with guidance zones and a smoke trail:

```c
DefinePhysicsObjType(TASKTYPE_MISSILE, 1, 10, 0.40, 5.0, 0.40, "<SAM>", "<SAMDESC>", "140_02_1", 1, …
  MISSILE_SMOKE_NORMAL, MISSILE_TYPE_MISSILE_DIRECT, 4, 1, 50, 0.25, 0.5, 1, 1, "smoke2.spr", "radarwind_1");
```

Trailing fields are the smoke type, trajectory type, particle count/scale/life/speed, smoke sprite, and
the flight sound.

## Planes — `planes/su27/plane.qsc`

Wing-lift aircraft with an explicit stall angle. Some values are written as multiplications in the
source (kept verbatim):

```c
DefinePhysicsObjType(TASKTYPE_PLANE, 0, 10000, 5.0, 16, 2.5, "<SU27>", "<SU27DESC>", "702_02_1", 0, 0.70, 0.001,
  700, 1.70, 0.90, 0.90, 0.90, 40.0, 0.90, 15000 * 1.5, 0.027 * 2, 0.003 * 2, 6, 6, …,
  -0.08709999918937683, 0.9961000084877014, …);  // stall angle (rad) + stall lift retention
```

## Trains — `trains/train.qsc` & generic — `weapons/physicsobj.qsc`

A train is just a rail wheel (the track constrains the rest):

```c
DefinePhysicsObjType(TASKTYPE_WHEEL, 1, 3, 0.30, 0.90, 0.90, "<TRAINWHEEL>", "<TRAINWHEELDESC>", "605_01_1",
  0, 0.70, 0.001, "605_01_1", 0.5, 0.5);
```

`weapons/physicsobj.qsc` is a light generic prop (`mass 3.4`) using collision boxes only.

## Root `physicsobj.qsc` — grenades & props

Base/reusable definitions. Grenades share physics but differ by explosion type:

```c
DefinePhysicsObjType(TASKTYPE_GRENADE, 0, 0.30, 0.10, 0.10, 0.15, "<GRENADE>", "<GRENADEDESC>", "115_01_1", 5, …,
  3.0, 0.016, 4, GRENADE_EXPLOSIONTYPE_NORMAL);
DefinePhysicsObjType(TASKTYPE_GRENADE, 1, 0.30, 0.10, 0.10, 0.15, … , GRENADE_EXPLOSIONTYPE_FLASHBANG);
DefinePhysicsObjType(TASKTYPE_GENERICPHYSICSMAGICOBJ, 6, 100, 1, 0.70, 0.30, "<SANDBAG>", …, "1713_01_1", …);
```

Explosion types: `GRENADE_EXPLOSIONTYPE_NORMAL`, `_FLASHBANG`, `_SMOKE`.

## How the categories differ

| Type | Mass | Power/thrust | Sub-objects | Flight/drive model |
|------|------|--------------|-------------|--------------------|
| Tank (T-80) | 18000 | 80000 | wheels | rigid suspension, tracked |
| Truck | 3000 | 5000 | wheels | soft suspension, road |
| Helicopter | 3000 | 3000 (rotor) | rotors | lift zones + blade dynamics |
| Missile | 10 | 200 thrust | — | direct thrust + guidance |
| Plane (Su-27) | 10000 | 22500 | — | wing lift + stall model |
| Train | 3 (wheel) | rail | wheel | track-constrained |
| Grenade | 0.3 | — | — | ballistic + blast radius |

## See Also

- [Engine & config](engine-config.md) — `magicobjconfig` attaches `TASKTYPE_WHEEL`/`ROTOR`/`CARDOOR` behaviour to models.
- [Player & combat](player-combat.md) — weapon `ProjectileLauncher` blocks reference grenade explosion data.
- [Missions & level scene](missions.md) — vehicles are placed and scripted in the level scene graph.
