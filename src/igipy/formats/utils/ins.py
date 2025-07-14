from abc import ABC
from io import BytesIO
from struct import Struct, unpack
from typing import Any, BinaryIO, ClassVar, Self

from pydantic import BaseModel, NonNegativeInt


class Instruction(BaseModel, ABC):
    address: NonNegativeInt
    next_address: NonNegativeInt

    @classmethod
    def model_validate_stream(cls, stream: BinaryIO, address: NonNegativeInt) -> Self:
        return cls(address=address, next_address=stream.tell())

    def model_dump_stream(self, stream: BinaryIO) -> None:
        pass


class NotImplementedInstruction(Instruction, ABC):
    @classmethod
    def model_validate_stream(cls, stream: BinaryIO, address: NonNegativeInt) -> Self:
        raise NotImplementedError(f"{cls.__name__} is not implemented")

    def model_dump_stream(self, stream: BinaryIO) -> None:
        raise NotImplementedError(f"{self.__class__.__name__} is not implemented")


NOP = type("NOP", (NotImplementedInstruction,), {})
RET = type("RET", (NotImplementedInstruction,), {})
BT = type("BT", (NotImplementedInstruction,), {})
JSR = type("JSR", (NotImplementedInstruction,), {})
PUSHA = type("PUSHA", (NotImplementedInstruction,), {})
PUSHS = type("PUSHS", (NotImplementedInstruction,), {})
PUSHI = type("PUSHI", (NotImplementedInstruction,), {})
BLK = type("BLK", (NotImplementedInstruction,), {})
ILLEGAL = type("ILLEGAL", (NotImplementedInstruction,), {})


class StructInstruction(Instruction, ABC):
    value_struct: ClassVar[Struct]
    value: Any

    @classmethod
    def model_validate_stream(cls, stream: BytesIO, address: NonNegativeInt) -> Self:
        value = cls.value_struct.unpack(stream.read(cls.value_struct.size))[0]
        return cls(address=address, next_address=stream.tell(), value=value)

    def model_dump_stream(self, stream: BytesIO) -> None:
        stream.write(self.value_struct.pack(self.value))


class LiteralInstruction(Instruction, ABC):
    value_struct: ClassVar[Struct] = Struct("<I")
    value: int | float


PUSH = type("PUSH", (LiteralInstruction, StructInstruction), {"value_struct": Struct("<I")})
PUSHB = type("PUSHB", (LiteralInstruction, StructInstruction), {"value_struct": Struct("<B")})
PUSHW = type("PUSHW", (LiteralInstruction, StructInstruction), {"value_struct": Struct("<H")})
PUSHF = type("PUSHF", (LiteralInstruction, StructInstruction), {"value_struct": Struct("<f")})


class ConstantInstruction(Instruction, ABC):
    value_struct: ClassVar[Struct] = Struct("<I")
    value: ClassVar[int]


PUSH0 = type("PUSH0", (ConstantInstruction,), {"value": 0})
PUSH1 = type("PUSH1", (ConstantInstruction,), {"value": 1})
PUSHM = type("PUSHM", (ConstantInstruction,), {"value": 0xFFFFFFFF})


class StringInstruction(Instruction, ABC):
    value_struct: ClassVar[Struct] = Struct("<I")
    value: int


PUSHSI = type("PUSHSI", (StringInstruction, StructInstruction), {"value_struct": Struct("<I")})
PUSHSIB = type("PUSHSIB", (StringInstruction, StructInstruction), {"value_struct": Struct("<B")})
PUSHSIW = type("PUSHSIW", (StringInstruction, StructInstruction), {"value_struct": Struct("<H")})


class VariableInstruction(Instruction, ABC):
    value_struct: ClassVar[Struct] = Struct("<I")
    value: int


PUSHII = type("PUSHII", (VariableInstruction, StructInstruction), {"value_struct": Struct("<I")})
PUSHIIB = type("PUSHIIB", (VariableInstruction, StructInstruction), {"value_struct": Struct("<B")})
PUSHIIW = type("PUSHIIW", (VariableInstruction, StructInstruction), {"value_struct": Struct("<H")})


class UnaryOpInstruction(Instruction, ABC):
    operator: ClassVar[str]


PLUS = type("PLUS", (UnaryOpInstruction,), {"operator": "+"})
MINUS = type("MINUS", (UnaryOpInstruction,), {"operator": "-"})
INV = type("INV", (UnaryOpInstruction,), {"operator": "~"})
NOT = type("NOT", (UnaryOpInstruction,), {"operator": "!"})


class BinaryOpInstruction(Instruction, ABC):
    operator: ClassVar[str]


ADD = type("ADD", (BinaryOpInstruction,), {"operator": "+"})
SUB = type("SUB", (BinaryOpInstruction,), {"operator": "-"})
MUL = type("MUL", (BinaryOpInstruction,), {"operator": "*"})
DIV = type("DIV", (BinaryOpInstruction,), {"operator": "/"})
SHL = type("SHL", (BinaryOpInstruction,), {"operator": "<<"})
SHR = type("SHR", (BinaryOpInstruction,), {"operator": ">>"})
AND = type("AND", (BinaryOpInstruction,), {"operator": "&"})
OR = type("OR", (BinaryOpInstruction,), {"operator": "|"})
XOR = type("XOR", (BinaryOpInstruction,), {"operator": "^"})
LAND = type("LAND", (BinaryOpInstruction,), {"operator": "&&"})
LOR = type("LOR", (BinaryOpInstruction,), {"operator": "||"})
EQ = type("EQ", (BinaryOpInstruction,), {"operator": "=="})
NE = type("NE", (BinaryOpInstruction,), {"operator": "!="})
LT = type("LT", (BinaryOpInstruction,), {"operator": "<"})
LE = type("LE", (BinaryOpInstruction,), {"operator": "<="})
GT = type("GT", (BinaryOpInstruction,), {"operator": ">"})
GE = type("GE", (BinaryOpInstruction,), {"operator": ">="})
ASSIGN = type("ASSIGN", (BinaryOpInstruction,), {"operator": "="})


