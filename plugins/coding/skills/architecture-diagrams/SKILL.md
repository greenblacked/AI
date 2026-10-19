---
name: architecture-diagrams
description: "Draw architecture, sequence and flow diagrams as code that renders where it will be read: choose the tool by the target surface (Mermaid where GitHub or GitLab render it natively, D2 or Graphviz committed as SVG for large graphs, Structurizr for a C4 model), give each C4 level its own diagram under a node cap, quote every label over plain identifiers, render with the tool's CLI and fail on a non-zero exit, then look at the render for overlap, and keep source and rendered output side by side. Use this skill whenever someone says \"draw the architecture of this service\", \"add a sequence diagram of the login flow to the README\", \"my mermaid diagram shows a syntax error\", or \"this diagram is an unreadable hairball\". Not for charts drawn from data, the prose around a diagram (technical-docs), trust boundaries and threats (threat-model), or recording a decision (decision-record)."
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(mmdc:*), Bash(d2:*), Bash(dot:*), Bash(git:*)
---

# Architecture Diagrams

A diagram is finished when it renders without error on the surface where it will be read, a reader who has not seen the source can follow it, and the source sits next to the rendered output so the next person can change it.

The text of a diagram is easy to write and easy to get subtly wrong. Each tool has its own failure: Mermaid refuses a label it cannot parse and shows an error box where the picture should be; D2 accepts an unquoted `#` and silently cuts the label short, with exit code 0; Graphviz treats an unknown attribute as a warning and still exits 0. Beyond syntax, a diagram of everything is a diagram of nothing: too many nodes and the layout engine tangles them, and the reader gives up. So the procedure is to pick the tool for the place the diagram will live, draw one question per diagram, write the text defensively, and then prove it by rendering it and looking at the result.

## Scope

Use for: architecture and C4-style views, sequence diagrams, flow and state diagrams, deployment views, written as text that lives in the repository.

Do not use for: charts drawn from data, the document around the diagram (technical-docs), the written orientation of an unfamiliar repository (codebase-orientation), data-flow diagrams drawn to find threats at trust boundaries (threat-model), or the reasoning behind a choice (decision-record, which may embed a diagram this skill produces).

## Workflow

### 1. Name the question and the reader

Write one sentence: "This diagram shows X to Y so that Z." If it needs an "and" joining two questions, it is two diagrams. Pick the kind from the question: who and what talks to our system (C4 context), what is deployed and how the pieces talk (C4 container), what happens in what order between parties (sequence), what branches and when (flow or state).

Draw from the code, configuration and infrastructure definitions, not from memory. A diagram drawn from memory is a confident claim about a system nobody checked. Where a link is inferred rather than read, mark the edge or leave it off; read the repository with codebase-orientation first when it is unfamiliar.

### 2. Pick the tool by where the diagram will be read

The surface decides the tool, because a diagram that does not render there is source code the reader has to decode.

| Where it will be read | Use | Why |
| --- | --- | --- |
| A Markdown file, issue, pull request or wiki on GitHub, or Markdown on GitLab | Mermaid in a fenced `mermaid` block | Both render it natively from the text. GitHub's documentation lists Markdown files, pull requests, issues, discussions and wikis; GitLab's lists Mermaid, PlantUML and Kroki. |
| The same surfaces, but the graph is large or needs careful layout control | D2 or Graphviz, rendered to SVG and committed, linked from the Markdown as an image | Mermaid gives you the least control over layout; both alternatives are command-line renderers with their own layout engines, and D2 lets you choose between them. |
| A surface you have not seen render a fenced block (a wiki, a slide deck, a PDF, a ticket tool) | The same D2 or Graphviz SVG, or a PNG made from the same source | Treat "renders natively" as false until you have seen it render there. |
| A C4 model where several views must stay consistent with each other | Structurizr DSL, with the views exported to an image or to Mermaid or D2 text | One model feeds every view, so a renamed container changes everywhere. See [references/c4-structurizr.md](references/c4-structurizr.md). |

Mermaid renders at the version GitHub or GitLab runs, which may differ from the version your CLI has. On GitHub a fenced block containing only `info` shows the running version; check it when a diagram that rendered locally breaks there.

### 3. Size it: one diagram per level, a node cap per diagram

Split by C4 level instead of squeezing a system onto one canvas: a context diagram (the system and what it talks to), a container diagram (the deployable pieces inside it), a component diagram for one container only when someone needs it. Each level is its own diagram, with its own title, and a box on one level is the subject of the next level down.

