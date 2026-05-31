import struct
from io import BytesIO
from typing import Self

from pydantic import BaseModel, NonNegativeInt

from igipy.core.base import FileModel

MAGIC = 0xFFEEDDCC
TLV_MARKER = 0x04

# Type codes
TYPE_UINT32 = 0x0505
TYPE_FLOAT32 = 0x0606
TYPE_3XFLOAT64 = 0x0808
TYPE_VARIABLE = 0x0909

# Node stride variants
STRIDE_FULL = 8
STRIDE_SHORT = 6

# Property hashes
HASH_MAX_NODE_CAPACITY = 0x0D3AE6

HASH_NODE_ID = 0x0735CE
HASH_NODE_POSITION = 0x1D4295
HASH_NODE_HEIGHT_OFFSET = 0x0F7E9C
HASH_NODE_RADIUS = 0x143023
HASH_NODE_MATERIAL_ID = 0x1BB629
HASH_NODE_LIGHT_INTENSITY = 0x2654DE
HASH_NODE_UNKNOWN_FLAG = 0x214E00
HASH_NODE_CRITERIA = 0x1BD3E5

HASH_EDGE_TARGET = 0x09104A
HASH_EDGE_SOURCE = 0x0918F6
HASH_EDGE_WEIGHT = 0x0DA923

NODE_HASHES = {
    HASH_NODE_ID,
    HASH_NODE_POSITION,
    HASH_NODE_HEIGHT_OFFSET,
    HASH_NODE_RADIUS,
    HASH_NODE_MATERIAL_ID,
    HASH_NODE_LIGHT_INTENSITY,
    HASH_NODE_UNKNOWN_FLAG,
    HASH_NODE_CRITERIA,
}

EDGE_HASHES = {
    HASH_EDGE_TARGET,
    HASH_EDGE_SOURCE,
    HASH_EDGE_WEIGHT,
}


class TLVEntry(BaseModel):
    property_hash: int
    type_code: int
    payload: bytes


class GraphNode(BaseModel):
    node_id: NonNegativeInt
    position: tuple[float, float, float]
    height_offset: float
    radius: float
    material_id: NonNegativeInt
    light_intensity: float | None = None
    unknown_flag: NonNegativeInt | None = None
    criteria: bytes


class GraphEdge(BaseModel):
    target: NonNegativeInt
    source: NonNegativeInt
    weight: NonNegativeInt


def _read_tlv_entries(stream: BytesIO) -> list[TLVEntry]:
    entries = []

    while True:
        marker_byte = stream.read(1)
        if len(marker_byte) == 0:
            break

        marker = marker_byte[0]
        if marker != TLV_MARKER:
            raise ValueError(f"Expected marker 0x{TLV_MARKER:02X}, got 0x{marker:02X}")

        hash_bytes = stream.read(3)
        property_hash = int.from_bytes(hash_bytes, "little")

        zero_padding = stream.read(2)
        if zero_padding != b"\x00\x00":
            raise ValueError(f"Expected zero padding, got {zero_padding!r}")

        type_code = struct.unpack("<H", stream.read(2))[0]

        if type_code in {TYPE_UINT32, TYPE_FLOAT32}:
            payload = stream.read(4)
        elif type_code == TYPE_3XFLOAT64:
            payload = stream.read(24)
        elif type_code == TYPE_VARIABLE:
            count = stream.read(1)[0]
            payload = stream.read(count)
        else:
            raise ValueError(f"Unknown type code 0x{type_code:04X}")

        entries.append(TLVEntry(property_hash=property_hash, type_code=type_code, payload=payload))

    return entries


def _decode_value(entry: TLVEntry) -> int | float | tuple[float, float, float] | bytes:
    if entry.type_code == TYPE_UINT32:
        return struct.unpack("<I", entry.payload)[0]
    if entry.type_code == TYPE_FLOAT32:
        return struct.unpack("<f", entry.payload)[0]
    if entry.type_code == TYPE_3XFLOAT64:
        return struct.unpack("<3d", entry.payload)
    return entry.payload


NODE_ORDER_8 = [
    HASH_NODE_ID,
    HASH_NODE_POSITION,
    HASH_NODE_HEIGHT_OFFSET,
    HASH_NODE_RADIUS,
    HASH_NODE_MATERIAL_ID,
    HASH_NODE_LIGHT_INTENSITY,
    HASH_NODE_UNKNOWN_FLAG,
    HASH_NODE_CRITERIA,
]

NODE_ORDER_6 = [
    HASH_NODE_ID,
    HASH_NODE_POSITION,
    HASH_NODE_HEIGHT_OFFSET,
    HASH_NODE_RADIUS,
    HASH_NODE_MATERIAL_ID,
    HASH_NODE_CRITERIA,
]


def _detect_node_stride(node_entries: list[TLVEntry]) -> int:
    if not node_entries:
        return STRIDE_FULL

    is_full = len(node_entries) % STRIDE_FULL == 0 and (
        len(node_entries) < STRIDE_FULL or node_entries[5].property_hash == HASH_NODE_LIGHT_INTENSITY
    )
    if is_full:
        return STRIDE_FULL
    if len(node_entries) % STRIDE_SHORT == 0:
        return STRIDE_SHORT

    raise ValueError(f"Node entry count {len(node_entries)} is not divisible by {STRIDE_FULL} or {STRIDE_SHORT}")


