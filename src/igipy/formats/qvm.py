import subprocess
from functools import singledispatchmethod
from io import BytesIO
from pathlib import Path
from struct import pack, unpack
from typing import Literal, Self

import typer
from pydantic import BaseModel, NonNegativeInt

from igipy.config import GameConfig
from igipy.formats import FileModel, qsc
from igipy.formats.utils import ins


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
        obj_values = unpack("<4s14I", data[:60])
        obj_mapping = dict(zip(cls.__pydantic_fields__.keys(), obj_values, strict=False))
        obj = cls(**obj_mapping)

        if obj.minor_version == 5 and len(data[60:]) > 4:  # noqa: PLR2004
            obj.footer_data_offset = unpack("<I", data[60:64])[0]

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
    instructions: dict[int, ins.Instruction]

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
    def bytes_to_dict_of_instructions(cls, data: bytes, version: Literal[5, 7]) -> dict[int, ins.Instruction]:
        stream = BytesIO(data)
        result = {}
        bytecode_to_instruction = ins.QVM_INSTRUCTION[version]

        while stream.tell() < len(data):
            address = stream.tell()
            instruction_class = bytecode_to_instruction.get(stream.read(1), ins.NotImplementedInstruction)
            instruction = instruction_class.model_validate_stream(stream, address)
            result[instruction.address] = instruction

        return result

    def to_qsc(self) -> qsc.QSC:
        return qsc.QSC(content=self.rebuild_block())

    def to_qsc_stream(self) -> BytesIO:
        return self.to_qsc().to_stream()

    def to_qsc_file(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.to_qsc_stream().getvalue())

    def to_qvm_v5_stream(self) -> BytesIO:
        stream = BytesIO()

        variables_offset: int = 0
        variables_points: list[int] = []

        for string in self.variables:
            variables_points.append(variables_offset)
            variables_offset += len(string) + 1

        variables_points_data = pack(f"<{len(variables_points)}I", *variables_points)
        variables_data = b"".join([string.encode("latin1") + b"\x00" for string in self.variables])

        strings_offset: int = 0
        strings_points: list[int] = []

        for string in self.strings:
            strings_points.append(strings_offset)
            strings_offset += len(string) + 1

        strings_points_data = pack(f"<{len(strings_points)}I", *strings_points)
        strings_data = b"".join([string.encode("latin1") + b"\x00" for string in self.strings])

        instructions_data_stream = BytesIO()

        for instruction in self.instructions.values():
            instructions_data_stream.write(ins.QVM_BYTECODE[ins.QVM_VERSION_5][instruction.__class__])
            instruction.model_dump_stream(instructions_data_stream)

        instructions_data = instructions_data_stream.getvalue()

        header_data = pack(
            "<4s14I",
            b"LOOP",
            8,
            5,
            60,
            60 + len(variables_points_data),
            len(variables_points_data),
            len(variables_data),
            60 + len(variables_points_data) + len(variables_data),
            60 + len(variables_points_data) + len(variables_data) + len(strings_points_data),
            len(strings_points_data),
            len(strings_data),
            60 + len(variables_points_data) + len(variables_data) + len(strings_points_data) + len(strings_data),
            len(instructions_data),
            0,
            0,
        )

        stream.write(header_data)
        stream.write(variables_points_data)
        stream.write(variables_data)
        stream.write(strings_points_data)
        stream.write(strings_data)
        stream.write(instructions_data)

        return stream

    def to_qvm_v5_file(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.to_qvm_v5_stream().getvalue())

    def rebuild_stack(self, next_address: int = 0, stop_address: int | None = None) -> qsc.Stack:
        stack = qsc.Stack()

        while next_address != stop_address:
            try:
                instruction = self.instructions[next_address]
                next_address = self.instruction_to_ast(instruction, stack=stack)
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
    def instruction_to_ast(self, instruction: ins.Instruction, stack: qsc.Stack) -> int:
        raise NotImplementedError(f"Not implemented for {type(instruction)}")

    @instruction_to_ast.register
    def _(self, instruction: ins.LiteralInstruction, stack: qsc.Stack) -> int:
        stack.push(qsc.Literal(value=instruction.value))
        return instruction.next_address

    @instruction_to_ast.register
    def _(self, instruction: ins.ConstantInstruction, stack: qsc.Stack) -> int:
        stack.push(qsc.Literal(value=instruction.value))
        return instruction.next_address

    @instruction_to_ast.register
    def _(self, instruction: ins.StringInstruction, stack: qsc.Stack) -> int:
        stack.push(qsc.Literal(value=self.strings[instruction.value]))
        return instruction.next_address

    @instruction_to_ast.register
    def _(self, instruction: ins.VariableInstruction, stack: qsc.Stack) -> int:
        stack.push(qsc.Variable(name=self.variables[instruction.value]))
        return instruction.next_address

    @instruction_to_ast.register
    def _(self, instruction: ins.UnaryOpInstruction, stack: qsc.Stack) -> int:
        operand = stack.pop_expression()
        node = qsc.UnaryOp(operator=qsc.UnaryOp.Operator(instruction.operator), operand=operand)
        stack.push(node)
        return instruction.next_address

    @instruction_to_ast.register
    def _(self, instruction: ins.BinaryOpInstruction, stack: qsc.Stack) -> int:
        right = stack.pop_expression()
        left = stack.pop_expression()
        node = qsc.BinaryOp(operator=qsc.BinaryOp.Operator(instruction.operator), left=left, right=right)
        stack.push(node)
        return instruction.next_address

    # noinspection PyUnusedLocal
    @instruction_to_ast.register
    def _(self, instruction: ins.POP, stack: qsc.Stack) -> int:  # noqa: ARG002
        return instruction.next_address

    @instruction_to_ast.register
    def _(self, instruction: ins.BRK, stack: qsc.Stack) -> int:  # noqa: ARG002
        raise StopIteration

    @instruction_to_ast.register
    def _(self, instruction: ins.BRA, stack: qsc.Stack) -> int:  # noqa: ARG002
        raise StopIteration

    @instruction_to_ast.register
    def _(self, instruction: ins.CALL, stack: qsc.Stack) -> int:
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

    @instruction_to_ast.register
    def _(self, instruction: ins.BF, stack: qsc.Stack) -> int:
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

    @classmethod
    def cli_decode_all(cls, config: GameConfig, pattern: str = "**/*.qvm") -> None:
        encode_qsc_model = qsc.QSC(content=qsc.BlockStatement(statements=[]))

        for src_path in config.game_dir.glob(pattern):
            if not src_path.is_file(follow_symlinks=False):
                continue

            decoded_path = config.decoded_dir / src_path.relative_to(config.game_dir).with_suffix(".qsc")

            qvm_model = cls.model_validate_file(src_path)

            decoded_path.parent.mkdir(parents=True, exist_ok=True)
            decoded_path.write_bytes(qvm_model.model_dump_stream()[0].getvalue())
            typer.secho(f"Created {decoded_path.as_posix()}", fg=typer.colors.GREEN)

            encode_qsc_model.content.statements.append(
                qsc.ExprStatement(
                    expression=qsc.Call(
                        function="CompileScript",
                        arguments=[
                            qsc.Literal(value=decoded_path.relative_to(config.work_dir).as_posix()),
                        ],
                    )
                )
            )

        encode_qsc_path = cls.get_decode_qsc_path(config)
        encode_qsc_model.to_file(encode_qsc_path)
        typer.secho(f"QSC script saved: {encode_qsc_path.as_posix()}", fg=typer.colors.YELLOW)

    # noinspection DuplicatedCode
    @classmethod
    def cli_encode_all(cls, config: GameConfig, **kwargs: dict) -> None:  # noqa: ARG003
        encode_qsc_path = cls.get_encode_qsc_path(config)

        if not encode_qsc_path.is_file(follow_symlinks=False):
            typer.secho(f"File not found: {encode_qsc_path.as_posix()}", fg=typer.colors.RED)

        subprocess.run(
            [config.gconv.absolute().as_posix(), encode_qsc_path.relative_to(config.work_dir).as_posix()],
            cwd=config.work_dir.absolute().as_posix(),
            check=False,
        )

        for src_path in config.decoded_dir.glob("**/*.qvm"):
            dst_path = config.build_dir / src_path.relative_to(config.decoded_dir)
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            src_path.replace(dst_path)

    @classmethod
    def get_encode_qsc_path(cls, config: GameConfig) -> Path:
        return config.scripts_dir / "encode-all-qvm.qsc"
