# Tool configuration and measurement

Read this when setting up the checker in CI or choosing a measurement.

## Contents

- mypy settings
- pyright settings
- Baselines
- Measurement commands
- Stubs for untyped packages

## mypy settings

```toml
[tool.mypy]
python_version = "3.11"
warn_unused_ignores = true
warn_redundant_casts = true
enable_error_code = ["ignore-without-code"]
mypy_path = "stubs"

[[tool.mypy.overrides]]
module = ["myapp.config", "myapp.schemas.*"]
disallow_untyped_defs = true
disallow_incomplete_defs = true
disallow_untyped_calls = true
disallow_untyped_decorators = true
check_untyped_defs = true
disallow_any_generics = true
disallow_subclassing_any = true
warn_return_any = true
no_implicit_reexport = true
strict_equality = true
warn_unused_ignores = true
warn_redundant_casts = true
```

`strict` is global-only in mypy, so an override must list the per-module flags as above.

Keep `ignore_missing_imports` out of the global section; set it per untyped package in an override so a typo in an import is still caught.

## pyright settings

```json
{
  "include": ["src"],
  "stubPath": "stubs",
  "reportUnnecessaryTypeIgnoreComment": true,
  "strict": ["src/myapp/config", "src/myapp/schemas"]
}
```

A file can opt in with `# pyright: strict` on its own line.

## Baselines

- basedpyright: `basedpyright --writebaseline` creates the baseline; a plain `basedpyright` run then reports only new errors. Regenerate it after fixing errors so the file shrinks.
- mypy: use `mypy-baseline` to store current output and filter later runs against it.
- Plain pyright has no baseline flag.

## Measurement commands

```bash
mypy --any-exprs-report reports/ src/
pyright --verifytypes myapp --ignoreexternal
grep -rnE "(type|pyright): ignore" src | wc -l
```

Record all three at the start and after each pull request that moves a module.

## Stubs for untyped packages

Order of preference: a published `types-<package>` or the package's own `py.typed`; a minimal local stub (`stubs/<package>/__init__.pyi`) covering what the code calls; a narrow per-package `ignore_missing_imports` with a comment.
