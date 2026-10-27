# WASM sections, WABT and the host boundary

Read this when the inventory from `wasm-objdump -x` needs interpreting, or when the question
is about what a module can reach rather than what it exports.

## The three things a module is

A WASM module is a binary with a preamble and a sequence of sections. Every section that
matters to an investigation is one of three kinds:

1. **Declarations** — types, imports, functions, tables, memories, globals, exports. These
   describe the module's shape and its contract with the host.
2. **Definitions** — the code section, one function body per declared function, plus data and
   element segments that initialise memory and tables.
3. **Custom sections** — free-form named blobs. `name`, `producers`, `target_features` and
   `sourceMappingURL` are the ones a reader cares about; an unfamiliar name is a lead, not
   noise.

A module with no start section runs no function of its own when instantiated, but
instantiation is not inert: active data and element segments are written into memory and
tables at that moment, and when the memory or table is imported, the write lands in state
the host shares. Settle two questions first: is there a start function, and do any active
segments target an imported memory or table? Only a module with neither does nothing until
the host calls an export.

## The import list is the capability list

Every capability the module has, it has because the host bound an import to it. Read the
imports in this shape:

| Import kind | What it lets the module do |
| --- | --- |
| `func` | Call host code — file access, network, crypto, another module |
| `memory` | Read and write a memory the host may share with other instances |
| `table` | Call host function references stored in it |
| `global` | Read a host-provided value such as an environment flag |

A module importing only arithmetic helpers cannot exfiltrate anything by itself. A module
importing a fetch wrapper and a filesystem call has those capabilities, and whether it uses
them is a different question answered by reading the call sites, not by reading the import
list alone.

## WABT commands and what each answers

WABT is caller-supplied. The analysis bridge's `inspect_wasm_artifact` requires an installation
(1.0.42 at the time of writing) and reports the same facts as Evidence; the binaries work
directly too.

| Command | Answers |
| --- | --- |
| `wasm-validate module.wasm` | Is this a well-formed module, and which validation rule fails if not |
| `wasm-objdump -h module.wasm` | Section list, sizes and offsets |
| `wasm-objdump -x module.wasm` | Every declaration: types, imports, exports, memories, globals |
| `wasm-objdump -d module.wasm` | Disassembly, all functions or a named one |
| `wasm2wat module.wasm` | The textual form, for reading control flow |

`wasm2wat` output is a reconstruction for reading. It is faithful to the binary and not to
the language the module was written in.

## Source maps and build leftovers

A `sourceMappingURL` custom section, or a `//# sourceMappingURL=` comment in the JavaScript
that instantiates the module, points at a map file. If the shipped site still serves it, the
original module names and sometimes the original sources are one request away — that is a
finding about the deployment, and it is authorised reading under the same scope as the
module. Fetch it once, record the URL and the digest, and do not mirror more of the site than
the map needs.

## Memory declarations

`memory` entries carry a minimum and an optional maximum, in 64 KiB pages. No maximum means
the host cannot bound growth from the module side; a large minimum means instantiation
reserves it. Report both numbers rather than "it uses memory", and check whether the memory
is exported or imported, because an exported memory is readable by the JavaScript that
instantiates the module.

## What stays unproven

The module's shape is observed. The host's bindings, the origin of the module, and whether
the deployed build matches the file you analysed are not. Record the digest and where it came
from, and treat any claim about runtime behaviour as belonging to the harness that provided
the imports.
