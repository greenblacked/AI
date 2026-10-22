# Generators per framework

## Contents

- Where each fact lives in the parser
- Man page and web reference generators
- Completion generators
- Snapshot-testing the help
- When the parser cannot be introspected

Check the framework version the project pins before copying a recipe: several of these
features arrived in a specific release, and the generator packages move faster than the
parsers they read.

## Where each fact lives in the parser

| Fact | argparse | click | Typer | cobra (Go) | clap (Rust) | oclif (Node) |
| --- | --- | --- | --- | --- | --- | --- |
| Purpose line | `description=` | docstring or `help=` on the command | docstring or `help=` | `Short` | first line of the doc comment, or `about` | `static summary` / `description` |
| Flag description | `help=` | `help=` | `help=` | the usage string in `Flags().StringP(...)` | doc comment or `help` on `#[arg]` | `description` on the flag |
| Default shown | `ArgumentDefaultsHelpFormatter`, or `%(default)s` in `help` | `show_default=True` | shown by default | shown automatically for non-zero defaults | `default_value_t` | `default` |
| Environment variable | no slot: `default=os.environ.get(...)` and name it in `help` | `envvar=` plus `show_envvar=True` | `envvar=` | no slot: bind with viper and name it in the usage string | `env = "VAR"` (needs the `env` feature) | `env` on the flag |
| Value placeholder | `metavar=` | `metavar=` | `metavar=` | a back-quoted word in the usage string (pflag's `UnquoteUsage`), otherwise the value's type name | `value_name` | `helpValue` |
| Flag groups | `add_argument_group(title)` | none built in | `rich_help_panel=` | command groups only (`AddGroup`, `GroupID`) | `help_heading` | `helpGroup` |
| Conflicts | `add_mutually_exclusive_group()` | check in a callback, raise `click.UsageError` | as click | `MarkFlagsMutuallyExclusive` | `conflicts_with` | `exclusive` |
| Requirements | none built in: check after parsing, call `parser.error()` | as conflicts | as click | `MarkFlagsRequiredTogether`, `MarkFlagRequired` | `requires` | `dependsOn` |
| Examples | `epilog=` with `RawDescriptionHelpFormatter` | in the docstring after a `\b` line so it is not rewrapped | `epilog=` | `Example` | `after_help` / `after_long_help` | `static examples` |
| Exit codes | `parser.exit(status)`; usage errors exit 2 | `ctx.exit(code)`; usage errors exit 2 | `raise typer.Exit(code)` | your `main` calls `os.Exit`; cobra itself returns an error | `std::process::exit`; usage errors exit 2 | `this.exit(code)` |

Where a slot is missing, keep the fact in one data structure in the code — a list of
`(code, meaning)` pairs, a list of examples — and render it into the help epilogue and
the generator input from that structure. That is still one source.

Cobra's `MarkFlagsMutuallyExclusive` and `MarkFlagsRequiredTogether` are relatively recent
additions; on an older cobra, enforce the rule in `PreRunE` and state it in both flags'
usage strings.

## Man page and web reference generators

| Framework | Man page | Web reference |
| --- | --- | --- |
| argparse | `argparse-manpage`, which reads the parser object | `sphinx-argparse` (`.. argparse::` directive) |
| click | `click-man` | `sphinx-click` (`.. click::` directive) or `mkdocs-click` |
| Typer | via click's tools on the underlying click command (`typer.main.get_command(app)`) | `typer <module> utils docs --name prog --output docs/cli.md` |
| cobra | `doc.GenManTree(cmd, header, dir)` from `github.com/spf13/cobra/doc` | `doc.GenMarkdownTree(cmd, dir)` or `doc.GenReSTTree` |
| clap | `clap_mangen` (`Man::new(cmd).render(&mut out)`) in `build.rs` or an xtask | `clap-markdown`, or render the help text into the docs build |
| oclif | none built in | `oclif readme` writes the command reference into the README or a docs directory |

Points that bite:

- **Generation timestamps.** cobra's doc generators append a footer naming cobra and
  the generation date unless `cmd.DisableAutoGenTag = true` is set on the root command. With the tag on, every regeneration is a diff and the freshness check
  fails daily for no reason.
- **Hidden and deprecated flags.** Confirm the generator honours `hidden` the same way the
  help does; otherwise the web reference documents what the help hides, or the reverse.
- **One page per subcommand.** The tree generators write one file per command. Link them
  from an index the docs build generates too, or the index becomes the hand-made copy.
- **Lint the output.** `mandoc -T lint` for man pages; run the docs build's own link
  checker over the generated reference.

## Completion generators

| Framework | How | Shells | Dynamic values |
| --- | --- | --- | --- |
| argparse | `shtab` generates a static script from the parser; `argcomplete` completes at run time | `shtab`: bash, zsh, tcsh | `argcomplete` completers on the argument |
| click | built in: `_PROG_COMPLETE=bash_source prog` (and `zsh_source`, `fish_source`), where `PROG` is the program name upper-cased with dashes as underscores | bash, zsh, fish | `shell_complete=` callback on the parameter |
| Typer | built in: `prog --install-completion`, `prog --show-completion` | bash, zsh, fish, PowerShell | `autocompletion=` on the parameter |
| cobra | built in `completion` subcommand; or `GenBashCompletionV2`, `GenZshCompletion`, `GenFishCompletion`, `GenPowerShellCompletionWithDesc` | bash, zsh, fish, PowerShell | `ValidArgsFunction`, `RegisterFlagCompletionFunc` |
| clap | `clap_complete::generate(Shell::Bash, &mut cmd, "prog", &mut out)` at build time | bash, zsh, fish, PowerShell, elvish | static by default; check the `clap_complete` release notes for dynamic support |
| oclif | `@oclif/plugin-autocomplete` | bash, zsh, PowerShell | per-flag completion functions in the plugin |

Install completions from the package: Homebrew formulae, Debian packages and most
distribution packaging have a standard location per shell. A completion script users have
to remember to `source` from a README is one most of them never install.

## Snapshot-testing the help

The shape is the same in every language: run each command's `--help` with the output
pinned, compare with a checked-in file, and offer an explicit flag to rewrite the files
so an intended change is one command and a reviewed diff.

Python, with pytest, through the installed entry point:

```python
import os
import subprocess
from pathlib import Path

import pytest

COMMANDS = [[], ["deploy"], ["rollback"]]
SNAPSHOTS = Path(__file__).parent / "help_snapshots"
PINNED = {**os.environ, "COLUMNS": "80", "NO_COLOR": "1", "LC_ALL": "C.UTF-8"}


@pytest.mark.parametrize("cmd", COMMANDS, ids=lambda c: "-".join(c) or "root")
def test_help_snapshot(cmd, request):
    out = subprocess.run(
        ["shipctl", *cmd, "--help"], env=PINNED, capture_output=True, text=True, check=True
    ).stdout
    path = SNAPSHOTS / f"{'-'.join(cmd) or 'root'}.txt"
    if request.config.getoption("--update-snapshots", default=False):
        path.write_text(out)
    assert out == path.read_text()


def test_usage_error_goes_to_stderr_with_exit_2():
    result = subprocess.run(
        ["shipctl", "deploy", "--no-such-flag"], env=PINNED, capture_output=True, text=True
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "--no-such-flag" in result.stderr
```

`COMMANDS` is written by hand here, so a new subcommand would have no snapshot and no
failure. Derive the list from the parser (click's `Group.commands`, cobra's `Commands()`,
argparse's subparsers action) or add a test asserting that the discovered set equals
`COMMANDS`. The `PINNED` environment also starts from the host's, so a developer's
exported `SHIPCTL_*` variable can change a default the help prints; build it from a
minimal base such as `{"PATH": os.environ["PATH"], ...}` when the help shows defaults.

Register `--update-snapshots` in `conftest.py` with `pytest_addoption`. For click and
Typer, `CliRunner().invoke(cli, ["deploy", "--help"], terminal_width=80)` avoids the
subprocess; running the installed entry point instead also catches a broken packaging
entry point. A snapshot library such as `syrupy` does the same job with less code.

Go: a golden-file test that executes the root command with `SetArgs`, captures output
through `SetOut` and `SetErr`, and compares against `testdata/*.golden`, rewritten when
the test runs with a custom `-update` flag. Set `COLUMNS` and `NO_COLOR` in the test's
environment if any help template reads them.

Rust: `trycmd` runs `.toml` or `.md` case files containing the command and its expected
output, and `TRYCMD=overwrite` rewrites them; `snapbox` and `insta` with `assert_cmd` are
the lower-level alternatives.

Node: run the built binary with `execFile` and compare against a file, or use the test
helpers the oclif project ships for its version.

Pin terminal width, colour and locale in every variant. A snapshot that passes on a
laptop and fails in CI because the CI runner reports a different terminal width is the
usual reason teams delete these tests.

## When the parser cannot be introspected

Some tools build their help by hand, or are shell scripts. Two fallbacks, in order:

1. **Move to a declarative parser.** Usually smaller than it looks, and the only fix that
   makes every later step free.
2. **Scrape the help.** `help2man ./prog` builds a man page from `--help` and `--version`
   output. It loses grouping and interactions and depends on the help following GNU
   conventions, so treat its output as a stopgap and snapshot-test the help it scrapes.
