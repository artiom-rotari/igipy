from abc import ABC
from functools import singledispatchmethod
from io import BytesIO
from struct import Struct, unpack
from typing import Any, BinaryIO, ClassVar, Literal, Self

from pydantic import BaseModel, NonNegativeInt

from igipy.core.base import FileModel
from igipy.core.formats import qsc


class Instruction(BaseModel, ABC):
    address: NonNegativeInt
    next_address: NonNegativeInt

    @classmethod
    def model_validate_stream(cls, stream: BinaryIO, address: NonNegativeInt) -> Self:
        return cls(address=address, next_address=stream.tell())


class NotImplementedInstruction(Instruction, ABC):
    @classmethod
    def model_validate_stream(cls, stream: BinaryIO, address: NonNegativeInt) -> Self:
        raise NotImplementedError(f"{cls.__name__} is not implemented")


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


class QVMHeader(BaseModel):
    signature: Literal[b"LOOP"]
    major_version: Literal[8]
    minor_version: Literal[5, 7]
    variables_points_offset: NonNegativeInt
    variables_data_offset: NonNegativeInt
    variables_points_size: NonNegativeInt
    variables_data_size: NonNegativeInt
    strings_points_offset: NonNegativeInt
    strings_data_offset: NonNegativeInt
    strings_points_size: NonNegativeInt
    strings_data_size: NonNegativeInt
    instructions_data_offset: NonNegativeInt
    instructions_data_size: NonNegativeInt
    unknown_1: Literal[0]
    unknown_2: Literal[0]
    footer_data_offset: NonNegativeInt | None = None

    @classmethod
    def model_validate_bytes(cls, data: bytes) -> "QVMHeader":
        obj_values = unpack("4s14I", data[:60])
        obj_mapping = dict(zip(cls.__pydantic_fields__.keys(), obj_values, strict=False))
        obj = cls(**obj_mapping)

        if obj.minor_version == 5 and len(data[60:]) > 4:  # noqa: PLR2004
            footer_offset = unpack("I", data[60:64])[0]
            obj.footer_data_offset = footer_offset

        return obj

    @property
    def variables_slice(self) -> slice:
        return slice(self.variables_data_offset, self.variables_data_offset + self.variables_data_size)

    @property
    def strings_slice(self) -> slice:
        return slice(self.strings_data_offset, self.strings_data_offset + self.strings_data_size)

    @property
    def instructions_slice(self) -> slice:
        return slice(self.instructions_data_offset, self.instructions_data_offset + self.instructions_data_size)


