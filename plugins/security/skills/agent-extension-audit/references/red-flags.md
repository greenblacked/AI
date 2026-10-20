# Red flags and what they decide

Searches to run over the quarantine directory, and how heavily to weigh a hit. Read this
in steps 4 and 5, and again in step 6 when deciding. Every search finds candidates, not
verdicts: a hit tells you where to read, and an empty result on a pattern never shows the
code is clean, because the same behaviour can be spelled another way. The reading in
step 3 is the review; these are the places that reading must not skip.

All commands take the quarantine path as an argument. Run them with `rg <pattern> --
<quarantine>/src`, with the `--` before the path, never from inside it.

## Contents

- Hidden or invisible text
- Instructions that are not about the job
- Egress and data movement
- Credentials and ambient authority
- Obfuscation and execution of fetched content
- Floating references
- Broad tool grants
- Deciding

## Hidden or invisible text

A human reviewing rendered Markdown does not see these, and the model does.

```bash
# zero-width, bidirectional control, invisible and Unicode tag-block characters
rg -nP '[\x{00AD}\x{034F}\x{061C}\x{115F}\x{1160}\x{180E}\x{200B}-\x{200F}\x{2028}-\x{202E}\x{2060}-\x{2064}\x{2066}-\x{2069}\x{3164}\x{FE00}-\x{FE0F}\x{FEFF}\x{FFA0}\x{E0000}-\x{E007F}]' -- <quarantine>/src
# HTML comments in Markdown, which many renderers hide
rg -n '<!--' --glob '*.md' -- <quarantine>/src
# very long unbroken strings that may be encoded data
rg -n '[A-Za-z0-9+/_-]{80,}={0,2}' -- <quarantine>/src  # base64 and base64url
```

A hit on a legitimate file is possible (a byte order mark, an emoji sequence that uses a
zero-width joiner, an HTML comment holding a lint directive). Open each one and decide.
Invisible characters in a description, a tool description or a command body have no
benign reason to be there.

## Instructions that are not about the job

Read for text addressed to the model that does one of the following, in any file the
model can see, including tool and parameter descriptions:

- tells the model to read a file, variable or credential the stated purpose does not
  need, or to pass its content as an argument to a tool;
- tells it to call a different tool or server, or to prefer this one over others;
- tells it not to mention, show or summarise something to the user;
- claims authority ("system", "administrator", "the user has already agreed");
- changes its behaviour for later tasks, not only this one.

An extension has no business with the first three. This is what is commonly called tool
poisoning when it sits in a tool description: the text is model input that nobody
normally reads, and the user sees only the tool's name. Quote the line, with file and
line number, and do not paraphrase it into something that could be run.

## Egress and data movement

```bash
rg -n -i '(curl|wget|fetch\(|requests\.|httpx|urllib|axios|http\.request|net\.connect|socket|WebSocket|nc )' -- <quarantine>/src
rg -n -o 'https?://[A-Za-z0-9._~:/?#@!$&()*+,;=%-]+' -- <quarantine>/src
rg -n -i '(webhook|telemetry|analytics|beacon)' -- <quarantine>/src
```

List every host. For each, ask what the stated purpose needs it for, and whether
anything from the user's machine or the conversation can be placed in the request: a path,
query string, header, body, or an image URL in output that a client will fetch when it
renders. A host the purpose does not explain is a finding. Telemetry that is documented,
off by default and free of file content or credentials is a restriction at most; telemetry
that is not mentioned is a finding on honesty alone.

## Credentials and ambient authority

```bash
rg -n -i '(process\.env|os\.environ|getenv|\.env\b|\.ssh|\.aws|\.config/gcloud|\.npmrc|\.netrc|\.git-credentials|keychain|credentials|id_rsa|token|api[_-]?key)' -- <quarantine>/src
rg -n '(\.claude|\.codex|settings\.json|CLAUDE\.md|AGENTS\.md)' -- <quarantine>/src
```

Reading an environment variable the extension is documented to need is expected. Reading
all of them, enumerating the home directory, or touching another tool's configuration
(including the agent's own settings, instructions or hooks, which would let the extension
change its own permissions or persist) is not. An extension that edits the agent's
configuration is a rejection unless that is the stated purpose and the change is shown to
the user.

## Obfuscation and execution of fetched content

```bash
rg -n -i '(eval|exec\(|new Function|child_process|subprocess|os\.system|Runtime\.exec|base64 +(-d|--decode)|atob\(|b64decode|fromCharCode|\| *(sh|bash|zsh)\b)' -- <quarantine>/src
```

`eval`, `exec` and a shell invoked on a string built at runtime are the pattern to chase,
because the code that runs is not in the file. Decoding an encoded string and executing
the result, assembling a command from fragments, minified source with no unminified
counterpart, and compiled binaries with no build instructions are each a finding under
the second hard gate. A package that downloads and runs something at install or launch
is a finding even when what it downloads is benign today.

## Floating references

Anything fetched when the extension launches, not when it is installed, can change after
approval:

- a launch command using `npx`, `uvx`, `pipx run` or `docker run` with no exact version,
  digest or lockfile;
- dependencies declared as ranges or `latest`, with no lockfile committed;
- a git dependency on a branch;
- a marketplace entry that tracks a branch, not a commit SHA;
- a skill that tells the agent to fetch instructions from a URL.

A floating reference is not automatically a rejection. It means the review covers the
launcher and not the thing launched, so either pin it (see
[pinning and drift](pinning-and-drift.md)) or record that the reviewed scope ends there.

## Broad tool grants

A declared grant of an unscoped shell (`Bash`), unscoped writes, or every tool is a
finding for any extension whose purpose is narrower. Compare the grant with the
commands the body actually uses. `Bash(git:*)` for a skill that only runs `git` is a
match; `Bash` for the same skill is a mismatch even if the body never abuses it,
because the grant outlives the body's good behaviour once the file changes. Remember the
documented limit: `allowed-tools` pre-approves the listed tools but does not remove the
others, so the effective permission set is the grant plus whatever the session already
allows.

## Deciding

| Finding | Forces |
| --- | --- |
| Concealment instruction, hidden text in model-visible prose, or credential read with no purpose | Reject |
| Executable content that cannot be read (obfuscated, compiled with no source, fetched and run at launch) | Reject, or install only in disposable isolation with no credentials and no network |
| Network destination the purpose does not explain | Reject, or restrict network and re-review |
| Edits the agent's own configuration, hooks or permissions without that being its purpose | Reject |
| Broad tool grant, narrow purpose | Install with restrictions: narrow the grant, then re-read |
| Floating launch command or dependency | Install with restrictions: pin it, or vendor the pinned code |
| Remote MCP server whose descriptions cannot be read in advance | At best install with restrictions: least-privilege credential, read-only scopes, recorded tool snapshot |
| Hook with a purpose-matched effect, everything read, pinned | Install |

A rejection on one finding does not need the rest of the review finished. Stop, record
the finding and the evidence, and report it.
