# IGI2 Shader Research (Direct3D 8, ~2002)

> Reverse-engineering notes on the GPU shaders shipped inside `igi2.exe`.
> Source binary: `.ignore/igi2_game/igi2.exe` (2,985,984 bytes), Innerloop in-house engine.
> Purpose: reference + validation oracle for the `igipy-unity` port (custom Unity
> terrain/water/object shaders should reproduce this original shading model).

## TL;DR

- IGI2 renders with **Direct3D 8** and ships a **programmable vertex pipeline + fixed-function
  pixel pipeline**.
- **10 vertex shaders** are embedded in `igi2.exe` as **plaintext `vs.1.0` assembly source**,
  assembled at runtime by the statically-linked **D3DX8 Shader Assembler v0.91**
  (`D3DXAssembleShader`). They are *not* precompiled — you can read them directly.
- **No pixel shaders.** There is no `ps.*` source and no compiled pixel-shader bytecode. The
  apparent `ps.1.4` byte tokens are version-compare constants (`D3DPS_VERSION(1,4)==0xFFFF0104`)
  inside the assembler's own x86 code, not shaders. The per-pixel work is done with
  **fixed-function texture stages** (`SetTextureStageState` / `D3DTSS_*`).
- The shaders split into three families: **water** (Fresnel + reflection + sun specular),
  **reflective/specular surface**, and a matrix of **terrain/world triplanar-projection**
  shaders that generate texture coordinates procedurally from vertex position.
- Extracted source: [`docs/igi2/research/shaders/`](shaders/) (`vs00_*.vsh` … `vs09_*.vsh`).

## How they were found

No external tools (`strings`/binwalk) were needed — a byte scan of `igi2.exe`:

1. **DLL / API strings** → confirms the renderer: `D3D8.DLL`, `Direct3DCreate8`,
   `ValidateVertexShader`, `ValidatePixelShader`, plus engine source paths
   `\Project\Igi2\B\2\Pc\pc_direct3d.c` and `pc_direct3dtexture.c`.
2. **Assembler fingerprint**: the literal string `D3DX8 Shader Assembler Version 0.91`, the
   full DX8 opcode keyword table (`texld`, `texm3x3vspec`, `texbem`, `texreg2rgb`, …), and
   assembler error messages (`shader version expected`, `coissue not supported in vertex
   shaders`, `constant modifiers not supported in ps.1.4`). This proves the *assembler* is
   compiled into the EXE and shaders are assembled from text at load time.
3. **Shader source blocks**: NUL-terminated C strings beginning with a `vs.1.0` directive
   followed by newlines + instructions. 10 unique blocks (region ~offset 2,857,888 onward in
   the `.rdata`/string area). `gconvapi.dll`, `vqdll.dll`, `mss32.dll` (Miles Sound System)
   contain none.

The scan is reproducible with a short Python `re` pass over the raw bytes (see commit history /
the exploration session that produced this doc).

## The pipeline at a glance

```
            VERTEX (programmable, vs.1.0)          PIXEL (fixed-function)
        +-------------------------------+      +---------------------------+
 mesh ->| transform (m4x4/m3x4/dp4 oPos)|      | D3DTSS texture stages     |
        | fog          -> oFog          |  ->  |  - modulate oD0 * tex0    | -> frame
        | N.L lighting -> oD0 (diffuse) |      |  - blend tex1/tex2 by ... |    buffer
        | specular     -> oD1           |      |    oD0.w / oT* coords     |
        | tex coords   -> oT0..oT2      |      |  - add specular oD1       |
        +-------------------------------+      +---------------------------+
              ^ register inputs v0..v4               ^ no ps.* shaders;
                                                       combine in TSS state
```

## Vertex input registers (`v#`)

The exact `D3DVSD_*` declaration tokens **were recovered statically** — they are not built at
runtime as previously assumed. Three `D3DVSD` token arrays sit in `.data` and are passed to
`CreateVertexShader` (vtable `+0x12C`); the register types below are now **confirmed**, not
inferred. (Method: a byte scan for `STREAM(0)…END(0xFFFFFFFF)` token runs + Capstone
disassembly of the `CreateVertexShader` call sites — see `.ignore/re_scratch/`.)

