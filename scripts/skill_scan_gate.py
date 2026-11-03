#!/usr/bin/env python3
"""Fail on a high or critical SkillSpector finding nobody has reviewed yet.

The `skillspector` job in `security.yml` scans one skill per process and leaves, for each
skill named in its manifest, a SARIF report and the scanner's exit code. A subagent or
command is scanned the same way through a one-file skill, a shim that
`scripts/definition_shims.py` writes, and its manifest line is `<id>\\t<source path>`
instead of a directory. A finding in a shim is reported and accepted against the source
path, so an accepted entry names the file a reviewer opens, and a command's line number is
mapped back past the one line its shim adds. This reads them
and fails the job on any HIGH or CRITICAL result whose key is not in the reviewed list,
`.github/skill-scan/skillspector-accepted.json`. Medium and low findings never gate; they
stay in the SARIF the job uploads.

The key is (rule id, repository-relative path, matched text with its whitespace
collapsed), deliberately without a line number. SkillSpector's own baseline fingerprint
hashes the whole file, the scanner version and the full finding, so editing any line of
a flagged file, or bumping the scanner, would reopen every finding in it and turn CI red
for a change that touched nothing reviewed. The matched text comes from the result's
`properties.finding`, which SkillSpector fills with the span its pattern matched; the
message text is the fallback only when a result carries no such property, because a
message names the rule rather than the text and so matches far more than was reviewed.
The cost of leaving the line out is that one accepted key covers every occurrence of the
same text in the same file, the same file-wide trade the Cisco policy makes.

The gate fails closed. A skill whose scan exited with anything but 0 or 1 (2 is the
scanner's own error code; 1 is only a risk score over its threshold), whose exit code or
SARIF is missing or unreadable, a results directory holding a different number of
reports than the manifest names skills, a report whose `analysisCompleteness` says a file
was left entirely uninspected, and an accepted entry without a reason or with a class
outside the reviewed set are all failures: a scan that did not happen must not read as a
scan that found nothing. An accepted entry that no longer matches anything in a
skill that was scanned is reported as a notice, not a failure, so the list can be pruned
without a stale entry blocking an unrelated change.

A scan SkillSpector cut short on one of its wall-clock budgets is incomplete, not a
finding. The scanner records that as `runtime_limit`, on the AE1 coverage finding it
raises for each file it stopped reading and on the invocation's notifications, and a
stalled runner trips it on a skill that has not changed. Its results are never matched
against the accepted list: a reviewed AE1 is about the file's content, and a scan that
stopped early may have missed a real finding. With `--incomplete-out`, such a skill is
written to that file and the gate exits 3 so the job can rescan it on its own, unless
something else failed; without it, which is the job's final pass, it fails as
incomplete.

Standard library only, like the checks it sits beside. Everything printed that came out
of a SARIF report is text a pull request controls, so it is escaped before it can reach
the runner as a workflow command.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
from dataclasses import dataclass
from pathlib import Path

GATED = {"HIGH", "CRITICAL"}
# The classes a reviewed entry may carry. A real issue is fixed, never accepted, so it
# has no class here and an entry claiming one fails the gate.
ACCEPTED_CLASSES = {
    "FP-scanner-limitation",
    "FP-defensive",
    "FP-legitimate-procedure",
    "FP-eval/data",
    "ACCEPTED-by-design",
}
ENTRY_FIELDS = ("rule_id", "path", "match", "class", "reason")
# The shape every skill directory in this repository has. The manifest is written by a
# shell step, so anything else in it is a selection bug rather than a skill to scan.
SKILL_DIR_RE = re.compile(r"plugins/[A-Za-z0-9][A-Za-z0-9._-]*/skills/[A-Za-z0-9][A-Za-z0-9._-]*")
# The manifest line for a subagent or command: the shim id, a tab and the source file. The
# id scheme is the one `scripts/definition_shims.py` documents, which the Cisco policy
# also keys on; `expected_id` recomputes it from the source so a line cannot pair a shim
# with a file it was not made from.
PART = r"[a-z0-9]+(?:-[a-z0-9]+)*"
DEFINITION_SOURCE_RE = re.compile(
    rf"(?:plugins/(?P<plugin>{PART})|(?P<repo>\.claude))/(?P<kind>agents|commands)/(?P<stem>{PART})\.md"
)
SHIM_LINE_RE = re.compile(
    rf"(?P<id>(?:agent|command)--{PART}--{PART})\t"
    rf"(?P<source>(?:plugins/{PART}|\.claude)/(?:agents|commands)/{PART}\.md)"
)
SHIM_FILE = "SKILL.md"
OK_EXIT_CODES = {0, 1}
MATCH_LIMIT = 200
# SkillSpector 2.13.1's reason code for a time budget running out. Every other reason
# (`static_parse_limit`, `obfuscated_instruction_text`, ...) comes from the content.
RUNTIME_LIMIT = "runtime_limit"
# The exit code that asks the job to rescan the skills in --incomplete-out.
RESCAN = 3


def normalise(text: str) -> str:
    """Collapse every run of whitespace to one space, so reflowing a line keeps its key."""
    return " ".join(text.split())


def stem(skill_dir: str) -> str:
    """`plugins/<plugin>/skills/<skill>` -> `<plugin>__<skill>`, the per-skill file stem."""
    parts = skill_dir.split("/")
    return f"{parts[1]}__{parts[3]}"


def expected_id(source: str) -> str | None:
    """The shim id for a definition's source path, or None if it is not a definition path."""
    match = DEFINITION_SOURCE_RE.fullmatch(source)
    if not match:
        return None
    kind = "agent" if match["kind"] == "agents" else "command"
    return f"{kind}--{match['plugin'] or 'claude'}--{match['stem']}"