Fix a node cap before adding the first node, and write it in a comment at the top of the source. Choose it so the render stays legible at the width of the surface that shows it, a README column and not a wall poster. When you pass the cap, split the diagram, collapse a group of nodes into one named box, or move detail to a lower level. Do not shrink the font. The tools' own limits are ceilings, not targets: Mermaid's schema sets a default maximum text size of 50,000 characters and a default maximum of 500 edges, and a diagram is unreadable long before either.

### 4. Write the text so it cannot be misparsed

- Use plain identifiers (lowercase ASCII letters, digits and underscores, starting with a letter) and put every human-readable string in a quoted label. The identifier is for the tool, the label is for the reader. Never use a tool's keyword as an identifier; Mermaid breaks on a lowercase `end`, and Graphviz rejects `node`, `edge` and `graph`.
- Quote every label, even the ones that look safe. Parentheses, colons, brackets, a hash, a semicolon and an ampersand are the characters that change meaning inside an unquoted label, and a quoted label costs nothing.
- Label every edge with the verb or protocol that matters (`"HTTPS"`, `"publishes OrderPlaced"`), and no edge without a direction a reader can state.
- Set the direction once (left to right for a pipeline, top to bottom for a hierarchy) and keep styling to a small number of classes. Colour carries meaning (a legend entry) or it is removed.
- Add a title and a one-line caption that states what the diagram shows and the date or commit it was checked against.

The per-tool syntax pitfalls are verified in [references/mermaid.md](references/mermaid.md), [references/d2.md](references/d2.md) and [references/graphviz.md](references/graphviz.md). Read the one for the tool you chose before writing, not after the render fails.

### 5. Validate by rendering, and fail on a non-zero exit

Render with the tool's own command line and stop on a non-zero exit. A parse that looks plausible in the editor is not evidence; a render is.

```bash
set -Eeuo pipefail
tool="${1:?usage: render.sh mmdc|d2|dot}"
name=docs/diagrams/orders-containers
case "$tool" in
  mmdc) mmdc -i "$name.mmd" -o "$name.svg" ;;
  d2)   d2 "$name.d2" "$name.svg" ;;
  dot)  dot -Tsvg "$name.dot" -o "$name.svg" ;;
  *)    echo "unknown tool: $tool" >&2; exit 2 ;;
esac
```

The script is one command per tool, not a sequence; keep only the line for the tool you picked, with the paths for your diagram. Two cases where exit code 0 is not enough: Graphviz prints a warning for an unknown attribute or shape and still exits 0, so run it as shown in [references/graphviz.md](references/graphviz.md) and treat any stderr output as failure; D2 truncates an unquoted `#` label silently, which only the next step catches.

### 6. Look at the render

The parser passing says nothing about whether the picture is readable. Render a PNG copy into a temporary directory (every tool above can write one), open it, and check three things: no node overlaps another and no label is clipped; every node and edge label is the full text you wrote; and a reader can trace the main path without lifting a pen off the screen. Fix by splitting or reordering, not by enlarging the canvas. Re-render after each change.

When the diagram is a Mermaid block in Markdown, the surface renders it, not your CLI: after the change is pushed to a branch, view the page there once.

### 7. Keep source and output side by side

Commit the source and its rendered SVG together, in one directory, with the same base name: `docs/diagrams/orders-containers.d2` and `docs/diagrams/orders-containers.svg`. Link the SVG from the Markdown as an image, with alt text that states the diagram's point, and keep the source linked in a sentence beside it. A rendered image without its source cannot be changed; a source without its render shows nothing on a surface that cannot run the tool.

Regenerate every diagram from one script or make target so nobody renders by hand, and pin the tool version it uses, because layout engines change between releases and a different version redraws a diagram you did not touch. A Mermaid block kept inline in a Markdown file needs no separate render; keep it in the file it explains and validate it with the CLI before committing.

State when each diagram was last checked against the code, in the caption. The write-up around it, its owner and its review date belong to technical-docs.

## Anti-patterns

**One diagram of the whole system.** It feels complete and reads as a wall of boxes. Split by level so each diagram answers one question, then link them.

**Labels as identifiers.** Writing `Orders API (v2)` unquoted as a node name works until a parenthesis, colon or the word `end` breaks the parse. Keep a plain identifier and put the text in a quoted label.

**Trusting the editor preview.** A preview that shows a picture proves one version of one renderer accepted the text, not that the CLI or the target surface will. Render with the CLI and look.

**Committing only the render.** The next change needs the source; a screenshot of a diagram is a dead end. Commit both, side by side.

**Fixing overlap with a bigger canvas.** The tangle is a symptom of too many nodes or edges. Split the diagram or collapse a group, and look at the result again.

**An edge nobody checked.** Every arrow is a claim about the system. If it was inferred, say so or leave it off.

**Colour with no key.** A reader cannot tell what red means, and a printout in greyscale loses it. Add a legend entry or remove the colour.
