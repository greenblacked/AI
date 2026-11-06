# Screen spec: [screen name]

Owner: [name]    Last updated: [date]    Opens from: [screen or event]

## Purpose

[One sentence: what the player does here, or what the HUD tells them.]

## Information

| Item | Question it answers | Rank (always / danger / on demand) | Threshold or trigger | Not by colour alone: how |
| --- | --- | --- | --- | --- |
| | | | | |

Always-tier count: [n]. Could a player name them all from memory after a minute of play: [yes / no, and what moved down].

## Layout

| Element | Anchor (safe-area edge or corner) | Size unit and value | Minimum text size | Behaviour when it does not fit (reflow / truncate / scroll) |
| --- | --- | --- | --- | --- |
| | | | | |

Safe-area source: [platform requirement consulted, per target, with date]. Player adjustment offered: [yes / no].

## Extremes

| Capture | Display | Text scale | Safe-area adjustment | Clipping | Overlap | Off screen | Fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Smallest display, largest text | | | | | | | |
| Largest display, smallest text | | | | | | | |
| Adjustment at its limit | | | | | | | |

## Focus

Default focus: [node]    Returns to on child close: [node]    Back goes to: [screen]

Nodes:

```text
node: <id> | type: button|toggle|slider|list|tab|text | indicator: <how focus shows>
```

Edges:

```text
<from-id> --up|down|left|right|confirm|back--> <to-id or screen:<name>>
```

Pointer-only behaviours (each needs a node and edges): [none / list]

## Checks

| Check | Result | Failures and owner |
| --- | --- | --- |
| Reachable from default focus | | |
| No focus trap | | |
| Back defined | | |
| No pointer-only control | | |
| Focus visible | | |