@dataclass(frozen=True)
class Target:
    """One scan: a skill directory, or a subagent or command read through its shim."""

    line: str  # exactly as the manifest (and the rescan list) writes it
    stem: str  # the stem of its <stem>.sarif and <stem>.rc
    label: str  # the skill directory or the definition's source path, for messages
    source: str | None = None  # a definition's repository path; None for a skill
    command: bool = False  # a command shim has one line inserted after its first

    @property
    def file(self) -> str:
        """The file an annotation without a finding location points at."""
        return self.source or f"{self.label}/SKILL.md"


def inert(text: str) -> str:
    """Break the legacy `##[command]` marker the runner honours anywhere in a line."""
    return text.replace("##[", "## [")


def escape_data(text: str) -> str:
    return inert(text).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def escape_property(text: str) -> str:
    return escape_data(text).replace(":", "%3A").replace(",", "%2C")


def annotate(
    level: str,
    message: str,
    *,
    file: str | None = None,
    line: int | None = None,
    title: str | None = None,
) -> None:
    props = []
    if file is not None:
        props.append(f"file={escape_property(file)}")
    if line is not None:
        props.append(f"line={line}")
    if title is not None:
        props.append(f"title={escape_property(title)}")
    head = f"::{level} {','.join(props)}" if props else f"::{level}"
    print(f"{head}::{escape_data(message)}")


def shorten(text: str) -> str:
    return text if len(text) <= MATCH_LIMIT else text[: MATCH_LIMIT - 3] + "..."


def read_manifest(path: Path) -> tuple[list[Target], list[str]]:
    """What the job scanned, and any problems with the list itself.

    A line is a skill directory, or `<id>\\t<source path>` for a subagent or command.
    """
    problems = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as err:
        return [], [f"cannot read the manifest {path}: {err.strerror}"]
    targets = []
    for line in (line for line in lines if line):
        shim = SHIM_LINE_RE.fullmatch(line) if "\t" in line else None
        if shim:
            ident, source = shim["id"], shim["source"]
            if expected_id(source) != ident:
                problems.append(f"manifest names {line!r}, whose id does not belong to its file")
                continue
            targets.append(Target(line, ident, source, source, ident.startswith("command--")))
        elif SKILL_DIR_RE.fullmatch(line):
            targets.append(Target(line, stem(line), line))
        elif "\t" in line:
            problems.append(f"manifest names {line!r}, which is not a subagent or command line")
        else:
            problems.append(f"manifest names {line!r}, which is not a skill directory")
    if len({t.line for t in targets}) != len(targets) or len({t.stem for t in targets}) != len(
        targets
    ):
        problems.append("manifest names a skill or definition more than once")
    return targets, problems