| Reg  | Type (confirmed) | Stream | Meaning | Evidence |
|------|------------------|--------|---------|----------|
| `v0` | `FLOAT3` (declA) / `FLOAT4` (declB/C) | 0 | **Position** | `m4x4 oPos,v0,c0`; `dp4 oPos.x,v0,c0`; fog `dp4 v0·c4` |
| `v1` | `FLOAT3` | 0 | **Normal** | `dp3 r,v1,c8` (N·L), reflection `mad oT0,v1,...` |
| `v2` | `FLOAT1` | 0 | **Per-vertex scalar** (water alpha/foam/wave weight) | `mul oD0.w, r3.x, v2.x` |
| `v4` | `FLOAT1` | **1** | **Per-vertex blend weight** (terrain layer alpha) | `mov oD0.w, v4.wwwx` — FLOAT1 expands to `(x,0,0,1)`, so `.wwwx` routes `v4.x` → `oD0.w` |

> **Correction:** `v4` is a single `FLOAT1` blend weight in its **own vertex stream (stream 1)**,
> **not** a packed `D3DCOLOR` diffuse colour. The `.wwwx` swizzle is the FLOAT1→alpha idiom, not a
> colour read. `v2` is likewise a `FLOAT1`, interleaved with position+normal in stream 0.

**The three declarations (static `.data` arrays), one per shader family:**

| Decl | VA | Tokens | Used by | `CreateVertexShader` site |
|------|----|--------|---------|---------------------------|
| A | `0x6d364c` | `STREAM(0) v0:FLOAT3 v1:FLOAT3 v2:FLOAT1` | water `vs00/01`, reflective `vs02` | `0x5944b0` (loops ×3) |
| B | `0x6d3bb4` | `STREAM(0) v0:FLOAT4` | single-tex terrain `vs06` | `0x605dbc` |
| C | `0x6d3bc0` | `STREAM(0) v0:FLOAT4` + `STREAM(1) v4:FLOAT1` | blended terrain `vs03/04/05/07/08/09` | `0x605c17`, `0x605cc7` |

> **Important for the port:** the terrain/world shaders (`vs03`–`vs09`) do **not** consume the
> mesh's stored UVs. They synthesize texture coordinates from `v0` (position). MEF *object*
> models (type 0/1 with explicit `uv_u/uv_v` + normals) are drawn through the fixed-function T&L
> path or a separate code path — none of the 10 vertex shaders reads `oT` from a stored UV
> attribute. So: **terrain = procedural triplanar UVs in this doc; rigid/skinned object UVs come
> from the MEF vertex buffer directly.**

## Constant registers (`c#`)

DX8 has one shared constant bank; **each shader is configured with its own constants per draw**,
so a register's meaning is *per-shader family*, not global. The register **sets** below are now
**confirmed** by disassembling the `SetVertexShaderConstant` (vtable `+0x13C`) call sites; the
per-register *roles* remain inference cross-checked against shader usage.

- **Water/lit upload (`~0x597xxx`)** sets: `c0, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14, c15, c20, c21`.
- **Terrain upload (`~0x606–608xxx`)** sets: `c0, c4, c5, c8, c9, c10, c11, c12, c13, c14, c15` + 4 loop-computed indices (per-texture-set tiling scales written with a variable register index).
- **`c0` (the MVP/world matrix) is uploaded via `SetVertexShaderConstant` here**, *not* via `SetTransform`. **`c15` is in active use** (newly observed; role not yet pinned).

**Water / lit family (`vs00`, `vs01`, `vs02`)**

| Reg        | Inferred role |
|------------|---------------|
| `c0..c3`   | world·view·proj matrix rows (`dp4 oPos.{xyzw}`) |
| `c4`       | fog params (`exp/expp` of `v0·c4` → `oFog`) |
| `c5`       | misc scalars: `c5.z = 1.0` (used as `1.0 - x`), `c5.w` = specular/Fresnel scale |
| `c6.x`     | diffuse bias added to `oD0.w` |
| `c7`       | camera/eye position (world-space view vector `v0 - c7`) |
| `c8`       | light direction (N·L = `v1·c8`) |
| `c9`       | light / diffuse color |
| `c10`      | ambient color |
| `c11..c14` | texture-coordinate / reflection projection scales & offsets |
| `c14.x/y/z`| Fresnel coefficients (`mad r,_,c14.y,c14.x`; `max r,_,c14.z`) in `vs00/01` |
| `c20`      | water tint/color |
| `c21`      | specular (sun-glint) color |

**Terrain / world family (`vs03`–`vs09`)**

