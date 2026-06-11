"""Temporary helper: decode a level ``objects.qvm`` into a type-grouped JSON registry.

An ``objects.qsc`` script (decompiled from ``objects.qvm``) has two phases:

* **Declarations** — a block of ``Task_DeclareParameters("Type", "field", "fieldType", ...)``
  calls that describe, per object type, the ordered list of fields and their types.
* **Tasks** — a deeply nested tree of ``Task_New(id, "Type", "label", ...values..., ...children...)``
  calls that build the actual scene graph.

This converter uses the declarations only as a schema to name the positional ``Task_New``
values, then drops them. Instead of preserving the nested task tree, it **flattens** every
task (root or nested) into a single registry grouped by type:

```
{
  "<Type>": {
    "<id>": {"id": ..., "type": ..., "label": ..., "fields"|"values": ..., "children": [<id>, ...]}
  }
}
```

Top-level type groups are ordered alphabetically; within each group, objects are ordered by
ascending task id. ``children`` becomes a flat list of child ids (in source order) rather than
nested objects, so the whole graph is reachable by id lookup. JSON object keys are always
strings, so an integer id such as ``3998`` serializes as the quoted key ``"3998"``. If two
tasks ever share an id within the same type, the last one wins (plain dict assignment).
"""

import json
from io import BytesIO
from pathlib import Path

from igipy.core.formats import qsc
from igipy.core.formats.qvm import QVM

# Number of positional values each declared field type consumes in a Task_New call.
# Anything not listed here is a single-component field. These arities were verified
# empirically against the shipped IGI 2 objects.qvm files (the trailing booleans of every
# affected type land exactly on their declared bool8 positions). Note: "Real32x9" stores only
# 3 values in instances (Euler angles), not a full 9-element matrix, and "RangeReal32" stores
# a single value, so neither is what its name suggests.
FIELD_TYPE_ARITY: dict[str, int] = {
    "RGB": 3,
    "Real32x3": 3,
    "Real64x3": 3,
    "Real32x9": 3,
    "ObjectPos": 3,
    "Graph": 3,
}


def field_arity(field_type: str) -> int:
    return FIELD_TYPE_ARITY.get(field_type, 1)


def statement_to_call(statement: qsc.Statement) -> qsc.Call | None:
    """Return the wrapped Call when the statement is a top-level call expression."""
    if isinstance(statement, qsc.ExprStatement) and isinstance(statement.expression, qsc.Call):
        return statement.expression
    return None


def expression_to_value(expression: qsc.Expression, serializer: qsc.QSC) -> object:
    """Convert a single QSC value expression into a JSON-native value.

    Literals become their native int/float/str/bool, variables become their name (this
    covers enum/symbolic constants such as ``AIType_Defensive``), a signed numeric literal
    folds into a signed number, and any other expression falls back to its QSC source text.
    """
    if isinstance(expression, qsc.Literal):
        return expression.value

    if isinstance(expression, qsc.Variable):
        return expression.name

    if (
        isinstance(expression, qsc.UnaryOp)
        and isinstance(expression.operand, qsc.Literal)
        and isinstance(expression.operand.value, int | float)
        and not isinstance(expression.operand.value, bool)
    ):
        if expression.operator is qsc.UnaryOp.Operator.MINUS:
            return -expression.operand.value
        if expression.operator is qsc.UnaryOp.Operator.PLUS:
            return expression.operand.value

    return serializer.to_str(expression)


def collect_schema(block: qsc.BlockStatement) -> dict[str, list[tuple[str, str]]]:
    """Build a {type name: [(field name, field type), ...]} map from the declaration calls."""
    schema: dict[str, list[tuple[str, str]]] = {}

    for statement in block.statements:
        call = statement_to_call(statement)

        if call is None or call.function != "Task_DeclareParameters" or not call.arguments:
            continue

        type_name = call.arguments[0].value
        remaining = call.arguments[1:]
        field_definitions = [
            (remaining[index].value, remaining[index + 1].value) for index in range(0, len(remaining) - 1, 2)
        ]
        schema[type_name] = field_definitions

    return schema