def read_accepted(path: Path) -> tuple[dict[tuple[str, str, str], dict], list[str]]:
    """The reviewed keys, and every reason the list itself cannot be trusted."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        return {}, [f"cannot read the accepted list {path}: {err}"]
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return {}, [f"{path} has no `entries` list"]
    accepted: dict[tuple[str, str, str], dict] = {}
    problems = []
    for number, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            problems.append(f"accepted entry {number} is not an object")
            continue
        missing = [
            field
            for field in ENTRY_FIELDS
            if not isinstance(entry.get(field), str) or not entry[field].strip()
        ]
        if missing:
            problems.append(f"accepted entry {number} has no {', '.join(missing)}")
            continue
        if entry["class"] not in ACCEPTED_CLASSES:
            problems.append(
                f"accepted entry {number} has class {entry['class']!r}; only a false "
                f"positive or an accepted-by-design finding may be listed, never a real one"
            )
            continue
        key = (entry["rule_id"], entry["path"], normalise(entry["match"]))
        if key in accepted:
            problems.append(f"accepted entry {number} repeats an earlier entry")
            continue
        accepted[key] = entry
    return accepted, problems


def severity_of(result: dict) -> str | None:
    """The result's severity, or HIGH for an `error`-level result that names none.

    SkillSpector puts its own severity in `properties.severity`. A result without one is
    read by its SARIF level, and an `error` is treated as gating rather than dropped.
    """
    props = result.get("properties")
    if isinstance(props, dict) and isinstance(props.get("severity"), str):
        return props["severity"].upper()
    return "HIGH" if result.get("level") == "error" else None


class IncompleteScanError(ValueError):
    """The scanner ran, but said it never looked at some of the skill's files."""


class RuntimeLimitError(IncompleteScanError):
    """The scanner ran out of time, so the report says nothing about the skill."""


def ran_out_of_time(run: dict) -> bool:
    """Whether a run records a time budget cutting its inspection short.

    Read from each result's `properties.evidence.reasons[].reason_code`, where AE1 says
    why a file was only partly inspected, and from each invocation's
    `toolExecutionNotifications[].properties.reasonCode`, which also records a budget that
    ran out without raising a finding. A `reasons` field that is present but not a list, or
    an entry in it that is not an object, raises ValueError: skipping it could let a
    time-limited finding be matched against the accepted list. Anything else of another
    shape is skipped here; the stricter reading that follows rejects it.
    """
    for result in run.get("results") or []:
        props = result.get("properties") if isinstance(result, dict) else None
        evidence = props.get("evidence") if isinstance(props, dict) else None
        reasons = evidence.get("reasons") if isinstance(evidence, dict) else None
        if reasons is None:
            continue
        if not isinstance(reasons, list):
            raise ValueError("a result's evidence reasons is not a list")
        for reason in reasons:
            if not isinstance(reason, dict):
                raise ValueError("an entry in a result's evidence reasons is not an object")
            if reason.get("reason_code") == RUNTIME_LIMIT:
                return True
    for invocation in run.get("invocations") or []:
        notes = (
            invocation.get("toolExecutionNotifications") if isinstance(invocation, dict) else None
        )
        for note in notes if isinstance(notes, list) else []:
            props = note.get("properties") if isinstance(note, dict) else None
            if isinstance(props, dict) and props.get("reasonCode") == RUNTIME_LIMIT:
                return True
    return False


def check_completeness(invocation: dict) -> None:
    """Raise when the invocation reports a file it did not inspect at all.

    SkillSpector 2.13.1 writes `analysisCompleteness` on each invocation's properties. A
    report without it, from an older or newer scanner, is read as complete rather than
    failed; one that carries it in a shape this cannot read is not.
    """
    props = invocation.get("properties")
    completeness = props.get("analysisCompleteness") if isinstance(props, dict) else None
    if completeness is None:
        return
    if not isinstance(completeness, dict):
        raise ValueError("analysisCompleteness is not an object")
    count = completeness.get("entirelyUninspectedFiles")
    if count is None:
        return
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("entirelyUninspectedFiles is not a count")
    if count > 0:
        raise IncompleteScanError(f"SkillSpector left {count} file(s) entirely uninspected")


