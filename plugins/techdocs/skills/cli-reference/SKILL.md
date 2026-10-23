---
name: cli-reference
description: "Document a command-line tool so --help, the man page, the web reference and shell completions all come from one source, the parser definition. Lays help out as a usage line, a one-line purpose, flags grouped by task with defaults and environment variables, three real examples and exit codes; states which flags conflict, require each other or override; generates the man page, reference and completions in the build instead of copying them; and snapshot-tests --help so an interface change shows up in review. Use whenever someone says \"document this command-line tool\", \"our --help and the README disagree\", \"generate a man page for our CLI\", \"add shell completions\" or \"what exit codes should we document\". Not for writing the tool (code-scaffold), an HTTP interface (api-design), the getting-started walkthrough (tutorial-clean-room), or a page per error code (error-catalogue)."
allowed-tools: Read, Write, Edit, Grep, Glob
---

# CLI Reference

The reference is done when `--help`, the man page, the web reference and the shell
completions are all generated from the parser definition, a snapshot test fails on any
change to the help output, and every flag's default, environment variable and
interactions with other flags are stated in all of them at once.

The usual failure is a README table of flags written once by hand. It is right on the day
it is written. A month later a default changes in the parser, a flag is renamed with an
alias, an environment variable is added, and the table still shows the old world. The
`--help` output is correct because the parser prints it, so the two disagree, and the
reader cannot tell which to believe. Copying help text into a docs page is the same
defect with a longer fuse. The fix is structural: there is one definition and everything
else is output.

## Scope

Use for: documenting an existing CLI, restructuring unreadable help text, generating a
man page or web reference from the parser, shipping completions, choosing and
documenting exit codes, and the test that keeps the help honest.

Not for: building the tool, which is `code-scaffold`; designing an HTTP or RPC interface,
which is `api-design`; the walkthrough that takes a newcomer to a first result, which is
`tutorial-clean-room`; an explanatory page per error code the tool prints, which is
`error-catalogue`; prose pages elsewhere that mention flags and go stale, which is
`docs-drift-detection`; keeping example snippets on docs pages executable, which is
`code-sample-testing`.

## Workflow

### 1. Inventory the interface from the parser

Read the parser definition, not the existing docs: every command and subcommand, every
flag with its short and long form, value type, choices, default, environment variable,
whether it repeats, and which flags are hidden or deprecated. Then find every hand-made
copy of that information — README tables, docs-site pages, a committed man page, help
text in a wiki — and diff each against the parser. Each disagreement is a defect report
for whichever side is wrong, and each copy is a candidate for deletion once generation is
in place.

Running the tool's `--help` for every command is the fastest cross-check. It runs the
project's own code, so it asks for approval like any other command.

### 2. Move every fact into the parser definition

Descriptions, defaults, choices, environment variable bindings, value placeholders and
examples belong in the parser's own fields, so the help printer and the generators read
the same data. Most frameworks have a slot for each; `references/generators.md` lists
them per framework.

Where the framework has no slot — exit codes and examples often have none — keep one
data structure in the code (a table of exit codes, a list of examples) that feeds both
the help epilogue and the generators. A second copy in a Markdown file is how drift
starts again.

