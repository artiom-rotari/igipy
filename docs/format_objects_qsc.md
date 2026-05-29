[← MEF Format](format_mef.md) · [Back to README.md](../README.md#supported-game-file-formats)

# objects.qsc — Level Scene Graph

Every level contains an `objects.qsc` file (decompiled from `objects.qvm`) that defines the complete scene graph: terrain, buildings, lights, soldiers, doors, forests, water, cameras, AI graphs, objectives, cutscenes, and more. It is the largest file per level (up to 404 KB decompiled).

## File Structure

An `objects.qsc` file has two sections:

```
┌──────────────────────────────────────────────────┐
│ Declarations                                      │
│   Task_DeclareParameters("TypeName", ...)         │
│   Task_DeclareParameters("TypeName", ...)         │
│   ...                                             │
├──────────────────────────────────────────────────┤
│ Scene Tree                                        │
│   Task_New(4095, "Static", "",                    │
│       Task_New(id, "Type", "Name", params...,     │
│           Task_New(id, "Type", "Name", ...),      │
│           ...),                                   │
│       ...);                                       │
│   Task_New(4089, "Dynamic", "",                   │
│       ...);                                       │
│   Task_New(id, "LevelFlow", ...);                 │
│   Task_New(id, "LevelInfo", ...);                 │
│   Task_New(id, "MissionScoreSettings", ...);      │
└──────────────────────────────────────────────────┘
```

**Declarations** define the parameter schema for each object type. They are identical across all 25 levels. Parameters are positional — each `Task_New` call passes values in the same order as the declaration.

**Scene Tree** is a hierarchy of `Task_New(id, "Type", "Name", ...params, ...children)` calls. Every object has a unique integer ID, a type string, an optional name string, positional parameter values, and zero or more child objects.

Two root containers split the scene:

| Root | Purpose | Contents |
|------|---------|----------|
| `Static` (ID 4095) | Baked/immovable geometry | Terrain, rigid objects, buildings, fences, lighting, sky, AI graphs, patrol paths |
| `Dynamic` (ID 4089) | Runtime/interactive objects | Player spawn, enemies, doors, vehicles, cutscenes, pickups, VFX, ambient audio |

Additional top-level tasks appear after the two root containers: `LevelFlow`, `LevelInfo`, `MissionScoreSettings`.

## Task ID Conventions

Task IDs link `objects.qsc` entries to external binary files:

| File pattern | Task type | Example |
|-------------|-----------|---------|
| `forest_<id>.dat` | Forest | `Task_New(2540, "Forest", ...)` → `forest_2540.dat` |
| `graphs/graph<id>.dat` | AIGraph | `Task_New(1, "AIGraph", ...)` → `graph1.dat` |
| `graphs/graphcover<id>.dat` | AIGraph | Same task → `graphcover1.dat` |
| `ai/<id>.qvm` | HumanAI | `Task_New(500, "HumanAI", ...)` → `ai/500.qvm` |
| `ai/Squad_<id>.qvm` | AISquad | `Task_New(700, "AISquad", ...)` → `ai/Squad_700.qvm` |

## Parameter Data Types

Declarations use these types to describe each parameter:

| Type | Size | Description | JSON mapping |
|------|------|-------------|-------------|
| `bool8` | 1 value | Boolean (`TRUE`/`FALSE`) | `boolean` |
| `Int16` | 1 value | 16-bit signed integer | `number` |
| `Int32` | 1 value | 32-bit signed integer | `number` |
| `Real32` | 1 value | 32-bit float | `number` |
| `Real64` | 1 value | 64-bit float | `number` |
| `Angle` | 1 value | Float angle in radians | `number` |
| `Degrees` | 1 value | Float angle in degrees | `number` |
| `RangeReal32` | 1 value | Float (range-constrained in editor) | `number` |
| `ObjectPos` | 3 values | Position as (X, Y, Z) floats | `[x, y, z]` |
| `Real32x3` | 3 values | 3-component float vector | `[x, y, z]` |
| `Real64x3` | 3 values | 3-component double vector | `[x, y, z]` |
| `Real32x9` | 3 values | Orientation stored as 3 floats (alpha, beta, gamma radians) | `[a, b, g]` |
| `RGB` | 3 values | Color as (R, G, B) floats 0–1 | `[r, g, b]` |
| `String16` | 1 value | String up to 16 chars (model IDs, sound names) | `string` |
| `String32` | 1 value | String up to 32 chars | `string` |
| `String256` | 1 value | String up to 256 chars (file paths) | `string` |
| `VarString` | 1 value | Variable-length expression string (scripting) | `string` |
| `EnumInt32` | 1 value | Enum stored as integer | `number` |
| `EnumString32` | 1 value | Enum stored as string | `string` |
| `DropDownCombo` | 1 value | Editor dropdown (string value) | `string` |
| `PushButton` | 1 value | Editor-only action button (always `FALSE` in data) | `boolean` |
| `Graph` | 1 value | AI graph data blob (node/edge counts as comma-separated) | `string` |
| `AnimData` | 1 value | Animation data blob | `string` |

**Multi-value types**: `ObjectPos`, `Real32x3`, `Real64x3`, `Real32x9`, and `RGB` each consume 3 positional argument slots in `Task_New` despite being declared as a single parameter.

## Instance Counts (across all 25 levels)

| Type | Instances | Category |
|------|-----------|----------|
| PatrolPathCommand | 9,384 | AI |
| EditRigidObj | 8,636 | Geometry |
| SpawnPoint | 1,528 | Multiplayer |
| Container | 921 | Structure |
| HumanSoldier | 901 | AI |
| HumanAI | 901 | AI |
| Door | 806 | Interactive |
| SplinePathNodeQTask | 716 | Paths |
| SplineObjWaypoint | 713 | Geometry |
| Smoke | 620 | VFX |
| LightmapInfo | 615 | Lighting |
| AmbientArea | 606 | Audio |
| SequenceCommand | 555 | Logic |
| ConditionalContainer | 525 | Logic |
| Building | 522 | Geometry |
| StatusMessage | 497 | Logic |
| EditCamera | 482 | Cutscenes |
| AISquad | 402 | AI |
| PatrolPath | 343 | AI |
| AreaActivate | 321 | Logic |
| EditBoneObj | 301 | Geometry |
| RotateAttachment | 250 | Geometry |
| EditVariable | 219 | Logic |
| AIGraph | 170 | AI |
| SoundGenerator | 162 | Audio |
| ExplodeObject | 159 | Interactive |
| Switch | 156 | Interactive |
| CutScene | 149 | Cutscenes |
| SCamera | 124 | Interactive |
| TerrainMaterial | 122 | Terrain |
| SplinePathDynCubeObj | 119 | Paths |
| SplinePathGuideQTask | 119 | Paths |
| ComputerHilight | 113 | UI |
| Forest | 104 | Vegetation |
| GenericTBA | 85 | Interactive |
| DirlightKeyframe | 83 | Lighting |
| SpawnArea | 81 | Multiplayer |
| LensflareItem | 77 | Lighting |
| GunPickup | 74 | Items |
| LevelTimer | 60 | Logic |
| SplineObj | 54 | Geometry |
| TerrainMap | 48 | Terrain |
| Fence | 48 | Geometry |
| WaterLayer | 45 | Water |
| Terminal | 41 | Interactive |
| AIStationaryGunHolder | 41 | AI |
| GlobalLightKeyframe | 38 | Lighting |
| DefineComputerObjective | 36 | UI |
| FlatSkyLayer | 34 | Sky |
| Water | 24 | Water |
| Lensflare | 24 | Lighting |
| Other (29 types) | ≤23 each | Various |

## Declarations Reference

All 88 object types declared via `Task_DeclareParameters`. Grouped by category.

---

### Terrain

#### Terrain (14 params)

Root terrain object. One per level (23 total across SP + MP).

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World origin (3 floats) |
| 2 | World width | Real32 | Terrain extent X in engine units |
| 3 | World height | Real32 | Terrain extent Y in engine units |
| 4 | Detail | Real32 | LOD detail factor |
| 5 | Adaption | Real32 | LOD adaption factor |
| 6 | Brush size | Real32 | Editor brush size |
| 7 | Brush power | Real32 | Editor brush power |
| 8 | Shadow samples | Int32 | Shadow ray sample count |
| 9 | Shadow spread | Real32 | Shadow softness |
| 10 | Minimum brush size | Real32 | Editor minimum brush |
| 11 | Maximum brush size | Real32 | Editor maximum brush |
| 12 | Minimum brush power | Real32 | Editor minimum power |
| 13 | Maximum brush power | Real32 | Editor maximum power |
| 14 | Number of brushes | Int32 | Editor brush count |

Children: `TerrainMap`, `TerrainMaterial`.

#### TerrainMap (8 params)

Heightmap tile reference. Typically 2 per level (low-res + hi-res).

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | ID | Int32 | Map index (0 = low-res, 1+ = hi-res) |
| 2 | Map width | Int32 | Heightmap grid columns |
| 3 | Map height | Int32 | Heightmap grid rows |
| 4 | Position | ObjectPos | World position of map origin (3 floats) |
| 5 | World width | Real32 | Map coverage in world X |
| 6 | World height | Real32 | Map coverage in world Y |
| 7 | Soften edge size | Real32 | Edge blending distance |
| 8 | DEM File name | String256 | Source DEM file (usually empty in compiled data) |

Links to external files: `heightmaps/heightmapNNN.thm`, `.tmm`, `.tlm` (via heightmaps.res).

#### TerrainMaterial (7 params)

Terrain texture layer. 3–6 per level.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | ID | Int32 | Material slot index (0–7) |
| 2 | Game material | Int32 | Physics material ID (footstep sounds etc.) |
| 3 | Texture | String256 | Main texture path (e.g. `MISSION:textures/k_rock.jpg`) |
| 4 | Detail texture | String256 | Detail/tiling texture path |
| 5 | Texture scale | Real32 | Main texture UV scale |
| 6 | Detail texture scale | Real32 | Detail texture UV scale |
| 7 | Mapping style | Int32 | UV projection mode |

---

### Geometry

#### EditRigidObj (6 params)

Static rigid prop — the most common object type (8,636 instances).

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Orientation | Real32x9 | Rotation (3 floats: alpha, beta, gamma in radians) |
| 3 | Model | String16 | Model ID (e.g. `600_12_1`) referencing a `.mef` file |
| 4 | RenderGroup | Int32 | Render group/priority |
| 5 | Protect from shadows | bool8 | Exclude from shadow casting |
| 6 | Excluded from clipping against portals | bool8 | Portal culling override |

#### EditBoneObj (11 params)

Animated skeletal object (flags, characters, machinery).

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Orientation | Real32x9 | Rotation (3 floats) |
| 3 | Loop animation list | bool8 | Loop animations |
| 4 | Use spline interpolation | bool8 | Smooth animation interpolation |
| 5 | Model | String16 | Model ID |
| 6 | Blinking | bool8 | Character blinking enabled |
| 7 | WeaponModel | String16 | Attached weapon model |
| 8 | WeaponModel Expression | VarString | Runtime weapon model expression |
| 9 | Animation list | VarString | Animation sequence names |
| 10 | Time factor | Real32 | Animation speed multiplier |
| 11 | Transition time | Real32 | Blend time between animations |

#### Building (4 params)

Building with interior. Affects ambient lighting when player is inside.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Orientation | Real32x9 | Rotation (3 floats) |
| 3 | Model | String16 | Model ID |
| 4 | Inside ambient | RGB | Ambient light color when inside (3 floats) |

#### Fence (5 params)

Fence segment — can be climbable or electrified.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Gamma | Angle | Y-axis rotation in radians |
| 3 | Model | String16 | Model ID |
| 4 | Climbable | bool8 | Player can climb over |
| 5 | Electric Expression | VarString | Expression controlling electrification |

#### RotateAttachment (5 params)

Rotating sub-object (helicopter rotors, radar dishes). Always a child of another object.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | AlphaRotationSpeed | Real32 | Rotation speed around X axis (rad/s) |
| 2 | BetaRotationSpeed | Real32 | Rotation speed around Y axis |
| 3 | GammaRotationSpeed | Real32 | Rotation speed around Z axis |
| 4 | Attachment model | String16 | Model to attach |
| 5 | Attachment model instance | Int32 | Instance index for model |

#### Ladder (3 params)

Climbable ladder.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Model | String16 | Model ID |
| 2 | Position | ObjectPos | World position (3 floats) |
| 3 | Orientation | Real32x9 | Rotation (3 floats) |

#### Floor (2 params)

Floor plane for multi-story buildings (used with Lift).

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Orientation | Real32x9 | Rotation (3 floats) |

#### ConveyorBelt (8 params)

Moving surface (conveyor belts in factory levels).

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Orientation | Real32x9 | Rotation (3 floats) |
| 3 | Model | String16 | Model ID |
| 4 | RenderGroup | Int32 | Render group |
| 5 | Protect from shadows | bool8 | Shadow exclusion |
| 6 | Excluded from clipping against portals | bool8 | Portal culling override |
| 7 | X Speed | Real32 | Conveyor speed X |
| 8 | Y Speed | Real32 | Conveyor speed Y |

---

### Spline Objects

#### SplineObj (8 params)

Spline-based geometry (roads, pipelines, rails). Defines the spline container.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Linear Segments | bool8 | Use linear interpolation |
| 2 | Display waypoints | bool8 | Editor display flag |
| 3 | Snap Length | bool8 | Snap segment length |
| 4 | Automatic Orientation | bool8 | Auto-orient segments along spline |
| 5 | Number of Matrices / Segment | Int32 | Tessellation quality |
| 6 | Collision LOD | Int32 | Collision mesh detail |
| 7 | Position | Real32x3 | Spline origin (3 floats) |
| 8 | Gamma Orientation | Angle | Base Y-rotation |

Children: `SplineObjWaypoint`.

#### SplineObjWaypoint (8 params)

Waypoint along a SplineObj.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Orientation | Real32x9 | Rotation at waypoint (3 floats) |
| 2 | Position | ObjectPos | World position (3 floats) |
| 3 | Waypoint Model | String16 | Editor marker model |
| 4 | Segment Model | String16 | Geometry model for segment to next waypoint |
| 5 | NumAreas | Int32 | Number of collision areas |
| 6 | Align | bool8 | Align to terrain |
| 7 | Flip | bool8 | Flip segment orientation |
| 8 | Automatic Orientation | bool8 | Auto-orient this waypoint |

---

### Spline Paths (Dynamic)

Used for vehicle/camera paths along splines (cutscene helicopters, trains).

#### SplinePathDynCubeObj (1 param)

Dynamic spline path container.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Show in editor | bool8 | Editor visibility |

Children: `SplinePathNodeQTask`, `SplinePathGuideQTask`.

#### SplinePathNodeQTask (7 params)

Node along a dynamic spline path.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Orientation | Real32x9 | Rotation (3 floats) |
| 3 | Use Free Orientation | bool8 | Override auto-orientation |
| 4 | Speed (KMH) | Real32 | Speed at this node in km/h |
| 5 | Time from start (Sec) | Real32 | Timestamp for this node |
| 6 | Tangent | Real64x3 | Spline tangent vector (3 doubles) |
| 7 | UseComputedTangent | bool8 | Auto-compute tangent |

#### SplinePathGuideQTask (5 params)

Links a spline path to an object that follows it.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Path ID | Int32 | Task ID of `SplinePathDynCubeObj` |
| 2 | RigidObject ID | Int32 | Task ID of object to move along path |
| 3 | Looping | bool8 | Loop the path |
| 4 | RunFromStart | bool8 | Start moving immediately |
| 5 | Startposition | Real32 | Starting position along spline (0–1) |

---

### Lighting

#### GlobalLight (8 params)

Global radiosity and color filter settings. One per level.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Radiosity intensity  | Real32 | Global indirect light strength |
| 2 | Radiosity gamma | Real32 | Indirect light gamma correction |
| 3 | Radiosity fadeout | Real32 | Indirect light distance fadeout |
| 4 | Radiosity dirlight softness | Real32 | Directional light shadow softness |
| 5 | Radiosity terrain shadows | bool8 | Enable terrain shadow baking |
| 6 | Texture filter ambient colour | RGB | Ambient color filter (3 floats) |
| 7 | Texture filter scale | RGB | Color scale filter (3 floats) |
| 8 | Texture filter gamma | Real32 | Gamma correction |

Children: `GlobalLightKeyframe`.

#### GlobalLightKeyframe (25 params)

Time-of-day lighting keyframe. Defines ambient, fog, and sky colors for terrain and 4 object categories.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Link All Sliders | PushButton | Editor action (always FALSE) |
| 2 | Ambient color terrain | RGB | Terrain ambient (3 floats) |
| 3 | Fog color terrain | RGB | Terrain fog color (3 floats) |
| 4 | Fog density terrain | Real32 | Terrain fog density |
| 5 | Link setting terrain | Int32 | Linked setting index |
| 6 | Ambient color object category 1 | RGB | Category 1 ambient (3 floats) |
| 7 | Fog color object category 1 | RGB | Category 1 fog (3 floats) |
| 8 | Fog density object category 1 | Real32 | Category 1 fog density |
| 9 | Link setting object category 1 | Int32 | Category 1 link |
| 10 | Ambient color object category 2 | RGB | Category 2 ambient (3 floats) |
| 11 | Fog color object category 2 | RGB | Category 2 fog (3 floats) |
| 12 | Fog density object category 2 | Real32 | Category 2 fog density |
| 13 | Link setting object category 2 | Int32 | Category 2 link |
| 14 | Ambient color object category 3 | RGB | Category 3 ambient (3 floats) |
| 15 | Fog color object category 3 | RGB | Category 3 fog (3 floats) |
| 16 | Fog density object category 3 | Real32 | Category 3 fog density |
| 17 | Link setting object category 3 | Int32 | Category 3 link |
| 18 | Ambient color object category 4 | RGB | Category 4 ambient (3 floats) |
| 19 | Fog color object category 4 | RGB | Category 4 fog (3 floats) |
| 20 | Fog density object category 4 | Real32 | Category 4 fog density |
| 21 | Link setting object category 4 | Int32 | Category 4 link |
| 22 | Sky color | RGB | Sky color (3 floats) |
| 23 | Water ambient | RGB | Water ambient color (3 floats) |
| 24 | Water color | RGB | Water body color (3 floats) |
| 25 | Time | Real32 | Keyframe time |

#### Dirlight (8 params)

Directional light (sun/moon). One per level.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Affects terrain | bool8 | Light affects terrain |
| 2 | Affects objects | bool8 | Light affects objects |
| 3 | Hard shadows | bool8 | Use hard shadow edges |
| 4 | Radiosity intensity | Real32 | Indirect light contribution |
| 5 | Shadow intensity | Real32 | Shadow darkness (0 = invisible, 1 = full) |
| 6 | Sun/Moon Texture | String32 | Sun/moon billboard texture |
| 7 | Sun/Moon Size | Real32 | Billboard size |
| 8 | Sun/Moon Colored | bool8 | Apply directional light color to sun billboard |

Children: `DirlightKeyframe`.

#### DirlightKeyframe (5 params)

Sun/moon direction and color for a time-of-day keyframe.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Beta | Angle | Elevation angle (radians) |
| 2 | Gamma | Angle | Azimuth angle (radians) |
| 3 | Front Color | RGB | Color facing the light (3 floats) |
| 4 | Back Color | RGB | Color opposite the light (3 floats) |
| 5 | Time | Real32 | Keyframe time |

#### Lensflare (3 params)

Lens flare attached to a directional light.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Direction | Real32x3 | Flare direction vector (3 floats) |
| 2 | Color | RGB | Flare tint (3 floats) |
| 3 | Dirlight QTask ID | Int32 | Task ID of parent Dirlight |

Children: `LensflareItem`.

#### LensflareItem (5 params)

Individual element in a lens flare chain.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Color | RGB | Element color (3 floats) |
| 2 | Position | RangeReal32 | Position along flare line (0 = center, 1 = edge) |
| 3 | Size | Real32 | Element size |
| 4 | SpriteIndex | Int32 | Sprite atlas index |
| 5 | Mirror? | bool8 | Mirror the element |

#### LightmapInfo (3 params)

Lightmap baking parameters. Attached as child to objects needing baked lighting.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Hemicube resolution | Int32 | Bake resolution |
| 2 | Indoors ambient light | RGB | Indoor ambient (3 floats) |
| 3 | Filename | String16 | Lightmap output filename |

---

### Sky & Weather

#### FlatSky (11 params)

Sky dome with gradient colors and fog.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Fog Amount | Real32 | Fog density |
| 2 | Z Pos | Real32 | Sky plane Z height |
| 3 | Distance | Real32 | Sky render distance |
| 4 | Fog Color | RGB | Fog tint (3 floats) |
| 5 | SkyDome Snap Colours | bool8 | Snap gradient to solid bands |
| 6 | SkyDome Angle | Degrees | Dome coverage angle |
| 7 | SkyDome Top Colour | RGB | Zenith color (3 floats) |
| 8 | SkyDome Middle Colour 1 | RGB | Upper horizon (3 floats) |
| 9 | SkyDome Middle Colour 2 | RGB | Lower horizon (3 floats) |
| 10 | SkyDome Bottom Colour 1 | RGB | Near-ground color 1 (3 floats) |
| 11 | SkyDome Bottom Colour 2 | RGB | Near-ground color 2 (3 floats) |

Children: `FlatSkyLayer`.

#### FlatSkyLayer (6 params)

Cloud/sky texture layer.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Texture File Name | String256 | Cloud texture path |
| 2 | Scale | Real32 | Texture scale |
| 3 | X Speed | Real32 | Scroll speed X |
| 4 | Y Speed | Real32 | Scroll speed Y |
| 5 | Alpha | Real32 | Layer opacity |
| 6 | Color | RGB | Layer tint (3 floats) |

#### FlatSkyKeyframe (6 params)

Sky gradient keyframe (rare — only 1 level uses this).

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | SkyDome Top Colour | RGB | Zenith color (3 floats) |
| 2 | SkyDome Middle Colour 1 | RGB | Upper horizon (3 floats) |
| 3 | SkyDome Middle Colour 2 | RGB | Lower horizon (3 floats) |
| 4 | SkyDome Bottom Colour 1 | RGB | Near-ground 1 (3 floats) |
| 5 | SkyDome Bottom Colour 2 | RGB | Near-ground 2 (3 floats) |
| 6 | Time | Real32 | Keyframe time |

#### Wind (10 params)

Wind simulation affecting forests.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Main Frequency | Real32 | Base wind oscillation frequency |
| 2 | Gust Frequency | Real32 | Gust oscillation frequency |
| 3 | Main Amplitude | Real32 | Base wind strength |
| 4 | Gust Amplitude | Real32 | Gust strength |
| 5 | Constant Strength | Real32 | Constant wind force |
| 6 | Gust Lower Clamp | Real32 | Minimum gust value |
| 7 | Gust Upper Clamp | Real32 | Maximum gust value |
| 8 | Phase shift between morph channels | Real32 | Phase offset for variety |
| 9 | Wind direction | Angle | Wind direction in radians |
| 10 | Preview | bool8 | Editor preview flag |

#### RainEffect (7 params)

Rain or snow particle effect.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Is Rain | bool8 | TRUE = rain, FALSE = snow |
| 2 | Traceline start | Real32 | Trace start height |
| 3 | Traceline end | Real32 | Trace end height |
| 4 | Rain Colour | RGB | Particle color (3 floats) |
| 5 | Rain Alpha | Real32 | Particle opacity |
| 6 | Density | Int32 | Particle count |
| 7 | Is Active | VarString | Activation expression |

---

### Vegetation

#### Forest (18 params)

Vegetation patch. Links to `forest_<id>.dat` for individual tree positions.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Patch center (3 floats) |
| 2 | Model | String16 | Tree/bush model ID |
| 3 | Area size | Real32 | Patch radius |
| 4 | Randomize area | PushButton | Editor action (always FALSE) |
| 5 | Update | PushButton | Editor action (always FALSE) |
| 6 | Calculate light | PushButton | Editor action (always FALSE) |
| 7 | Density of trees [1/m^2] | Real32 | Trees per square meter |
| 8 | Random rotation range | Real32 | Max random rotation |
| 9 | Random X-scale range | Real32 | Random scale variance X |
| 10 | Random Y-scale range  | Real32 | Random scale variance Y |
| 11 | Random Z-scale range | Real32 | Random scale variance Z |
| 12 | Isotropic scaling | bool8 | Uniform scaling on all axes |
| 13 | Number of trees | Int32 | Total tree count |
| 14 | Brush size (m) | Real32 | Editor placement brush size |
| 15 | Brush draw/delete | bool8 | Editor brush mode |
| 16 | View cutoff (m) (limited by object lod settings) | Real32 | LOD visibility distance |
| 17 | Normalize objects to ground | bool8 | Snap trees to terrain height |
| 18 | Number of LODs affected by the wind | Int32 | Wind-animated LOD levels |

#### BirdFlock (4 params)

Bird flock ambient animation.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Flock center (3 floats) |
| 2 | Radius (meter) | Real32 | Flight radius |
| 3 | Cutoff Distance (meter) | Real32 | LOD visibility distance |
| 4 | Individuals (max 100) | Int32 | Number of birds |

---

### Water

#### Water (30 params)

Water plane with reflection and wave simulation.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Center position (3 floats) |
| 2 | Size | Real32 | Water plane size |
| 3 | Detail | Real32 | Tessellation detail |
| 4 | Alpha | Real32 | Water opacity |
| 5 | UV Scale | Real32 | Texture tiling |
| 6 | Env Scale | Real32 | Environment map scale |
| 7 | Fadeout | Real32 | Edge fadeout distance |
| 8 | Texture | String256 | Water surface texture path |
| 9 | Envmap | String256 | Environment reflection texture path |
| 10 | Diffuse Color | RGB | Water diffuse color (3 floats) |
| 11 | Specular Color | RGB | Water specular color (3 floats) |
| 12 | Absorption length (depth) (m) | Real32 | Depth absorption distance |
| 13 | Max Reflection Angle (cos) | Real32 | Reflection angle limit |
| 14 | Cubemap | bool8 | Use cubemap reflections |
| 15 | Plain env. map file | String16 | Flat environment map |
| 16 | Resolution of the environmental map | Int32 | Env map resolution |
| 17 | Camera position | ObjectPos | Env map camera pos (3 floats) |
| 18 | Camera orientation | Real32x9 | Env map camera rotation (3 floats) |
| 19 | FOV | Real32 | Env map camera FOV |
| 20 | Sky | bool8 | Reflect sky |
| 21 | Terrain | bool8 | Reflect terrain |
| 22 | Rigid objects | bool8 | Reflect rigid objects |
| 23 | Forests | bool8 | Reflect forests |
| 24 | Spline objects | bool8 | Reflect spline objects |
| 25 | Rebuild env. map | PushButton | Editor action (always FALSE) |
| 26 | Environmental map number | Int32 | Env map index |
| 27 | Save env. map | PushButton | Editor action (always FALSE) |
| 28 | Resource list | String16 | Resource list for env maps |
| 29 | Make resource file | PushButton | Editor action (always FALSE) |
| 30 | Environmental map index | VarString | Runtime env map selection |

Children: `WaterLayer`.

#### WaterLayer (4 params)

Wave animation layer (typically 1 per Water).

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Frequency | Real32 | Wave frequency |
| 2 | Amplitude | Real32 | Wave height |
| 3 | Speed | Real32 | Wave speed |
| 4 | Angle | Real32 | Wave direction |

---

### AI & Enemies

#### AIGraph (13 params)

Navigation graph reference. Links to `graphs/graph<id>.dat` and `graphs/graphcover<id>.dat`.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Graph position | ObjectPos | Graph world origin (3 floats) |
| 2 | Relative | bool8 | Positions relative to origin |
| 3 | Update | PushButton | Editor action (always FALSE) |
| 4 | Graphdata | Graph | Node count, capacity, edge count |
| 5 | Node cover midoffset | Real64 | Cover check mid-height offset |
| 6 | Node cover topoffset | Real64 | Cover check top-height offset |
| 7 | Max height difference between linked nodes | Real64 | Max elevation change per link |
| 8 | Width of node links | Real64 | Link corridor width |
| 9 | Link maximum distance to ground | Real64 | Max gap under a link |
| 10 | Max Link-length | Real64 | Maximum link distance |
| 11 | Use precise link method (SLOW!) | bool8 | Use raycast-based linking |
| 12 | Precise link method step value | Real64 | Raycast step size |
| 13 | Update & Display CoverInfo | bool8 | Editor display flag |

#### AISquad (8 params)

Squad that groups soldiers with shared behavior. Links to `ai/Squad_<id>.qvm`.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Formation Distance | Real32 | Spacing between squad members |
| 2 | SquadType | EnumInt32 | Squad behavior type (e.g. `AIType_Defensive`) |
| 3 | AlarmTriggerID | Int32 | Task ID of alarm trigger (-1 = none) |
| 4 | AlarmControlID | Int32 | Task ID of alarm control (-1 = none) |
| 5 | StationaryGunID | Int32 | Task ID of stationary gun (-1 = none) |
| 6 | Max Run Distance Alarm/Gun (m) | Real32 | Max distance to run to alarm/gun |
| 7 | TargetTimeout (sec) | Int32 | Seconds before losing target |
| 8 | TenseTimeout (sec) | Int32 | Seconds in tense state after combat |

Children: `HumanSoldier`.

#### HumanSoldier (7 params)

Enemy soldier placement.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Spawn position (3 floats) |
| 2 | Gamma | Angle | Facing direction (radians) |
| 3 | Model | String16 | Character model ID |
| 4 | Team | Int32 | Team index (0 = player, 1 = enemy) |
| 5 | Weapon | VarString | Weapon loadout script |
| 6 | Bone Heirachy | Int32 | Skeleton type |
| 7 | Stand Animation | Int32 | Idle animation index |

Children: `HumanAI`.

#### HumanAI (3 params)

AI behavior assignment for a soldier. Links to `ai/<id>.qvm`.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | AI Type | String32 | AI type constant (e.g. `HUMANAI_TYPE_C1_NORMAL_SOLDIER`) |
| 2 | Anim Type | String32 | Animation set (e.g. `HUMANAI_ANIMTYPE_SOLDIER_RIFLE`) |
| 3 | Graph ID | Int32 | Task ID of AIGraph to use for navigation |

#### PatrolPath (1 param)

Patrol route definition. Contains ordered `PatrolPathCommand` children.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Graph ID | Int32 | Task ID of AIGraph this path uses |

Children: `PatrolPathCommand`.

#### PatrolPathCommand (5 params)

Single step in a patrol path.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Command | Int32 | Command type (3=run to node, 6=end script, 7=quit) |
| 2 | Command Parameter | Int32 | Target graph node ID |
| 3 | eNodeId | Int32 | Current node ID |
| 4 | Command Expression | VarString | Conditional expression |
| 5 | Command Text | String32 | Description text |

#### AIStationaryGunHolder (19 params)

AI-controlled mounted gun emplacement.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Orientation | Real32x9 | Rotation (3 floats) |
| 3 | Holder model | String32 | Gun mount model |
| 4 | Viewcone Alpha | Degrees | Vertical view angle |
| 5 | Viewcone Gamma | Degrees | Horizontal view angle |
| 6 | Viewcone Length | Real32 | Detection range |
| 7 | On expression | VarString | Activation expression |
| 8 | Team expression | VarString | Team assignment expression |
| 9 | Barrel model | String32 | Gun barrel model |
| 10 | Rotationsound | String32 | Turret rotation sound |
| 11 | Min Alpha (deg) | Real32 | Min vertical angle |
| 12 | Max Alpha (deg) | Real32 | Max vertical angle |
| 13 | Max Gamma (deg) | Real32 | Max horizontal angle |
| 14 | Ammo | Int32 | Ammunition count |
| 15 | Alpha speed (deg/sec) | Real32 | Vertical rotation speed |
| 16 | Gamma speed (deg/sec) | Real32 | Horizontal rotation speed |
| 17 | Beta speed (deg/sec) | Real32 | Roll speed |
| 18 | Accuracy (0..1) | Real32 | Aim accuracy |
| 19 | WeaponID | String32 | Weapon type identifier |

---

### Player

#### HumanPlayer (10 params)

Player spawn point and initial loadout. One per single-player level.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Spawn position (3 floats) |
| 2 | Gamma | Angle | Facing direction (radians) |
| 3 | Model | String16 | Player character model |
| 4 | Team | Int32 | Team index (always 0) |
| 5 | Weapon | VarString | Weapon loadout script |
| 6 | 1st Person Model | String16 | First-person arms model |
| 7 | Visibility Gamma | Real32 | Stealth visibility parameter |
| 8 | Visibility Minimum | Real32 | Min visibility |
| 9 | Visibility Maximum | Real32 | Max visibility |
| 10 | Carry over weapons from previous mission | bool8 | Inherit weapons from last level |

Children: `HumanPlayerInput`.

#### HumanPlayerInput (2 params)

Player input configuration.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Mapcomputer on expression | VarString | Expression to enable map computer |
| 2 | Mapcomputer unavailable expression | VarString | Expression when map is unavailable |

---

### Interactive Objects

#### Door (23 params)

Door with open/close animation and optional lock-picking.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position start | ObjectPos | Closed position (3 floats) |
| 2 | Position stop X | Real32 | Open position X offset |
| 3 | Position stop Y | Real32 | Open position Y offset |
| 4 | Position slider | Real32 | Current slide position |
| 5 | Orientation | Real32x9 | Rotation (3 floats) |
| 6 | Model | String16 | Door model ID |
| 7 | Max angle | Real32 | Maximum swing angle |
| 8 | Open time | Real32 | Time to fully open (seconds) |
| 9 | Pickable | bool8 | Can be lock-picked |
| 10 | Open Both Ways | bool8 | Swings in both directions |
| 11 | Pick lock time (s) | Real32 | Lock-picking duration |
| 12 | Locked expression | VarString | Lock state expression |
| 13 | Open door expression | VarString | Trigger to open |
| 14 | Close door expression | VarString | Trigger to close |
| 15 | StopOnCollision | bool8 | Stop on collision with player |
| 16 | Link up to a portal | bool8 | Connected to building portal |
| 17 | Delta scale factor | Real32 | Animation speed factor |
| 18 | Open sound | String16 | Sound when opening |
| 19 | Close sound | String16 | Sound when closing |
| 20 | Move sound | String16 | Sound while moving |
| 21 | Begin open sound | String16 | Sound at open start |
| 22 | Begin close sound | String16 | Sound at close start |
| 23 | Activate Sound | String32 | Interaction sound |

#### Switch (12 params)

Interactable switch with on/off states and separate models.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Orientation | Real32x9 | Rotation (3 floats) |
| 3 | Active | VarString | Activation expression |
| 4 | Initial on | bool8 | Starting state |
| 5 | Sound | String16 | Toggle sound |
| 6 | On model | String16 | Model when on |
| 7 | On pressed model | String16 | Model when on + pressed |
| 8 | Off model | String16 | Model when off |
| 9 | Off pressed model | String16 | Model when off + pressed |
| 10 | Destroyed model | String16 | Model when destroyed |
| 11 | Destructable | bool8 | Can be destroyed |
| 12 | Click to select sprite | DropDownCombo | Interaction UI sprite |

#### GenericTBA (22 params)

Generic "To Be Activated" object — hackable panels, code pads, etc.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Orientation | Real32x9 | Rotation (3 floats) |
| 3 | Model | String16 | Model ID |
| 4 | Destroyed model | String16 | Model after destruction |
| 5 | Damage scale | Real32 | Damage multiplier |
| 6 | Explosion radius | Real32 | Explosion range |
| 7 | Explosion falloff radius | Real32 | Damage falloff range |
| 8 | Explosion damage scale | Real32 | Explosion damage multiplier |
| 9 | Explosion delay | Real32 | Delay before explosion |
| 10 | Explosion fragments | Int32 | Fragment count |
| 11 | Explosion fireballs | Int32 | Fireball count |
| 12 | Explosion expression | VarString | Trigger on explosion |
| 13 | Explosion sound | String16 | Explosion sound effect |
| 14 | Activate Offset X | Real64 | Interaction point offset X |
| 15 | Activate Offset Y | Real64 | Interaction point offset Y |
| 16 | Activate Offset Z | Real64 | Interaction point offset Z |
| 17 | Explodable | bool8 | Can be blown up |
| 18 | Active | VarString | Activation expression |
| 19 | Activate Anim | String32 | Player animation on use |
| 20 | Activate Time (s) | Real32 | Use duration |
| 21 | Click to select sprite | DropDownCombo | Interaction UI sprite |
| 22 | Activate Sound | String32 | Interaction sound |

#### ExplodeObject (13 params)

Destructible object (barrels, crates).

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Orientation | Real32x9 | Rotation (3 floats) |
| 3 | Model | String16 | Model ID |
| 4 | Destroyed model | String16 | Model after destruction |
| 5 | Damage scale | Real32 | Damage multiplier |
| 6 | Explosion radius | Real32 | Explosion range |
| 7 | Explosion falloff radius | Real32 | Damage falloff range |
| 8 | Explosion damage scale | Real32 | Explosion damage multiplier |
| 9 | Explosion delay | Real32 | Delay before explosion |
| 10 | Explosion fragments | Int32 | Fragment count |
| 11 | Explosion fireballs | Int32 | Fireball count |
| 12 | Explosion expression | VarString | Trigger on explosion |
| 13 | Explosion sound | String16 | Explosion sound effect |

#### Terminal (16 params)

Hackable computer terminal.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Orientation | Real32x9 | Rotation (3 floats) |
| 3 | Model | String16 | Model ID |
| 4 | Destroyed model | String16 | Model after destruction |
| 5 | Damage scale | Real32 | Damage multiplier |
| 6 | Explosion radius | Real32 | Explosion range |
| 7 | Explosion falloff radius | Real32 | Damage falloff range |
| 8 | Explosion damage scale | Real32 | Explosion damage |
| 9 | Explosion delay | Real32 | Delay before explosion |
| 10 | Explosion fragments | Int32 | Fragment count |
| 11 | Explosion fireballs | Int32 | Fireball count |
| 12 | Explosion expression | VarString | Trigger on explosion |
| 13 | Explosion sound | String16 | Explosion sound |
| 14 | Active | VarString | Activation expression |
| 15 | Hack Time (s) | Real32 | Hacking duration |
| 16 | Activate Sound | String32 | Interaction sound |

#### AlarmControl (18 params)

Alarm control panel — can be hacked to disable alarms.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Orientation | Real32x9 | Rotation (3 floats) |
| 3 | Model | String16 | Model ID |
| 4 | Destroyed model | String16 | Model after destruction |
| 5 | Damage scale | Real32 | Damage multiplier |
| 6 | Explosion radius | Real32 | Explosion range |
| 7 | Explosion falloff radius | Real32 | Damage falloff range |
| 8 | Explosion damage scale | Real32 | Explosion damage |
| 9 | Explosion delay | Real32 | Delay before explosion |
| 10 | Explosion fragments | Int32 | Fragment count |
| 11 | Explosion fireballs | Int32 | Fireball count |
| 12 | Explosion expression | VarString | Trigger on explosion |
| 13 | Explosion sound | String16 | Explosion sound |
| 14 | Active | VarString | Active state expression |
| 15 | Hack Time (s) | Real32 | Hacking duration |
| 16 | Activate Sound | String32 | Interaction sound |
| 17 | Trigger Expression | VarString | Alarm trigger condition |
| 18 | Alarm Expression | VarString | Alarm active expression |

#### SCamera (17 params)

Security camera with detection cone.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Holder Position | ObjectPos | Mount position (3 floats) |
| 2 | Holder Gamma | Angle | Mount rotation |
| 3 | Holder Model | String16 | Mount model |
| 4 | Camera Visible on Computer | bool8 | Visible on map computer |
| 5 | Camera Alpha | Angle | Camera vertical angle |
| 6 | Camera Gamma | Angle | Camera horizontal angle |
| 7 | Camera Model | String16 | Camera model |
| 8 | Camera Destroyed Model | String16 | Model when destroyed |
| 9 | Rotate Gamma Left(d) | Int16 | Left sweep limit (degrees) |
| 10 | Rotate Gamma Right(d) | Int16 | Right sweep limit (degrees) |
| 11 | Rotate Gamma Speed (d/s) | Int16 | Sweep speed (degrees/sec) |
| 12 | Gamma Delay (s) | Real32 | Pause at sweep ends |
| 13 | Viewcone Alpha (d) | Int16 | Detection cone vertical half-angle |
| 14 | Viewcone Gamma (d) | Int16 | Detection cone horizontal half-angle |
| 15 | Viewcone length (m) | Real32 | Detection range (meters) |
| 16 | On Expression | VarString | Camera active expression |
| 17 | Max damage factor | Real32 | Damage threshold |

#### Lift (12 params)

Elevator moving between floors.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Model | String16 | Elevator model |
| 2 | Start floor task ID | Int32 | Task ID of starting Floor |
| 3 | Max speed | Real32 | Maximum movement speed |
| 4 | Speed inertia | Real32 | Acceleration/deceleration |
| 5 | Floor down | VarString | Move down expression |
| 6 | Floor up | VarString | Move up expression |
| 7 | Can start | VarString | Movement allowed expression |
| 8 | Start sound | String32 | Sound at departure |
| 9 | Stop sound | String32 | Sound at arrival |
| 10 | Move sound | String32 | Sound while moving |
| 11 | Start Position | ObjectPos | Initial position (3 floats) |
| 12 | Start Orientation | Real32x9 | Initial rotation (3 floats) |

Children: `Floor`.

#### StationaryGun (8 params)

Player-usable mounted weapon.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Orientation | Real32x9 | Rotation (3 floats) |
| 3 | Holder model | String32 | Gun mount model |
| 4 | Weapon ID | String32 | Weapon type |
| 5 | Max up angle | Degrees | Max upward aim |
| 6 | Max down angle | Degrees | Max downward aim |
| 7 | Max sideways angle | Degrees | Max horizontal aim |
| 8 | Ammo | Int32 | Ammunition count |

#### MineField (12 params)

Proximity mine area.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Mine position (3 floats) |
| 2 | Explode | VarString | Detonation trigger expression |
| 3 | Explosion radius (meter) | Real32 | Blast radius |
| 4 | Explosion falloff radius (meter) | Real32 | Damage falloff |
| 5 | Explosion damage scale | Real32 | Damage multiplier |
| 6 | Explosion delay (seconds) | Real32 | Delay before detonation |
| 7 | Explosion fragments | Int32 | Fragment count |
| 8 | Explosion fireballs | Int32 | Fireball count |
| 9 | Explosion sound | String16 | Explosion sound |
| 10 | Explode close to task ID | Int32 | Chain-explode nearby object |
| 11 | Explosion delay between explosions (seconds) -1: explode once | Real32 | Chain delay |
| 12 | Snap explosion to ground | bool8 | Explosion at ground level |

#### Wire (4 params)

Climbable wire/zipline between two points.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Start position | ObjectPos | Start point (3 floats) |
| 2 | Stop position | ObjectPos | End point (3 floats) |
| 3 | Model | String16 | Wire model |
| 4 | Useable expression | VarString | Availability expression |

#### Cabinet (5 params)

Searchable storage cabinet.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Orientation | Angle | Y-rotation |
| 3 | Model | String16 | Model ID |
| 4 | Search Time (s) | Real32 | Time to search |
| 5 | Activate Sound | String32 | Interaction sound |

---

### Items & Pickups

#### GunPickup (4 params)

Weapon pickup.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Orientation | Real32x9 | Rotation (3 floats) |
| 3 | ID | EnumString32 | Weapon type ID |
| 4 | Respawn Time | String32 | Respawn delay (multiplayer) |

#### GenericPickup (3 params)

Generic item pickup (keycards, documents).

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Orientation | Real32x9 | Rotation (3 floats) |
| 3 | Model | String16 | Model ID |

---

### Vehicles

#### Car (24 params)

Vehicle with optional turret.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Orientation | Real32x9 | Rotation (3 floats) |
| 3 | Original Thrust | Real32 | Engine power |
| 4 | Speed | Real32x3 | Speed vector (3 floats) |
| 5 | Model | String16 | Vehicle model |
| 6 | Collision detection | bool8 | Enable collision |
| 7 | Force Z | bool8 | Force vertical position |
| 8 | Open door | VarString | Door open trigger |
| 9 | Can fire | VarString | Weapon fire condition |
| 10 | Play sound | VarString | Sound trigger |
| 11 | ViewCone Alpha (degrees) | Degrees | Turret vertical view |
| 12 | ViewCone Gamma (degrees) | Degrees | Turret horizontal view |
| 13 | ViewCone Length (meter) | Real32 | Turret detection range |
| 14 | Barrel model | String16 | Turret barrel model |
| 15 | Rotationsound | String16 | Turret rotation sound |
| 16 | Min Alpha (deg) | Real32 | Min barrel elevation |
| 17 | Max Alpha (deg) | Real32 | Max barrel elevation |
| 18 | Max Gamma (deg) | Real32 | Max barrel traverse |
| 19 | Ammo | Int32 | Ammunition count |
| 20 | Alpha speed (deg/sec) | Real32 | Vertical aim speed |
| 21 | Gamma speed (deg/sec) | Real32 | Horizontal aim speed |
| 22 | Beta speed (deg/sec) | Real32 | Roll speed |
| 23 | Accuracy | Real32 | Weapon accuracy |
| 24 | WeaponID | String32 | Weapon type |

#### CarAI (10 params)

AI driver for a vehicle.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Driver position (3 floats) |
| 2 | Orientation | Real32x9 | Driver orientation (3 floats) |
| 3 | Driver Model | String16 | Driver character model |
| 4 | Driving animation | String32 | Animation while driving |
| 5 | Idle animation | String32 | Animation when stopped |
| 6 | Death animation | String32 | Death animation |
| 7 | Driving expression | VarString | Drive condition |
| 8 | AI Type | String32 | AI behavior type |
| 9 | Graph ID | Int32 | Navigation graph task ID |
| 10 | Route ID | Int32 | Patrol route task ID |

#### Train (10 params)

Train on rails (follows SplineObj).

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | Real32 | Position along rail (0–1) |
| 2 | Original thrust | Real32 | Engine power |
| 3 | RailroadQTaskID | Int32 | Task ID of SplineObj (track) |
| 4 | Model | String256 | Train model |
| 5 | Acceleration | Real32 | Acceleration rate |
| 6 | MaxSpeed | Real32 | Maximum speed |
| 7 | Flip Direction | bool8 | Reverse on track |
| 8 | Displacement X | Real32 | Lateral offset from track |
| 9 | Displacement Z | Real32 | Vertical offset from track |
| 10 | Play Sound | VarString | Sound trigger expression |

---

### VFX & Particles

#### Smoke (26 params)

Particle emitter for smoke, fire, steam.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Emitter position (3 floats) |
| 2 | Alpha | Angle | Emission angle alpha |
| 3 | Gamma | Angle | Emission angle gamma |
| 4 | Number of Particles | Int32 | Max particle count |
| 5 | Radius | Real32 | Emission radius |
| 6 | Maximum Random Angle | Angle | Random spray angle |
| 7 | Minimum Velocity | Real32 | Min particle speed |
| 8 | Maximum Velocity | Real32 | Max particle speed |
| 9 | Colour | RGB | Particle color (3 floats) |
| 10 | Life Time | Real32 | Particle lifetime (seconds) |
| 11 | Fade Time | Real32 | Fade-out duration |
| 12 | Fade Mode | Int32 | Fade behavior (0–2) |
| 13 | Sprite index | Int32 | Particle sprite atlas index |
| 14 | Particle Size | Real32 | Base particle size |
| 15 | Particle Size Delta | Real32 | Size change over lifetime |
| 16 | Minimum Rotation Speed | Angle | Min spin speed |
| 17 | Maximum Rotation Speed | Angle | Max spin speed |
| 18 | Intensity | Real32 | Brightness multiplier |
| 19 | Gravity factor | Real32 | Gravity influence |
| 20 | Initial generate factor value | Real64 | Initial emission rate |
| 21 | Generate factor | VarString | Runtime emission rate expression |
| 22 | Move Particles | bool8 | Particles affected by wind |
| 23 | View cutoff | Real32 | LOD visibility distance |
| 24 | Do Damage | bool8 | Particles deal damage |
| 25 | Damage Per Sec | Real32 | Damage rate |
| 26 | Damage Radius (m) | Real32 | Damage area |

#### OverlayHolder (4 params)

HUD overlay (infrared markers, objective indicators).

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Visible expression | VarString | Normal visibility condition |
| 2 | Infrared expression | VarString | Infrared visibility condition |
| 3 | Overlay type | EnumInt32 | Overlay rendering mode |
| 4 | Show Distance | bool8 | Display distance to player |

---

### Cutscenes

#### CutScene (13 params)

Cutscene sequence container.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Camera origin (3 floats) |
| 2 | Orientation | Real32x9 | Camera orientation (3 floats) |
| 3 | Run | VarString | Play condition expression |
| 4 | Reset | VarString | Reset expression |
| 5 | Time delta (seconds) | VarString | Time offset expression |
| 6 | Start time (seconds) | Real32 | Start timestamp |
| 7 | Time scale | Real32 | Playback speed |
| 8 | Viewport height factor | Real32 | Letterbox factor (< 1 = letterboxed) |
| 9 | Viewport height factor fade in time | Real32 | Letterbox fade-in |
| 10 | Viewport height factor fade out time | Real32 | Letterbox fade-out |
| 11 | Time of day | Real32 | Override time-of-day |
| 12 | Start expression | VarString | Expression on start |
| 13 | Stop expression | VarString | Expression on end |

Children: `EditCamera`.

#### EditCamera (16 params)

Camera position/settings for cutscenes.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Camera position (3 floats) |
| 2 | Alpha | Angle | Pitch (radians) |
| 3 | Beta | Angle | Roll (radians) |
| 4 | Gamma | Angle | Yaw (radians) |
| 5 | FOV | Real32 | Field of view |
| 6 | Duration | Real32 | Hold duration (seconds) |
| 7 | Link task ID | Int32 | Task ID to follow (-1 = none) |
| 8 | Update link continously | bool8 | Track linked object |
| 9 | Target task ID | Int32 | Task ID to look at (-1 = none) |
| 10 | Update target continously | bool8 | Track target object |
| 11 | Smooth to next | bool8 | Smooth transition to next camera |
| 12 | Time of day (-1 means use default) | Real32 | Override time-of-day |
| 13 | FILTER | EnumString32 | Post-processing filter |
| 14 | Noise | Real32 | Film grain intensity |
| 15 | Filter color | RGB | Filter tint (3 floats) |
| 16 | Camera shake | Real32 | Camera shake intensity |

#### AnimTask (6 params)

Triggered animation on an object (rare — 1 level).

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Orientation | Real32x9 | Rotation (3 floats) |
| 3 | TargetID | Int32 | Task ID of target object |
| 4 | Run | VarString | Play expression |
| 5 | Initial run | bool8 | Play on level start |
| 6 | AnimData | AnimData | Animation data |

---

### Audio

#### AmbientArea (13 params)

3D ambient sound zone.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Zone center (3 floats) |
| 2 | Orientation | Real32x9 | Zone rotation (3 floats) |
| 3 | Size | Real64x3 | Zone dimensions (3 doubles) |
| 4 | Falloff | Real64 | Volume falloff distance |
| 5 | Min delay | Real64 | Minimum delay between plays |
| 6 | Random wait | Real64 | Random delay added |
| 7 | SoundDef | String256 | Sound definition name(s), comma-separated |
| 8 | Inside Buildings | bool8 | Audible inside buildings |
| 9 | Outside Buildings | bool8 | Audible outside buildings |
| 10 | On expression | VarString | Activation expression |
| 11 | Fade time | Real64 | Volume fade duration |
| 12 | Controlled By Music Volume Setting | bool8 | Use music volume slider |
| 13 | Noise level | Real32 | Alert level for AI |

#### SoundGenerator (0 params)

Empty container for sound children. No parameters.

#### SoundDefSoundEdit (11 params)

Sound definition with positional audio settings.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | SoundDef | String32 | Sound definition name |
| 2 | Sound | String32 | Sound file reference |
| 3 | Position | ObjectPos | World position (3 floats) |
| 4 | Volume | Real32 | Volume (0–1) |
| 5 | Falloff Begin | Real32 | Distance where falloff starts |
| 6 | Falloff End | Real32 | Distance where sound is silent |
| 7 | VolumeChannel | Int32 | Volume channel index |
| 8 | PitchChannel | Int32 | Pitch channel index |
| 9 | SoundChannel | Int32 | Sound channel index |
| 10 | MinPlayLength | Real32 | Minimum play duration |
| 11 | Looped | bool8 | Loop the sound |

---

### Logic & Scripting

#### Container (1 param)

Grouping container for organizing the scene tree.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Exclude from lightmaps | bool8 | Exclude children from lightmap baking |

#### ConditionalContainer (3 params)

Container that enables/disables children based on expressions.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Condition | VarString | Activation condition |
| 2 | Run at start | VarString | Expression on enable |
| 3 | Run at stop | VarString | Expression on disable |

#### AreaActivate (4 params)

Trigger zone that activates when a criteria is met.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Zone center (3 floats) |
| 2 | Orientation | Real32x9 | Zone rotation (3 floats) |
| 3 | Dimensions | Real32x3 | Zone size (3 floats) |
| 4 | Criteria | VarString | Activation criteria (e.g. `CRITERIA_HUMAN0`) |

#### EditVariable (4 params)

Script variable.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Editor position (3 floats) |
| 2 | Initial value | Int32 | Starting value |
| 3 | Add | VarString | Increment expression |
| 4 | Sub | VarString | Decrement expression |

#### LevelTimer (5 params)

Programmable timer.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Editor position (3 floats) |
| 2 | Orientation | Real32x9 | Editor rotation (3 floats) |
| 3 | On | VarString | Enable expression |
| 4 | Reset | VarString | Reset expression |
| 5 | Initial run | bool8 | Start running immediately |

#### MissionTimer (3 params)

Mission countdown timer.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Start Timer Expression | VarString | Start condition |
| 2 | Pause Timer Expression | VarString | Pause condition |
| 3 | Time In Seconds | Real32 | Countdown duration |

#### SequenceCommand (4 params)

Scripted action step.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | IsRun Expression | VarString | Check if running |
| 2 | Run Expression | VarString | Execute expression |
| 3 | IsNext Expression | VarString | Check if should advance |
| 4 | Next Expression | VarString | Advance expression |

#### StatusMessage (10 params)

On-screen message or subtitle.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Editor position (3 floats) |
| 2 | Orientation | Real32x9 | Editor rotation (3 floats) |
| 3 | Send | VarString | Trigger expression |
| 4 | Text | VarString | Text resource key(s), comma-separated |
| 5 | Sprite | String256 | Status sprite |
| 6 | Sound | String256 | Voice-over sound |
| 7 | Is send once | bool8 | Only display once |
| 8 | Cutscene message | bool8 | Show during cutscene |
| 9 | Duration | Real32 | Display duration (seconds) |
| 10 | Morph QTask IDs | String256 | Task IDs for lip-sync morph targets |

#### LevelFlow (7 params)

Mission win/lose conditions. One per level.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Editor position (3 floats) |
| 2 | Orientation | Real32x9 | Editor rotation (3 floats) |
| 3 | Start time | Real32 | Mission start time |
| 4 | Complete | VarString | Win condition expression |
| 5 | Failed | VarString | Lose condition expression |
| 6 | Interface timer enabled | bool8 | Show countdown timer |
| 7 | Max level play time | Real32 | Time limit (seconds, 0 = no limit) |

#### DiscardTask (3 params)

Editor discard marker (used to soft-delete objects without removing them).

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Position (3 floats) |
| 2 | Width | Real32 | Area width |
| 3 | Height | Real32 | Area height |

---

### UI & Objectives

#### DefineComputerObjective (33 params)

Mission objective definitions (up to 8 objectives per level).

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Objectives Valid | VarString | Expression for which objectives are valid |
| 2–5 | Objective 1 (Text Resource, Link To Position, Complete Expression, Failed Expression) | String32, Int32, VarString, VarString | Objective 1 definition |
| 6–9 | Objective 2 ... | ... | Objective 2 definition |
| 10–13 | Objective 3 ... | ... | Objective 3 definition |
| 14–17 | Objective 4 ... | ... | Objective 4 definition |
| 18–21 | Objective 5 ... | ... | Objective 5 definition |
| 22–25 | Objective 6 ... | ... | Objective 6 definition |
| 26–29 | Objective 7 ... | ... | Objective 7 definition |
| 30–33 | Objective 8 ... | ... | Objective 8 definition |

Each objective has: text resource key, position task ID to highlight, complete expression, failed expression.

#### ComputerHilight (9 params)

Map computer highlight marker (shows objectives/items on the in-game map).

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | World position (3 floats) |
| 2 | Hilight | VarString | Visibility expression |
| 3 | TaskID | String256 | Task ID to highlight |
| 4 | Click to select sprite | DropDownCombo | Map marker sprite |
| 5 | Marker mesh | String32 | 3D marker model |
| 6 | Marker color | String32 | Marker color name |
| 7 | Title text resource | String256 | Title text key |
| 8 | Info text resource | String256 | Description text key |
| 9 | Objective | Int32 | Objective index (-1 = none) |

#### ComputerPlan (1 param)

Map computer plan overlay image (rare — 1 level).

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Picture filename | String256 | Plan image path |

#### DefineComputerLimit (2 params)

Map computer bounds.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Map center (3 floats) |
| 2 | Quadrant Size (m) | Real32 | Map extent radius |

#### MissionScoreSettings (15 params)

Mission rating thresholds for 3 difficulty levels: Bodyguard, Secret Agent, IGI Operative.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1–3 | Time Required (secs) | Real32 ×3 | Max time per difficulty |
| 4–6 | Times Spotted Limit | Real32 ×3 | Max times spotted per difficulty |
| 7–9 | Number of Loads Allowed | Real32 ×3 | Max save loads per difficulty |
| 10–12 | Health Required (%) | Real32 ×3 | Min health at end per difficulty |
| 13–15 | Accuracy Required (%) | Real32 ×3 | Min accuracy per difficulty |

#### LevelInfo (3 params)

Editor metadata (not gameplay-relevant).

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Update info | PushButton | Editor action (always FALSE) |
| 2 | Save mission models | PushButton | Editor action (always FALSE) |
| 3 | Model path | String256 | Path to model list QSC |

---

### LOD Settings

#### ModelLODSettings (6 params)

Per-model LOD distance overrides.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Model | String16 | Model ID |
| 2 | Distance to LOD 2 | Real32 | LOD 2 switch distance |
| 3 | Distance to LOD 3 | Real32 | LOD 3 switch distance |
| 4 | Distance to LOD 4 | Real32 | LOD 4 switch distance |
| 5 | Distance to LOD 5 | Real32 | LOD 5 switch distance |
| 6 | Distance to cutoff | Real32 | Full culling distance |

#### LocalModelLODSettingsContainer (1 param)

Container for level-local LOD overrides.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Path | String256 | Path to LOD settings file |

---

### Multiplayer

#### Network_Mission (3 params)

Multiplayer mission settings.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Start Camera Position | ObjectPos | Lobby camera position (3 floats) |
| 2 | Start Camera Orientation | Real32x9 | Lobby camera rotation (3 floats) |
| 3 | Mission Violated Expression | VarString | Rule violation expression |

#### Network_Objective (6 params)

Multiplayer objective.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Objective Expression | VarString | Completion expression |
| 2 | Objective Failed Expression | VarString | Failure expression |
| 3 | Order number for objective | Int32 | Display order |
| 4 | Team this objective is for | Int32 | Team index |
| 5 | Time for objective | Int32 | Time limit (seconds) |
| 6 | Is the c4 bomb required for this objective | bool8 | Requires C4 |

#### SpawnArea (6 params)

Multiplayer spawn zone.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Zone center (3 floats) |
| 2 | Orientation | Real32x9 | Zone rotation (3 floats) |
| 3 | Dimentions | Real32x3 | Zone size (3 floats) |
| 4 | Camera Position | ObjectPos | Spawn camera position (3 floats) |
| 5 | Camera Orientation | Real32x9 | Spawn camera rotation (3 floats) |
| 6 | Team | Int32 | Team index |

Children: `SpawnPoint`.

#### SpawnPoint (2 params)

Individual spawn point within a SpawnArea.

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Spawn position (3 floats) |
| 2 | Gamma | Angle | Facing direction (radians) |

#### C4BombArea (4 params)

C4 bomb placement zone (multiplayer demolition objectives).

| # | Parameter | Type | Description |
|---|-----------|------|-------------|
| 1 | Position | ObjectPos | Zone center (3 floats) |
| 2 | Orientation | Real32x9 | Zone rotation (3 floats) |
| 3 | Dimensions | Real32x3 | Zone size (3 floats) |
| 4 | Active Expression | VarString | Zone active expression |

## See Also

- [QVM Format](format_qvm.md) — bytecode format and decompilation details
- [Game Structure](game_structure.md) — level directory layout and task ID naming convention
- [Forest DAT](format_forest_dat.md) — vegetation placement data linked by Forest task IDs
- [Graph DAT](format_graph_dat.md) — AI navigation graph data linked by AIGraph task IDs
