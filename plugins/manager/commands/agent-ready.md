---
description: Clone a repository and run every fenced shell command its AGENTS.md contains — on this machine, with a stripped environment rather than a sandbox — after listing the commands and stopping for confirmation. Use only on a repository you would already trust enough to run its test suite. Also checks instruction-file size against a known agent tool cap and flags dangling paths and exposed secrets.
argument-hint: '[path or URL to the repository, default the current directory]'
allowed-tools: Bash(git clone:*), Bash(git worktree:*), Bash(rg:*), Read, Glob, Grep
---

Audit `$0` (default `.`, the current directory) for whether an agent can actually work in
it, by running its own instructions rather than reading them.

This runs the target's own commands on this machine, with a stripped environment rather
than a sandbox: `env -i` in step 3 clears inherited variables and redirects `HOME`, but the
process still runs as you, and a command that reads `~/.ssh` or `~/.aws` by its absolute
path rather than through an environment variable can still find it. Use this only on a
repository you would already be willing to run its test suite in. `make install` in this
very repository symlinks skills into `~/.claude/skills`, outside any worktree — exactly the
shape of command step 2 excludes by default, and the reason step 2's confirmation exists
rather than a blanket promise that nothing outside the isolation gets touched.

1. **Isolate once.** `scratch=$(mktemp -d)` and, separately, `home=$(mktemp -d)` for step
   3's stripped `HOME` — outside `$scratch` so it never sits inside the tree being audited,
   never gets swept up by a command that walks the whole checkout, and is removed on its
   own in cleanup. Then:
   - a URL: `GIT_LFS_SKIP_SMUDGE=1 git -c core.hooksPath=/dev/null clone --depth 1 -- "$0"
     "$scratch"` — `GIT_LFS_SKIP_SMUDGE=1` skips the LFS smudge filter, because a
     repository-supplied `.lfsconfig` can point Git LFS at a host of its own choosing and
     cloning is the first moment that file gets read; `-c core.hooksPath=/dev/null`
     disables the target's own hooks (confirmed against git 2.43: it suppresses
     `post-checkout` on both `clone` and `worktree add`, below); `--` stops a repository
     path or URL that happens to start with `-` from being read as an option.
   - `.` or no argument: `git -c core.hooksPath=/dev/null worktree add "$scratch" HEAD`.
   - any other local path: `git -C "$0" -c core.hooksPath=/dev/null worktree add "$scratch"
     HEAD` — plain `git worktree add` with no `-C` always operates on the current
     directory's repository, never on `$0`, so this form is required for auditing anything
     but `.`.

   `git worktree add` and `git clone` both run a target's own `post-checkout` hook, with
   the caller's full environment, before step 2's confirmation exists to gate anything —
   `-c core.hooksPath=/dev/null` on the one invocation that creates the copy closes that.
   None of the three forms above is guaranteed to match the allow-list above once the
   safety flags are on it, so treat every one of them as a prompt, not a pre-approval —
   correct, since creating a copy of a repository this command has not yet audited is
   exactly the moment that should ask.

   Every command below runs inside `$scratch`. A local worktree adds an entry under
   `.git/worktrees` in the target's own repository until step 6 removes it — that is
   metadata, not a change to any tracked file, but it is not nothing, so say so rather than
   claiming the checkout is untouched.
2. **List the commands, then stop.** Extract every fenced shell or bash block from
   `AGENTS.md` and any file it imports — a `CLAUDE.md`'s `@AGENTS.md` line, for instance —
   and print each one verbatim and in full: show a multi-line block whole, never a
   paraphrase that could hide what it actually does. Exclude by default anything that
   installs outside the tree, pushes, tags, publishes, releases or deploys — `git push`,
   `npm publish`, `docker push`, `gh release create`, `make install`, a global or `--user`
   package install, anything invoking `sudo` — and print each excluded command with the
   reason. This exclusion reads only the command text on the page: a Makefile target,
   package script or checked-in script is opaque until it actually runs, so a confirmed
   `make check` can still push or install if that is what its recipe does — confirming a
   command is informed consent to run the named thing, not a guarantee of everything it
   does once running. Print the remaining commands as a numbered list and stop here for the
   user to confirm before running any of them; do not proceed on an assumption of consent.
