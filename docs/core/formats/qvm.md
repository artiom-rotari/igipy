[Back to README](../../../README.md)

# QVM Format — Quest Virtual Machine Bytecode

QVM files contain compiled bytecode for the IGI engine's scripting virtual machine. They define game logic: AI behavior,
mission objectives, object placement, sound triggers, weapon configs, cutscene scripting, and more. The converter
decompiles QVM bytecode back into readable QSC (Quest Script) source code.

## Structure Overview

```
┌────────────────────────────────────────┐
│ Header (60 bytes)                      │
│   Signature: "LOOP"                    │
│   Version, section offsets/sizes       │
├────────────────────────────────────────┤
│ Padding (4 bytes, always 0)            │
├────────────────────────────────────────┤
│ Variable Points — offset LUT           │
├────────────────────────────────────────┤
│ Variable Data — null-terminated names  │
├────────────────────────────────────────┤
│ String Points — offset LUT             │
├────────────────────────────────────────┤
│ String Data — null-terminated literals │
├────────────────────────────────────────┤
│ Instructions — bytecode stream         │
└────────────────────────────────────────┘
```

The six sections after the header are always contiguous with no gaps. Variable Points always start at offset 64.

## Header (60 bytes)

All fields are little-endian.

| Offset | Type   | Field                   | Description                          |
|--------|--------|-------------------------|--------------------------------------|
| 0      | 4s     | signature               | Always `"LOOP"`                      |
| 4      | uint32 | major_version           | Always 8                             |
| 8      | uint32 | minor_version           | 5 (IGI 1) or 7 (IGI 2)               |
| 12     | uint32 | variables_points_offset | Always 64                            |
| 16     | uint32 | variables_data_offset   | Start of variable name strings       |
| 20     | uint32 | variables_points_size   | Size of variable offset LUT in bytes |
| 24     | uint32 | variables_data_size     | Size of variable name data in bytes  |
| 28     | uint32 | strings_points_offset   | Start of string literal offset LUT   |
| 32     | uint32 | strings_data_offset     | Start of string literal data         |
| 36     | uint32 | strings_points_size     | Size of string offset LUT in bytes   |
| 40     | uint32 | strings_data_size       | Size of string literal data in bytes |
| 44     | uint32 | instructions_offset     | Start of bytecode stream             |
| 48     | uint32 | instructions_size       | Size of bytecode stream in bytes     |
| 52     | uint32 | unknown_1               | Always 0                             |
| 56     | uint32 | unknown_2               | Always 0                             |

Bytes 60–63 are zero padding (not part of the header struct). Data sections begin at offset 64.

### Version 5 Footer

Version 5 files (IGI 1) may have an additional uint32 at offset 60 — a `footer_data_offset` — before the padding. This
field is absent in version 7.

## Variable Pool

Two subsections store named identifiers used by the bytecode (function names, constants, type names):

**Variable Points** — an array of `uint32` offsets into Variable Data. Count = `variables_points_size / 4`.

**Variable Data** — null-terminated UTF-8 strings packed contiguously. Each offset in the point array indexes into this
buffer.

Example from `animtrigger/animtrigger.qvm` (15 variables):

```
Points: [0, 18, 46, 61, 92, ...]
Data:   "DefineAnimTrigger\0HUMANANIM_TRIGGER_FEETSOUND\0TASKTYPE_HUMAN\0..."
         ^0                  ^18                        ^46
```

## String Pool

Same structure as the variable pool, but for string literals (file paths, display text, sound names):

**String Points** — array of `uint32` offsets into String Data. Count = `strings_points_size / 4`.

**String Data** — null-terminated UTF-8 strings packed contiguously.

Files with no string literals have both sizes set to 0.

## Instruction Set

The bytecode stream is a sequence of 1-byte opcodes, some followed by inline operands. The opcode-to-instruction mapping
differs between version 5 and version 7.

### Opcode Table

