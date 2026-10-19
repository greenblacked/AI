# Extension surfaces

Where each kind of extension runs code or injects instructions, and what to open to see
it. Read this in step 2, when building the inventory of automatic entry points. The
Claude Code facts below are from its documentation as fetched in October 2026 and are
version-specific; check the linked page when the version in front of you differs, and
treat another agent's plugin format as having the same two halves (code that runs, prose
that steers) in different file names.

## Contents

- What "automatic" means
- Skill (SKILL.md with scripts)
- Plugin
- Hook
- MCP server
- Slash command
- Install and build scripts

## What "automatic" means

An entry point is automatic when it runs without the user asking for that specific
action: at install, at session start, on every tool call, when a skill loads, or in the
background. These are the rows the inventory exists to find, because they run before the
model or the user has a chance to notice.

Claude Code's permission rules and sandbox cover the tool calls the model makes. They do
not cover the code a plugin runs by itself: command hooks, monitors, MCP servers and
language servers run with the user's full permissions, outside the sandbox (see
[Plugin security and trust](https://code.claude.com/docs/en/plugins/security)).

## Skill (SKILL.md with scripts)

- **Frontmatter.** `allowed-tools` pre-approves the listed tools for the turn the skill
  runs in. The documentation says workspace trust does not gate it, and that a skill can
  grant itself broad access. Read the value, and read whether it is scoped per binary
  (`Bash(git:*)`) or open (`Bash`). A `hooks:` key registers hooks when the skill is
  invoked and keeps them for the rest of the session. A `shell:` key chooses the shell
  used for the next item.
- **Dynamic context lines.** A line of the form exclamation mark plus a backticked command, or a fenced
  block opened with three backticks and an exclamation mark, runs a shell command when the skill renders,
  before the model sees the text. The command output replaces the line. Search the body
  for both forms. The setting `disableSkillShellExecution` turns this off for skills from
  user, project, plugin and additional-directory sources, and is the right restriction
  when the skill is otherwise wanted ([Skills](https://code.claude.com/docs/en/skills)).
- **Scripts the body names.** Every path the body tells the agent to run is code the agent
  will execute with whatever the session permits. `scripts/`, `assets/` and anything under
  `references/` that is not Markdown count.
- **Prose.** The body, every `references/*.md` and the description are instructions. The
  description is resident in context for every session once installed, which makes a
  poisoned description the cheapest place to put text.

## Plugin

Start from the manifest, `.claude-plugin/plugin.json`, because it can point components
at non-default paths; reading only the default locations misses those. Then every
component:

| Component | Default location | Why it matters |
| --- | --- | --- |
| Hooks | `hooks/hooks.json`, plus any path or inline config in the manifest | Shell commands at lifecycle events, such as before or after each tool call |
| Monitors | `monitors/monitors.json` | Background shell commands started with the session |
| MCP servers | `.mcp.json` or inline in the manifest | A stdio server is a process started on the machine; a remote entry names a URL and headers |
| Executables | `bin/` | Files here are on the Bash tool's `PATH` while the plugin is enabled, so a bare command name can resolve to them |
| Language servers | `.lsp.json` or the manifest | Started by the plugin |
| Mods | declared by the plugin; see the mods pages of the Claude Code documentation | JavaScript that runs inside Claude Code with the user's permissions |
| Workflows | `workflows/` | JavaScript files the plugin ships |
| Settings | `settings.json` at the plugin root | Defaults applied while the plugin is enabled, such as which agent runs |
| Output styles | `output-styles/` | Markdown that changes how the model responds; prose, so read it as instructions |
| Skills, commands, agents | `skills/`, `commands/`, `agents/` | Prose; steer the tools the agent already has |

Two more things to read in a plugin. The `${CLAUDE_PLUGIN_ROOT}` variable in a command is
where the plugin's own files live, so a hook that runs a script under it runs a file you
must have read. And the marketplace entry that lists the plugin: whether it pins a source
by commit SHA, and whether the marketplace has auto-update on, since an update replaces
the files you reviewed.

The `/plugin` details pane lists that a hook exists but not what it runs. Claude Code can
also print a component inventory from the files without starting a session
(`claude --plugin-dir <plugin directory> plugin details <plugin name>`); the documentation
presents it as a way to see what Claude Code finds. Use it as a cross-check on your own
inventory, run it from a directory that is not the quarantine and not a project with
settings you care about, and still read the files.

## Hook

A hook is a shell command, or another handler type, that Claude Code runs at an event.
The documentation states that command hooks execute with the user's full permissions and
can modify, delete or read any file the account can. For each hook read:

- the event and matcher, which say how often it fires (a matcher on every tool call runs
  constantly);
- the command, including every variable it expands and whether the script path is a file
  inside the package;
- what the script does with the event's input, which contains tool inputs and can include
  file contents and commands;
- whether it can change a tool call (block, rewrite or approve), since a hook that
  approves is a permission grant by another name.

## MCP server

- **Local (stdio).** The `command` and `args` are what runs. Check whether they launch a
  file in the package or fetch a package at launch (`npx`, `uvx`, `docker run` with a
  floating tag), because then the code that runs is not the code you read. Check `env` for
  credentials passed in, and the working directory.
- **Remote (HTTP).** There is no code to read. The URL, the OAuth scopes or the headers
  it asks for, and the operator are the whole surface. Tool descriptions arrive from the
  server at connection time and may change.
- **Project `.mcp.json`.** Claude Code asks for approval before using project-scoped
  servers, and a cloned repository cannot approve its own servers in a folder you have
  not trusted ([MCP](https://code.claude.com/docs/en/mcp)). That approval is a prompt, not
  a review.
- **Tool definitions.** Read every tool name, description, parameter description, schema
  default and enum value in the source. The MCP specification says clients must consider
  tool annotations untrusted unless they come from a trusted server, and describes a
  `notifications/tools/list_changed` message a server can send when its tool list changes
  ([tools](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-11-25/server/tools.mdx)).
  So the list is not fixed for the life of the connection.

## Slash command

A command is a Markdown prompt, optionally with the same dynamic context lines and
`allowed-tools` as a skill, run when invoked. It is smaller than a skill but has the
same two halves: read its frontmatter for tool grants and its body for shell lines and
instructions. A command that takes an argument and interpolates it into a shell line is
an injection point; note it even when the shipped use is benign.

## Install and build scripts

These run when the package is installed or built, which can be before any of the above.
Read `package.json` `scripts` (`preinstall`, `install`, `postinstall`, `prepare`),
`setup.py` and `pyproject.toml` build hooks, `Makefile`, `install.sh`, `Dockerfile`, and
any one-line install command in the README. A README that says to pipe a download into a
shell is itself a finding: the file you would read is not the file that runs.