3. **Run each confirmed command with a stripped environment.** `env -i PATH="$PATH"
   HOME="$home" timeout 300 bash -c "$cmd"`, recording its exit code and wall time. This
   runs as plain `Bash`, which is not on the allow-list above, so it prompts for approval
   the same as any other command outside it — that repetition is deliberate, the same gate
   as step 2's confirmation enforced a second time by the tool permission itself. Never
   re-run a failing command with the caller's own environment restored to see whether that
   was the cause — that hands the target repository's own code the caller's tokens
   (`GH_TOKEN`, `AWS_*`, `SSH_AUTH_SOCK`, an npm or PyPI token), which is exactly what
   stripping the environment in the first place exists to prevent. Classify a failure from
   the command's own output instead, never by re-running anything: a `command not found`, a
   missing version-manager shim, a name-resolution or proxy error, or a network-unreachable
   error in the output is evidence, not proof, that the stripped environment removed
   something the command needed — quote the line, name the missing piece, and label the
   result "likely a stripped-environment failure" rather than assert it as confirmed. Label
   everything else "fails". If the caller wants to confirm a stripped-environment case, name
   the one variable that looks responsible in the report and let them re-run that single
   command themselves with only that variable added — this command never restores the
   environment and reruns anything on its own.
4. **Check size against Codex's cap, and report the rest separately.** Codex loads only the
   `AGENTS.md` / `AGENTS.override.md` chain from the project root down to the current
   directory — it does not read `CLAUDE.md`, and it does not follow an `@` import. Sum only
   that chain's byte size and compare it against Codex's project-doc cap, which defaults to
   32 KiB and silently truncates past it rather than rejecting it —
   `codex-rs/config/src/config_toml.rs`'s `DEFAULT_PROJECT_DOC_MAX_BYTES`, in `openai/codex`
   upstream. Name that figure explicitly when the chain's combined size is close to or past
   it, because the failure mode is silent: nothing tells a team that half its instructions
   were dropped. Report the combined size of any `CLAUDE.md` and whatever it imports as a
   separate figure, with no cap attached — Codex does not read it, so a cap asserted against
   it would be exactly the kind of overclaim this file exists to avoid. Do not repeat 32 KiB
   as a default for any other agent tool; report only what has actually been checked against
   a primary source.
5. **Check for dangling pointers.** Grep the prose of `AGENTS.md` and its imports for every
   `references/`, `scripts/` or other path-shaped mention, and confirm each exists in the
   tree — the same class of check this repository's own validator runs on itself, applied
   to the target instead.
6. **Check for exposed secrets, then clean up.** `rg -l --hidden --no-ignore -g '!.git'
   <pattern>` (files-with-matches only, one run per credential-shaped pattern) over the
   worktree, so a secret's actual value never reaches this command's own output. `--hidden`
   and `--no-ignore` matter here specifically because the default is the opposite of what a
   security sweep needs: plain `rg` skips dotfiles and honours the target's own
   `.gitignore`, `.ignore` and `.rgignore`, so a tracked `.env` can be invisible to it and a
   repository can blank its own sweep by ignoring everything; `-g '!.git'` is the one
   exclusion still worth keeping, since it only keeps the walk out of Git's own internal
   objects rather than anything the repository controls.
   Report the file path and which pattern matched — a tracked `.env`, an AWS-key-shaped
   string, a private-key header — and never the value itself, even truncated; the policy
   decision belongs to `ai-enablement`, not here. Then remove the isolation: `git worktree
   remove --force "$scratch"` (adding `-C "$0"` too, if the non-default local-path form was
   used in step 1) for a worktree, or delete the clone directory outright — and remove
   `$home` either way, since it was created outside the tree precisely so nothing else
   would clean it up.
7. **Report.** One row per confirmed command — name, exit code, wall time, and, for a
   failure, "fails" or "likely a stripped-environment failure" with the missing piece named
   and its evidence quoted — the excluded list with reasons, the size figure against the
   cited cap (Codex's chain only) alongside the separate uncapped `CLAUDE.md` figure, every
   dangling path, every exposed-secret candidate (path and matched pattern only), and a
   closing line naming `ai-enablement` for anything that needs a policy decision.

Never report a command as passing on the strength of having read it rather than run it,
and never run a command step 2 did not print and get confirmed for first.

For the full readiness checklist this executes, use the `ai-enablement` skill.
