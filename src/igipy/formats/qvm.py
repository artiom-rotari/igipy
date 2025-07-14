import subprocess
from functools import cached_property, singledispatchmethod
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
    def from_stream(cls, stream: BytesIO) -> Self:
        values = unpack("<4s14I", stream.read(60))
        fields = list(cls.__pydantic_fields__.keys())
        fields.remove("footer_data_offset")

        dictionary = dict(zip(fields, values, strict=True))

        if dictionary["minor_version"] == 7:
            dictionary["footer_data_offset"] = unpack("<I", stream.read(4))[0]

        return cls(**dictionary)


class QVMStrings(BaseModel):
    root: dict[int, str]

    @classmethod
    def from_stream(
        cls, stream: BytesIO, table_offset: int, table_length: int, value_offset: int, value_length: int
    ) -> Self:
        stream.seek(table_offset)
        table = unpack(f"<{table_length // 4}I", stream.read(table_length))

        stream.seek(value_offset)
        value_bytes = stream.read(value_length)
        value_dirty = [value.decode("utf-8") for value in value_bytes.split(b"\x00")[:-1]]
        value_clean = [value.replace("\n", "\\n").replace('"', '\\"') for value in value_dirty]

        return cls(root=dict(zip(table, value_clean, strict=True)))

    @cached_property
    def table_bytes(self) -> bytes:
        return pack(f"<{len(self.root)}I", *self.root.keys())

    @cached_property
    def value_bytes(self) -> bytes:
        value_dirty = [value.replace("\\n", "\n").replace('\\"', '"') for value in self.root.values()]
        return b"".join([string.encode("utf-8") + b"\x00" for string in value_dirty])


class QVM(FileModel):
    header: QVMHeader
    variables_pool: QVMStrings
    strings_pool: QVMStrings
    instructions: dict[int, ins.Instruction]

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        header = QVMHeader.from_stream(stream)

        variables_pool = QVMStrings.from_stream(
            stream,
            table_offset=header.variables_points_offset,
            table_length=header.variables_points_size,
            value_offset=header.variables_data_offset,
            value_length=header.variables_data_size,
        )

        strings_pool = QVMStrings.from_stream(
            stream,
            table_offset=header.strings_points_offset,
            table_length=header.strings_points_size,
            value_offset=header.strings_data_offset,
            value_length=header.strings_data_size,
        )

        instruction_mapping = ins.QVM_INSTRUCTION[header.minor_version]

        stream.seek(header.instructions_data_offset)
        instruction_stream = BytesIO(stream.read(header.instructions_data_size))

        instruction_pool = {}

        while instruction_stream.tell() < header.instructions_data_size:
            address = instruction_stream.tell()
            instruction_class = instruction_mapping.get(instruction_stream.read(1), ins.NotImplementedInstruction)
            instruction = instruction_class.model_validate_stream(instruction_stream, address)
            instruction_pool[instruction.address] = instruction

        return cls(
            header=header,
            variables_pool=variables_pool,
            strings_pool=strings_pool,
            instructions=instruction_pool,
        )

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

        variables_table = self.variables_pool.table_bytes
        variables_value = self.variables_pool.value_bytes
        strings_table = self.strings_pool.table_bytes
        strings_value = self.strings_pool.value_bytes

        instructions_data_stream = BytesIO()

        for instruction in self.instructions.values():
            instructions_data_stream.write(ins.QVM_BYTECODE[ins.QVM_VERSION_5][instruction.__class__])
            instruction.model_dump_stream(instructions_data_stream)

        instructions_data = instructions_data_stream.getvalue()

        header_dict = {
            "signature": b"LOOP",
            "major_version": 8,
            "minor_version": 5,
            "variables_points_offset": 60,
            "variables_data_offset": 60 + len(variables_table),
            "variables_points_size": len(variables_table),
            "variables_data_size": len(variables_value),
            "strings_points_offset": 60 + len(variables_table) + len(variables_value),
            "strings_data_offset": 60 + len(variables_table) + len(variables_value) + len(strings_table),
            "strings_points_size": len(strings_table),
            "strings_data_size": len(strings_value),
            "instructions_data_offset": (
                60 + len(variables_table) + len(variables_value) + len(strings_table) + len(strings_value)
            ),
            "instructions_data_size": len(instructions_data),
            "unknown_1": 0,
            "unknown_2": 0,
        }

        header_data = pack("<4s14I", *list(header_dict.values()))

        stream.write(header_data)
        stream.write(variables_table)
        stream.write(variables_value)
        stream.write(strings_table)
        stream.write(strings_value)
        stream.write(instructions_data)

        return stream

    def to_qvm_v5_file(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.to_qvm_v5_stream().getvalue())

    @cached_property
    def variables(self) -> list[str]:
        return list(self.variables_pool.root.values())

    @cached_property
    def strings(self) -> list[str]:
        return list(self.strings_pool.root.values())

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

            qsc_model = qvm_model.to_qsc()
            qsc_model.to_file(decoded_path)
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

        encode_qsc_path = cls.get_encode_qsc_path(config)
        encode_qsc_model.to_file(encode_qsc_path)
        typer.secho(f"QSC script saved: {encode_qsc_path.as_posix()}", fg=typer.colors.YELLOW)

    # noinspection DuplicatedCode
    @classmethod
    def cli_encode_all(cls, config: GameConfig, **kwargs: dict) -> None:  # noqa: ARG003
        encode_qsc_path = cls.get_encode_qsc_path(config)

        if not encode_qsc_path.is_file(follow_symlinks=False):
            typer.secho(f"File not found: {encode_qsc_path.as_posix()}", fg=typer.colors.RED)

        result = subprocess.run(
            [config.gconv.absolute().as_posix(), encode_qsc_path.relative_to(config.work_dir).as_posix()],
            cwd=config.work_dir.absolute().as_posix(),
            check=False,
        )

        if result.returncode != 0:
            typer.secho(f"Error while running gconv: {result.stderr}", fg=typer.colors.RED)
            raise typer.Exit(code=result.returncode)

        for src_path in config.decoded_dir.glob("**/*.qvm"):
            dst_path = config.build_dir / src_path.relative_to(config.decoded_dir)
            qvm_v7_model = cls.model_validate_file(src_path)
            qvm_v7_model.to_qvm_v5_file(dst_path)
            typer.secho(f"Created {dst_path.as_posix()}", fg=typer.colors.GREEN)

            src_path.unlink()
            typer.secho(f"Deleted {src_path.as_posix()}", fg=typer.colors.YELLOW)

    @classmethod
    def get_encode_qsc_path(cls, config: GameConfig) -> Path:
        return config.scripts_dir / "encode-all-qvm.qsc"
