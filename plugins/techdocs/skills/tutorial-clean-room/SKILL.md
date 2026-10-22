---
name: tutorial-clean-room
description: "Prove a tutorial, quickstart or getting-started guide works for a stranger before it ships: run it in a brand-new container or VM with no cached credentials, dotfiles or warm caches, stopwatch running, executing only what the page literally says; log every stumble as a defect with the minutes it cost; state a time-to-first-result target on the page; then watch one outsider follow it with no questions allowed, and ship only after a zero-stumble run. Use whenever someone says \"write our getting-started guide\", \"verify the quickstart still works\", \"new users keep getting stuck on install\" or \"how long does it really take to get going with our SDK\". Not for internal READMEs and how-tos (technical-docs), a publishable blog tutorial (write-technical-article), or keeping each snippet compiling in CI (code-sample-testing)."
allowed-tools: Read, Grep, Glob
---

# Tutorial Clean Room

A tutorial is done when a run in a fresh environment, following only the rendered page, reaches the promised first result with zero stumbles inside the time the page states, and one person outside the team has done the same without asking anything. The page carries the date, product version and platform of that run.

The usual failure is that the author tests on their own machine. Their shell exports the API key, `~/.npmrc` points at the internal mirror, the CLI is already on `PATH` from last month, and they skip step 3 because "that is already done". Every one of those hides a step the stranger does not have. The tutorial then works for everyone who wrote it and for nobody it was written for, and the first sign is a support queue or a silent drop-off, never a failing check.

## Scope

Use for a quickstart, getting-started guide, install guide, "your first X" walkthrough or any page whose job is to take a newcomer from nothing to a first working result. Writing or pruning internal documentation in general belongs to `technical-docs`; a narrative tutorial written for a blog belongs to `write-technical-article`; making every code sample in the docs compile and run in CI belongs to `code-sample-testing`, which this skill relies on rather than replaces. Stale screenshots inside the tutorial go to `screenshot-rot`.

## Workflow

### 1. Fix the reader, the first result and the target time

Write three things above the draft. The reader and what they already have ("a developer with Node 20 and a terminal, no account with us"). The first result, as something observable: a response body, a printed line, a URL that loads. And the time-to-first-result target, measured from opening the page to seeing that result, including sign-up, email confirmation, downloads and waiting for provisioning.

The target goes on the page ("about 10 minutes") because it is a promise the reader plans around, and because a number on the page is one the team will notice breaking. Choose it from the first clean run, not from hope.

### 2. Build the clean room

The environment must have exactly what the page's prerequisites list and nothing else. `references/clean-rooms.md` has the recipe per platform and the contamination checklist; the rules that matter most:

- A new container or VM from a minimal base image, started for this run and thrown away after. Record the image digest so a later run can tell a page regression from an image change:

  ```bash
  docker pull ubuntu:24.04
  docker image inspect --format '{{index .RepoDigests 0}}' ubuntu:24.04
  docker run --rm -it --name tutorial-run ubuntu:24.04 bash
  ```

  The pull comes first because `RepoDigests` is empty until the image has been pulled from a registry, and the interactive `run` blocks until the container exits. The page under test is text the team did not necessarily write and the container runs what it says, so the skill pre-approves no `docker` command: each one runs with the user's approval, as does every file write, and none mounts a host path, passes `--privileged` or joins the host network.

  That form is for a person at a terminal. When driving the container from a script or a tool rather than a terminal, drop `-t` (`docker run --rm -i ...`), or start it detached with a long-running command (`docker run -d --rm --name tutorial-run ubuntu:24.04 sleep infinity`) and run each step through `docker exec tutorial-run ...`, because `-t` fails without a TTY.

- No mounted home directory, no forwarded SSH agent, no `--env-file`, no credential helper. Docker does not pass the host's environment into a container unless told to, which is exactly the property wanted.
- A new account created by following the page, never a staff account. Staff accounts carry feature flags, raised quotas and admin roles that make broken steps pass.
- The public network path: off the corporate VPN, no internal package mirror, no allowlisted office IP. An internal mirror that has the package hides a public registry that does not.
- Hosted CI runners are not clean rooms. Their images ship many tools preinstalled, so a missing "install X" step passes there and fails for the reader.

