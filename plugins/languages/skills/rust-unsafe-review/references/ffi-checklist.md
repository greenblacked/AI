# FFI checklist

Imports (calling C from Rust):

- The declared signature matches the header exactly: integer widths (`c_int`, `c_long`, `size_t` as `usize`), signedness, pointer constness.
- Shared structs are `#[repr(C)]`; enums crossing the boundary have an explicit `#[repr(...)]` and the C side cannot return a value outside it.
- Nullable pointers are `Option<NonNull<T>>`, `Option<&T>` or checked before use. Returned pointers are checked for null.
- Strings: `CStr::from_ptr` needs a NUL-terminated, valid pointer for the call's duration; `CString::new` fails on interior NULs and the pointer is valid only while the `CString` lives.
- Lifetime: state how long the C side may keep a pointer you passed; if it keeps it, the memory must be owned somewhere that outlives it.
- Ownership: who frees, and with which function. Memory allocated by Rust must be freed by Rust, and by C must be freed by the C library's own function.
- Thread rules of the library (not thread-safe, or must be called on one thread) are expressed by not implementing `Send` or `Sync` on the wrapper.

Exports (calling Rust from C):

- Mark `extern "C"` with a stable name (`#[unsafe(no_mangle)]` on edition 2024, `#[no_mangle]` before).
- No panic may unwind out: wrap the body in `std::panic::catch_unwind` and return an error code, or build with `panic = "abort"`.
- Do not hand out references with Rust lifetimes; return opaque pointers made with `Box::into_raw` and a matching free function using `Box::from_raw`.
- Validate every pointer and length from C before building a slice.

Tests: bindings are exercised from a small C or Rust driver under an AddressSanitizer build; Miri cannot run foreign calls, so test the Rust wrapper logic against a stub implementation of the C functions.

Tooling: `bindgen` generates import declarations and `cbindgen` generates headers; review the output rather than trusting it, since it cannot know ownership or nullability rules.
