[← Game Structure](game_structure.md) · [Back to README.md](../README.md#supported-game-file-formats) · [QVM Format →](format_qvm.md)

# File Extensions

Full inventory of file types found in IGI2 game data, with current conversion status.

| Extension         | Count | Status                         |
|-------------------|-------|--------------------------------|
| .olm              | 32532 | Can be ignored                 |
| .mef              | 7609  | Must create converter          |
| .tex              | 5394  | Can be converted to tga        |
| .qvm              | 1786  | Can be converted to qsc        |
| .wav              | 1634  | Can be converted to wav        |
| .iff              | 1244  | Must create converter          |
| .mp3              | 615   | Copy as is                     |
| .dat (forest)     | 109   | Can be converted to json       |
| .dat (graph)      | 182   | Can be converted to json       |
| .dat (graphcover) | 138   | Must create converter          |
| .syn              | 369   | Can be converted to json       |
| .spr              | 257   | Can be converted to tga        |
| .bmp              | 192   | Copy as is                     |
| .jpg              | 119   | Copy as is                     |
| .tga              | 103   | Copy as is                     |
| .thm              | 50    | Can be converted to tga        |
| .tmm              | 50    | Can be converted to tga        |
| .tlm              | 50    | Can be converted to tga        |
| .json             | 42    | Copy as is                     |
| .fnt              | 23    | Can be converted to tga + json |
| .pic              | 3     | Can be converted to tga        |

## See Also

- [Game Structure](game_structure.md) — IGI2 directory layout and mission numbering
- [QVM Format](format_qvm.md) — bytecode script format details
- [Terrain System](format_terrain.md) — terrain height, material, and light maps