class CALL(Instruction):
    value: list[int]

    @classmethod
    def model_validate_stream(cls, stream: BinaryIO, address: NonNegativeInt) -> Self:
        value_count: int = unpack("<I", stream.read(4))[0]
        value_bytes = stream.read(4 * value_count)
        value = unpack("<" + "i" * value_count, value_bytes)
        return cls(address=address, next_address=stream.tell(), value=list(value))

    def model_dump_stream(self, stream: BinaryIO) -> None:
        stream.write(Struct("<I").pack(len(self.value)))
        stream.write(Struct("<" + "i" * len(self.value)).pack(*self.value))


POP = type("POP", (Instruction,), {})

BF = type("BF", (StructInstruction,), {"value_struct": Struct("<i")})

BRK = type("BRK", (Instruction,), {})
BRA = type("BRA", (StructInstruction,), {"value_struct": Struct("<i")})


QVM_VERSION_5 = 5

QVM_VERSION_7 = 7

# noinspection DuplicatedCode
QVM_INSTRUCTION: dict[int, dict[bytes, type[Instruction]]] = {
    QVM_VERSION_5: {
        b"\x00": BRK,
        b"\x01": NOP,
        b"\x02": PUSH,
        b"\x03": PUSHB,
        b"\x04": PUSHW,
        b"\x05": PUSHF,
        b"\x06": PUSHA,
        b"\x07": PUSHS,
        b"\x08": PUSHSI,
        b"\x09": PUSHSIB,
        b"\x0a": PUSHSIW,
        b"\x0b": PUSHI,
        b"\x0c": PUSHII,
        b"\x0d": PUSHIIB,
        b"\x0e": PUSHIIW,
        b"\x0f": PUSH0,
        b"\x10": PUSH1,
        b"\x11": PUSHM,
        b"\x12": POP,
        b"\x13": RET,
        b"\x14": BRA,
        b"\x15": BF,
        b"\x16": BT,
        b"\x17": JSR,
        b"\x18": CALL,
        b"\x19": ADD,
        b"\x1a": SUB,
        b"\x1b": MUL,
        b"\x1c": DIV,
        b"\x1d": SHL,
        b"\x1e": SHR,
        b"\x1f": AND,
        b"\x20": OR,
        b"\x21": XOR,
        b"\x22": LAND,
        b"\x23": LOR,
        b"\x24": EQ,
        b"\x25": NE,
        b"\x26": LT,
        b"\x27": LE,
        b"\x28": GT,
        b"\x29": GE,
        b"\x2a": ASSIGN,
        b"\x2b": PLUS,
        b"\x2c": MINUS,
        b"\x2d": INV,
        b"\x2e": NOT,
        b"\x2f": BLK,
        b"\x30": ILLEGAL,
    },
    QVM_VERSION_7: {
        b"\x00": BRK,
        b"\x01": NOP,
        b"\x02": RET,
        b"\x03": BRA,
        b"\x04": BF,
        b"\x05": BT,
        b"\x06": JSR,
        b"\x07": CALL,
        b"\x08": PUSH,
        b"\x09": PUSHB,
        b"\x0a": PUSHW,
        b"\x0b": PUSHF,
        b"\x0c": PUSHA,
        b"\x0d": PUSHS,
        b"\x0e": PUSHSI,
        b"\x0f": PUSHSIB,
        b"\x10": PUSHSIW,
        b"\x11": PUSHI,
        b"\x12": PUSHII,
        b"\x13": PUSHIIB,
        b"\x14": PUSHIIW,
        b"\x15": PUSH0,
        b"\x16": PUSH1,
        b"\x17": PUSHM,
        b"\x18": POP,
        b"\x19": ADD,
        b"\x1a": SUB,
        b"\x1b": MUL,
        b"\x1c": DIV,
        b"\x1d": SHL,
        b"\x1e": SHR,
        b"\x1f": AND,
        b"\x20": OR,
        b"\x21": XOR,
        b"\x22": LAND,
        b"\x23": LOR,
        b"\x24": EQ,
        b"\x25": NE,
        b"\x26": LT,
        b"\x27": LE,
        b"\x28": GT,
        b"\x29": GE,
        b"\x2a": ASSIGN,
        b"\x2b": PLUS,
        b"\x2c": MINUS,
        b"\x2d": INV,
        b"\x2e": NOT,
        b"\x2f": BLK,
        b"\x30": ILLEGAL,
    },
}


QVM_BYTECODE: dict[int, dict[type[Instruction], bytes]] = {
    QVM_VERSION_5: dict(
        zip(QVM_INSTRUCTION[QVM_VERSION_5].values(), QVM_INSTRUCTION[QVM_VERSION_5].keys(), strict=False)
    ),
    QVM_VERSION_7: dict(
        zip(QVM_INSTRUCTION[QVM_VERSION_7].values(), QVM_INSTRUCTION[QVM_VERSION_7].keys(), strict=False)
    ),
}