### 3. Run it literally, against the clock

Start the stopwatch, open the rendered page (not the Markdown source, because rendering is where smart quotes, wrapped lines and copied `$` prompts appear), and execute only what it says, in order, by copying from the page. Note the wall-clock time at the end of each step. Record the terminal session so a stumble can be shown rather than described.

Knowing the product is the hazard here. When a step needs something the page did not say, that is a stumble, even if the fix is obvious to you. Log it, apply the smallest workaround a stranger could plausibly find, and keep the clock running.

### 4. Log every stumble as a defect

A stumble is any point where the page alone did not get you to the next step: a missing prerequisite, a command that fails or prints something other than what the page shows, a value the reader has to invent, an implicit wait, a platform difference, an instruction readable two ways. Each gets a row with the step, what happened, the minutes it cost, its class and the fix. `references/run-log.md` has the log template and the stumble classes.

Size does not decide whether it counts. A thirty-second confusion is still a defect, because ten of them are the five minutes that make a stranger close the tab, and because small stumbles are the ones the author stops seeing first.

### 5. Fix the product before the page where that is cheaper

Some stumbles are product defects wearing documentation clothes: an error message that does not say what is missing, a default that requires a manual edit, a confirmation email that takes ten minutes. A sentence explaining the workaround leaves the cost with every reader; fixing the default removes it. Raise those with the owning team and record which stumbles are waiting on a product change.

### 6. Re-run from a new clean room

After fixing, start again from step 2 with a new container and a new account. Resuming the old environment carries state from the broken run, which is precisely the contamination the clean room exists to prevent. Repeat until one run has zero stumbles and meets the target time.

### 7. Watch one outsider, without helping

Give the page to one person who matches the reader and has not seen the product: another team, a recent hire, a contractor. Use their own fresh environment from step 2. They think aloud; you watch and take notes; neither of you may ask or answer questions. Agree before starting how long a stall lasts before you end the session, since that is the point where a real reader gives up.

The questions they would have asked are the defects. An author cannot find these by re-reading, because the author's knowledge fills each gap before it is noticed. Fix what the session found and repeat step 6.

### 8. Ship with the evidence on the page

Ship only after a zero-stumble clean run that meets the target. Stamp the page with the date of that run, the product version and the platforms it was run on, and keep the run log beside the page source so the next editor sees what was tested.

### 9. Keep it true

A tutorial breaks without anyone editing it: a dependency releases, a sign-up flow changes, a base image moves. Script the command steps into a scheduled job that replays the page top to bottom in a fresh container against the released product, and run it on every release as well. The scripted replay catches broken commands; it cannot catch a confusing sentence or a changed web form, so repeat the human run whenever the install path, the sign-up flow or a major version changes. Per-snippet compilation belongs to `code-sample-testing`; this replay is about the page as a sequence.

## What to hand back

- The run log: environment digest, account type, network path, per-step times, every stumble with class, minutes lost and fix.
- The time-to-first-result of each run, showing the trend to the zero-stumble run.
- Notes from the outsider session and the changes they produced.
- The stumbles routed to product teams instead of fixed on the page, with owners.
- The page diff, including the target time and the tested-on stamp.

## Anti-patterns

**Testing on the author's laptop.** Every cached credential and global install is a step the reader lacks. The run passes because of the environment, not the page.

**Fixing silently and carrying on.** The author hits a stumble, knows the fix, applies it and forgets it. That is the one stumble the reader will hit too. Log first, then fix.

**A staff account.** Feature flags and quotas differ from a new account's. Create the account the reader creates.

**Helping the outsider.** One hint invalidates the session from that point, because the reader at home has nobody to give it.

**A time target that excludes waiting.** Readers experience the email confirmation and the provisioning delay. Measure wall-clock time from opening the page.

## Reference files

- `references/clean-rooms.md` — read when building the environment for a run: recipes for containers, VMs, Windows Sandbox, fresh browser profiles and fresh cloud accounts, and the contamination checklist to clear before starting the clock.
- `references/run-log.md` — read when recording a run or the outsider session: the run log template, the stumble classes with examples, and the observer protocol.
