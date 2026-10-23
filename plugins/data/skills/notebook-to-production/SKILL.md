---
name: notebook-to-production
description: "Turn an exploratory Jupyter notebook into a scheduled, tested job without changing its answer: prove it runs top to bottom headless, record golden output on a pinned sample as a characterisation test, extract functions behind that test, take dates and paths as parameters, secrets from the environment, lock dependencies, strip outputs and keep the notebook as a thin caller, and write output to a partition keyed by run date so a rerun replaces rather than appends. Run it on a clean checkout before scheduling. Use when someone says \"productionise this notebook\", \"schedule the analyst's notebook\", \"it only works if you run the cells in order\" or \"make the script give the notebook's numbers\". Not for restructuring code already in production (refactoring), writing a new tool from scratch (code-scaffold), designing CI stages (ci-pipeline-design) or a leaked key (secret-rotation)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Notebook to Production

The move is done when a package holds the notebook's logic as functions; a headless entry point takes the run date, paths and environment as arguments and reads secrets from the environment; a lockfile pins every dependency; a golden test proves the job reproduces the notebook's output on a pinned input sample; the notebook itself is a thin caller with outputs stripped; and one run on a clean checkout, repeated for the same date, has produced the same partition twice — all before the job is put on a schedule.

The usual failure is copying the cells into a `.py` file and scheduling it. A notebook carries state that is not in its text: cells run out of order, a variable defined in a cell since deleted, a file read from someone's home directory, `datetime.now()` deciding which day is computed, a manual cell that dropped one bad customer on the day the numbers were checked. The scheduled copy runs, computes something slightly different from what was signed off, and nobody can tell, because there was never a reference output to compare against. Every step below either removes a piece of hidden state or keeps the reference output honest while you do.

## Scope

Use for: a notebook whose output someone relies on (a report, a feature table, a trained model, a scoring run) that must now run unattended; a notebook that only works when cells run in a particular order; making a scripted version reproduce the notebook's numbers; parameterising a notebook by date for backfills.

Do not use for: restructuring code that is already a package in production, which is `refactoring`; writing a new tool with no notebook behind it, which is `code-scaffold`; deciding what CI runs and which checks block a merge, which is `ci-pipeline-design`; a credential that has already been committed, which is `secret-rotation` first; repairing rows an earlier run wrote wrongly, which is `safe-backfill`; moving to new major versions of pandas or scikit-learn, which is `dependency-upgrade` once this is done.

This skill pre-approves no shell command. It reads the notebook, including its cells and saved outputs, which other people wrote, and a pre-approved interpreter or `git` would let instructions planted there run without anyone agreeing to them. The Python, SQL and shell in this skill and its references run only when the user approves each command. Executing the notebook runs its code, so state what is about to run.

## Workflow

### 1. Prove it runs top to bottom, headless

Restart the kernel and run every cell in order, without the interface:

```bash
jupyter nbconvert --to notebook --execute --output executed.ipynb analysis.ipynb
```

If it fails, the notebook depended on state outside its text. Make the smallest edits that let it run clean from a fresh kernel — define the missing variable, reorder the cells — and treat that version as the one you will characterise. Record the package versions of the kernel that produced the signed-off result (`pip freeze` or `conda list` inside that environment), because those versions produced the numbers people trust.

### 2. Pin an input sample and record golden output

Replace every live read ("the latest file", "yesterday's partition", a query against a moving table) with a fixed snapshot: a date-limited extract saved as Parquet, or a pinned warehouse partition. Make it small enough to run in about a minute and large enough to exercise the edge cases the notebook handles — nulls, the special-cased customer, a month boundary.

Run the notebook on the snapshot and save its output, sorted by key, as the golden file. Run it a second time and compare. If the two runs differ, find the non-determinism (an unseeded random call, a set iterated in arbitrary order, an unsorted group-by) and remove it before going on, since a golden test over a non-deterministic job fails for reasons that have nothing to do with your changes.

Write the golden test now, before extracting anything. It is a characterisation test: it pins what the notebook does, including anything that looks like a bug. Note suspected bugs in a comment and fix them later as a separate, deliberate change. Read `references/golden-and-idempotent-output.md` for capturing the sample and the comparison code.

### 3. Inventory the hidden logic

Search the notebook for every place where behaviour depends on something not passed in, and decide what each becomes.

