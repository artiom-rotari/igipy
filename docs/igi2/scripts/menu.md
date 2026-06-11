[← Sound definitions](sounds.md) · [Scripts Index](README.md) · [Back to Project README](../../../README.md) · [Physics objects →](physics-objects.md)

# 5. Menu UI

The front-end and pause-menu interfaces are built entirely from script in `menusystem/`. Both files
declare widget schemas with `Task_DeclareParameters`, then build a tree of screens and widgets under
one root `MenuManager`.

| File | Defines |
|------|---------|
| `mainmenu.qsc` | Startup/lobby menus (mission select, profiles, options, multiplayer browser) |
| `ingamemenu.qsc` | In-game pause menus (resume, HUD options, team/skin/shop, radio) |

## Structure

A `MenuScreen` is a full screen; widgets are its children. Widgets carry their logic as **VarString
expressions** — small scripts evaluated for enable/visible state and run on click/change. The
recurring callbacks are screen navigation (`MenuManager_PushScreen` / `_PopScreen` /
`_RequestScreen(id, save)` / `_LeaveMenus(id, reason, bool)`), config setters (`Config_*`,
`GfxOptions_*`, `Game_Set*`), and — in-game — multiplayer flow (`NetManager_*`, `Netshop_Activate`,
`SlotSelector_*`, `RadioCom_Activate`).

Widget types (declared in both files): `MenuScreen`, `MenuFrame`, `MenuText`, `SlideBar`, `ListBox`,
`ToggleBox`, `InputBox`, `ScrollListBox`, `PictureBox`, `AsciiBox`, `DialogWindow`, `ColumnView`
(+ `ColumnViewColumn`), `TypeWriterBox`, `MenuStatsScreen`; `ingamemenu.qsc` adds `MenuTextSelection`.

## `mainmenu.qsc`

A `MenuScreen` declares background art, logo position, a content frame rectangle, and an on-escape
action. The Main Menu screen (id 900) and a navigation button:

```c
Task_New(900, "MenuScreen", "Main Menu", "mainmenu.jpg", "logo.pic", 320, 100, TRUE, 100, 163, 540, 470,
  "MenuManager_ActivatePopupScreen(934)", "", "", -1, -1, FALSE,
    Task_New(-1, "MenuText", "single player", "Single Player", "font3.fnt", 2, 1,
      "TRUE", "TRUE", "MenuManager_PushScreen(914)", "", TRUE, ""),
```

A `MenuText` carries: text/label, font, colour index, alignment, then **isEnabled**, **isVisible**, and
**onClick** expressions, a click sound, a dim flag, and an optional dynamic-label expression.

A **slider** wires three scripts — get, set, and live-modify — to a config value. The Gamma slider:

```c
Task_New(973, "SlideBar", "", "slide", TRUE, 150,
  "Config_GraphicOptionsGetGamma()",
  "Config_GraphicOptionsSetGamma(this.vValue)",
  "Config_GraphicOptionsSetGamma(this.vValue)", "", "", "");
```

A **list box** (render device) and a **toggle** (blood) follow the same get/set pattern:

```c
Task_New(951, "ListBox", "", "slide", "font1.fnt", 150,
  "Config_FillRenderDeviceListBox()", "Config_GraphicOptionsGetDevice()",
  "Config_GraphicOptionsSetDevice(this.nActiveID)", "MenuManager_ForceUpdateWindow(950)\n", "");

Task_New(965, "ToggleBox", "",
  "Config_GameOptionsInputGetBloodEnabled()", "Config_GameOptionsInputSetBloodEnabled(this.isOn)", "", "");
```

Screens cover Main (900), Configuration (904), Graphics (905), Sound (906), Controls (907), Language
(910), Player (912), Readme (913), Select Level (914), Content Control (915), Credits (916),
Multiplayer hub/server/maplist/GameSpy (917/919/922/924), Select Savegame (999), and modal
`DialogWindow` popups (930–935).

## `ingamemenu.qsc`

Same widget toolkit, but the root opens to a different screen depending on mode:

```c
// MenuManager default screen: "Game_GetGameMode() == GAME_GAMEMODE_SINGLEPLAYER ? 901 : 900"
Task_New(901, "MenuScreen", "1P Main Menu", "", "", 0, 0, TRUE, 85, 80, 555, 410,
  "Config_SaveConfig(),\nMenuManager_LeaveMenus(900, MENUMANAGER_IDLE, FALSE)", "", "", -1, -1, FALSE,
    Task_New(-1, "MenuText", "resume", "Resume Game", "font3.fnt", 2, 1,
      "!LevelFlow_LevelFailed()", "TRUE",
      "Config_SaveConfig(),\nMenuManager_LeaveMenus(901, MENUMANAGER_IDLE, FALSE)", "", TRUE, ""),
```

Note **Resume** is enabled by `!LevelFlow_LevelFailed()` — greyed out after a mission fails. In-game
extras: live HUD crosshair RGB/alpha sliders (`Config_GraphicOptions…CrossHair…`), the multiplayer
team/skin join flow (`NetManager_SetTeam(HUMAN_TEAM_GOOD)`, `NetManager_SetMode(NETMANAGER_MODE_*)`),
the weapon shop (`Netshop_Activate`, `SlotSelector_ItemClicked(slot, category)`), and the radio
commands wheel (`RadioCom_Activate`). `MenuManager_LeaveMenus` takes a reason such as
`MENUMANAGER_IDLE`, `MENUMANAGER_RESTARTLEVEL`, `MENUMANAGER_QUITTOMAINMENU`, `MENUMANAGER_JOINGAME`.

## See Also

- [Engine & config](engine-config.md) — `config.qsc` is the file these menus read and write.
- [Missions & level scene](missions.md) — `LevelFlow` drives the `LevelFlow_LevelFailed()` gate.
- [QVM Scripts overview](../formats/qvm.md) — all categories at a glance.
