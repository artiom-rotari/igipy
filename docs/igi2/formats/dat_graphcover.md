[Back to README](../../../README.md)

# DAT Graphcover Format

DAT Graphcover files (`graphcover*.dat`) store AI cover and visibility data for navigation graphs. Each file is an ILFF container (the standard IGI2 container format) with content type `AICC`. There are 138 files across all levels. Graphcover files share their numeric suffix with the corresponding `graph*.dat` file — both derive from the same `AIGraph` task ID in `objects.qsc`. Not every AIGraph has a graphcover file (138 graphcover vs 182 graph files).

## Location

```
missions/location*/level*/graphs/graphcover*.dat
```

## Structure Overview

```
┌──────────────────────────────────────┐
│ ILFF Header (16 bytes)               │
│   Signature: "ILFF"                  │
│   File size, version (4), reserved   │
├──────────────────────────────────────┤
│ Content type: "AICC" (4 bytes)       │
├──────────────────────────────────────┤
│ AICH Chunk — Cover header            │
│   (8 bytes)                          │
├──────────────────────────────────────┤
│ AICN Chunk — Cover node 0            │
│   (144 bytes)                        │
├──────────────────────────────────────┤
│ AICN Chunk — Cover node 1            │
│   (144 bytes)                        │
├──────────────────────────────────────┤
│ ...                                  │
├──────────────────────────────────────┤
│ AICN Chunk — Cover node N-1          │
│   (144 bytes)                        │
└──────────────────────────────────────┘
```

Each chunk follows the standard ILFF chunk layout:

| Field     | Type   | Description                            |
|-----------|--------|----------------------------------------|
| FourCC    | 4s     | Chunk signature (e.g. `AICH`, `AICN`) |
| Length    | uint32 | Content length in bytes                |
| Alignment | uint32 | Padding alignment (always 4)          |
| Offset    | uint32 | Offset to next chunk (0 if last)       |

## ILFF Container

| Field        | Value  | Description                    |
|--------------|--------|--------------------------------|
| Signature    | `ILFF` | Standard IGI2 container        |
| Version      | 4      | ILFF version                   |
| Content type | `AICC` | AI Cover/visibility Container  |

## AICH — Cover Header

8 bytes, 2 × uint32 little-endian.

| Offset | Type   | Field       | Description                     |
|--------|--------|-------------|---------------------------------|
| 0      | uint32 | node_count  | Number of AICN chunks to follow |
| 4      | uint32 | version     | Always 1                        |

## AICN — Cover Node

144 bytes per node. Each AICN chunk describes cover/visibility data for one navigation graph node.

| Offset | Type      | Field         | Description                         |
|--------|-----------|---------------|-------------------------------------|
| 0      | uint32    | node_ptr      | Runtime memory pointer to AIGraphNode |
| 4      | uint32    | prev_node_ptr | Previous node pointer (linked list) |
| 8      | uint32    | flags_1       | Flags or metadata                   |
| 12     | uint32    | flags_2       | Flags or metadata                   |
| 16     | 32×uint32 | coverage_data | Coverage bitmask (128 bytes)        |

The first two fields are **runtime memory pointers**, not logical node IDs. Consecutive AICN entries show a stride of exactly 232 bytes between `node_ptr` values, confirming these are heap addresses with `sizeof(AIGraphNode) = 232`. These pointers are only meaningful at the time the file was serialized from the editor's memory and cannot be used to map back to graph node IDs directly.

The 128-byte coverage data block contains 32 uint32 values that encode a bitmask or lookup table describing which other nodes are visible or provide cover from this node's position.

## Empty Files

Files with no cover data are 44 bytes: the ILFF header (16 bytes) + content type (4 bytes) + AICH chunk header (16 bytes) + AICH content (8 bytes) with `node_count = 0`. No AICN chunks follow.

## Validation

All 138 files satisfy `AICH.node_count == number of AICN chunks` with zero failures.

## Parser

```python
from igipy.igi2.formats import DATGraphCover
```

`DATGraphCover.model_validate_stream(stream)` returns an ILFF model with `aich: AICHChunk` (header with `node_count` and `version`) and `nodes: list[AICNChunk]`. Each `AICNChunk` has `node_ptr`, `prev_node_ptr`, `flags_1`, `flags_2`, and `coverage_data: list[int]` (32 uint32 values).