| Opcode | v5 Instruction | v7 Instruction | Operand         | Description                   |
|--------|----------------|----------------|-----------------|-------------------------------|
| 0x00   | BRK            | BRK            | —               | End of block / halt           |
| 0x01   | NOP            | NOP            | —               | No operation                  |
| 0x02   | PUSH           | RET            | u32 / —         | Push literal / return         |
| 0x03   | PUSHB          | BRA            | u8 / i32        | Push byte / branch always     |
| 0x04   | PUSHW          | BF             | u16 / i32       | Push word / branch if false   |
| 0x05   | PUSHF          | BT             | f32 / —         | Push float / branch if true   |
| 0x06   | PUSHA          | JSR            | — / —           | Push address / jump sub       |
| 0x07   | PUSHS          | CALL           | — / count+i32[] | Push string / function call   |
| 0x08   | PUSHSI         | PUSH           | u32 / u32       | String index / push literal   |
| 0x09   | PUSHSIB        | PUSHB          | u8 / u8         | String index byte / push byte |
| 0x0A   | PUSHSIW        | PUSHW          | u16 / u16       | String index word / push word |
| 0x0B   | PUSHI          | PUSHF          | — / f32         | Push int / push float         |
| 0x0C   | PUSHII         | PUSHA          | u32 / —         | Var index / push address      |
| 0x0D   | PUSHIIB        | PUSHS          | u8 / —          | Var index byte / push string  |
| 0x0E   | PUSHIIW        | PUSHSI         | u16 / u32       | Var index word / string index |
| 0x0F   | PUSH0          | PUSHSIB        | — / u8          | Push 0 / string index byte    |
| 0x10   | PUSH1          | PUSHSIW        | — / u16         | Push 1 / string index word    |
| 0x11   | PUSHM          | PUSHI          | — / —           | Push 0xFFFFFFFF / push int    |
| 0x12   | POP            | PUSHII         | — / u32         | Pop / variable index          |
| 0x13   | RET            | PUSHIIB        | — / u8          | Return / var index byte       |
| 0x14   | BRA            | PUSHIIW        | i32 / u16       | Branch always / var idx word  |
| 0x15   | BF             | PUSH0          | i32 / —         | Branch false / push 0         |
| 0x16   | BT             | PUSH1          | — / —           | Branch true / push 1          |
| 0x17   | JSR            | PUSHM          | — / —           | Jump subroutine / push mask   |
| 0x18   | CALL           | POP            | count+i32[] / — | Function call / pop           |
| 0x19   | ADD            | ADD            | —               | Add                           |
| 0x1A   | SUB            | SUB            | —               | Subtract                      |
| 0x1B   | MUL            | MUL            | —               | Multiply                      |
| 0x1C   | DIV            | DIV            | —               | Divide                        |
| 0x1D   | SHL            | SHL            | —               | Shift left                    |
| 0x1E   | SHR            | SHR            | —               | Shift right                   |
| 0x1F   | AND            | AND            | —               | Bitwise AND                   |
| 0x20   | OR             | OR             | —               | Bitwise OR                    |
| 0x21   | XOR            | XOR            | —               | Bitwise XOR                   |
| 0x22   | LAND           | LAND           | —               | Logical AND                   |
| 0x23   | LOR            | LOR            | —               | Logical OR                    |
| 0x24   | EQ             | EQ             | —               | Equal                         |
| 0x25   | NE             | NE             | —               | Not equal                     |
| 0x26   | LT             | LT             | —               | Less than                     |
| 0x27   | LE             | LE             | —               | Less or equal                 |
| 0x28   | GT             | GT             | —               | Greater than                  |
| 0x29   | GE             | GE             | —               | Greater or equal              |
| 0x2A   | ASSIGN         | ASSIGN         | —               | Assignment                    |
| 0x2B   | PLUS           | PLUS           | —               | Unary plus                    |
| 0x2C   | MINUS          | MINUS          | —               | Unary minus                   |
| 0x2D   | INV            | INV            | —               | Bitwise invert                |
| 0x2E   | NOT            | NOT            | —               | Logical NOT                   |
| 0x2F   | BLK            | BLK            | —               | Block marker                  |
| 0x30   | ILLEGAL        | ILLEGAL        | —               | Illegal instruction           |

