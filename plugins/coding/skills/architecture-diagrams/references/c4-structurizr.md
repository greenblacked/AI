# C4 diagrams and Structurizr

Read this when the request is a C4 model, when several diagrams of one system have to stay consistent with each other, or when you are deciding whether to draw the C4 levels in Mermaid or D2 instead. It states what was checked against a primary source and what was not.

## The levels, one diagram each

C4 describes a system at four zoom levels. Draw each as its own diagram, and give each a title that says which level it is. The level names are the C4 model's own (c4model.com, which could not be fetched while writing this skill, so check it for the current wording); what to draw at each level here is this repository's guidance.

| Level | Subject | Shows |
| --- | --- | --- |
| Context | The system as one box | The people and external systems it talks to |
| Container | The system's deployable or runnable pieces (a web app, an API, a database, a queue) | How those pieces talk to each other and to the outside |
| Component | One container only | The major parts inside it |
| Code | One component | Classes or functions; generate it from the code when someone needs it rather than drawing it by hand, since the code changes faster than a drawing |

The rule that matters is the zoom: a box on one level is the subject of the level below it, and a diagram never mixes levels, so a database sits beside APIs on the container diagram and never beside a class. Draw the component level only for the container someone is about to change.

## Choosing how to draw them

| Situation | Choice |
| --- | --- |
| One or two small views, read on GitHub or GitLab | Mermaid, either a plain flowchart with subgraphs or Mermaid's C4 syntax, described next |
| A larger container or component view | D2 or Graphviz, committed as SVG |
| Several views that must all change when a container is renamed or split | Structurizr DSL: one model, many views |

Mermaid has C4 diagram types (`C4Context`, `C4Container`, `C4Component`, `C4Dynamic`, `C4Deployment`). Its own documentation calls them experimental, says the syntax may change, and says the layout is not automatic: the position of shapes follows the order of the statements, adjustable with `UpdateLayoutConfig`. That makes it workable for a small context diagram and a poor fit for a dense container view; for the latter a flowchart with subgraphs, or D2, gives you a layout engine.

## Structurizr

Structurizr is a models-as-code tool built for the C4 model: you write Structurizr DSL once to describe a model, and define several views over it. Its README describes it as the reference implementation, by the author of the C4 model. The code is Apache-2.0 licensed.

Status, as of the READMEs read for this skill: the standalone Structurizr CLI and Structurizr Lite repositories each carry a notice that they will not receive further updates and point to new consolidated tooling (the `structurizr/structurizr` repository), with commands documented at docs.structurizr.com/commands. Do not write a pipeline against the old CLI's command names from memory.

Not verified, and not stated here: the exact command that exports a view, and which export formats the consolidated tooling currently offers. The documentation site was not reachable when this skill was written. Before writing the export step, read the commands page, run the export on a small model, and check the output renders with the CLI of the format you exported to (Mermaid, D2 or Graphviz). The D2 README also lists a community Structurizr-to-D2 exporter; it is third party, so read what it emits before committing its output.

Whatever the export route, keep the DSL as the source and commit the exported text or image beside it, named for the view. An export is a build artefact, so regenerate it from a script rather than editing it by hand.

## Checking a C4 set

After rendering each diagram, check across them: every external system on the context diagram appears on the container diagram, every container name is spelled the same on every diagram, and no box appears on one level that is not a child of a box on the level above.