Defaults must be the real ones. A default computed at runtime (the number of CPUs, a
path under the user's home directory) is shown as the rule ("number of CPUs"), not as the
value on the machine that built the docs, or the generated page will publish the build
server's core count as the default.

### 3. Lay out the help

Work to the layout in `references/help-layout.md`. In order:

1. A usage line with the conventional notation: `[...]` optional, `<...>` a value,
   `...` repeatable, `|` alternatives.
2. One line saying what the command does, starting with a verb.
3. Flags grouped by task (input, output, behaviour, connection), not alphabetically.
   Each shows its short and long form, a value placeholder, a one-line description, its
   default and its environment variable.
4. Three real examples, most common task first, each one a command a user would
   actually run with a one-line comment saying what it achieves.
5. Exit codes, and the environment variables the command reads.

Help goes to standard output and exits 0, so `prog --help | less` works. A usage error
prints the short usage and one line naming the mistake to standard error and exits
non-zero — 2 is the common convention for usage errors. When the tool has a short `-h`
and a long `--help`, say which is which in both.

### 4. State flag interactions

Readers are hurt more by combinations than by single flags. For each command, state:

- **Conflicts.** Flags that cannot be combined, enforced by the parser so the error is
  immediate, and listed in each flag's description.
- **Requirements.** A flag that is meaningful only with another.
- **Overrides and precedence.** Which wins when the same setting comes from a flag, an
  environment variable, a config file and a default. Command-line flags over environment
  over config file over default is the common order; whatever the tool does, write it
  once in the reference and test it.
- **Repetition.** Whether a repeated flag accumulates (`-v -v`), takes the last value or
  is an error.
- **Negation.** Whether `--no-x` exists for each boolean, so a default turned on in
  a config file can be turned off for one run.

Declare conflicts and requirements in the parser where the framework allows it, so the
generated help and the runtime error say the same thing.

### 5. Generate the man page, web reference and completions in the build

Generate all three from the parser in the build, using the framework's generator listed
in `references/generators.md`. Two arrangements work:

- **Generated at release, not committed.** The package build produces the man page and
  completions; the docs build produces the web reference. Nothing can drift because there
  is nothing to edit.
- **Committed, with a freshness check.** Useful when the web reference must live in a
  docs repository. CI regenerates and fails when the committed copy differs:
  regenerate into an emptied directory and fail on any change, including a new file:
  `rm -rf docs/cli && make docs-cli && test -z "$(git status --porcelain -- docs/cli)"`.
  `git diff --exit-code` alone passes when a new command's page was generated but never
  added, and cannot see a page left behind for a removed command.

Lint the generated man page with `mandoc -T lint` before shipping it. A help generator
that scrapes `--help` output (`help2man`) is a fallback for tools whose parser cannot be
introspected; it loses grouping and interactions, so prefer the parser's own generator.

Version the web reference with the tool. Readers on an older release need that release's
flags, and a reference that shows only the latest flags is wrong for most of them.

### 6. Snapshot-test the help

Record the `--help` output of every command as a checked-in snapshot and fail the test
when it changes. The point is not to freeze the help: it is that any change to the
interface arrives in the pull request as a readable diff of what users will see, which a
reviewer can judge when a change to parser code alone would slip past.

Pin what makes the output vary between machines: terminal width (set `COLUMNS=80`, since
several parsers wrap to the terminal), colour (`NO_COLOR=1`, and run without a terminal)
and locale. Add cases for a usage error's output and exit code, and for `--version`.

### 7. Test the examples and ship the completions

Run each help example in CI against a fixture, since an example that fails is worse than
no example. Generate completions for bash, zsh and fish (and PowerShell where Windows is
supported) from the same parser, install them from the package rather than asking users
to source a file, and include dynamic completion of values — resource names, profiles —
where the framework supports it, because that is where completion saves the most typing.

### 8. Deprecate in the reference, not by deletion

A renamed or retired flag stays accepted for at least one release with a warning that
names its replacement. Hide it from the main help, keep it in a deprecated section of the
reference with the version it will be removed in, and record the removal in the release
notes.

## What to hand back

- The inventory: every command and flag, with the disagreements found between the parser
  and each hand-made copy, and which copies are being deleted.
- The parser changes that move descriptions, defaults, environment variables, examples
  and exit codes into one definition.
- The new help layout for one representative command, shown as output.
- The interaction statements per command, and the precedence order.
- The generation setup for man page, web reference and completions, and where each is
  installed or published.
- The snapshot tests and the CI step that runs them.

## Anti-patterns

**A hand-written flag table.** It is a second source of truth with no test. Generate it
or delete it.

**Alphabetical flag lists.** The reader is looking for how to do a task, not for a letter.
Group by task.

**Defaults described as "sensible".** State the value or the rule that computes it.

**Examples that are syntax diagrams.** `prog [OPTIONS] FILE` is the usage line, not an
example. An example is a real command with real values.

**Undocumented exit codes.** Scripts branch on them. An exit code that changes without
notice breaks every script that checked it, and it was never written down to be
reviewed.

**Help on standard error.** `prog --help | grep timeout` then shows nothing, and the
reader concludes the flag does not exist.

## Reference files

- `references/help-layout.md` — read at step 3 when writing or restructuring help: the
  annotated help template, the man page section order, exit code conventions, and the
  checklist for a reviewed help text.
- `references/generators.md` — read at steps 2, 5 and 6 when wiring generation and tests:
  per-framework slots, man page and web reference generators, completion generators and
  snapshot-test recipes for argparse, click, Typer, cobra, clap and oclif.
