# Safety contracts by operation

Template, placed directly above the block:

```rust
// SAFETY: <requirement 1> holds because <reason at this call site>;
// <requirement 2> holds because <reason>.
unsafe { ... }
```

| Operation | What it requires | Where the proof usually comes from |
| --- | --- | --- |
| Dereference a raw pointer | Non-null, aligned, points to a live, initialised value of the type, no conflicting mutable access | A reference it was derived from, still in scope; an owner that outlives the pointer |
| `slice::from_raw_parts` / `_mut` | Non-null, aligned pointer, `len * size_of::<T>()` within one allocation and no larger than `isize::MAX`, elements initialised, no aliasing for `_mut` | A `Vec` or buffer whose length you control and that is not touched while the slice lives |
| `get_unchecked` | Index in bounds | A check immediately above, or a loop bound derived from the length |
| `transmute` | Source and target have the same size, and every source bit pattern is a valid target value | Prefer `from_ne_bytes`, `bytemuck` or `zerocopy`; with `#[repr(C)]` or `#[repr(transparent)]` on both sides if you must |
| `MaybeUninit::assume_init` | Every byte of the value was written and is valid for the type | Writes in the lines above covering the whole value |
| `String::from_utf8_unchecked`, `str::from_utf8_unchecked` | The bytes are valid UTF-8 | A validation earlier on the same data, not on a copy |
| `unsafe impl Send` / `Sync` | Moving or sharing the value across threads cannot cause a data race | The fields are themselves thread-safe, or access is guarded by a lock the type owns |
| `unsafe fn` | The `# Safety` section lists every caller obligation | The doc comment, checked at each call site |

Questions to ask of any contract: is the argument about this call site or about "usually"? Could a safe caller or a future change break it? Does a lifetime or type express it so the compiler enforces it?

Aliasing: creating a `&mut T` while another reference or pointer to the same data is used afterwards is undefined behaviour even if nothing is read; Miri reports it.
