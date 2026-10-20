# Pinning and drift

How to make the approval name the thing that was read, and what to do about the parts
that cannot be pinned. Read this in step 7 when recording the decision, and when
re-reviewing an extension whose version changed.

## Contents

- Why an approval drifts
- What to record
- Carrying the pin into the install
- What cannot be pinned
- Re-review triggers

## Why an approval drifts

A reviewed extension changes underneath the approval in four ways:

- the source moves: a branch gets new commits, a tag is re-pointed, a package version is
  republished or yanked and replaced;
- the installer updates it: Claude Code updates a plugin in the background when the
  marketplace it came from has auto-update on, so the files that were reviewed can change
  on disk ([Plugin security and trust](https://code.claude.com/docs/en/plugins/security));
- it fetches more at launch: a floating `npx` or `uvx` command, a dependency range, a
  script that downloads another script;
- it describes itself differently later: an MCP server returns its tool descriptions at
  connection time, and the specification lets a server announce a changed tool list
  through a `listChanged` capability, so an approved description is not fixed for the
  life of the connection ([tools](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-11-25/server/tools.mdx)).
  A description that changes after approval is commonly called a rug pull.

## What to record

One block per extension, written before install:

```markdown
Extension:      <name>, <type>
Source:         <repository URL or package registry URL>
Publisher:      <owner and how you checked it>
Commit:         <full 40-character SHA>
Tree hash:      <git rev-parse HEAD^{tree}, or HEAD:<subdirectory>>
Archive sha256: <sha256sum of the downloaded file, if an archive>
Fetched:        <date>
Read in full:   <list of executable files>
Read in part / not read: <list, with why>
Decision:       install | install with restrictions | reject
Restrictions:   <each one, and where it is enforced>
Tool snapshot:  <hash of the MCP tool list, if any>
Re-review when: <triggers>
```

The commit SHA and tree hash come from `git -C <quarantine>/src rev-parse HEAD` and
`git -C <quarantine>/src rev-parse HEAD^{tree}`. For a plugin inside a larger repository,
`rev-parse HEAD:<path>` gives the hash of that subdirectory alone, which is what changes
when the plugin changes. For a downloaded archive, `sha256sum` of the file.

## Carrying the pin into the install

Record alone does nothing; install from the pinned reference.

- **A marketplace entry.** For `github`, `url` and `git-subdir` sources, the
  marketplace schema takes an optional `sha`, a full 40-character lowercase commit SHA,
  and checks out that commit when it is set
  ([marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference)).
  Writing your own marketplace entry with the `sha` you reviewed is the strongest pin
  available inside the tool. A source set to a `ref` alone names a branch or tag, which
  can move. An archive source can pin a `sha256` digest, and Claude Code refuses an
  archive whose digest does not match (see the trust page above).
- **Auto-update.** Turn it off for the marketplace the extension comes from when you
  cannot pin by SHA, and make updates a deliberate re-review. The `/plugin` Marketplaces
  tab has the control.
- **An MCP launch command.** Replace a floating command with an exact version
  (`pkg@1.2.3`), a lockfile you reviewed, or a container image referenced by digest, not
  a tag. Prefer vendoring the reviewed source and launching that.
- **A skill or command copied into a repository.** Commit the reviewed files. The git
  history then holds the pin, and a change shows up as a diff in review.
- **A team.** Put the approved list, with the commit SHAs, where the team installs from,
  and have installs come from it. An approval that lives in one person's head is the
  same as none.

## What cannot be pinned

A remote MCP server and any extension that fetches instructions or code from a URL at run
time. For these the approval is of an operator, not of content. Record that, then
reduce the damage instead:

- give it the narrowest credential and read-only scopes, and no access to data from
  other systems in the same session, since a poisoned description in one server can
  influence how the model uses another's tools;
- keep a snapshot of the tool list (names, descriptions, parameter descriptions,
  schemas) as it was when you approved it, hash it, and compare at each re-review. Take
  the snapshot from a session that has no other servers and no sensitive data;
- decide who looks at the diff, and how often. A snapshot nobody compares is a record,
  not a control.

## Re-review triggers

Re-review, from step 1, when any of these happens, and do not let the installer decide
that a change is minor:

- the pinned commit or version changes, including a patch version;
- a new hook, monitor, executable, MCP server or tool appears;
- `allowed-tools` widens, or a new network host appears in the code;
- the publisher or repository ownership changes;
- the tool-list snapshot differs from the recorded one;
- a security advisory names the extension or one of its dependencies (then handle the
  dependency question in `dependency-triage`).

A re-review of an update starts from `git diff <approved-sha>..<new-sha>` over the same
quarantine, but a diff only covers what changed: if the update touches a launcher,
a manifest or a dependency lockfile, read what it now pulls in, not only the changed
lines.
