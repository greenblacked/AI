# Reading WASM code, not just its sections

Read once the imports, exports and memory limits are recorded and the question needs what a
function actually does. The module is a stack machine: every instruction pushes or pops
values, and control flow is structured rather than a graph of jumps.

## Get a readable form

```bash
wasm2wat ./module.wasm -o ./module.wat
wasm-objdump -d ./module.wasm
wasm-decompile ./module.wasm -o ./module.dcmp
```

`wasm2wat` is the faithful textual form and is what to cite by function index and offset.
`wasm-decompile` produces C-like pseudocode that is easier to skim and easier to over-read:
it is a reconstruction, not the source that generated the module.

## The shapes worth recognising

- **A function body starts with locals**, then the instruction sequence. Locals beyond the
  parameters are the compiler's temporaries; a local named `var7` tells you nothing.
- **`call` takes an index into the function table.** `call_indirect` takes a type index and
  a table slot computed at run time — that is a virtual dispatch or a function pointer, and
  the target is not visible from the call site alone. Record it as indirect and unresolved
  until the table is read.
- **`i32.load`/`i32.store` with a constant offset** are struct-field or global accesses. The
  offset is a fact; the field's meaning is not.
- **`memory.grow`** is the module asking the host for more memory. It is not an allocation
  failure; it is the module exercising a declared capability.
- **`unreachable`** is a trap the compiler emits for an impossible path or a failed assert.
  Its presence is not a vulnerability by itself.
- **Structured blocks**: `block`, `loop`, `if`/`else`, `br`, `br_if`, `br_table`. A
  `br_table` is the usual shape of a `switch`; read the labels to recover the cases.

## Strings and data

String literals live in a data segment at a memory offset, not in an instruction. Find the
segment with `wasm-objdump -x` (the `Data` section), then map the offset to the code that
loads it: a `i32.const` equal to the segment offset followed by a load and a call that
consumes it. Since the offsets are compiler-chosen, a literal in the data section proves
the bytes ship; it does not prove the function that references it is ever called.

## Names, if the build kept them

The `name` custom section maps function and local indices to names. When it exists, prefer
those names in the report and say they came from the section. When it does not, refer to
functions by index and export, and do not invent a name from the pseudocode.

## What the code cannot prove

The module is a capability surface, not a running system. Which import the host actually
binds, whether the export is reachable from the page's JavaScript, and what the host does
with the values passed back are separate claims. Read the instantiating JavaScript for the
binding, and put the runtime observation in the isolated environment the skill's gate 2
describes.
