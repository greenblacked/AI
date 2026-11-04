---
name: game-narrative-graph-check
description: "Verify a branching dialogue or quest graph as data before content lock. Exports the graph to a plain node and edge list, then runs a standard-library checker that reports node id and reason for unreachable nodes, dead ends not marked as endings, flags read before any path sets them, conditions that can never be true, cycles with no exit, lines longer than the text box at the longest locale, and line keys missing from the string table. Use whenever someone asks to check a dialogue tree, quest chain or branching story for soft-locks, orphaned lines or broken flags, or wants a narrative pass before lock or a release candidate. Not for translating or managing strings (game-localisation), writing the story or quest design (game-design-doc), running a human playtest (game-playtest), or level layout (game-level-design)."
allowed-tools: Read, Grep, Glob
---

# Game Narrative Graph Check

The work is done when the checker exits 0 on the graph the build will ship, against the string table the build will ship, and every finding it raised earlier was fixed in the content or waived in writing with the node id beside the reason.

A branching story is a program written by people who test it by playing one route. The routes nobody played hold the defects: a reply that leads nowhere, a quest step gated on a flag that nothing sets, a conversation loop with no leave option, a line that spills out of its box only in German. These are mechanical and a script finds them in seconds; a human finds them by luck, after lock, when the fix means re-recording voice or re-submitting a build.

## Scope

Use for: checking dialogue trees, quest chains and other branching content for structural defects; building the export that makes that possible; running it in the build so a regression fails before a tester sees it.

Do not use for: translating, extracting or managing strings, which is `game-localisation`; this skill only checks that keys exist and fit. The story and quest design itself is `game-design-doc`. Whether the story is good, or players understand it, is `game-playtest`. Walking a built game with a bot is `automated-playthrough`.

## Workflow

### 1. Export the graph

Produce the node and edge list described in `references/export-and-fixture.md`: nodes with `id`, `start`, `ending`, `line_key` and `sets`; edges with `from`, `to` and `when`; and `defaults` for every flag at game start. Export from the authoring tool's save file in the build, not by hand. Mark every entry point `start`, every intended stopping place `ending`, and list flags set by code outside the graph in `defaults`.

### 2. Run the checker

```bash
python3 -I "${CLAUDE_SKILL_DIR}/scripts/check_graph.py" graph.json --strings strings.json --max-chars N
```

It prints `node: code: reason` per finding and exits 1 if there is any. The codes: `unreachable`, `dead-end`, `cycle-no-exit`, `read-before-set`, `never-true`, `bad-condition`, `unknown-node`, `no-start`, `duplicate-node`, `missing-key`, `missing-locale`, `too-long`.

### 3. Structure first

Fix `duplicate-node` (the checker judges the first occurrence of an id), `unknown-node`, `no-start`, `unreachable` and `dead-end` before anything else; they change which later findings are real. A dead end is a soft-lock for the player. An unreachable node is either cut content still costing localisation and voice money, or a missing edge. Decide which, in the content, not in the checker.

### 4. Flags and conditions

`read-before-set` means no path to that node can have set the flag and it has no default; the branch silently takes the wrong side, or the quest step never opens. `never-true` means the condition compares to a value nothing ever sets, or contradicts itself. Both are usually a typo in a flag name or a setter that was cut. Fix the name or the setter; do not add a default to quiet the check unless the flag truly starts with that value.

### 5. Cycles

A cycle with no edge out and no ending traps the player. A hub that returns to a menu is a cycle by design, so confirm its leave option exists and its condition can be met rather than excusing it.

### 6. Strings

Set `--max-chars` from the text box at the longest locale, measured in the engine at the shipped font and size, not guessed from English. `missing-key` and `missing-locale` mean the build would show a raw key or a fallback. Repair translation in `game-localisation`'s process; report here.

### 7. Gate it

Run the checker in the build and fail on a non-zero exit. Waive a finding only in a file reviewed with the content, naming node id and reason. Rerun the fixture in `references/export-and-fixture.md` after any change to the checker.

## Anti-patterns

**Checking the English build only.** Length and missing-key defects live in the other locales.

**Hand-kept exports.** The list drifts from the shipped graph and the check passes on a graph nobody plays.

**Skipping conditions the exporter cannot parse.** A skipped condition is an unchecked one; report it.

**Treating green as a read-through.** The checker proves the mechanics, not that the story works.

## References

- `references/export-and-fixture.md` — read at step 1 for the export format and line-length caveats, and when changing the checker for the fixture that proves it still finds each defect.
- `scripts/check_graph.py` — the checker, run at step 2.
- `fixtures/graph.json`, `fixtures/strings.json` and `fixtures/expected.txt` — the deliberately defective fixture and its expected findings.
