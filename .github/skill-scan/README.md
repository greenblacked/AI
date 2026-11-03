# Skill scan baselines

Two jobs in [`security.yml`](../workflows/security.yml) scan the shipped skills under
`plugins/*/skills/*/`, and the subagent and command definitions, with a third-party
agent-skill scanner and fail only on a high or critical finding nobody has reviewed.
Cisco's scans every skill and definition on every run; SkillSpector scans the skills and
definitions a pull request changes (all of them when the pull request changes the scan
configuration) and all of them on other events. The scan configuration is `security.yml`
itself, anything in this directory, `.github/requirements/skillspector.txt`,
`scripts/skill_scan_gate.py` and `scripts/definition_shims.py`: a change to any of them can
change the verdict on a skill or definition the diff never touches, so it re-scans them all. This directory holds what they were reviewed against.
[`docs/ci.md`](../../docs/ci.md#the-security-jobs-in-detail) explains the jobs.

| File | Read by | What it holds |
| --- | --- | --- |
| `cisco-policy.yaml` | `skill-scanner` (`cisco skill scan`) | Suppressions for cisco-ai-skill-scanner, each scoped to one rule, the named skills and one file |
| `skillspector-accepted.json` | `skillspector` (`skillspector skill scan`), through `scripts/skill_scan_gate.py` | Accepted SkillSpector findings, each keyed on rule, path and matched text |

## Definitions

Neither scanner has an agent or command type; each reads a skill directory's `SKILL.md`
only. `scripts/definition_shims.py` wraps every `*.md` directly inside
`plugins/*/agents/` and `.claude/agents/`, and at any depth inside `plugins/*/commands/`
and `.claude/commands/`, as a one-file skill, `<out>/<id>/SKILL.md`, so both scanners can
read it; that is where the validator looks for each. `agents/evals/`,
`.claude/agents/benchmarks/` and an agent in a folder are not wrapped, and a `README.md`
or `readme.md` directly in an `agents/` folder is skipped only while it has no frontmatter, which an
agent needs to load; one that opens with frontmatter fails the run. One in a `commands/` folder is wrapped like any command, with the id from its
lowercased stem (`command--<plugin>--readme`), because Claude Code loads every `.md` there
as a slash command; the validator ignores it, and the scan deliberately does not, so a
planted one cannot ship unscanned. It also writes `<out>/map.tsv`, one `<id>`, a tab, the
source path, a tab and the number of lines the shim adds above the source's own, per line;
the SkillSpector gate reads it to report and match a finding against the real file.

The id is part of the contract, because a Cisco suppression names it:

| Source | Id |
| --- | --- |
| `plugins/<plugin>/agents/<stem>.md` | `agent--<plugin>--<stem>` |
| `plugins/<plugin>/commands/<stem>.md` | `command--<plugin>--<stem>` |
| `plugins/<plugin>/commands/<folder>/<stem>.md` | `command--<plugin>--<folder>--<stem>` |
| `.claude/agents/<stem>.md` | `agent--claude--<stem>` |
| `.claude/commands/<stem>.md` | `command--claude--<stem>` |
| `.claude/commands/<folder>/<stem>.md` | `command--claude--<folder>--<stem>` |

Every part is lowercase letters, digits and single hyphens, so `--` is always a separator, and deeper folders add one part each. No plugin may be named `claude`, and a duplicate id fails the script. A shim is a byte
copy of the source except for its `name`. An agent's `name:` line is replaced in place with
`name: <id>`, so line numbers are unchanged. A command has no `name`, so `name: <id>` is
inserted as the first frontmatter line: Cisco's strict load needs one, and without it
discards the command's `allowed-tools`. A command README with no frontmatter is given a minimal block, `name: <id>` and
`description: <id>`, so both scanners load it; its findings map back four lines. A finding
on any other command is mapped back one line.
Cisco matches a suppression's `skills:` against that name, so a Cisco suppression for a
definition names the shim id, while a SkillSpector accepted entry names the source path.

What this covers is the scanners' prompt-injection, exfiltration and obfuscation rules
over each definition's instructions and frontmatter. It does not analyse tool grants:
both scanners' permission checks compare declared tools against executable code, and
these files have none, so an agent's `tools:` is text-scanned only. Review owns the grant.

A clean scan is one layer, not proof that a skill or definition is safe: Cisco's own README
reports its rules alone catch only about 8% of held-out malicious skills, and both tools
match patterns rather than read intent.

## The triage rule

An entry goes in either file only when the flagged text is one of these, read by hand:

- a false positive: the scanner matched a word or pattern the skill names in order to
  warn against it, quotes as data, or uses in an ordinary procedure;
- accepted by design: the skill does the flagged thing on purpose, and a guard in the
  skill — a confirmation, a scoped permission, a read-only command — keeps it safe.

A real issue is never accepted. It is fixed, and the finding disappears with the fix. The
gate refuses an accepted entry with no reason, or with a class other than the five above
(`FP-scanner-limitation`, `FP-defensive`, `FP-legitimate-procedure`, `FP-eval/data`,
`ACCEPTED-by-design`).

Both files cover a whole file rather than a line. Cisco's policy has no line selector, and
the SkillSpector key leaves the line out so that an edit above a reviewed finding does not
reopen it. The cost is the same in both: a new finding of the same rule in the same file,
with the same matched text for SkillSpector, is hidden too. Review a change to a flagged
file with that in mind.

A short accepted match widens that further. A handful of SkillSpector entries match only
a few characters — `rm -rf /`, `&& rm -`, `| sudo`, `--privileged`, `.env`, `keychain`,
`access token` — which recur in almost any text about the same subject, so each acts close
to a suppression of its rule for the whole file. They stand as triaged today; tighten each
to the longer span around it at the next refresh rather than carrying it forward.

## When a scan fails

1. Download the job's report artifact (`skill-scanner-report` or `skillspector-report`)
   and read the finding in the SARIF, not only the annotation.
2. Read the flagged lines in the skill. If the finding is real, fix the skill.
   A definition is triaged by the same rule: a real issue is fixed in the agent or command
   file itself, never in the shim.
3. If it is not, add an entry: for Cisco, a suppression in `cisco-policy.yaml` with the
   rule, skill (for a definition, the shim id from the table above), file, reason and the same `expires` date as the rest; for SkillSpector, an
   entry in `skillspector-accepted.json` with `rule_id`, `path`, `match` (the SARIF
   result's `properties.finding`, whitespace collapsed to single spaces), `class` and
   `reason`. For a definition, `path` is the source path, such as
   `plugins/<plugin>/agents/<stem>.md`, not the shim. Say in the commit why it is not real.

The SkillSpector gate prints a notice for each accepted entry that no longer matches
anything in a skill it scanned. Remove those entries; they would otherwise hide the same
text if it came back.

An AE1 finding (`<file> (partial)`) whose SARIF evidence gives the reason code
`runtime_limit` is not about the skill: SkillSpector ran out of one of its time budgets,
which a slow runner can cause on a skill nobody changed. The gate lists such a skill and
the workflow step rescans it on its own, once; the final pass fails it as an incomplete
scan only if it runs out of time again; then re-run the job. Never add a time-limited AE1 to `skillspector-accepted.json`. The gate
would not match it anyway, and the scan behind it may have missed a real finding. The
accepted AE1 entries are the content-driven ones, `static_parse_limit` and
`obfuscated_instruction_text`.

## Refreshing after a scanner bump

A new scanner version can rename rules, change what text a rule reports, or add rules, so
a bump is a re-review, not a version edit:

1. Regenerate the matching file in `.github/requirements/` as its header describes, and
   move `SKILL_SCANNER_VERSION`, or `SKILLSPECTOR_VERSION` together with
   `SKILLSPECTOR_COMMIT`, in `security.yml`. The header's `uv lock` step carries an
   `--upgrade-package` pin for each dependency moved past upstream's lock to clear an
   advisory: drop a pin the new upstream lock already meets or passes, keep the rest, and
   set `--exclude-newer` to seven days before the run.
2. Run the new version over the whole tree (`docs/ci.md` has the commands) and triage every
   high and critical finding under the rule above.
3. Rewrite the accepted list or policy from that triage rather than carrying old entries
   forward, and prune what no longer matches.

A security advisory against a dependency between scanner bumps is fixed the way step 1
regenerates the file: add an `--upgrade-package` pin at the fixed version to the header,
with the advisory id, and regenerate. Never edit a version line by hand. A new version can need a dependency the
file does not carry, which the `--require-hashes` install refuses, and the next
regeneration would revert it. `.github/dependabot.yml` ignores every dependency in that
directory for this reason, so an advisory shows up as an alert in the Security tab rather
than as a pull request. The weekly `dependency-advisories` job in
[`scheduled.yml`](../workflows/scheduled.yml) looks the locks up in OSV and goes red on a
new advisory; `docs/ci.md` says how to clear it, and `.github/requirements/advisories-accepted.json`
holds a reviewed acceptance, with a reason and an expiry.

The Cisco suppressions all expire on 2027-05-02. When they lapse, the findings they cover
fail the job again; re-read each one against the flagged lines and set a new date only for
those that still hold.
