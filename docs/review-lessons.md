# Review lessons

A curated ledger of defect classes caught by the review stage of this repository's
`/ship` loop before merge — not a general list of good practice, and not everything a
gate has ever flagged. Each entry is a class specific enough that naming it saves the
round trip of rediscovering it: `implementer` reads this before writing, so it does not
reintroduce a class already caught once; `reviewer` reads it after `AGENTS.md` and
checks the change against it before anything else.

This file is memory, not a rulebook. A rule that fully replaces the need to remember —
because a validator check or a CI gate now makes the mistake impossible rather than
merely likely — gets its entry pruned, and the pruning commit names the rule that made it
unnecessary. Until that happens, the entry stays, because a gate that nobody reads is only
as good as the gate that catches what it does not yet check.

## Adding an entry

When a review here finds a defect class not already below, the commit that fixes it adds
the entry alongside the fix — not as a separate follow-up, and not paraphrased from
memory afterwards. Four parts, in this order:

- **The class** — what kind of mistake this is, named generally enough to recognise in a
  different file.
- **How it shows up** — the concrete shape it took, specific enough to search for.
- **The check that catches it** — the test, validator rule or CI step that now exercises
  this, so the entry doubles as a pointer to where the guarantee actually lives.
- **Where it was first caught** — the pull request number.

## The entries

### A tag's message drops its own subheadings

**Class.** `git tag -a -F -` defaults to `--cleanup=strip`, which drops every line
starting with `#` from the message — including a Markdown subheading, not only a shell
comment.

**How it shows up.** A release tag built from a `CHANGELOG.md` section loses its
`### Added`-style subheadings silently; the tag message and the GitHub Release body built
from it read as one flat list with no error anywhere.

**The check that catches it.** `scripts/release.py` passes `--cleanup=verbatim`
explicitly, and `tests/test_release.py` asserts that a `#`-led line survives into the tag
message.

**First caught:** #59.

### A shell audit parses YAML with grep, sed or awk

**Class.** A workflow step that inspects YAML structure — a `permissions:` block, a pin —
using line-oriented text tools rather than a real parser is reading text, not structure,
and several equivalent spellings of the same YAML value will not read as equivalent to it.

**How it shows up.** A trailing comment on the value line, a quoted `'write'` against an
unquoted `write`, a flow-map grant (`{contents: write}`), and a comment starting in column
zero each changed whether an early version of the permissions audit fired.

**The check that catches it.** Probe a new shell-based audit against a trailing comment, a
quoted value, a flow map and a column-zero comment before trusting it. `.github/workflows/
security.yml`'s permissions-audit step handles all four, with
`tests/test_permissions_audit.py` exercising each shape.

**First caught:** #58.

### A new strictness rule rejects a form a real parser accepts

**Class.** Tightening the frontmatter reader to reject more ambiguous shapes can reject a
form that a real YAML parser reads without complaint, if the new rule was not checked
against one before landing.

**How it shows up.** A `paths:` block sequence that opens with an explanatory comment
before its first entry — `paths:` then a `# comment` line then `- "src/**"` — is valid
YAML; an early version of the ambiguous-value check treated the comment as ending the
list.

**The check that catches it.** `tests/test_frontmatter.py`'s
`test_a_paths_block_sequence_may_open_with_an_explanatory_comment` asserts the reader
accepts it; the PyYAML reading was recorded by hand in the file's comments, the way
every other case in that file is. Every new `ambiguous-yaml` rejection should get a
matching case, checked against PyYAML the same way, before it ships.

**First caught:** #58.

### Editing a description or raising a listing ceiling to make a check pass

**Class.** Forbidden outright by `AGENTS.md`'s Boundaries: trimming a skill's
`description`, or raising `listing-budget.json`'s ceiling, only to turn a new gate green,
rather than because the content itself changed for its own reason.

**How it shows up.** Adding the per-skill description ratchet found 33 of the 73
descriptions here already past the 500–900 character guidance, the longest at 971 —
each written and tuned against a measured trigger score; trimming them purely to satisfy
the new gate would have thrown that tuning away for no reason connected to the
description's own job.

**The check that catches it.** `scripts/check_listing_budget.py --update` records the
ratchet at what is actually measured rather than forcing a rewrite, and the commit that
runs it says why. `reviewer` reads any diff to `listing-budget.json` or a `description`
line by line for exactly this.

**First caught:** #23.

### A count in prose goes stale

**Class.** A specific number written into documentation prose drifts the moment the thing
it counts changes, with nothing tying the sentence to the value.

**How it shows up.** `docs/ci.md` once read "the three warnings are the correct state" for
the per-plugin `no-version` warning `validate-plugin` emits — a sentence that is wrong the
moment the plugin count is not three, which it was not for long.

**The check that catches it.** Phrase the count so it cannot drift — "one warning per
plugin" rather than a fixed number — or have a script own the count the way
`scripts/check_readme.py` owns the skills badge.

**First caught:** #59.

### A script that fails midway leaves a valid-looking partial artefact

**Class.** Building an archive or export incrementally means a failure partway through
can leave a file that looks complete — every member present except the one that made the
run fail — with nothing about the failed run visible from the artefact itself.

**How it shows up.** `package_skills.py` used to check for a repository-root `LICENSE` and
`NOTICE` only after opening the `.skill` archive in write mode; `zipfile.ZipFile` in `"w"`
mode truncates the archive path immediately, so a missing licence file failed after a
partial, plausible-looking archive already existed in `dist/`.

**The check that catches it.** Verify every input exists before opening any output for
writing. `package_skills.py` now checks for `LICENSE` and `NOTICE` at the repository root
before creating the archive, not after.

**First caught:** #61.

### Release artefacts missing the licence notice

**Class.** Anything this repository distributes — a packaged `.skill` archive, the
portable export — has to carry `LICENSE` and `NOTICE` itself; carrying them at the
repository root is not enough once a copy leaves the repository.

**How it shows up.** A packaged skill or a portable bundle installed somewhere else with
no licence text travelling with it, which narrows what the MIT licence actually requires
without anyone deciding that on purpose.

**The check that catches it.** `package_skills.py` and `export_portable.py` both refuse to
run without a `LICENSE` and `NOTICE` at the repository root, and the `mini_repo` test
fixture carries both so the test suite exercises the real path rather than a fixture that
happens to avoid the case.

**First caught:** #61.

### A legal or factual claim states more, or less, than the facts

**Class.** Summarising a licence, a policy or a source in prose can misstate the actual
condition in either direction — broader than what is true, or narrower.

**How it shows up.** The README's Licence section once said MIT's "one condition" was
that the copyright notice travels with a copy; MIT actually requires the copyright notice
*and* the full licence text to accompany every copy, which is a narrower claim than the
licence actually makes.

**The check that catches it.** Quote the source — the licence text, the policy, the
report — rather than paraphrasing it from memory, and check every legal or factual claim
against the primary source rather than against how it reads. This is `investigator`'s job
when the claim is checkable in isolation, and `reviewer`'s when it is one line among many
in a larger change.

**First caught:** #61.