Opcodes 0x19–0x30 are identical between versions. The difference is in 0x02 – 0x18: version 7 reordered control flow
opcodes (RET, BRA, BF, BT, JSR, CALL) to precede data push opcodes.

### Instruction Categories

**Data Push** — push values onto the evaluation stack:

| Instruction | Operand | Stack effect | Description                     |
|-------------|---------|--------------|---------------------------------|
| PUSH        | uint32  | → value      | Push 32-bit integer literal     |
| PUSHB       | uint8   | → value      | Push 8-bit integer literal      |
| PUSHW       | uint16  | → value      | Push 16-bit integer literal     |
| PUSHF       | float32 | → value      | Push 32-bit float literal       |
| PUSH0       | —       | → 0          | Push constant 0                 |
| PUSH1       | —       | → 1          | Push constant 1                 |
| PUSHM       | —       | → 0xFFFFFFFF | Push constant -1 / max uint32   |
| PUSHSI      | uint32  | → string     | Push string by index (32-bit)   |
| PUSHSIB     | uint8   | → string     | Push string by index (8-bit)    |
| PUSHSIW     | uint16  | → string     | Push string by index (16-bit)   |
| PUSHII      | uint32  | → variable   | Push variable by index (32-bit) |
| PUSHIIB     | uint8   | → variable   | Push variable by index (8-bit)  |
| PUSHIIW     | uint16  | → variable   | Push variable by index (16-bit) |

The `PUSHSI*` variants index into the String Pool. The `PUSHII*` variants index into the Variable Pool. The `B`/`W`
suffixes are compact encodings for indices that fit in 8 or 16 bits.

**Control Flow:**

| Instruction | Operand                    | Description                                |
|-------------|----------------------------|--------------------------------------------|
| BRK         | —                          | End of block, terminates execution         |
| BRA         | int32 (relative)           | Unconditional branch                       |
| BF          | int32 (relative)           | Branch if top of stack is false (if/while) |
| BT          | —                          | Branch if true (not used in IGI 2)         |
| CALL        | uint32 count, int32[count] | Call function with argument sub-programs   |
| RET         | —                          | Return from subroutine                     |
| JSR         | —                          | Jump to subroutine (not used in IGI 2)     |
| POP         | —                          | Discard top of stack                       |

**CALL encoding:** The operand starts with an uint32 argument count, followed by that many int32 absolute addresses.
Each address points to a subprogram within the instruction stream that evaluates one argument. After CALL, a BRA
instruction follows to skip past the inlined argument code.

**Arithmetic and Logic** (all stack-based, no operands):

| Category   | Instructions           | Operators           |
|------------|------------------------|---------------------|
| Arithmetic | ADD, SUB, MUL, DIV     | `+  -  *  /`        |
| Bitwise    | SHL, SHR, AND, OR, XOR | `<< >> &  \|  ^`    |
| Logical    | LAND, LOR              | `&& \|\|`           |
| Comparison | EQ, NE, LT, LE, GT, GE | `== != <  <= >  >=` |
| Assignment | ASSIGN                 | `=`                 |
| Unary      | PLUS, MINUS, INV, NOT  | `+  -  ~  !`        |

## Execution Model

The VM uses a **stack-based architecture**:

1. Push operands onto the stack (literals, variables, strings)
2. Execute operators that pop operands and push results
3. CALL pops a function name variable from the stack, evaluates arguments from subprograms, and pushes the call result
4. BF pops a condition and branches — used for `if/else` and `while` loops
5. BRK terminates a block; BRA jumps unconditionally (used after CALL to skip argument code, and for else/loop branches)

### Control Flow Reconstruction

The decompiler reconstructs the structured control flow from branch offsets:

- **BF with forward BRA at end of then-block (offset > 0)** → `if/else`
- **BF with BRA offset = 0 at end of then-block** → `if` (no else)
- **BF with backward BRA at end of then-block (offset < 0)** → `while` loop

