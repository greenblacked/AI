# Exporting the graph and testing the checker

Read at step 1 to export, and again before trusting the checker on a new project.

## The node and edge list

The checker reads one JSON file. Keep it this plain so any authoring tool can produce it.

- `defaults`: each flag or variable and the value it has before play starts. A flag with no default and no setter is the thing step 4 hunts for.
- `nodes[]`: `id` (stable, unique), `start` (true on every entry point: each conversation opener, each quest giver), `ending` (true where the conversation or quest is meant to stop), `line_key` (the string table key, if the node speaks), `sets` (flag to value, applied on entering the node).
- `edges[]`: `from`, `to`, and `when`, a list of `{flag, op, value}` that must all hold. `op` is one of `==`, `!=`, `>`, `>=`, `<`, `<=`. Omit `when` for an unconditional edge.

Export from the authoring tool's own save file with a short script, not by hand: a hand-kept list drifts from the real graph, and then the check passes on a graph nobody ships. Run the export in the build, so the file the checker sees is the file the game loads. If the tool stores conditions as script text, either restrict designers to the structured form or flag every node whose condition the exporter cannot parse as `bad-condition` rather than skipping it; a skipped condition is an unchecked one.

Hub nodes that return to a menu are cycles with an exit through the menu's leave option. If the checker reports one, the leave option is missing or its condition cannot be met.

## Line length

`--max-chars` is a character count, which is a proxy. The real limit is pixels at the font and size shipped, so for the longest locale measure the rendered width in the engine and set the count from that, or export pixel widths and compare them instead. Check for scripts where a character is wider than a Latin one, for right-to-left text, and for languages whose words are long. Strings and translation are owned by `game-localisation`; this check only reports lines that overflow.

## Fixture

`fixtures/graph.json` and `fixtures/strings.json` contain one deliberate defect of every kind except `no-start`, which cannot coexist with the start node the other defects need; `tests/test_check_graph.py` covers it. Run:

```bash
python3 -I "${CLAUDE_SKILL_DIR}/scripts/check_graph.py" "${CLAUDE_SKILL_DIR}/fixtures/graph.json" --strings "${CLAUDE_SKILL_DIR}/fixtures/strings.json" --max-chars 40
```

The output must name each node and code in `fixtures/expected.txt`, one `node: code` per line, and exit 1. To compare:

```bash
python3 -I "${CLAUDE_SKILL_DIR}/scripts/check_graph.py" "${CLAUDE_SKILL_DIR}/fixtures/graph.json" --strings "${CLAUDE_SKILL_DIR}/fixtures/strings.json" --max-chars 40 \
  | grep -v finding | cut -d: -f1,2 | sort | diff - "${CLAUDE_SKILL_DIR}/fixtures/expected.txt"
```

Silence from `diff` means the checker still finds everything it should. Rerun it after any change to the checker, and add a defect to the fixture whenever a real one slips past.

## Limits

The flag analysis over-approximates: it asks whether any path could supply a value, not whether the path is playable in order. It cannot see flags set by code outside the graph, so list those in `defaults` or the check will report them. A clean run means these mechanical defects are absent, not that the story reads well.