| Reg        | Inferred role |
|------------|---------------|
| `c0..c2`   | object→world (or →clip) 3×4 transform rows (`m3x4 r1,v0,c0`) |
| `c11`      | texture-set 0 projection scale |
| `c12`      | texture-set 1 projection scale |
| `c13`      | world offset for the detail/3rd texture (`sub r0,v0,c13`) |
| `c14`      | translation added after `m3x4`, and the 3rd-texture (`oT2`) scale |

## The 10 shaders

Full extracted source lives in [`shaders/`](shaders/). Summary:

| File | Lines | Family | What it does |
|------|-------|--------|--------------|
| `vs00_water_reflective_envmap.vsh` | 39 | Water | Fog, normalized view vector, Fresnel falloff (`(1-N·V)^5`), **reflection vector** → `oT0` (environment map), high-power sun specular → `oD1`, water tint via `c20`. Full `m4x4` transform. The "highest water quality" path. |
| `vs01_water_planar.vsh` | 38 | Water | Same lighting/Fresnel/specular as `vs00` but planar UV (`oT0.xy = v0.xy - c7.xy`) instead of a reflection vector — cheaper water tier. |
| `vs02_reflective_specular_surface.vsh` | 22 | Reflective | Per-vertex diffuse (`N·L`·`c9`+`c10`) → `oD0`, reflection vector → `oT1`, `dp4` MVP transform. Glass/shiny surfaces. |
| `vs03_terrain_triplanar_x_plane_3tex.vsh` | 9 | Terrain | 3 texture sets, UVs projected from `v0.yz` (surfaces facing **X**). `oT2` is a world-offset detail layer; `oD0.w = v4.w` blend weight; `m3x4` transform. |
| `vs04_terrain_triplanar_y_plane_3tex.vsh` | 9 | Terrain | As above, UVs from `v0.xz` (horizontal — **floors/ground**). |
| `vs05_terrain_triplanar_z_plane_3tex.vsh` | 9 | Terrain | As above, UVs from `v0.xy` (surfaces facing **Z**). |
| `vs06_terrain_single_tex.vsh` | 6 | Terrain | Minimal: one texture set `(v0 - c11)·c12`, fog, `m3x4`. No color, no blend. |
| `vs07_terrain_x_plane_2tex.vsh` | 7 | Terrain | 2 texture sets from `v0.yz`, vertex color `v4`, no detail/offset layer. |
| `vs08_terrain_y_plane_2tex.vsh` | 7 | Terrain | 2 texture sets from `v0.xz`. |
| `vs09_terrain_z_plane_2tex.vsh` | 7 | Terrain | 2 texture sets from `v0.xy`. |

**The terrain matrix** = `{2-texture, 3-texture}` × `{X-plane (yz), Y-plane (xz), Z-plane (xy)}`
projection, plus one single-texture fallback. This is **triplanar terrain texturing**: the engine
picks the shader whose projection axis best matches the surface orientation, multiplies world
position by a per-material tiling scale to get UVs, and blends 2–3 texture layers using a
per-vertex weight in `v4.w`. Texture/material assignment comes from the THM/MTP/terrain-material
data (`CreateTerrainMaterial`, `TerrainLightMap`, `TerrainMap` strings in the EXE).

### Annotated example — `vs00` water (reflective)

```
vs.1.0
dp4  r0.x, v0, c4        ; fog: distance·fogparams
exp  r1.x, r0.x          ; exp fog
rcp  oFog, r1.x          ; -> fog output
dp3  r0.x, v0, v0
rsq  r0.x, r0.x
mul  r0,   r0.x, -v0     ; r0 = normalized view dir (-V)
dp3  r1.w, v1, c8        ; N·L
mul  r1,   c9, r1.w
mul  r1,   r1, c20       ; * water tint
add  r1,   r1, c10       ; + ambient
dp3  r2.x, r0, v1        ; N·V
max  r2.x, r2.x, c14.z
mul  r3.x, r2.x, c5.w
mad  oT0.xyz, v1.xzy, r3.xxx, -r0.xzy   ; reflection vector -> env-map coords
add  r3.x, c5.z, -r2.x   ; 1 - N·V                  \
mul  r4.x, r3.x, r3.x     ;                          | Fresnel (1-N·V)^5
mul  r4.x, r4.x, r4.x     ;                          |
mul  r4.x, r4.x, r3.x     ;                          /
mad  r3.w, r4.x, c14.y, c14.x   ; Fresnel scaled+biased
...                       ; specular sun glint -> oD1, alpha -> oD0.w
m4x4 oPos, v0, c0         ; clip-space position
```