class QVM(FileModel):
    header: QVMHeader
    variables: list[str]
    strings: list[str]
    instructions: dict[int, Instruction]

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        return cls.model_validate_bytes(data=stream.read())

    @classmethod
    def model_validate_bytes(cls, data: bytes) -> Self:
        header = QVMHeader.model_validate_bytes(data=data)

        variables = cls.bytes_to_list_of_strings(data=data[header.variables_slice])
        strings = cls.bytes_to_list_of_strings(data=data[header.strings_slice])

        instructions = cls.bytes_to_dict_of_instructions(
            data=data[header.instructions_slice],
            version=header.minor_version,
        )

        return cls(header=header, variables=variables, strings=strings, instructions=instructions)

    @classmethod
    def bytes_to_list_of_strings(cls, data: bytes) -> list[str]:
        value_bytes = data.split(b"\x00")[:-1]
        value_strings = [value.decode("utf-8") for value in value_bytes]
        value = [value.replace("\n", "\\n").replace('"', '\\"') for value in value_strings]
        return value  # noqa: RET504

    @classmethod
    def bytes_to_dict_of_instructions(cls, data: bytes, version: Literal[5, 7]) -> dict[int, Instruction]:
        stream = BytesIO(data)
        result = {}
        bytecode_to_instruction = QVM_INSTRUCTION[version]

        while stream.tell() < len(data):
            address = stream.tell()
            instruction_class = bytecode_to_instruction.get(stream.read(1), NotImplementedInstruction)
            instruction = instruction_class.model_validate_stream(stream, address)
            result[instruction.address] = instruction

        return result

    def rebuild_stack(self, next_address: int = 0, stop_address: int | None = None) -> qsc.Stack:
        stack = qsc.Stack()

        while next_address != stop_address:
            try:
                instruction = self.instructions[next_address]
                next_address = self.to_ast(instruction, stack=stack)
            except StopIteration:
                break

        return stack

    def rebuild_block(self, next_address: int = 0, stop_address: int | None = None) -> qsc.BlockStatement:
        stack = self.rebuild_stack(next_address=next_address, stop_address=stop_address)
        statements = []

        for node in stack.root:
            if isinstance(node, qsc.Expression):
                statement_node = qsc.ExprStatement(expression=node)
            elif isinstance(node, qsc.Statement):
                statement_node = node
            else:
                raise TypeError(f"Unexpected node type: {type(node)}")

            statements.append(statement_node)

        return qsc.BlockStatement(statements=statements)

    @singledispatchmethod
    def to_ast(self, instruction: Instruction, stack: qsc.Stack) -> int:
        raise NotImplementedError(f"Not implemented for {type(instruction)}")

    @to_ast.register
    def _(self, instruction: LiteralInstruction, stack: qsc.Stack) -> int:
        stack.push(qsc.Literal(value=instruction.value))
        return instruction.next_address

    @to_ast.register
    def _(self, instruction: ConstantInstruction, stack: qsc.Stack) -> int:
        stack.push(qsc.Literal(value=instruction.value))
        return instruction.next_address

    @to_ast.register
    def _(self, instruction: StringInstruction, stack: qsc.Stack) -> int:
        stack.push(qsc.Literal(value=self.strings[instruction.value]))
        return instruction.next_address

    @to_ast.register
    def _(self, instruction: VariableInstruction, stack: qsc.Stack) -> int:
        stack.push(qsc.Variable(name=self.variables[instruction.value]))
        return instruction.next_address

    @to_ast.register
    def _(self, instruction: UnaryOpInstruction, stack: qsc.Stack) -> int:
        operand = stack.pop_expression()
        node = qsc.UnaryOp(operator=qsc.UnaryOp.Operator(instruction.operator), operand=operand)
        stack.push(node)
        return instruction.next_address

    @to_ast.register
    def _(self, instruction: BinaryOpInstruction, stack: qsc.Stack) -> int:
        right = stack.pop_expression()
        left = stack.pop_expression()
        node = qsc.BinaryOp(operator=qsc.BinaryOp.Operator(instruction.operator), left=left, right=right)
        stack.push(node)
        return instruction.next_address

    # noinspection PyUnusedLocal
    @to_ast.register
    def _(self, instruction: POP, stack: qsc.Stack) -> int:  # noqa: ARG002
        return instruction.next_address

    @to_ast.register
    def _(self, instruction: BRK, stack: qsc.Stack) -> int:  # noqa: ARG002
        raise StopIteration

    @to_ast.register
    def _(self, instruction: BRA, stack: qsc.Stack) -> int:  # noqa: ARG002
        raise StopIteration

    @to_ast.register
    def _(self, instruction: CALL, stack: qsc.Stack) -> int:
        function: qsc.Variable = stack.pop_variable()
        arguments: list[qsc.Expression] = []

        for argument_address in instruction.value:
            argument_stack = self.rebuild_stack(next_address=argument_address, stop_address=None)
            argument = argument_stack.pop_expression()
            argument_stack.empty()
            arguments.append(argument)

        stack.push(qsc.Call(function=function.name, arguments=arguments))

        next_instruction = self.instructions[instruction.next_address]
        next_address = next_instruction.next_address + next_instruction.value

        return next_address  # noqa: RET504

    @to_ast.register
    def _(self, instruction: BF, stack: qsc.Stack) -> int:
        condition = stack.pop_expression()
        then_block = self.rebuild_block(next_address=instruction.next_address, stop_address=None)

        next_instruction_address = instruction.next_address + instruction.value - 5
        next_instruction = self.instructions[next_instruction_address]

        if next_instruction.value > 0:
            else_block = self.rebuild_block(
                next_address=instruction.next_address + instruction.value,
                stop_address=next_instruction.next_address + next_instruction.value,
            )

            node = qsc.IfStatement(condition=condition, then_block=then_block, else_block=else_block)
            next_address = next_instruction.next_address + next_instruction.value

        elif next_instruction.value == 0:
            node = qsc.IfStatement(condition=condition, then_block=then_block)
            next_address = instruction.next_address + instruction.value

        else:
            node = qsc.WhileStatement(condition=condition, loop_block=then_block)
            next_address = instruction.next_address + instruction.value

        stack.push(node)

        return next_address
