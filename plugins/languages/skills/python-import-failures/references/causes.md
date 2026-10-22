# The five causes, in detail

Contents: shadowing, script versus module, missing from the wheel, namespace packages, editable installs, a quick decision table.

## Shadowing

Symptom: `AttributeError: module 'random' has no attribute 'choice'`, or an import that works and then misbehaves. A file or directory in the first `sys.path` entry has the name of a stdlib module or an installed package. Common culprits: `random.py`, `types.py`, `email/`, `logging.py`, `test.py`, `requests.py`, `numpy.py`.

Prove it:

```bash
python -c 'import random; print(random.__file__)'
python -I -c 'import random; print(random.__file__)'
```

A path inside your project on the first line and a stdlib path on the second is the whole diagnosis. Rename the local file; do not work around it.

## Script versus module

`python pkg/tool.py` makes `pkg/` the first path entry. `import pkg` then looks for `pkg/pkg`, and `import sibling` finds `pkg/sibling.py` as a top-level module, so the same file is later imported a second time under another name (`pkg.sibling`) and module-level state is duplicated. `python -m pkg.tool` from the project root puts the root first and keeps names consistent. For anything others run, declare a console script entry point so the installed command does not depend on the cwd.

## Missing from the wheel

Check in this order: is the directory a package at all (see namespace packages), does the build configuration list or discover it, and is data included. With setuptools in `pyproject.toml`, discovery lives under `[tool.setuptools.packages.find]` (set `where = ["src"]` for a `src/` layout); non-Python files need `package-data` or `include-package-data`. Compare `python -m zipfile -l dist/*.whl` with the tree. A package present in an sdist but absent from the wheel points at configuration, not at the build tool.

## Namespace packages

A directory without `__init__.py` is importable as a namespace package. Its `__file__` is `None` and its `__path__` can span several directories. This is how two distributions share a top-level name on purpose, and how an accidental missing file turns into a package that imports fine locally and is dropped by `find_packages()` when building. If the intent is an ordinary package, add the file. If the intent is a namespace, use namespace discovery explicitly and make sure no distribution ships an `__init__.py` at the shared level.

## Editable installs

`pip show <dist>` reports `Editable project location` for a legacy or modern editable install. Modern editable installs add a `.pth` file or an import hook named `__editable__*` in site-packages; list it with `ls "$(python -c 'import site; print(site.getsitepackages()[0])')" | grep -i editable`. Stale when the checkout was moved, a branch removed a package, or a hook maps only the top-level modules that existed at install time, so a new top-level package added later is not importable until you reinstall. Reinstall with `pip install -e .` from the right directory in the right environment.

## Decision table

| Observation | Likely cause |
| --- | --- |
| `__file__` inside your project for a stdlib name | shadowing |
| Works with `-m`, fails as a script, or the reverse | script versus module |
| Works in the tree, fails after `pip install` of the wheel | missing from the wheel |
| `__file__` is `None` | namespace package |
| Works for old modules, fails for a new one, in an editable install | stale editable hook |
| `python -I` fails, plain run works | the cwd or `PYTHONPATH` was supplying it |
