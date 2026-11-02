# Skill scan baselines

Two jobs in [`security.yml`](../workflows/security.yml) scan the shipped skills under
`plugins/*/skills/*/` with a third-party agent-skill scanner and fail only on a high or
critical finding nobody has reviewed. Cisco's scans every skill on every run;
SkillSpector scans the skills a pull request changes (every skill when the pull request
changes the scan configuration) and every skill on other events. The scan configuration
is `security.yml` itself, anything in this directory,
`.github/requirements/skillspector.txt` and `scripts/skill_scan_gate.py`: a change to any
of them can change the verdict on a skill the diff never touches, so it re-scans them all. This directory holds what they were reviewed against.
[`docs/ci.md`](../../docs/ci.md#the-security-jobs-in-detail) explains the jobs.

| File | Read by | What it holds |
| --- | --- | --- |
| `cisco-policy.yaml` | `skill-scanner` (`cisco skill scan`) | Suppressions for cisco-ai-skill-scanner, each scoped to one rule, the named skills and one file |
| `skillspector-accepted.json` | `skillspector` (`skillspector skill scan`), through `scripts/skill_scan_gate.py` | Accepted SkillSpector findings, each keyed on rule, path and matched text |

Neither scanner reads subagent or command files (`plugins/*/agents/`,
`plugins/*/commands/`), so those get no scan here. A clean scan is one layer, not proof that
a skill is safe: Cisco's own README reports its rules alone catch only about 8% of held-out
malicious skills, and both tools match patterns rather than read intent.

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
3. If it is not, add an entry: for Cisco, a suppression in `cisco-policy.yaml` with the
   rule, skill, file, reason and the same `expires` date as the rest; for SkillSpector, an
   entry in `skillspector-accepted.json` with `rule_id`, `path`, `match` (the SARIF
   result's `properties.finding`, whitespace collapsed to single spaces), `class` and
   `reason`. Say in the commit why it is not real.

The SkillSpector gate prints a notice for each accepted entry that no longer matches
anything in a skill it scanned. Remove those entries; they would otherwise hide the same
text if it came back.

## Refreshing after a scanner bump

A new scanner version can rename rules, change what text a rule reports, or add rules, so
a bump is a re-review, not a version edit:

1. Regenerate the matching file in `.github/requirements/` as its header describes, and
   move `SKILL_SCANNER_VERSION`, or `SKILLSPECTOR_VERSION` together with
   `SKILLSPECTOR_COMMIT`, in `security.yml`. The header's `uv lock` step carries an
   `--upgrade-package` pin for each dependency moved past upstream's lock to clear an
   advisory: drop a pin the new upstream lock already meets or passes, keep the rest, and
   set `--exclude-newer` to seven days before the run.

A security advisory against a dependency between scanner bumps is fixed the same way:
add an `--upgrade-package` pin at the fixed version to the header, with the advisory id,
and regenerate. Never edit a version line by hand. A new version can need a dependency the
file does not carry, which the `--require-hashes` install refuses, and the next
regeneration would revert it. `.github/dependabot.yml` ignores every dependency in that
directory for this reason, so an advisory shows up as an alert in the Security tab rather
than as a pull request.
2. Run the new version over the whole tree (`docs/ci.md` has the commands) and triage every
   high and critical finding under the rule above.
3. Rewrite the accepted list or policy from that triage rather than carrying old entries
   forward, and prune what no longer matches.

The Cisco suppressions all expire on 2027-05-02. When they lapse, the findings they cover
fail the job again; re-read each one against the flagged lines and set a new date only for
those that still hold.
