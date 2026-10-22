# Wheel tags and a decision table

Read this when a tag is unfamiliar, the probe result is confusing, or you need to choose between the options.

## Contents

- Reading a wheel filename
- Common platform tags
- Probe results and next step
- Builder stage template

## Reading a wheel filename

`name-version-pythontag-abitag-platformtag.whl`, for example `numpy-2.0.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`. The python tag `cp312` means CPython 3.12; `py3` means any Python 3. The ABI tag `none` plus platform `any` means pure Python. `abi3` wheels work across several CPython versions from the named one upward.

## Common platform tags

| Tag | Target |
| --- | --- |
| `manylinux_2_17_x86_64`, `manylinux2014_x86_64` | glibc Linux, x86-64, glibc 2.17 or newer |
| `manylinux_2_17_aarch64`, `manylinux2014_aarch64` | glibc Linux on arm64, including Docker on Apple Silicon |
| `musllinux_1_2_x86_64`, `musllinux_1_2_aarch64` | musl Linux such as Alpine |
| `macosx_11_0_arm64`, `macosx_10_9_x86_64` | macOS on Apple Silicon and Intel |
| `win_amd64` | Windows x86-64 |

A newer `manylinux_2_28` wheel needs glibc 2.28 or newer; an older distribution may reject it even though it is glibc.

## Probe results and next step

| Probe result | Meaning | Next step |
| --- | --- | --- |
| Wheel downloads for the target tag | A wheel exists | Find why pip picked the sdist: upgrade pip, check `--no-binary`, hashes, index |
| "No matching distribution" for the target tag | No wheel for that tag | Try a neighbouring version, then a glibc image, then a builder stage |
| Wheel exists for `manylinux` but not `musllinux` | Alpine is the cause | Change base image |
| Wheel exists for `cp311` but not `cp313` | Interpreter too new for that release | Pin the older interpreter or wait for the release |
| Only an sdist exists | Project does not publish binaries | Builder stage, or replace the dependency |

## Builder stage template

```dockerfile
FROM python:3.12-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential
RUN pip wheel "<pkg>==<ver>" -w /wheelhouse

FROM python:3.12-slim
COPY --from=build /wheelhouse /wheelhouse
RUN pip install --no-index --find-links /wheelhouse "<pkg>==<ver>"
```

Both stages use the same base so the interpreter and C library match. Add the runtime system libraries the wheel needs to the final stage by name, and nothing else.