## Pixel side (fixed-function) — terrain combine recovered

Because there are no pixel shaders, the final color is produced by `D3DTSS_*` texture-stage state
set in C (`pc_direct3dtexture.c`). The **terrain** combine was recovered by disassembling the
`SetTextureStageState` (vtable `+0xFC`) calls in the terrain draw code (`~0x6066xx–0x606cxx`):

```
3-texture terrain (pairs with vs03/04/05):
  Stage0  COLOROP=MODULATE    COLORARG1=TEXTURE  COLORARG2=DIFFUSE   ; tex0 * oD0   (oD0.w = v4 weight)
  Stage1  COLOROP=MODULATE    COLORARG1=TEXTURE  COLORARG2=CURRENT   ; * tex1
  Stage2  COLOROP=MODULATE2X  COLORARG1=TEXTURE  COLORARG2=CURRENT   ; * tex2 * 2   (detail layer)
  Stage3  COLOROP=DISABLE
  ALPHAOP=SELECTARG2 ; sampler: stage0/1 ADDRESS=WRAP, stage2 ADDRESS=CLAMP, MIN/MAG/MIP=LINEAR

2-texture (vs07/08/09): Stage0 MODULATE tex0*diffuse, Stage1 MODULATE *tex1, rest DISABLE
single   (vs06):        Stage0 SELECTARG1 tex0, Stage1 DISABLE
```

So terrain layer blending is **fixed-function MODULATE chaining gated by the per-vertex `v4` weight
in `oD0.w`**, with the detail (3rd) layer brightened via `MODULATE2X` and address-clamped.

> **Still open:** the **water** pixel combine (around `~0x597xxx` / the water-draw path) was only
> partially sampled — the reflection/tint/specular stage setup that consumes `oT0`, `oD0`, `oD1`
> still needs to be isolated.

## RenderMode method registry — object vs terrain/water draw paths

The engine routes every draw through a named **RenderMode method** registry. The names are
registered at runtime in `igi2.exe` (format string `RenderMode: Failed to create new method '%s'`;
**56 methods**, recovered by disassembling the registration call sites — see `.ignore/re_scratch/`).
This pins which geometry classes use the `vs.1.0` shaders and which do not:

| Draw method                   | Geometry class                       | Vertex pipeline                         |
|-------------------------------|--------------------------------------|-----------------------------------------|
| `DrawWater`                   | water surfaces                       | **vertex shaders** `vs00`/`vs01`        |
| `DrawTerrain`                 | terrain / world                      | **vertex shaders** `vs03`–`vs09`        |
| `DrawRigidMesh`               | static rigid MEF (`model_type` 0)    | fixed-function T&L                      |
| `DrawBoneMesh`                | skeletal/dynamic MEF (`model_type` 1)| fixed-function T&L (skinned)            |
| `DrawLightmapMesh`            | lightmapped building MEF (`type` 3)  | fixed-function T&L × baked lightmap     |
| `DrawSplineMesh`              | spline geometry                      | fixed-function T&L                      |
| `DrawForest`                  | vegetation                           | fixed-function T&L                      |
| `PolyListDynCubeObjPrimitive` | reflective/env-mapped objects        | reflective surface (`vs02`) + cube env-map |
| `RotorPrimitive` / `AfterburnerPrimitive` | rotor / jet-afterburner FX | special animated (UV-scroll / additive) |

Spatial evidence corroborates the shader split: the water/lit shader-assembly loop is at `0x594430`
and `DrawWater` registers at `0x59805b`; terrain shaders at `0x605ba0+` and `DrawTerrain` at
`0x60a9cc` — each shader-using method sits next to its own shader setup. The `Draw*Mesh` methods have
no neighbouring `D3DXAssembleShader`/`CreateVertexShader` and run fixed-function. The reflective
object material exposes editor-tunable params seen as adjacent strings in the EXE: `Envmap`,
`Specular Color`, `Diffuse Color`, `Max Reflection Angle (cos)`, `Env Scale`, `UV Scale`.

