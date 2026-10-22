# Help layout

## Contents

- The help template
- Writing each part
- Man page sections
- Exit codes
- Review checklist

## The help template

An annotated `--help` for one subcommand. The tool, flags and values are invented to show
the shape; replace them with the parser's real ones.

```text
Usage: shipctl deploy [OPTIONS] <SERVICE> [<SERVICE>...]

Deploy one or more services to an environment.

Target:
  -e, --env <NAME>          Environment to deploy to (one of: dev, stage, prod)
                            [env: SHIPCTL_ENV] [required]
      --region <REGION>     Region to deploy to [default: the environment's primary]

Behaviour:
      --dry-run             Print the plan and exit without changing anything
                            (conflicts with --force)
      --force               Deploy even if health checks are failing
                            (conflicts with --dry-run)
      --timeout <DURATION>  Give up waiting for health after this long [default: 5m]
                            [env: SHIPCTL_TIMEOUT]

Output:
  -o, --output <FORMAT>     Output format (one of: text, json) [default: text]
  -q, --quiet               Print errors only
  -v, --verbose             More detail; repeat for more (-vv)

Examples:
  # Deploy the API to staging
  shipctl deploy --env stage api

  # See what a production deploy of two services would change
  shipctl deploy --env prod --dry-run api worker

  # Deploy from CI with machine-readable output
  SHIPCTL_ENV=prod shipctl deploy -o json api

Exit codes:
  0  Deployed, or plan printed with --dry-run
  1  Deploy failed; see the error for the service and step
  2  Usage error
  3  Health checks did not pass within --timeout

Flags override environment variables, which override ~/.config/shipctl/config.toml.
See 'shipctl help environment' for every variable shipctl reads.
```

## Writing each part

| Part | Rule | Why |
| --- | --- | --- |
| Usage line | Real command path, then options, then positionals with `<>`, optional in `[]`, repeatable with `...` | It is the first thing read and the line copied into bug reports |
| Purpose line | One sentence, starts with a verb, no "This command..." | The listing of subcommands reuses it, so it must stand alone |
| Groups | By task, three to five groups, the commonest first | Readers scan for a job, not a letter |
| Flag line | Short and long form, placeholder naming the kind of value, one-line description | A placeholder like `<DURATION>` tells the reader the format without another sentence |
| Choices | Listed inline when there are few, otherwise "see `prog help formats`" | Hidden choices get guessed |
| Default | Shown in brackets, real value or the rule that computes it | "Sensible default" is not information |
| Environment variable | Shown in brackets on the flag it sets | Readers debugging CI need to know a variable is in play |
| Interactions | "conflicts with", "requires" on the flag itself | The reader sees it at the moment they choose the flag |
| Examples | Three, real values, a comment saying the outcome | Most readers copy an example before they read a flag |
| Exit codes | Every code the command can return on purpose | Scripts branch on them |
| Precedence | One line, on the top-level help and in the reference | It decides which of three settings won |

Keep descriptions under the terminal width at 80 columns. A description that needs a
paragraph belongs in the long help or the man page; the short help gets one line.

When the tool distinguishes `-h` from `--help`, make `-h` the compact form (usage,
purpose, flags) and `--help` the full form (plus long descriptions, examples, exit codes),
and say so at the bottom of the compact form. `prog help <command>` and
`prog <command> --help` print the same text.

`--version` prints the program name and version on one line to standard output and
exits 0, so scripts and bug reports can capture it.

## Man page sections

Use the conventional section names in this order, as described in `man-pages(7)`; omit a
section only when it would be empty.

| Section | Content |
| --- | --- |
| NAME | `prog-deploy - deploy one or more services to an environment` |
| SYNOPSIS | The usage line or lines |
| DESCRIPTION | What the command does, in a paragraph or two |
| OPTIONS | Every flag, in the same groups as the help |
| EXIT STATUS | The exit code table |
| ENVIRONMENT | Every variable read, with the flag it corresponds to |
| FILES | Config files and where they are looked for, in order |
| EXAMPLES | The help examples, plus any longer ones |
| SEE ALSO | Related subcommands and the web reference URL |

User commands go in section 1, so the file is `prog-deploy.1` and is installed under the
system's `man1` directory. Lint it with `mandoc -T lint prog-deploy.1` and view a local
copy with `man ./prog-deploy.1`.

## Exit codes

| Code | Common meaning | Note |
| --- | --- | --- |
| 0 | Success | Including "nothing to do" unless scripts need to tell the two apart |
| 1 | General failure | The default for an unhandled error |
| 2 | Usage error | Bad flag, missing argument; argparse and click both use 2 |
| 3 to 63 | Tool-specific outcomes | Document each; keep them stable once released |
| 64 to 78 | BSD `sysexits.h` codes | Only if the tool adopts that convention throughout |
| 126, 127 | Set by the shell | Command not executable, command not found; do not reuse |
| 128 + n | Set by the shell | Terminated by signal n (130 is Ctrl-C); do not reuse |

Distinct codes are worth having only where a script would act differently on them: a
health-check timeout that a pipeline retries is worth its own code, a malformed config
file is not distinguishable in practice from any other failure. Once released, an exit
code's meaning is part of the interface, the same as a flag's name.

## Review checklist

- [ ] Usage line matches the parser's actual argument order and arity
- [ ] Every flag has a description, a default or "required", and its environment variable
- [ ] Groups by task; no group of one
- [ ] Every conflict and requirement is stated on both flags involved
- [ ] Precedence of flags, environment and config file is written once and tested
- [ ] Three examples, each run in CI
- [ ] Exit codes listed and matching what the code returns
- [ ] Help on standard output, exit 0; usage errors on standard error, non-zero
- [ ] Deprecated flags hidden from the main help, listed in the reference with a removal version
- [ ] Output identical at `COLUMNS=80` with `NO_COLOR=1` on two machines
