# Using the skills

This library is a set of procedures written as Markdown. How you load them depends on
what you are using, and only a tool that loads skills natively gives you the thing that
makes a skill worth having: automatic triggering, where the assistant recognises the
situation and reaches for the procedure without being told. Claude Code is the first
option below; the [table in the README](../README.md#chatgpt-grok-codex-and-everything-else) says which other agent tools do the same,
and where each one looks.

- [First run with Codex](#first-run-with-codex) — preview, install and try a real task
- [Claude Code](#claude-code) — install the plugins; skills fire on their own
- [ChatGPT](#chatgpt) — upload the bundles to a Project or a Custom GPT
- [Grok](#grok) — paste the skill, or attach a bundle
- [Codex, Gemini CLI and other terminal agents](#terminal-agents-that-read-agentsmd) — several now load skills natively; see the [README table](../README.md#chatgpt-grok-codex-and-everything-else)
- [Anything else, or nobody at all](#no-assistant-at-all)
- Routing Claude Code to a DeepSeek model through OpenRouter instead of Claude:
  [`docs/deepseek.md`](deepseek.md), not covered below — the tool still loads the
  skills, only the model behind it changes.

## First run with Codex

This walkthrough uses the existing symlink installer and an installed Codex CLI. You
need Git, Bash and standard Unix tools. Start with **one plugin**, such as `coding`,
and add others when you need them. Omit `--plugin` to install every skill, or repeat it
(for example, `--plugin coding --plugin operations`) to select several plugins.
It does not install this repository's Claude Code subagents or slash commands.
[Codex documents](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)
`$HOME/.agents/skills` as its user discovery location and supports symlinked folders.

1. Clone the library into a directory you will keep, then preview the links:

   ```bash
   git clone https://github.com/greenblacked/AI.git
   cd AI
   CLAUDE_SKILLS_DIR="$HOME/.agents/skills" ./scripts/install.sh --plugin coding --dry-run
   ```

2. Read the preview, then install into Codex's skills directory:

   ```bash
   CLAUDE_SKILLS_DIR="$HOME/.agents/skills" ./scripts/install.sh --plugin coding
   readlink "$HOME/.agents/skills/codebase-orientation"
   ```

   The last command should print the `plugins/coding/skills/codebase-orientation`
   directory in your checkout. Keep the checkout there: these are links, not copies.
   An existing file or a link to another checkout is skipped; the installer exits 3.
   Inspect the conflict rather than adding `--force` blindly. A real directory is never
   replaced, even with `--force`.

3. Start a new Codex session in a repository you want to understand. Ask:

   > Use the codebase-orientation skill to map this repository. Start with its purpose,
   > entry points and one real execution path. Report the evidence and proposed first
   > change before editing files or running commands that change external state.

   Check that the response follows the [procedure](../plugins/coding/skills/codebase-orientation/SKILL.md)
   and names files and evidence from your repository. A successful symlink check proves
   installation, not model routing or completion of the task. If the skill is not
   available, check the destination against the [tool table](../README.md#chatgpt-grok-codex-and-everything-else)
   and read the skill directly while investigating.

To update this local installation, pull the checkout, rerun the same installation
command to link any newly added skills, and start a new session. Existing links still
point to the same files. Selecting a narrower set later does not remove earlier links.
To remove a skill, inspect its target and unlink it only if it points to this checkout:

```bash
readlink "$HOME/.agents/skills/codebase-orientation"
unlink "$HOME/.agents/skills/codebase-orientation"
```

Repeat that check for each installed skill you want to remove, leaving unrelated skills
alone. Remove stale links to skills deleted upstream the same way. For other tools and
portable chat files, continue with the routes below.

## Claude Code

### Install

```shell
/plugin marketplace add greenblacked/AI
/plugin install coding@greenblacked-ai
/plugin install gamedev@greenblacked-ai
/reload-plugins
```

The first line registers the marketplace; it downloads nothing on its own. Each
`/plugin install` adds one plugin. `/reload-plugins` makes them live in the current
session — without it you will wonder why nothing fires.

Installing `gamedev`: [`docs/gamedev.md`](gamedev.md) picks a production scale and a game
type and routes through the plugin's eleven skills from there, rather than leaving you to
read all eleven cold.

Install the plugins you will actually use. Every description a plugin ships sits in
context for the whole session, and the runtime caps that listing at about 1% of the
context window. Past the cap it drops the descriptions of the skills you invoke least,
which leaves them invocable by name and stops them being chosen on their own — silently.
Only `career` and `personal` fit the default budget by themselves. If you
install any of the other eight, or more than one plugin, raise it in
`~/.claude/settings.json`:

```json
{ "skillListingBudgetFraction": 0.119 }
```

### How a skill fires

You do not invoke a skill. You describe the situation, and the model matches what you
said against every installed description and loads the one that fits. "this file is 2000
lines and I need to add a feature to it" reaches `refactoring` without you naming it.

That is the whole design, and it is also why a description is written the way it is: it
names the circumstances and the casual phrasings someone actually types, because the
description is the only text loaded before the skill runs.

Two things follow. If a skill never seems to fire, the description is the suspect, not the
body. And you can always force it — "use the refactoring skill" works, and is the right
move when you know exactly what you want.

### Subagents

27 ship across eight plugins, and they work differently: the main agent delegates to one
when the work would otherwise flood your context with material you do not need afterwards.
A megabyte of CI logs, a Terraform plan, a billing export, a release range. You get the
conclusion; the raw material never enters your session.

You do not usually invoke them either. Paste a failing run and `ci-log-reader` is chosen.
Ask for one by name when you want to be sure.

### Slash commands

Eight ship, and unlike skills they run only when you type them: each declares
`disable-model-invocation: true`, the reason [writing a slash command](writing-commands.md)
gives. That makes them the right shape for work that takes an argument, or that should
happen when asked rather than when merely relevant.

```shell
/ci-fail 18234567          # classify a failing run
/blast-radius plan.json    # what the apply destroys
/weekly                    # draft this week's status update
```

### Working on this repository

If you cloned this repository to change the skills themselves, `/ship` runs the loop
from survey to merge over a change: `explorer` surveys what already covers it, alongside
`investigator` in parallel when the change rests on an outside claim; `implementer`
writes it and runs the gates; `reviewer` judges the result on a fresh context with no
editing tools; then `/ship` opens the pull request and merges once `reviewer`, `ci` and
`security` pass. See [writing a subagent](writing-agents.md#the-two-loops).

### Updating and removing

```shell
/plugin marketplace update greenblacked-ai
/plugin uninstall coding@greenblacked-ai
```

Updates still follow the latest commit on `main` by default: the marketplace source is a
git ref, so Claude Code derives a version from the commit, and `/plugin marketplace
update` takes you to whatever that ref points at now.

There is no published release tag to recommend yet. Use the default `main` route above;
do not copy an example release name that does not exist. For a reproducible checkout,
choose an existing commit from the [repository history](https://github.com/greenblacked/AI/commits/main/)
and record its full SHA. [`CHANGELOG.md`](../CHANGELOG.md) records the changes, but an
Unreleased section is not a downloadable release.

### When something does not work

- **Nothing fires.** Did you run `/reload-plugins`? Then check the description names your
  situation — `/doctor` reports what the skill listing costs and its biggest contributors.
- **A skill fires that should not.** Say so plainly in the session, and open an issue: a
  description stealing a neighbour's queries is a defect in this repository, and the eval
  sets exist to catch exactly that.
- **Some skills stopped being chosen after you installed more plugins.** That is the
  listing budget. Raise it, or uninstall a plugin you do not use.

## ChatGPT

For the repository contribution loop, the [ChatGPT workflow guide](chatgpt-agents.md)
provides copy-ready coordinator and role prompts. It is separate from the skill export
below and distinguishes sequential passes from actual delegation.

There is no marketplace to read, so the skills are flattened into files that stand alone
— frontmatter turned into a plain "Use this when" line, and every reference file inlined
so no path is left for a reader with no filesystem to follow.

**Download them, no toolchain needed.** Every CI run builds the flattened files and
attaches them as the **portable-skills** artifact. Open the
[latest run](https://github.com/greenblacked/AI/actions/workflows/ci.yml?query=branch%3Amain),
scroll to Artifacts, and download `portable-skills`. This is the route to use if you are
here because you do not have a coding setup — being told to clone a repository and run
`make` would be the distribution problem restated as instructions.

**Or build them.** If you do have a terminal:

```bash
git clone https://github.com/greenblacked/AI.git && cd AI
make portable          # writes dist/portable/
```

**A Project** is the closest fit to how the skills are meant to work. Create one, upload
the `plugins/*.md` bundles you want **and `index.md` alongside them** — a Project answers
from retrieved chunks rather than the whole file, so the index is what guarantees the
model can see every "Use this when" line at once and choose between them. Then put this in
the project instructions:

> You have a library of procedures in the project files. Before answering, check whether
> one applies — each begins with "Use this when". If one does, follow it rather than
> improvising, and say which you used. If none applies, answer normally.

**A Custom GPT** is the same arrangement: bundles in Knowledge, that text in Instructions.

**For one skill**, paste `dist/portable/skills/<name>.md` into the conversation and say
"follow this". The bundles are large — `coding` is several hundred kilobytes — so the
single-skill files are the better unit when you already know which one you want.

`dist/portable/index.md` lists every skill with its description. Give a model the index
when you want it to choose, then hand it the file it asks for.

## Grok

The same flattened files. Grok's surfaces differ in whether they keep files around, so the
single-skill file is usually the right unit: paste `dist/portable/skills/<name>.md` and
say "follow this procedure". Where you have custom instructions and attachments, use the
project text above with a bundle attached.

## Terminal agents that read AGENTS.md

Several terminal agents, Codex and Gemini CLI among them, now load `SKILL.md` skills
natively and fire them on their own. That is the better route where it exists: the
[table in the README](../README.md#chatgpt-grok-codex-and-everything-else) says which tools do and how to install for each.

For one that does not, most terminal agents read `AGENTS.md` from the working directory,
and what lands there has to fit inside what that tool actually reads. Codex's default is
`project_doc_max_bytes`, 32 KiB, and it is configurable — but past whatever it is set to,
Codex truncates `AGENTS.md` silently: the cut shows up as a `tracing::warn!` log line,
never as anything the interactive session is told, so a file over budget reads as
complete right up until the missing part turns out to be the part you needed. Grok Build
documents no cap at all — it loads the file in full. Gemini CLI, GitHub Copilot and
Mistral Vibe have no documented cap in the sources checked, which is a narrower claim than
"no cap": it says nobody has written one down, not that none exists.

That budget is why the router, not a bundle or `index.md`, is what belongs in
`AGENTS.md`. `make portable` writes `dist/portable/router.md` — one line per skill, drawn
from its own description, naming when it applies and the path to open then — plus a
narrower `dist/portable/router-<plugin>.md` per plugin. Paste the one you want into
`AGENTS.md`, and copy `dist/portable/skills/` to a `skills/` directory next to that
`AGENTS.md`: the router's own paths are `skills/<name>.md`, relative to wherever
`AGENTS.md` itself sits, not to `dist/portable/`.

```bash
cat dist/portable/router-coding.md >> path/to/your/repo/AGENTS.md
mkdir -p path/to/your/repo/skills && cp -r dist/portable/skills/. path/to/your/repo/skills/
```

The agent reads each line on every turn and opens the file it names only once the
situation matches. A single large skill file is fine to open that way —
`website-builder.md` alone is about 70 KB, already over Codex's default on its own, which
is exactly why it is something opened on demand rather than pasted whole. Never append a
plugin bundle (well over a hundred kilobytes each) or `index.md` (about 80 KB) to `AGENTS.md`
directly: both are far past 32 KiB by themselves, and the router exists precisely so
neither one has to be.

The trigger eval harness in this repository already speaks to several of these. It scores
whether a description actually fires, against whichever CLI you have signed in:

```bash
python scripts/run_trigger_eval.py --skill plugins/coding/skills/refactoring --backend codex
```

## No assistant at all

They are procedures. `plugins/*/skills/*/SKILL.md` reads fine on its own, and several of
them — the review checklists, the prep sheets, the incident timelines — were written by
someone who wanted the checklist more than the automation.

## What does not travel

Be clear about what you lose outside Claude Code, because it is the valuable part:

- **Automatic triggering**, except in the agent tools that load skills natively — the
  [README table](../README.md#chatgpt-grok-codex-and-everything-else) lists them. Everywhere else you either tell the assistant to check the
  library, or name the skill yourself. The instruction text above is the closest
  approximation and it is not the same thing.
- **Tool restriction.** `allowed-tools` and a subagent's denied `Write` are enforced by
  the runtime. In a chat window they are a description of intent.
- **Subagents.** Context isolation needs a runtime that can spawn one. A flattened
  subagent is just a prompt you can paste.
- **The listing budget** specifically — the mechanism where Claude Code drops the
  least-used descriptions past about 1% of the context window — is Claude Code's own, and
  uploading one bundle to a Project genuinely has no equivalent of it. That is not the
  same as saying nowhere else has a cap of any kind: Codex still truncates `AGENTS.md`
  past `project_doc_max_bytes` (32 KiB by default), silently, which is the reason the
  [terminal-agent section above](#terminal-agents-that-read-agentsmd) hands you a router
  rather than a bundle.

The content itself travels intact. Of the skills here, two name Claude anywhere in
their text: `new-skill`, which is about authoring a skill in this format and could not
avoid it, and `website-builder`, which names a real constraint of Claude.ai artifacts.
The rest are procedures about code, systems, teams and life, and nothing in them assumes
which assistant is reading. CI builds the export on every run, so that stays true.

## Running the loop without a subagent mechanism

The [ChatGPT workflow guide](chatgpt-agents.md) provides copy-ready coordinator and
role prompts. Its repository gate requires an independent reviewer to execute
`make validate`, `make catalogue` and `make test` on the reviewed snapshot. On a
contributor change the reviewer runs them only when every changed path is inert content
(Markdown under `plugins/` or `docs/`, a trigger eval set, or the root `README.md` or
`CHANGELOG.md`, as regular files whose whole NUL-delimited names match
`^\.?[A-Za-z0-9_][A-Za-z0-9._-]*(/\.?[A-Za-z0-9_][A-Za-z0-9._-]*)*$`, the change fails that check if `git diff -z --name-only '<base>'...refs/review/<n> | grep -zvxE '<pattern>'` selects any record (exit 0 means an unsafe name), or if Python `re.fullmatch` fails on any decoded record; a
changed name outside that, such as `docs/$(cmd).md`, makes the change non-inert and is a
blocking finding asking for a rename; dot-prefixed paths such as `.github/` and `.claude/` are canonical but non-inert, since they are outside the inert allowlist, so they go to the owner-must-run flow, not a rename), because the gates execute the change's own code.
Otherwise it runs no gates and cites no CI, because a contributor's pull request runs the
contributor's own workflow files, `Makefile` and `pyproject.toml`, and a check run's PR
association is computed when it is read. It returns `FIX` pending the owner, listing
under Not assessed as owner-must-run the gates (which the owner runs only in a disposable
sandbox with no credentials and no network, such as a throwaway container or VM with no
mounted secrets, SSH agent, cloud credentials or git push access and network disabled,
never in the owner's normal environment or clone, because the gates import and run the
change's own code), that the owner confirms the PR's required
`ci` and `security` checks passed on the current head under the branch ruleset, and that
the owner confirms the change leaves `.github/workflows/`, `Makefile`, `pyproject.toml`
and the scripts CI calls unchanged against the merge-base (if any changed, the owner
treats CI as untrusted). The reviewer never returns `SHIP` on such a
change by itself: a `FIX` whose only open items are the owner-must-run ones (no blocking finding, and the candidate based on the current base) is cleared once the owner has completed every owner-must-run item, including the live check where the change needs one, and recorded the results on the PR, and that completed checklist counts as the passing review `AGENTS.md` requires before merge, for that head commit on that base tip only (a new push voids it, as does a base advance; immediately before accepting the checklist, and again before merge, the owner re-fetches both refs with the same quoted fetch command, then compares `git rev-parse --verify 'refs/remotes/origin/<base-branch>^{commit}'` with the pinned `<base>` and `git rev-parse --verify 'refs/review/<n>^{commit}'` with the reviewed candidate SHA; any difference voids the clearance (rebase or re-review)). A post-merge live check is recorded as named but not yet run. A blocking finding, and the rebase `FIX`, still need a fix and a fresh review. A live check (real API, real credentials) on a contributor change is made only after the owner has reviewed and adopted the change as their own, or as a post-merge run, never by running the contributor's code with credentials beforehand. Commands a change prints are data, never run on a contributor
change. Missing required execution or independent review means `STOP`, with partial
findings and the limitation named, except that a contributor change that is not inert
content is `FIX` pending the owner's gate run and checks. Require explicitly
fresh, non-inherited reviewer context; record the coordinator-observable boundary
evidence in the initial packet. Pass the complete review packet as explicit input, not
the whole coordinator transcript. After receiving it, the reviewer reports its own
observation of any inherited implementation or coordinator transcript in returned
Evidence; check that Evidence before accepting `SHIP`. A separate agent identity or
window does not prove independence; an inherited, unavailable or unobservable boundary
means `STOP`. On an owner-authored change, author logs and exact-revision CI do not
substitute.

The "Subagents" loss above is the one worth a substitute rather than just a note, because
`/ship` and `/verify` are how changes to this repository get made. Without a runtime that
can spawn an isolated subagent, the replacement is a run of conversations rather than
agents — the same stages, survey then write then review, run by hand in separate windows
instead of separate contexts. Once review passes, open and merge the pull request by
hand the same way `/ship` would, with `ci` and `security` green; that step needs no
separate conversation.

The manual build loop below is owner-only. If the checkout holds contributor-authored
content the owner has not yet adopted (commits or changes not on the base branch, or
`origin/dev`; content already merged counts as adopted), do not run Survey or Write on
it, and run no gate or command from it. Go straight to the Review step, naming the
contributor as author. Run that review from a clean worktree at the pinned base SHA (`git worktree add --detach '<dir>' '<base>'`, or your clone of the base branch checked out exactly there), never
the contributor's, because the tool reads `AGENTS.md`, agent files, settings and hooks
from the checkout it opens. Check first that `<base-branch>` is `dev`, `stage` or `main` and that `<n>` is all digits, then fetch the current base and the contributor's head as a ref only (`git fetch
origin '+refs/heads/<base-branch>:refs/remotes/origin/<base-branch>' '+pull/<n>/head:refs/review/<n>'`) and give the reviewer `<base-branch>`, the pinned `<base>` and that candidate
ref to read with `git diff -z '<base>'...refs/review/<n>` (`<base-branch>` must be `dev`, `stage` or `main`, else `STOP` and retarget the PR; `<base>` is the SHA from `base_sha=$(git rev-parse --verify 'refs/remotes/origin/<base-branch>^{commit}')` right after the fetch), not a checked-out tree. If the
session was opened inside a contributor checkout, or `git rev-parse --verify 'HEAD^{commit}'` is not `<base>`, stop and restart from a clean worktree at the pinned SHA.

**Survey**, in a new conversation, report-only. Describe the change and ask what already
covers it, where the affected files are, and which existing description its trigger
surface would overlap. Take the answer, then do not reuse the survey conversation for
writing. Closing a conversation does not enforce isolation; reusing the survey for
writing changes its role and carries the survey history forward.

**Decide the shape yourself.** Which plugin owns the change and what it must not collide
with is not something `/ship` delegates either — that decision needs judgement built up
over the session, and it travels badly through a cold prompt whether the prompt goes to a
subagent or to a fresh conversation. This step does not change when the mechanism goes
away.

**Write**, in your working session, and run the gates yourself — `make validate`,
`make catalogue`, `make test` — rather than accepting a report that they passed. There is
no separate context to trust here; you are both the one writing the change and the one
who has to believe the result.

**Review**, in a new conversation, naming the author ("repository owner" for your own
work, otherwise the contributor; a change with any contributor-authored content keeps
the contributor as author through every fix round). For owner work, hand it `git diff`
as text, together with every file `git ls-files --others --exclude-standard` names, in
full. The diff alone omits untracked files, which on a change that adds one is the whole
change. Pasting rather than pointing removes the material only when the reviewing
conversation cannot reach the checkout; in a terminal agent sitting in the repository it
has the tree whatever you paste. For a contributor change, hand it a clean worktree at the pinned base SHA
plus `git diff '<base>'...refs/review/<n>`; the candidate is checked out only in
the throwaway gate worktree below. Keep the reviewer report-only, with execution tools
for its own gates, which on a contributor change it uses only under the inert-content
rule above, in this order: it first requires the candidate to be based on the current base, then decides inert-only from `git diff -z --raw
'<base>'...refs/review/<n>`, then itself creates a detached worktree in a fresh directory
outside the project, as the current base plus the candidate merged, runs the gates there and removes it, all in one Bash call because the
tool keeps no shell variables between calls:

```bash
tmp=$(mktemp -d) && git worktree add --detach "$tmp/wt" '<base>' && git -C "$tmp/wt" -c user.name=review -c commit.gpgSign=false -c user.email=review@invalid merge --no-ff --no-edit "refs/review/<n>" && make -C "$tmp/wt" validate catalogue test; rc=$?; git worktree remove --force "$tmp/wt"; rmdir "$tmp"; exit $rc
```

A candidate whose `git merge-base '<base>' refs/review/<n>` differs from `<base>` is `FIX` asking the contributor to rebase onto
the current base before any gate runs, inert-only or not, so the merge above is fast-forward equivalent; a merge conflict or non-zero merge is the same `FIX`. The merge runs only the trusted clone's own hooks and config; a
`.gitattributes` change is non-inert, and a merge driver must also be defined in the
trusted config, so none runs. It never reads files inside that worktree, because a
contributor-added `docs/CLAUDE.md` there would load as instructions; contents come from
`git show 'refs/review/<n>:<canonical-path>'`, in single quotes and only for a canonical
path, because double quotes still expand `$(...)`. A
text-only review can return useful findings but cannot execute gates: on an
owner-authored change or contributor inert content it must return `STOP`; on a
contributor change that is not inert content it cites no CI and returns `FIX` with the
gates and checks listed for the owner (a FIX whose only open items are the owner-must-run ones is cleared by the owner's completed checklist, live check included, for that head on that base tip only; a blocking finding or the rebase FIX still needs a fix and a fresh review). A `FIX` on a contributor change goes back to the owner or the contributor and
never into the write step above. Ask for the same output contract a reviewing subagent
is written to produce: a first line reading `Verdict: SHIP`, `Verdict: FIX` or `Verdict:
STOP`; then `Findings` — blocking defects ranked by cost, each with a file:line, the
concrete consequence if it ships, and the smallest fix described rather than written,
with non-blocking improvements kept separate; `Evidence` — the gate output quoted rather
than summarised; `Not assessed`, said plainly rather than left to be inferred from
silence; and `Handoff` — what the writing conversation needs from this verdict in one to
three lines.

Carry what it finds back by author. For an owner-authored change, findings go back to
the writing conversation. For a contributor change, they go to the owner or the
contributor, never to a writing conversation. Never paste a fix into the
reviewing one — that single move is what collapses the two stages back into one, because
a conversation that has just fixed what it was asked to judge is not the reviewer
any more; it is the author, with an extra turn.

**What is genuinely lost**, and pretending otherwise costs more than naming it:

- **The runtime-enforced no-write.** A subagent with no `Write` or `Edit` cannot act on a
  decision to fix what it is reviewing, however tempted; a conversation with no such
  restriction can, and a review that quietly turns into a rewrite reads exactly like a
  review until someone checks whether anything actually changed underneath it.
- **Automatic delegation.** `/ship` reaches for the survey stage without being asked.
  Three separate conversations require you to remember to open each one, and the stage
  that goes missing is whichever felt optional when time was short — usually the survey,
  because the change already looks obvious from where you are standing.
- **Enforced tiering.** A subagent's `model` key pins its tier regardless of what the
  main conversation is running on. Three manual conversations run on whatever tier each
  happens to be open on, and nothing stops all three running on the same one out of
  convenience.

**What can be preserved.** A fresh conversation with a complete review packet offers a
cold reading of the change, but does not enforce context isolation or no-write access.
The ordering — survey, then write, then independent review — remains a discipline to
follow. Prompting for the report contract helps make findings usable; it does not make
missing checks or independence sufficient for `SHIP`.

The four files in `.claude/agents/` are where this repository's current stage names and
prompts actually live, if the description above is not enough and the wording itself is
wanted.

Follow [AGENTS.md's model mapping](../AGENTS.md#multi-agent-workflow) and explicit task
assignments. Record requested and observed settings; if a requested model or effort is
unavailable, report the limitation rather than automatically substituting another one.
A pasted role prompt cannot enforce model selection or runtime permissions.