def findings_in(target: Target, sarif_path: Path) -> list[tuple[tuple[str, str, str], int, str]]:
    """Every gating result in one report, as (key, line, severity). Raises on a bad file."""
    data = json.loads(sarif_path.read_text(encoding="utf-8"))
    runs = data.get("runs") if isinstance(data, dict) else None
    if not isinstance(runs, list) or not runs:
        raise ValueError("no runs")
    found = []
    for run in runs:
        if not isinstance(run, dict) or not isinstance(run.get("results", []), list):
            raise ValueError("a run is not an object with a results list")
        for invocation in run.get("invocations") or []:
            if not isinstance(invocation, dict):
                continue
            if invocation.get("executionSuccessful") is False:
                raise ValueError("the scanner reported an unsuccessful execution")
        if ran_out_of_time(run):
            raise RuntimeLimitError("SkillSpector ran out of time")
        for invocation in run.get("invocations") or []:
            if isinstance(invocation, dict):
                check_completeness(invocation)
        for result in run.get("results", []):
            if not isinstance(result, dict):
                raise ValueError("a result is not an object")
            severity = severity_of(result)
            if severity not in GATED:
                continue
            rule = result.get("ruleId")
            if not isinstance(rule, str) or not rule:
                raise ValueError("a gating result has no ruleId")
            path, line = location(target, result)
            props = result.get("properties") or {}
            text = props.get("finding") if isinstance(props, dict) else None
            if not isinstance(text, str) or not text.strip():
                message = result.get("message")
                text = message.get("text", "") if isinstance(message, dict) else ""
            found.append(((rule, path, normalise(str(text))), line, severity))
    return found


def location(target: Target, result: dict) -> tuple[str, int]:
    """The repository-relative path and line of a result; the skill itself if it has none.

    SkillSpector writes each URI relative to the skill it scanned. One that is absolute,
    or that climbs out of the skill, is refused: the key would not mean the file it names.
    A shim holds one file, so any URI but its `SKILL.md` is refused too, and the result is
    reported against the definition's source, one line up for a command.
    """
    if target.source is not None:
        return shim_location(target, result)
    skill = target.label
    try:
        physical = result["locations"][0]["physicalLocation"]
    except (KeyError, IndexError, TypeError):
        return skill, 1
    uri = (physical.get("artifactLocation") or {}).get("uri")
    region = physical.get("region") or {}
    line = region.get("startLine")
    line = line if isinstance(line, int) and line > 0 else 1
    if not isinstance(uri, str) or not uri:
        return skill, line
    joined = posixpath.normpath(posixpath.join(skill, uri))
    if uri.startswith("/") or ":" in uri or not joined.startswith(skill + "/"):
        raise ValueError(f"a result's location {uri!r} is outside the skill")
    return joined, line


def shim_location(target: Target, result: dict) -> tuple[str, int]:
    source = target.source or target.label
    try:
        physical = result["locations"][0]["physicalLocation"]
    except (KeyError, IndexError, TypeError):
        return source, 1
    uri = (physical.get("artifactLocation") or {}).get("uri")
    region = physical.get("region") or {}
    line = region.get("startLine")
    line = line if isinstance(line, int) and line > 0 else 1
    if isinstance(uri, str) and uri:
        if uri.startswith("/") or ":" in uri or posixpath.normpath(uri) != SHIM_FILE:
            raise ValueError(f"a result's location {uri!r} is outside the skill")
        if target.command:
            # The shim's second line is the inserted `name:`, so the source is one above.
            line = max(1, line - 1)
    return source, line