> **Two material layers (don't conflate):** the GPU appearance above is separate from the engine's
> **physical/surface** material system in `MATERIAL/material.qvm` (33 `GameMaterial`s — Ground, Wood,
> Glass, Concrete, Flesh…), which the MEF `TAMC` collision chunk indexes for footstep sounds, bullet
> decals and penetration — gameplay/FX, not rendering. See [../formats/mef.md](../formats/mef.md).

## Implications for `igipy-unity`

- **Terrain shader (Unity HLSL/Shader Graph):** implement triplanar projection driven by world
  position with a per-material tiling scale (mirrors `c11/c12/c13`), then reproduce the recovered
  fixed-function combine: `out = tex0 · weight`, `· tex1`, `· (tex2 · 2)` — i.e. multiply 2–3
  tiling layers in sequence with the 3rd (detail) layer doubled, all gated by the per-vertex blend
  weight from `v4.x` (carried in `oD0.w`). WRAP the tiling layers, CLAMP the detail layer. Select
  the projection axis by surface normal orientation (the X/Y/Z-plane variants). Bake lighting from
  the lightmap path (`TerrainLightMap`) rather than per-vertex `N·L`.
- **Water shader:** Fresnel `(1-N·V)^5` blend between reflection (env/planar) and water tint
  (`c20`), plus a sharp sun-specular highlight (`oD1`). Two quality tiers exist (reflective vs.
  planar) matching the in-game Water Quality setting.
- **Rigid/skinned objects:** these do **not** use the 10 vertex shaders for UVs — object UVs come
  straight from the MEF vertex buffer; lighting was per-vertex N·L or fixed-function T&L. The engine
  picks the path by `model_type`: `DrawRigidMesh` (static, type 0), `DrawBoneMesh` (skinned, type 1),
  `DrawLightmapMesh` (lightmap-lit building, type 3). Shiny objects add cube/env-map reflection via
  `PolyListDynCubeObjPrimitive` (the `vs02` reflective family + the `Envmap`/`Specular Color`/`Max
  Reflection Angle` material). So the Unity importer should branch on `model_type`: textured+dynamic-lit
  for rigid, +skinning for bone meshes, ×lightmap (second UV) for buildings, +env-map for reflective.

## Open threads / next investigations

1. ~~**Vertex declarations**~~ — ✅ **RESOLVED.** Three static `D3DVSD` arrays in `.data` (declA/B/C
   above). `v2`=`FLOAT1` (stream 0), `v4`=`FLOAT1` (stream 1) — both confirmed, doc corrected.
2. ~~**Constant register map**~~ — ✅ **CONFIRMED.** `SetVertexShaderConstant` sites show the exact
   register sets uploaded per family (above). Inferred roles validated; `c0` matrix is uploaded
   here; `c15` newly observed (role still unpinned).
3. **Fixed-function pixel stages** — ✅ **terrain combine recovered** (MODULATE→MODULATE→MODULATE2X
   chain, above). **Remaining:** the **water** pixel-stage setup (reflection/tint/specular consuming
   `oT0`/`oD0`/`oD1`) around `~0x597xxx`.
4. **Shader ↔ render-mode binding** — ✅ **mostly resolved.** Family→declaration→`CreateVertexShader`
   site mapped; source-pointer tables identified (`0x6d3660` water/lit, `0x6d3bd4`/`0x6d3be4` terrain);
   `D3DXAssembleShader` is the internal fn at `0x64d4dc`. The **RenderMode method registry** (56 named
   methods) now ties geometry classes to draw paths: `DrawWater`/`DrawTerrain` use the vertex shaders;
   `DrawRigidMesh`/`DrawBoneMesh`/`DrawLightmapMesh` are fixed-function per `model_type` (table above).
   **Remaining:** bind each `Draw*Mesh` method name to its handler function (the registrar uses a
   name→func dispatch table, not a simple `push func; push name`) and read the per-class fixed-function
   `SetTextureStageState`/`SetRenderState` recipe — same treatment given to the terrain combine.
5. **Object fixed-function combine + skinning** — **open.** For `DrawRigidMesh`/`DrawBoneMesh`/
   `DrawLightmapMesh`: capture the exact texture-stage/render-state recipe, and determine whether
   `DrawBoneMesh` skins on the CPU or via fixed-function vertex blending (`D3DRS_VERTEXBLEND`) — this
   decides how the Unity importer consumes `XTRVItem1.bone_weight`. Also confirm `PolyListDynCubeObj` ↔
   `vs02` and capture its env-map stage setup (neighbour of the still-open water pixel-stage trace).

---
*Generated during `/aif-explore` sessions (string scan → static `D3DVSD` scan + Capstone
disassembly of the D3D8 COM call sites). igipy is reference-only — this is spec/oracle material,
not import code. Reproducible analysis scripts: `.ignore/re_scratch/`.*