def flatten_task(
    call: qsc.Call,
    schema: dict[str, list[tuple[str, str]]],
    serializer: qsc.QSC,
    accumulator: list[dict],
) -> object:
    """Flatten a Task_New call (and its descendants) into ``accumulator``; return its id.

    Each call becomes one object dict appended to ``accumulator``. Child Task_New calls are
    flattened recursively and referenced by id under the ``children`` key (in source order),
    rather than nested inline. The returned id lets the parent assemble its children list.
    """
    task_id = expression_to_value(call.arguments[0], serializer)
    task_type = call.arguments[1].value
    label = call.arguments[2].value

    value_expressions: list[qsc.Expression] = []
    child_calls: list[qsc.Call] = []

    for argument in call.arguments[3:]:
        if isinstance(argument, qsc.Call) and argument.function == "Task_New":
            child_calls.append(argument)
        else:
            value_expressions.append(argument)

    result: dict = {"id": task_id, "type": task_type, "label": label}

    named_fields = map_values_to_fields(task_type, value_expressions, schema, serializer)
    if named_fields is not None:
        result["fields"] = named_fields
    else:
        result["values"] = [expression_to_value(expression, serializer) for expression in value_expressions]

    child_ids = [flatten_task(child_call, schema, serializer, accumulator) for child_call in child_calls]
    if child_ids:
        result["children"] = child_ids

    accumulator.append(result)
    return task_id


def map_values_to_fields(
    task_type: str,
    value_expressions: list[qsc.Expression],
    schema: dict[str, list[tuple[str, str]]],
    serializer: qsc.QSC,
) -> dict | None:
    """Map positional values to declared field names, or return None when not possible.

    Returns None (signalling a flat ``values`` fallback) when the type is undeclared or when
    the declared field arities do not sum to the number of supplied values.
    """
    field_definitions = schema.get(task_type)
    if field_definitions is None:
        return None

    if sum(field_arity(field_type) for _, field_type in field_definitions) != len(value_expressions):
        return None

    named_fields: dict = {}
    index = 0

    for field_name, field_type in field_definitions:
        count = field_arity(field_type)
        if count == 1:
            named_fields[field_name] = expression_to_value(value_expressions[index], serializer)
        else:
            named_fields[field_name] = [
                expression_to_value(value_expressions[index + offset], serializer) for offset in range(count)
            ]
        index += count

    return named_fields


def task_id_sort_key(task_id: object) -> tuple[int, float, str]:
    """Order ids numerically when possible, keeping non-numeric ids stable and grouped last.

    Numeric ids (the normal case) sort ascending in the first group; anything else (symbolic
    names, source-text fallbacks) sorts lexically in a second group so mixed id types never
    raise a TypeError during sorting.
    """
    if isinstance(task_id, bool):
        return (1, 0.0, str(task_id))
    if isinstance(task_id, int | float):
        return (0, float(task_id), "")
    return (1, 0.0, str(task_id))


def objects_to_json(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:
    target_path: Path | None = source_path.with_suffix(".json") if source_path is not None else None

    qvm_instance = QVM.model_validate_stream(source_io)
    block = qvm_instance.rebuild_block()

    schema = collect_schema(block)
    serializer = qsc.QSC(content=qsc.BlockStatement(statements=[]))

    accumulator: list[dict] = []
    for statement in block.statements:
        call = statement_to_call(statement)
        if call is not None and call.function == "Task_New":
            flatten_task(call, schema, serializer, accumulator)

    grouped: dict[str, dict[object, dict]] = {}
    for task_object in accumulator:
        grouped.setdefault(task_object["type"], {})[task_object["id"]] = task_object

    registry: dict[str, dict] = {}
    for task_type in sorted(grouped):
        objects_by_id = grouped[task_type]
        registry[task_type] = {
            task_id: objects_by_id[task_id] for task_id in sorted(objects_by_id, key=task_id_sort_key)
        }

    target_io = BytesIO()
    target_io.write(json.dumps(registry, indent=2, ensure_ascii=False).encode("utf-8"))
    target_io.seek(0)
    return target_io, target_path
