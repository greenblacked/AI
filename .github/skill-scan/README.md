# Skill scan baselines

Two jobs in [`security.yml`](../workflows/security.yml) scan every shipped skill under
`plugins/*/skills/*/` with a third-party agent-skill scanner and fail only on a high or
critical finding nobody has reviewed. This directory holds what they were reviewed against.
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
   `SKILLSPECTOR_COMMIT`, in `security.yml`.
2. Run the new version over the whole tree (`docs/ci.md` has the commands) and triage every
   high and critical finding under the rule above.
3. Rewrite the accepted list or policy from that triage rather than carrying old entries
   forward, and prune what no longer matches.

The Cisco suppressions all expire on 2027-05-02. When they lapse, the findings they cover
fail the job again; re-read each one against the flagged lines and set a new date only for
those that still hold.
