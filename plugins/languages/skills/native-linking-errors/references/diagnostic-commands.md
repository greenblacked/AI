# Diagnostic commands

Read this when the message in step 1 of the skill does not point straight at a missing library.

## Message to first command

| You see | Run first | Reads |
| --- | --- | --- |
| `undefined reference to 'foo::bar(int)'` | `nm -C --defined-only lib*.a \| grep 'foo::bar'` | Which archive defines it |
| `undefined reference to '_Z3fooi'` and the library is C | `nm lib.a \| grep foo` | Unmangled in the library means a missing `extern "C"` |
| `undefined reference` mentioning `[abi:cxx11]` | `grep -r GLIBCXX_USE_CXX11_ABI build/ CMakeLists.txt` | Which flag value each target used |
| `multiple definition of 'x'` | relink with `-Wl,-Map=out.map`, then search the map for `x` | Both input files |
| `cannot find -lfoo` | `ld --verbose \| grep SEARCH_DIR`, then `ls` the directories | The search path and the file name (`libfoo.so` versus `libfoo.so.1`) |
| `error while loading shared libraries: libfoo.so.1` | `readelf -d ./app \| grep NEEDED` (`ldd` only on a binary you built) | Which `NEEDED` entry is unresolved |
| `version 'GLIBC_2.34' not found` | `objdump -T ./app \| grep GLIBC_2.34` | Which imported symbol needs it |
| `version 'GLIBCXX_3.4.30' not found` | `objdump -T ./app \| grep GLIBCXX_3.4.30` | Which C++ runtime symbol needs it |
| `symbol lookup error: undefined symbol` | `LD_DEBUG=libs,bindings ./app 2>&1 \| grep -B2 -A2 SYMBOL` | Which library was loaded instead of the expected one |
| Works here, crashes there | `readelf -d ./app \| grep -E 'NEEDED\|RUNPATH'` on both machines | Differences in loaded libraries |

## Checking an install tree

```bash
find dist -type f \( -name '*.so*' -o -perm -u+x \) -print0 | while IFS= read -r -d '' f; do
  file "$f" | grep -q ELF || continue
  v=$(objdump -T "$f" 2>/dev/null | grep -o 'GLIBC_[0-9.]*' | sort -Vu | tail -1)
  [ -n "$v" ] || continue
  printf '%s %s\n' "$v" "$f"
done | sort -V | tail -5
```

The last line is the file that sets the minimum glibc for the whole package. Repeat with `GLIBCXX_` and `CXXABI_`. Use `readelf --version-info` when you need the version needs per library rather than per symbol.

## Reading LD_DEBUG

`LD_DEBUG=help ./app` lists the categories the loader supports. The useful ones are `libs` (search order and the file chosen), `bindings` (which definition each symbol bound to, so you can see interposition) and `versions` (version dependency checks). Output goes to stderr; redirect it to a file before searching it.

## Build container recipe

1. Pick the oldest distribution release you still support and pin the image by digest.
2. Install the toolchain from that release, or a newer compiler built to target its glibc; do not copy a newer glibc in.
3. Build with the same flags as release, including `-D_GLIBCXX_USE_CXX11_ABI` if you ship against a prebuilt library that fixes it.
4. After the build, run the loops above and fail the job when the highest `GLIBC_` or `GLIBCXX_` exceeds a recorded ceiling, so a toolchain bump cannot raise the baseline unnoticed.
5. Run the artefact in a second, bare container of the same release.

## Dual ABI quick reference

Since GCC 5 libstdc++ ships two ABIs for `std::string` and `std::list`. Symbols in the new one carry `__cxx11` in the namespace or `[abi:cxx11]` on the function. Mixing the two compiles and fails to link when a signature crosses the boundary, or worse, links where only the name differs. Choose one value for the whole product and for every prebuilt dependency; if a vendor library fixes the old value, build everything with `=0` and note it.
