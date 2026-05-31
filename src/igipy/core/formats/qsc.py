from abc import ABC
from enum import StrEnum
from functools import singledispatchmethod
from io import BytesIO

from pydantic import BaseModel

from igipy.core.base import FileModel


class AST(BaseModel, ABC):
    """Base class for all AST nodes"""


class Expression(AST, ABC):
    """Base class for all expression nodes"""


class Literal(Expression):
    value: int | float | str | bool


class Variable(Expression):
    name: str


class UnaryOp(Expression):
    class Operator(StrEnum):
        PLUS = "+"
        MINUS = "-"
        INV = "~"
        NOT = "!"

        @property
        def precedence(self) -> int:
            return {
                self.PLUS: 11,
                self.MINUS: 11,
                self.INV: 11,
                self.NOT: 11,
            }[self]

    operand: Expression
    operator: Operator


class BinaryOp(Expression):
    class Operator(StrEnum):
        SUM = "+"
        SUB = "-"
        MUL = "*"
        DIV = "/"
        SHL = "<<"
        SHR = ">>"
        AND = "&"
        OR = "|"
        XOR = "^"
        LAND = "&&"
        LOR = "||"
        EQ = "=="
        NE = "!="
        LT = "<"
        LE = "<="
        GT = ">"
        GE = ">="
        ASSIGN = "="

        @property
        def precedence(self) -> int:
            return {
                self.LOR: 1,
                self.LAND: 2,
                self.OR: 3,
                self.XOR: 4,
                self.AND: 5,
                self.EQ: 6,
                self.NE: 6,
                self.LT: 7,
                self.LE: 7,
                self.GT: 7,
                self.GE: 7,
                self.SHL: 8,
                self.SHR: 8,
                self.SUM: 9,
                self.SUB: 9,
                self.MUL: 10,
                self.DIV: 10,
                self.ASSIGN: 0,
            }[self]

    left: Expression
    right: Expression
    operator: Operator


class Call(Expression):
    function: str
    arguments: list[Expression]


class Statement(AST):
    """Base class for all statement nodes"""


class BlockStatement(Statement):
    statements: list[Statement]


class IfStatement(Statement):
    condition: Expression
    then_block: BlockStatement
    else_block: BlockStatement | None = None


class WhileStatement(Statement):
    condition: Expression
    loop_block: BlockStatement


class ExprStatement(Statement):
    expression: Expression


class AssignStatement(Statement):
    target: Variable
    value: Expression


# noinspection PyStringConversionWithoutDunderMethod
class Stack(BaseModel):
    root: list[AST] = []

    def pop_expression(self) -> Expression:
        node = self.root.pop()

        if not isinstance(node, Expression):
            raise TypeError(f"Expected expression, got {type(node)}")

        return node

    def pop_variable(self) -> Variable:
        node = self.root.pop()

        if not isinstance(node, Variable):
            raise TypeError(f"Expected variable, got {type(node)}")

        return node

    def push(self, node: AST) -> None:
        if not isinstance(node, AST):
            raise TypeError(f"Expected node, got {type(node)}")
        self.root.append(node)

    def empty(self) -> bool:
        if self.root:
            raise ValueError("Stack is not empty")
        return True


# noinspection PyUnusedLocal
class QSC(FileModel):
    indent_width: int = 1
    indent_char: str = "\t"
    max_line_length: int = 300

    content: BlockStatement

    @property
    def indent(self) -> str:
        return self.indent_char * self.indent_width

    def model_dump_stream(self) -> tuple[BytesIO, str]:
        stream = BytesIO()
        stream_text = self.to_str(self.content, indent=0)
        stream_text = f"{stream_text.rstrip('\n')}\n"
        stream.write(stream_text.encode("utf-8"))
        return stream, ".qsc"

    @singledispatchmethod
    def to_str(self, node: AST, indent: int = 0, parent_precedence: int = 0) -> str:
        # noinspection PyStringConversionWithoutDunderMethod
        raise NotImplementedError(f"Not implemented for {type(node)}")

    @to_str.register
    def _(self, node: Literal, indent: int = 0, parent_precedence: int = 0) -> str:  # noqa: ARG002
        if isinstance(node.value, str):
            return f'"{node.value}"'

        if isinstance(node.value, bool):
            return "TRUE" if node.value else "FALSE"

        return str(node.value)

    @to_str.register
    def _(self, node: Variable, indent: int = 0, parent_precedence: int = 0) -> str:  # noqa: ARG002
        return node.name

    @to_str.register
    def _(self, node: UnaryOp, indent: int = 0, parent_precedence: int = 0) -> str:
        operand_string = self.to_str(node.operand, indent + 1, parent_precedence=node.operator.precedence)

        string = f"{node.operator.value}{operand_string}"
        string = f"({string})" if node.operator.precedence < parent_precedence else string

        return string  # noqa: RET504

    @to_str.register
    def _(self, node: BinaryOp, indent: int = 0, parent_precedence: int = 0) -> str:
        left_string = self.to_str(node.left, indent + 1, parent_precedence=node.operator.precedence)

        right_precedence = node.operator.precedence + (1 if node.operator.value != "=" else 0)
        right_string = self.to_str(node.right, indent + 1, parent_precedence=right_precedence)

        string = f"{left_string} {node.operator.value} {right_string}"
        string = f"({string})" if node.operator.precedence < parent_precedence else string

        return string  # noqa: RET504

    @to_str.register
    def _(self, node: Call, indent: int = 0, parent_precedence: int = 0) -> str:  # noqa: ARG002
        function_token = node.function
        token_length = len(function_token)
        token_list = []

        for argument in node.arguments:
            argument_token = self.to_str(argument, indent + 1)

            if isinstance(argument, Call):
                argument_token_indent = self.indent * (indent + 1)
                argument_token = f"\n{argument_token_indent}{argument_token}"
                token_length = len(argument_token) + 2
            elif len(argument_token) + token_length > self.max_line_length:
                argument_token = f"\n{argument_token}"
                token_length = len(argument_token) + 2
            else:
                token_length += len(argument_token) + 2

            token_list.append(argument_token)

        arguments_token = ", ".join(token_list)
        return f"{function_token}({arguments_token})"

    @to_str.register
    def _(self, node: ExprStatement, indent: int = 0, parent_precedence: int = 0) -> str:  # noqa: ARG002
        return f"{self.indent * indent}{self.to_str(node.expression, indent)};"

    @to_str.register
    def _(self, node: BlockStatement, indent: int = 0, parent_precedence: int = 0) -> str:  # noqa: ARG002
        lines = [self.to_str(stmt, indent) for stmt in node.statements]
        return "\n".join(lines)

    @to_str.register
    def _(self, node: IfStatement, indent: int = 0, parent_precedence: int = 0) -> str:  # noqa: ARG002
        lines = [
            f"{self.indent * indent}if({self.to_str(node.condition, indent + 1)})",
            f"{self.indent * indent}{{",
            *self.to_str(node.then_block, indent + 1).splitlines(),
            f"{self.indent * indent}}}",
        ]

        if node.else_block:
            lines.extend(
                [
                    f"{self.indent * indent}else",
                    f"{self.indent * indent}{{",
                    *self.to_str(node.else_block, indent + 1).splitlines(),
                    f"{self.indent * indent}}}",
                ]
            )

        return "\n".join(lines)
