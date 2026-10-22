# Harness templates

Read this at steps 2 and 3. Each section is a complete harness for one entry point, `parse` on a message format, with the build, run, reproduce and minimise commands. Every harness has the same contract: return normally on any input, treat the documented rejection as normal, and let everything else surface as a finding. Where decoding succeeds, each one also re-encodes and re-parses, which turns a crash-only harness into a round-trip check at no extra cost.

## Contents

- [libFuzzer (C and C++)](#libfuzzer-c-and-c)
- [AFL++ with the same harness](#afl-with-the-same-harness)
- [cargo-fuzz (Rust)](#cargo-fuzz-rust)
- [Go native fuzzing](#go-native-fuzzing)
- [Atheris (Python)](#atheris-python)
- [Jazzer (Java and the JVM)](#jazzer-java-and-the-jvm)
- [Dictionaries](#dictionaries)
- [Typed arguments with FuzzedDataProvider](#typed-arguments-with-fuzzeddataprovider)

## libFuzzer (C and C++)

```cpp
// fuzz/parse_message_fuzzer.cc
#include <cstddef>
#include <cstdint>
#include <string>

#include "message/parser.h"

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
  message::Parser parser;  // fresh state for every input
  message::Message msg;
  if (!parser.Parse(data, size, &msg).ok()) {
    return 0;  // documented rejection
  }
  const std::string encoded = message::Encode(msg);
  message::Message again;
  if (!parser.Parse(reinterpret_cast<const uint8_t *>(encoded.data()), encoded.size(), &again).ok() ||
      !(again == msg)) {
    __builtin_trap();  // round trip broke: a finding
  }
  return 0;
}
```

In the parser, guard the checksum so mutated inputs get past it in fuzzing builds only:

```cpp
#ifndef FUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION
  if (!VerifyChecksum(data, size)) return Status::Corrupt();
#endif
```

Build, with the code under test compiled into the same binary:

```bash
clang++ -g -O1 -fno-omit-frame-pointer \
  -fsanitize=fuzzer,address,undefined -fno-sanitize-recover=undefined \
  -DFUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION \
  -Isrc fuzz/parse_message_fuzzer.cc src/message/*.cc -o parse_message_fuzzer
```

When the library is built by its own build system, compile its objects with `-fsanitize=fuzzer-no-link,address,undefined` and link only the harness with `-fsanitize=fuzzer`.

Run. The first directory is where new interesting inputs are written; later directories are read-only seeds.

```bash
mkdir -p corpus/parse_message crashes
./parse_message_fuzzer -dict=fuzz/parse_message.dict -max_len=65536 -timeout=5 \
  -rss_limit_mb=2048 -max_total_time=1800 -artifact_prefix=crashes/ -print_final_stats=1 \
  corpus/parse_message fuzz/seeds/parse_message
```

- Reproduce one input: `./parse_message_fuzzer crashes/crash-<sha1>`. Passing files rather than directories runs each once and exits.
- Minimise a crash: `./parse_message_fuzzer -minimize_crash=1 -runs=100000 crashes/crash-<sha1>`.
- Minimise the corpus: `./parse_message_fuzzer -merge=1 corpus_min/parse_message corpus/parse_message`.
- Use several cores: `-fork=<n>`, which also survives individual crashes and keeps going.

Artefacts are named by kind: `crash-`, `timeout-`, `oom-` and `leak-`, each followed by the input's SHA-1.

## AFL++ with the same harness

AFL++ builds a libFuzzer-style harness directly, so one harness serves both engines and the second engine's different mutation strategy finds what the first misses.

```bash
AFL_USE_ASAN=1 AFL_USE_UBSAN=1 afl-clang-fast++ -g -O1 -fsanitize=fuzzer \
  -DFUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION \
  -Isrc fuzz/parse_message_fuzzer.cc src/message/*.cc -o parse_message_afl
afl-fuzz -i fuzz/seeds/parse_message -o findings -x fuzz/parse_message.dict -- ./parse_message_afl
```

For a standalone program that reads a file path rather than a libFuzzer harness, put `@@` where the path goes in the target's command line. Minimise with `afl-tmin` and the corpus with `afl-cmin`.

## cargo-fuzz (Rust)

```bash
cargo install cargo-fuzz
cargo fuzz init
cargo fuzz add parse_message
```

```rust
// fuzz/fuzz_targets/parse_message.rs
#![no_main]
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    if let Ok(msg) = mycrate::message::parse(data) {
        let encoded = mycrate::message::encode(&msg);
        let again = mycrate::message::parse(&encoded).expect("re-parse of encoded message failed");
        assert_eq!(again, msg);
    }
});
```

In the crate, skip checksum verification under `#[cfg(not(fuzzing))]`; cargo-fuzz builds with `--cfg fuzzing`.

```bash
cargo +nightly fuzz run parse_message -- -max_total_time=1800 -timeout=5 -rss_limit_mb=2048 -dict=fuzz/parse_message.dict
cargo +nightly fuzz run parse_message fuzz/artifacts/parse_message/crash-<sha1>   # reproduce
cargo +nightly fuzz tmin parse_message fuzz/artifacts/parse_message/crash-<sha1>  # minimise
cargo +nightly fuzz cmin parse_message                                            # minimise the corpus
cargo +nightly fuzz coverage parse_message                                        # coverage data
```

AddressSanitizer is the default sanitiser. The corpus lives in `fuzz/corpus/parse_message/` and crashes in `fuzz/artifacts/parse_message/`. For an entry point that takes structured input, derive `arbitrary::Arbitrary` on an input type and write `fuzz_target!(|input: MyInput| { ... })`.

## Go native fuzzing

```go
// message/fuzz_test.go
package message

import (
    "reflect"
    "testing"
)

func FuzzParse(f *testing.F) {
    f.Add([]byte("MSG1\x00\x00\x00\x00"))
    f.Fuzz(func(t *testing.T, data []byte) {
        msg, err := Parse(data)
        if err != nil {
            return // documented rejection
        }
        again, err := Parse(msg.Encode())
        if err != nil {
            t.Fatalf("re-parse of encoded message: %v", err)
        }
        if !reflect.DeepEqual(again, msg) {
            t.Fatalf("round trip changed the message")
        }
    })
}
```

```bash
go test ./message -run='^$' -fuzz='^FuzzParse$' -fuzztime=30m
```

- `-fuzz` must match exactly one fuzz target in exactly one package per invocation.
- Seeds come from `f.Add` and from files in `testdata/fuzz/FuzzParse/`, which use Go's own corpus encoding rather than raw bytes; `golang.org/x/tools/cmd/file2fuzz` converts raw sample files into it.
- A failing input is minimised and written to `testdata/fuzz/FuzzParse/` automatically, and plain `go test ./message` replays it from then on. Commit that file with the fix.
- The corpus the fuzzer grows is kept in the build cache (`go env GOCACHE`), not in the repository.

## Atheris (Python)

```python
# fuzz/fuzz_parse_message.py
import sys

import atheris

with atheris.instrument_imports():
    from mylib import message


def TestOneInput(data: bytes) -> None:
    try:
        msg = message.parse(data)
    except message.ParseError:
        return  # documented rejection; anything else propagates as a finding
    again = message.parse(message.encode(msg))
    if again != msg:
        raise RuntimeError("round trip changed the message")


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
```

```bash
python3 fuzz/fuzz_parse_message.py -max_total_time=1800 -timeout=5 -dict=fuzz/parse_message.dict \
  corpus/parse_message fuzz/seeds/parse_message
python3 fuzz/fuzz_parse_message.py crash-<sha1>   # reproduce
```

Atheris accepts libFuzzer's flags. Pure-Python findings are uncaught exceptions, `RecursionError` on deeply nested input, hangs and memory growth. For a native extension, build the extension with sanitisers and follow Atheris's documentation for loading them, or memory bugs in the extension go unseen.

## Jazzer (Java and the JVM)

```java
import static org.junit.jupiter.api.Assertions.assertEquals;

import com.code_intelligence.jazzer.junit.FuzzTest;

class MessageParserFuzzTest {
    @FuzzTest(maxDuration = "30m")
    void parse(byte[] data) {
        Message msg;
        try {
            msg = MessageParser.parse(data);
        } catch (MalformedMessageException e) {
            return; // documented rejection
        }
        assertEquals(msg, MessageParser.parse(MessageEncoder.encode(msg)));
    }
}
```

Run with the environment variable `JAZZER_FUZZ=1` set to fuzz. Without it, the same test runs as an ordinary JUnit test over the stored inputs, which is the regression replay. Findings are saved into the test resources inputs directory Jazzer documents for the test class; commit them with the fix. Jazzer's built-in detectors also report some injection-style findings in addition to uncaught exceptions.

## Dictionaries

A dictionary gives the mutator the format's tokens so it does not have to discover them byte by byte. One entry per line, optionally named, with `\xNN` escapes:

```text
# fuzz/parse_message.dict
magic="MSG1"
version_2="MSG2"
hdr_len="content-length:"
"\x00\x00\x00\x01"
"\xff\xff\xff\xff"
```

Take the tokens from the specification: magic numbers, version markers, field names, delimiters, and the boundary integers the length fields use. libFuzzer, AFL++ and Atheris read the same format.

## Typed arguments with FuzzedDataProvider

When the entry point takes several arguments, split the input with the provider rather than inventing a framing format:

```cpp
#include <fuzzer/FuzzedDataProvider.h>
#include <vector>

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
  FuzzedDataProvider fdp(data, size);
  const uint32_t flags = fdp.ConsumeIntegral<uint32_t>();
  const std::string name = fdp.ConsumeRandomLengthString(256);
  const std::vector<uint8_t> body = fdp.ConsumeRemainingBytes<uint8_t>();
  (void)message::Decode(flags, name, body.data(), body.size());
  return 0;
}
```

Atheris has `atheris.FuzzedDataProvider` and Jazzer has `com.code_intelligence.jazzer.api.FuzzedDataProvider` with the same idea. Consume the variable-length remainder last, so small changes to the input do not shift every later argument.