## Decompiled Output (QSC)

The converter decompiles QVM bytecode into QSC — a C-like scripting language. Example:

**Input:** `missions/location1/level1/ai/500.qvm` (389 bytes)

**Output:**

```c
if(AIFunction_GetCurrentEventType() == AIEVENT_CREATE)
{
	AIFunction_DefaultHandler();
}
if(AIFunction_GetCurrentEventType() == AIEVENT_IDLE)
{
	AIAction_WalkToNode(100, 1);
	AIAction_LookAtNode(69, 1);
	AIFunction_PassEventOnToSquad();
}
else
{
	AIFunction_DefaultHandler();
}
```

QSC files use tab indentation and semicolon-terminated statements. Function calls use the
`Task_New(id, "Type", "Name", ...)` pattern for object definitions, and engine API calls like `AIFunction_*`,
`AIAction_*` for AI scripting.

## File Organization

QVM files appear throughout the game directory structure:

```
config.qvm                              ← Game configuration
common/
  ai/default.qvm                        ← Default AI behavior
  ai/settings.qvm                       ← AI difficulty parameters
  ai/squaddefault.qvm                   ← Default squad behavior
  sounds/sounds.qvm                     ← Sound definitions
animtrigger/animtrigger.qvm             ← Animation event triggers
humanplayer/humanplayer.qvm             ← Player logic
weapons/weapons.qvm                     ← Weapon definitions
material/material.qvm                   ← Material properties
physicsobj/*.qvm                        ← Physics object configs (18 files)
menusystem/*.qvm                        ← Menu system scripts
missions/
  location1/level1/
    objects.qvm                         ← Level object placement (largest files)
    mission.qvm                         ← Mission logic
    sounds/sounds.qvm                   ← Level-specific sounds
    ai/500.qvm                          ← Individual AI scripts
    ai/Squad_700.qvm                    ← Squad behavior scripts
```

## Statistics (IGI 2)

| Metric             | Value                                         |
|--------------------|-----------------------------------------------|
| Total files        | 1,786                                         |
| All version 8.7    | Yes (100%)                                    |
| Signature          | `"LOOP"` (all files)                          |
| Size range         | 105–393,614 bytes                             |
| Median size        | 292 bytes                                     |
| P90 size           | 661 bytes                                     |
| Variables per file | 1–182 (avg 5.3)                               |
| Strings per file   | 0–2,063 (avg 22.1)                            |
| Contiguous layout  | 100% of files                                 |
| Trailing data      | 1 file (`config.qvm` has `"Hello, world!\0"`) |

### Largest Files

| File                                  | Size      | Variables | Strings |
|---------------------------------------|-----------|-----------|---------|
| missions/location3/level4/objects.qvm | 393,614 B | —         | —       |
| missions/location1/level1/objects.qvm | 285,208 B | —         | —       |
| missions/location3/level5/objects.qvm | 271,459 B | —         | —       |
| common/sounds/sounds.qvm              | 103,047 B | 6         | 1,025   |

The `objects.qvm` files are by far the largest — they contain all object definitions for a level.

### Opcode Frequency (across all 1,786 files)

| Opcode  | Count   | Description               |
|---------|---------|---------------------------|
| BRK     | 530,932 | Block terminators         |
| PUSHSIW | 124,805 | String index (16-bit)     |
| PUSHIIB | 91,742  | Variable index (8-bit)    |
| PUSHF   | 87,262  | Float literals            |
| PUSHW   | 55,956  | Integer literals (16-bit) |
| PUSH0   | 55,149  | Constant 0                |
| BRA     | 50,899  | Unconditional branches    |
| PUSHSIB | 49,073  | String index (8-bit)      |
| CALL    | 48,373  | Function calls            |
| PUSHB   | 46,229  | Integer literals (8-bit)  |
| MINUS   | 37,703  | Unary minus               |

23 of 49 opcodes are used. Unused opcodes include NOP, BT, JSR, PUSHA, PUSHS, PUSHI, and all bitwise/shift operators.