def _build_nodes(entries: list[TLVEntry]) -> list[GraphNode]:
    node_entries = [e for e in entries if e.property_hash in NODE_HASHES]
    stride = _detect_node_stride(node_entries)
    expected_order = NODE_ORDER_8 if stride == STRIDE_FULL else NODE_ORDER_6

    nodes = []
    for i in range(0, len(node_entries), stride):
        group = node_entries[i : i + stride]

        for j, expected_hash in enumerate(expected_order):
            if group[j].property_hash != expected_hash:
                raise ValueError(
                    f"Node entry {i + j}: expected hash 0x{expected_hash:06X}, got 0x{group[j].property_hash:06X}"
                )

        if stride == STRIDE_FULL:
            nodes.append(
                GraphNode(
                    node_id=_decode_value(group[0]),
                    position=_decode_value(group[1]),
                    height_offset=_decode_value(group[2]),
                    radius=_decode_value(group[3]),
                    material_id=_decode_value(group[4]),
                    light_intensity=_decode_value(group[5]),
                    unknown_flag=_decode_value(group[6]),
                    criteria=_decode_value(group[7]),
                )
            )
        else:
            nodes.append(
                GraphNode(
                    node_id=_decode_value(group[0]),
                    position=_decode_value(group[1]),
                    height_offset=_decode_value(group[2]),
                    radius=_decode_value(group[3]),
                    material_id=_decode_value(group[4]),
                    criteria=_decode_value(group[5]),
                )
            )

    return nodes


def _build_edges(entries: list[TLVEntry]) -> list[GraphEdge]:
    edge_entries = [e for e in entries if e.property_hash in EDGE_HASHES]

    if len(edge_entries) % 3 != 0:
        raise ValueError(f"Edge entry count {len(edge_entries)} is not divisible by 3")

    edges = []
    for i in range(0, len(edge_entries), 3):
        group = edge_entries[i : i + 3]

        expected_order = [HASH_EDGE_TARGET, HASH_EDGE_SOURCE, HASH_EDGE_WEIGHT]

        for j, expected_hash in enumerate(expected_order):
            if group[j].property_hash != expected_hash:
                raise ValueError(
                    f"Edge entry {i + j}: expected hash 0x{expected_hash:06X}, got 0x{group[j].property_hash:06X}"
                )

        edges.append(
            GraphEdge(
                target=_decode_value(group[0]),
                source=_decode_value(group[1]),
                weight=_decode_value(group[2]),
            )
        )

    return edges


def _write_tlv_entry(stream: BytesIO, property_hash: int, type_code: int, payload: bytes) -> None:
    stream.write(bytes([TLV_MARKER]))
    stream.write(property_hash.to_bytes(3, "little"))
    stream.write(b"\x00\x00")
    stream.write(struct.pack("<H", type_code))
    if type_code == TYPE_VARIABLE:
        stream.write(bytes([len(payload)]))
    stream.write(payload)


class DATGraph(FileModel):
    """DAT Graph — AI navigation graph with nodes and edges."""

    max_node_capacity: NonNegativeInt
    nodes: list[GraphNode]
    edges: list[GraphEdge]

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        magic = struct.unpack("<I", stream.read(4))[0]
        if magic != MAGIC:
            raise ValueError(f"Expected magic 0x{MAGIC:08X}, got 0x{magic:08X}")

        entries = _read_tlv_entries(stream)

        header_entries = [e for e in entries if e.property_hash == HASH_MAX_NODE_CAPACITY]
        if len(header_entries) != 1:
            raise ValueError(f"Expected 1 header entry, got {len(header_entries)}")

        max_node_capacity = _decode_value(header_entries[0])
        nodes = _build_nodes(entries)
        edges = _build_edges(entries)

        return cls(max_node_capacity=max_node_capacity, nodes=nodes, edges=edges)

    def model_dump_stream(self) -> tuple[BytesIO, str]:
        stream = BytesIO()
        stream.write(struct.pack("<I", MAGIC))

        _write_tlv_entry(stream, HASH_MAX_NODE_CAPACITY, TYPE_UINT32, struct.pack("<I", self.max_node_capacity))

        for node in self.nodes:
            _write_tlv_entry(stream, HASH_NODE_ID, TYPE_UINT32, struct.pack("<I", node.node_id))
            _write_tlv_entry(stream, HASH_NODE_POSITION, TYPE_3XFLOAT64, struct.pack("<3d", *node.position))
            _write_tlv_entry(stream, HASH_NODE_HEIGHT_OFFSET, TYPE_FLOAT32, struct.pack("<f", node.height_offset))
            _write_tlv_entry(stream, HASH_NODE_RADIUS, TYPE_FLOAT32, struct.pack("<f", node.radius))
            _write_tlv_entry(stream, HASH_NODE_MATERIAL_ID, TYPE_UINT32, struct.pack("<I", node.material_id))
            if node.light_intensity is not None:
                _write_tlv_entry(
                    stream, HASH_NODE_LIGHT_INTENSITY, TYPE_FLOAT32, struct.pack("<f", node.light_intensity)
                )
            if node.unknown_flag is not None:
                _write_tlv_entry(stream, HASH_NODE_UNKNOWN_FLAG, TYPE_UINT32, struct.pack("<I", node.unknown_flag))
            _write_tlv_entry(stream, HASH_NODE_CRITERIA, TYPE_VARIABLE, node.criteria)

        for edge in self.edges:
            _write_tlv_entry(stream, HASH_EDGE_TARGET, TYPE_UINT32, struct.pack("<I", edge.target))
            _write_tlv_entry(stream, HASH_EDGE_SOURCE, TYPE_UINT32, struct.pack("<I", edge.source))
            _write_tlv_entry(stream, HASH_EDGE_WEIGHT, TYPE_UINT32, struct.pack("<I", edge.weight))

        stream.seek(0)
        return stream, ".dat"
