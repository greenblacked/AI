#!/usr/bin/env python3
"""Fail on a high or critical SkillSpector finding nobody has reviewed yet.

The `skillspector` job in `security.yml` scans one skill per process and leaves, for each
skill named in its manifest, a SARIF report and the scanner's exit code. This reads them
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
reports than the manifest names skills, and an accepted entry without a reason or with a
class outside the reviewed set are all failures: a scan that did not happen must not read
as a scan that found nothing. An accepted entry that no longer matches anything in a
skill that was scanned is reported as a notice, not a failure, so the list can be pruned
without a stale entry blocking an unrelated change.

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
OK_EXIT_CODES = {0, 1}
MATCH_LIMIT = 200


def normalise(text: str) -> str:
    """Collapse every run of whitespace to one space, so reflowing a line keeps its key."""
    return " ".join(text.split())


def stem(skill_dir: str) -> str:
    """`plugins/<plugin>/skills/<skill>` -> `<plugin>__<skill>`, the per-skill file stem."""
    parts = skill_dir.split("/")
    return f"{parts[1]}__{parts[3]}"


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


def read_manifest(path: Path) -> tuple[list[str], list[str]]:
    """The skill directories the job scanned, and any problems with the list itself."""
    problems = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as err:
        return [], [f"cannot read the manifest {path}: {err.strerror}"]
    skills = [line for line in lines if line]
    for skill in skills:
        if not SKILL_DIR_RE.fullmatch(skill):
            problems.append(f"manifest names {skill!r}, which is not a skill directory")
    if len(skills) != len(set(skills)):
        problems.append("manifest names a skill more than once")
    return skills, problems


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


def findings_in(skill: str, sarif_path: Path) -> list[tuple[tuple[str, str, str], int, str]]:
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
            if isinstance(invocation, dict) and invocation.get("executionSuccessful") is False:
                raise ValueError("the scanner reported an unsuccessful execution")
        for result in run.get("results", []):
            if not isinstance(result, dict):
                raise ValueError("a result is not an object")
            severity = severity_of(result)
            if severity not in GATED:
                continue
            rule = result.get("ruleId")
            if not isinstance(rule, str) or not rule:
                raise ValueError("a gating result has no ruleId")
            path, line = location(skill, result)
            props = result.get("properties") or {}
            text = props.get("finding") if isinstance(props, dict) else None
            if not isinstance(text, str) or not text.strip():
                message = result.get("message")
                text = message.get("text", "") if isinstance(message, dict) else ""
            found.append(((rule, path, normalise(str(text))), line, severity))
    return found


def location(skill: str, result: dict) -> tuple[str, int]:
    """The repository-relative path and line of a result; the skill itself if it has none.

    SkillSpector writes each URI relative to the skill it scanned. One that is absolute,
    or that climbs out of the skill, is refused: the key would not mean the file it names.
    """
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


def exit_code(rc_path: Path) -> int | None:
    try:
        return int(rc_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def gate(manifest: Path, results: Path, accepted_path: Path) -> int:
    failures = 0
    skills, problems = read_manifest(manifest)
    accepted, accepted_problems = read_accepted(accepted_path)
    for problem in problems + accepted_problems:
        annotate("error", problem, title="SkillSpector gate")
        failures += 1
    if problems:
        return 1

    reports = sorted(results.glob("*.sarif"))
    if len(reports) != len(skills):
        annotate(
            "error",
            f"found {len(reports)} SARIF report(s) for {len(skills)} skill(s) scanned; "
            f"a skill without a report was not scanned, and a report without a skill "
            f"came from somewhere else",
            title="SkillSpector gate",
        )
        failures += 1

    seen: set[tuple[str, str, str]] = set()
    new = 0
    for skill in skills:
        name = stem(skill)
        rc = exit_code(results / f"{name}.rc")
        if rc not in OK_EXIT_CODES:
            reason = "left no exit code" if rc is None else f"exited {rc}"
            annotate(
                "error",
                f"SkillSpector {reason} scanning {skill}; see {name}.log in the artifact",
                file=f"{skill}/SKILL.md",
                title="SkillSpector scan failed",
            )
            failures += 1
            continue
        try:
            found = findings_in(skill, results / f"{name}.sarif")
        except (OSError, ValueError) as err:
            annotate(
                "error",
                f"no readable SARIF for {skill}: {err}",
                file=f"{skill}/SKILL.md",
                title="SkillSpector scan failed",
            )
            failures += 1
            continue
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

    scanned = tuple(skill + "/" for skill in skills)
    stale = sorted(key for key in accepted if key[1].startswith(scanned) and key not in seen)
    for rule, path, text in stale:
        annotate(
            "notice",
            f"accepted {rule} entry no longer matches anything; prune it: {shorten(text)}",
            file=path,
            title="Stale SkillSpector entry",
        )

    print(
        f"skillspector gate: {len(skills)} skill(s) scanned, {len(seen)} high or critical "
        f"key(s) seen, {new} new, {len(stale)} stale accepted entr"
        f"{'y' if len(stale) == 1 else 'ies'}, {failures} other failure(s)"
    )
    if not skills:
        annotate("notice", "no skill to scan", title="SkillSpector gate")
    return 1 if failures or new else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="newline-separated skill directories that were scanned",
    )
    parser.add_argument(
        "--results",
        type=Path,
        required=True,
        help="directory of <plugin>__<skill>.sarif and .rc files",
    )
    parser.add_argument(
        "--accepted", type=Path, required=True, help="the reviewed list of accepted findings"
    )
    args = parser.parse_args(argv)
    return gate(args.manifest, args.results, args.accepted)


if __name__ == "__main__":
    sys.exit(main())