def exit_code(rc_path: Path) -> int | None:
    try:
        return int(rc_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def describe(targets: list[Target]) -> str:
    skills = sum(1 for t in targets if t.source is None)
    text = f"{skills} skill(s)"
    if len(targets) > skills:
        text += f" and {len(targets) - skills} definition(s)"
    return text


def gate(
    manifest: Path, results: Path, accepted_path: Path, incomplete_out: Path | None = None
) -> int:
    failures = 0
    targets, problems = read_manifest(manifest)
    accepted, accepted_problems = read_accepted(accepted_path)
    for problem in problems + accepted_problems:
        annotate("error", problem, title="SkillSpector gate")
        failures += 1
    if problems:
        return 1

    reports = sorted(results.glob("*.sarif"))
    if len(reports) != len(targets):
        annotate(
            "error",
            f"found {len(reports)} SARIF report(s) for {describe(targets)} scanned; "
            f"a skill without a report was not scanned, and a report without a skill "
            f"came from somewhere else",
            title="SkillSpector gate",
        )
        failures += 1

    seen: set[tuple[str, str, str]] = set()
    judged: list[str] = []
    rescan: list[str] = []
    new = 0
    for target in targets:
        name, skill = target.stem, target.label
        rc = exit_code(results / f"{name}.rc")
        if rc not in OK_EXIT_CODES:
            reason = "left no exit code" if rc is None else f"exited {rc}"
            annotate(
                "error",
                f"SkillSpector {reason} scanning {skill}; see {name}.log in the artifact",
                file=target.file,
                title="SkillSpector scan failed",
            )
            failures += 1
            continue
        try:
            found = findings_in(target, results / f"{name}.sarif")
        except RuntimeLimitError:
            if incomplete_out is not None:
                annotate(
                    "notice",
                    f"SkillSpector ran out of time scanning {skill}; its results are set "
                    f"aside, and it is rescanned on its own unless something else failed",
                    file=target.file,
                    title="SkillSpector scan incomplete",
                )
                rescan.append(target.line)
                continue
            annotate(
                "error",
                f"SkillSpector ran out of time scanning {skill}, so neither a clean result "
                f"nor a coverage finding there says anything about the skill; re-run the "
                f"job, and see {name}.sarif in the artifact",
                file=target.file,
                title="SkillSpector scan incomplete",
            )
            failures += 1
            continue
        except IncompleteScanError as err:
            annotate(
                "error",
                f"{err} in {skill}, so a clean result there means nothing; see "
                f"{name}.sarif in the artifact",
                file=target.file,
                title="SkillSpector scan incomplete",
            )
            failures += 1
            continue
        except (OSError, ValueError) as err:
            annotate(
                "error",
                f"no readable SARIF for {skill}: {err}",
                file=target.file,
                title="SkillSpector scan failed",
            )
            failures += 1
            continue
        judged.append(target)
        reported: set[tuple[str, str, str]] = set()
        for key, line, severity in found:
            seen.add(key)
            if key in accepted or key in reported:
                continue
            reported.add(key)
            rule, path, text = key
            annotate(
                "error",
                f"{severity} {rule} finding not in .github/skill-scan/"
                f"skillspector-accepted.json: {shorten(text)}",
                file=path,
                line=line,
                title=f"SkillSpector {rule}",
            )
            new += 1

    # Only a skill whose report was read can show that an entry no longer matches.
    skill_dirs = tuple(t.label + "/" for t in judged if t.source is None)
    sources = {t.source for t in judged if t.source is not None}
    stale = sorted(
        key
        for key in accepted
        if (key[1].startswith(skill_dirs) or key[1] in sources) and key not in seen
    )
    for rule, path, text in stale:
        annotate(
            "notice",
            f"accepted {rule} entry no longer matches anything; prune it: {shorten(text)}",
            file=path,
            title="Stale SkillSpector entry",
        )

    if incomplete_out is not None:
        # Written even when empty, so a list left from an earlier run is never rescanned.
        try:
            incomplete_out.write_text("".join(f"{skill}\n" for skill in rescan), encoding="utf-8")
        except OSError as err:
            annotate(
                "error",
                f"cannot write the rescan list {incomplete_out}: {err.strerror}",
                title="SkillSpector gate",
            )
            failures += 1

    print(
        f"skillspector gate: {describe(targets)} scanned, {len(seen)} high or critical "
        f"key(s) seen, {new} new, {len(stale)} stale accepted entr"
        f"{'y' if len(stale) == 1 else 'ies'}, {failures} other failure(s), "
        f"{len(rescan)} to rescan"
    )
    if not targets:
        annotate("notice", "no skill to scan", title="SkillSpector gate")
    if failures or new:
        return 1
    return RESCAN if rescan else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="newline-separated skill directories, and <id><TAB><source> lines for "
        "subagents and commands, that were scanned",
    )
    parser.add_argument(
        "--results",
        type=Path,
        required=True,
        help="directory of <plugin>__<skill>.sarif and .rc files, and <id>.sarif for a shim",
    )
    parser.add_argument(
        "--accepted", type=Path, required=True, help="the reviewed list of accepted findings"
    )
    parser.add_argument(
        "--incomplete-out",
        type=Path,
        help="write the manifest line of each scan that ran out of time here and exit 3 "
        "rather than failing it; leave out on the final pass, which fails such a scan",
    )
    args = parser.parse_args(argv)
    return gate(args.manifest, args.results, args.accepted, args.incomplete_out)


if __name__ == "__main__":
    sys.exit(main())
