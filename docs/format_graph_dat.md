[Back to README](../README.md)

# Graph DAT Format

Graph DAT files (`graph*.dat`) store AI navigation graphs used for pathfinding. Each file defines a set of nodes with 3D positions and edges connecting them. There are 182 files across all levels. Each graph file corresponds to an `AIGraph` task in the level's `objects.qsc` — the numeric suffix in the filename is the task ID (e.g. `graph1.dat` corresponds to `Task_New(1, "AIGraph", "City", ...)`).

## Correlation with objects.qsc

The `AIGraph` task in `objects.qsc` declares per-graph parameters that map directly to graph file contents:

```
Task_New(1, "AIGraph", "City",
    0, 0, 0,          # Graph position (ObjectPos)
    TRUE,              # Relative
    FALSE,             # Update (editor PushButton)
    1603, 2000, 8158,  # Graphdata: node_count, max_node_capacity, edge_count
    1,                 # Node cover midoffset (Real64)
    2,                 # Node cover topoffset (Real64)
    3,                 # Max height difference between linked nodes (Real64)
    0.3,               # Width of node links (Real64)
    0.5,               # Link maximum distance to ground (Real64)
    30,                # Max Link-length (Real64)
    FALSE,             # Use precise link method (bool8)
    0.05,              # Precise link method step value (Real64)
    TRUE)              # Update & Display CoverInfo (bool8)
```

The `Graphdata` triple contains: **(node_count, max_node_capacity, edge_count)**. These match exactly:
- `node_count` = number of node TLV groups in the file
- `max_node_capacity` = the header property value (`0x0D3AE6`)
- `edge_count` = number of edge TLV groups in the file

Verified across all tested levels (location1/level1, location2/level1, location3/level1, etc.).

## Location

```
missions/location*/level*/graphs/graph*.dat
```

## Structure Overview

```
┌──────────────────────────────────────┐
│ Magic: 0xFFEEDDCC (4 bytes)         │
├──────────────────────────────────────┤
│ TLV Entry 0                         │
│   Marker (1 byte): 0x04             │
│   Property hash (3 bytes)           │
│   Zero padding (2 bytes)            │
│   Type code (2 bytes)               │
│   Payload (variable)                │
├──────────────────────────────────────┤
│ TLV Entry 1                         │
├──────────────────────────────────────┤
│ ...                                  │
├──────────────────────────────────────┤
│ TLV Entry N-1                        │
└──────────────────────────────────────┘
```

## Magic

| Offset | Size | Type   | Value        | Description          |
|--------|------|--------|--------------|----------------------|
| 0      | 4    | uint32 | `0xFFEEDDCC` | File magic (LE)      |

## TLV Entry Format

After the 4-byte magic, the file is a stream of TLV (tag-length-value) entries with no separators or padding between them:

| Offset | Size | Field         | Description                       |
|--------|------|---------------|-----------------------------------|
| 0      | 1    | marker        | Always `0x04`                     |
| 1      | 3    | property_hash | Property identifier (little-endian) |
| 4      | 2    | zero_padding  | Always `0x0000`                   |
| 6      | 2    | type_code     | Determines payload size and type  |
| 8      | var  | payload       | Data (size depends on type_code)  |

## Type Codes

| Code     | Payload size | Interpretation          |
|----------|-------------|-------------------------|
| `0x0505` | 4 bytes     | uint32                  |
| `0x0606` | 4 bytes     | float32                 |
| `0x0808` | 24 bytes    | 3×float64 (XYZ position)|
| `0x0909` | 1 + N bytes | Variable: 1-byte count, then N bytes of data |

### Variable-Length Payload (0x0909)

The first byte is a count `N`, followed by `N` bytes of data. This is used for node criteria strings (null-terminated) and single-byte flags:

- Single flag: `count=1`, 1 byte of data
- String: `count=len+1`, null-terminated ASCII string (e.g. `NODECRITERIA_STAIR\0`)

## Property Hashes

12 unique property hashes have been identified across all 182 files:

### Header Property

| Hash       | Type   | Semantics            | Value range |
|------------|--------|----------------------|-------------|
| `0x0D3AE6` | uint32 | Max node capacity    | 100–2000    |

This is the pre-allocated capacity for the node array. Always >= the actual node count. Corresponds to the 2nd value of the `Graphdata` triple in `objects.qsc`.

### Node Properties

Two node variants exist: the full 8-property format (152 files) and a shorter 6-property format (30 files) that omits light intensity and unknown flag. The parser auto-detects the variant from the entry sequence.

#### Full node format (8 properties)

Each node consists of 8 consecutive TLV entries in this order:

| Hash       | Type     | Semantics           | Value range              | Confidence |
|------------|----------|---------------------|--------------------------|------------|
| `0x0735CE` | uint32   | Node ID             | 1–1999                   | Confirmed  |
| `0x1D4295` | 3×f64    | Node position (XYZ) | World coordinates        | Confirmed  |
| `0x0F7E9C` | float32  | Height offset       | −1.06 to 7.30            | Probable   |
| `0x143023` | float32  | Node radius         | 0.125 or 0.5             | Uncertain  |
| `0x1BB629` | uint32   | Game material ID    | e.g. 1, 19, 26, 27, 28  | Confirmed  |
| `0x2654DE` | float32  | Light intensity     | 0.0 to ~0.78             | Probable   |
| `0x214E00` | uint32   | Unknown flag        | 0 or 1                   | Unknown    |
| `0x1BD3E5` | varlen   | Node criteria       | 1-byte flag or string    | Confirmed  |

#### Short node format (6 properties)

30 of 182 files use a shorter node format that omits `light_intensity` (`0x2654DE`) and `unknown_flag` (`0x214E00`):

| Hash       | Type     | Semantics           | Value range              | Confidence |
|------------|----------|---------------------|--------------------------|------------|
| `0x0735CE` | uint32   | Node ID             | 1–1999                   | Confirmed  |
| `0x1D4295` | 3×f64    | Node position (XYZ) | World coordinates        | Confirmed  |
| `0x0F7E9C` | float32  | Height offset       | −1.06 to 7.30            | Probable   |
| `0x143023` | float32  | Node radius         | 0.125 or 0.5             | Uncertain  |
| `0x1BB629` | uint32   | Game material ID    | e.g. 1, 19, 26, 27, 28  | Confirmed  |
| `0x1BD3E5` | varlen   | Node criteria       | 1-byte flag or string    | Confirmed  |

These appear across location1/LEVEL7, location2/LEVEL2-6, location3/level1-LEVEL5 — likely graphs created with an older editor version or for levels where lighting data was not computed.

#### Field Notes

**Height offset** (`0x0F7E9C`): Most nodes have 0.0 (ground level). Uniform non-zero values appear for elevated structures (e.g. all 70 nodes in a walkway graph share 1.571). Negative values indicate underground nodes. Values 2.4–2.8 appear in ship interior graphs (location3/level5). Only 5 unique values in a typical graph.

**Node radius** (`0x143023`): Essentially constant — 0.5 in 181 of 182 graph files. One graph (`location3/level1/graph7.dat`) uses 0.125. Purpose uncertain; may be a node spacing parameter.

**Game material ID** (`0x1BB629`): Identifies the terrain surface type at the node's position. Cross-referenced with `TerrainMaterial` tasks in `objects.qsc` where the `Game material` parameter uses the same values. Examples: 1 = Rock/Street, 19 = Pebbles, 26 = Dirt/Rock, 27 = Grass, 28 = Sand. Non-terrain values (3, 6, 10, 11, 12, 16, etc.) likely represent building/object floor materials.

**Light intensity** (`0x2654DE`): Continuous distribution with many unique values per graph. Varies even between nodes at the same height on a flat surface (e.g. rooftop nodes range 0.39–0.44). Likely an editor-computed ambient occlusion or shadow factor.

### Edge Properties

Edges follow after all nodes and connect pairs of nodes:

| Hash       | Type   | Semantics         | Value range |
|------------|--------|-------------------|-------------|
| `0x09104A` | uint32 | Edge target node  | 2–1999      |
| `0x0918F6` | uint32 | Edge source node  | 1–1998      |
| `0x0DA923` | uint32 | Edge weight/flag  | Always 1    |

## Node Criteria Strings

Nodes can carry criteria strings that describe special navigation properties:

| String                 | Meaning                      |
|------------------------|------------------------------|
| `NODECRITERIA_DOOR`    | Node is near a door          |
| `NODECRITERIA_STAIR`   | Node is on stairs            |
| `NODECRITERIA_VEHICLE` | Node is a vehicle waypoint   |
| `NODECRITERIA_VIEW`    | Node is a vantage/view point |

When no criteria string is present, the variable-length entry contains a single byte flag instead.

## File Structure Example

A typical graph file has this logical structure:

```
Magic: 0xFFEEDDCC
Max node capacity: 500                  (header entry)
Node 1: id=1, pos=(x,y,z), height_offset, radius, material_id, light, flag, criteria
Node 2: id=2, pos=(x,y,z), height_offset, radius, material_id, light, flag, criteria
...
Node N: id=N, pos=(x,y,z), height_offset, radius, material_id, light, flag, criteria
Edge: target=5, source=1, weight=1
Edge: target=3, source=1, weight=1
...
```

## Parser

```python
from igipy.igi2.formats import DATGraph
```

`DATGraph.model_validate_stream(stream)` returns a model with `max_node_capacity`, `nodes: list[GraphNode]`, and `edges: list[GraphEdge]`. For 6-property nodes, `light_intensity` and `unknown_flag` are `None`.

## Validation

All 182 files parse completely with zero failures (152 full-format + 30 short-format).

## See Also

- [Forest DAT Format](format_forest_dat.md) — vegetation placement data
- [Graphcover DAT Format](format_graphcover_dat.md) — AI cover/visibility data
- [File extensions overview](extensions.md) — full list of game file formats