| Found | Becomes |
| --- | --- |
| Hard-coded paths, bucket names, table names | Arguments or configuration |
| `datetime.now()`, `date.today()`, "latest" lookups | A required `--run-date` argument, so a backfill computes the right day |
| Credentials, tokens, connection strings in cells or outputs | Environment variables or a secret manager; history checked |
| Inline filters and overrides (`df = df[df.id != 1234]`) | A named rule in code with a comment saying why, or a reviewed override table |
| Magic numbers (thresholds, exchange rates, cut-off dates) | Named constants or configuration, with their source |
| Display cells (`head()`, plots, `describe()`) | Deleted from the job path; kept in the thin notebook if useful |
| Cells that write files as a side effect | The single output step, or deleted |
| Unseeded randomness | A seed argument with a default |

Read `references/hidden-state-inventory.md` for the search patterns and the less obvious cases.

### 4. Extract functions behind the golden test

Start from `jupyter nbconvert --to script analysis.ipynb` and shape the result into load, transform and write. Transforms take data frames and parameters and return data frames, with no I/O inside, so they can be tested and reused; loading and writing sit at the edges. Run the golden test after each extraction and commit each one green. The mechanics of a safe extraction are those of `refactoring`; the golden test is what makes them safe here.

### 5. Parameters and secrets

Give the package one entry point, runnable as `python -m <package>`, taking `--run-date` (required; let the scheduler pass it rather than defaulting to today), input and output locations, and an environment name. Read secrets from environment variables at start-up, fail fast with a message naming the missing variable, and never log their values. Keep differences between environments in configuration, not in branches of code.

If a credential ever sat in a cell or its output, it is in the repository's history and in every copy of the notebook that was shared. Rotate it before scheduling anything.

### 6. Lock the environment

Declare dependencies in the project file and generate a lockfile with the tool the team already uses: `uv lock`, `poetry lock`, `pip-compile --generate-hashes`, or `conda-lock`. Pin the Python version too. Start from the versions recorded in step 1; if the resolver picks different versions of pandas, NumPy or scikit-learn, the golden test will say whether it matters. Upgrading is a separate change after this one.

### 7. Keep the notebook thin and strip its outputs

The notebook stays useful for exploration, but it imports the package and calls its functions rather than holding a second copy of the logic. Where the notebook is itself the report, parameterise it with papermill: tag one cell `parameters` and run `papermill report.ipynb out/report-2026-10-01.ipynb -p run_date 2026-10-01`.

Strip outputs before they reach the repository with `nbstripout --install`, which sets a git filter for the clone. Outputs carry data, sometimes personal data and sometimes secrets, and they make every diff unreadable.

### 8. Make reruns safe

Write output to a location keyed by run date — a `run_date=2026-10-01` partition, or rows deleted and inserted for that date inside one transaction — so running the same date twice replaces the result instead of appending to it. Write to a temporary location and move it into place at the end, so a failed run leaves no half-written partition that looks complete. In Spark, set `spark.sql.sources.partitionOverwriteMode` to `dynamic` so an overwrite touches only the partitions the run produced.

End the run with two cheap checks that fail it: the output is not empty, and its key is unique.

### 9. Run it on a clean checkout before scheduling

Clone into an empty directory, build the environment from the lockfile alone, set only the environment variables the scheduler will set, and run the entry point for a past date. Run the same date again and confirm the output is identical, not doubled. Run once with a secret missing and confirm it fails loudly with a non-zero exit. Do this in the image the scheduler will use where there is one, because "works on my laptop" is the condition this whole procedure exists to remove. Only then add the schedule, and write down the backfill command.

## Output format

```markdown
## Job
[Package, entry point and its arguments, the schedule it is ready for, owner.]

## Proof
[Golden test: input snapshot location, comparison tolerance, result. Clean-checkout run: date run, rerun identical, missing-secret failure.]

## Hidden logic resolved
[Each item from the inventory and what it became; suspected bugs pinned and not yet fixed.]

## Environment
[Lockfile, Python version, any version that differs from the notebook's kernel and why.]

## Rerun and backfill
[Output partitioning, the backfill command, the output checks.]
```

## Anti-patterns

**Cells pasted into a script and scheduled.** The script inherits the notebook's hidden state without the person who knew about it. Characterise first.

**Fixing bugs during the move.** A changed number cannot then be told apart from a broken extraction. Pin the bug, move the code, fix it afterwards on its own.

**`today()` inside the job.** A backfill for last Tuesday computes today. Take the date as a required argument.

**Appending output.** Every retry doubles the rows. Key the output by run date and overwrite that key.

**A notebook that still holds the logic.** Two copies diverge within a month. The notebook calls the package.

**Scheduling first, testing on the scheduler.** The first failure is then in production at 2am with no golden output to compare against.

## Reference files

- `references/hidden-state-inventory.md` — read at step 3: search patterns for hidden state in a notebook, the less obvious cases, and what each becomes.
- `references/golden-and-idempotent-output.md` — read at steps 2, 8 and 9: capturing the input snapshot, the golden test, partition-keyed writes, and the clean-checkout run script.
