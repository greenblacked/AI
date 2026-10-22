# Golden and idempotent output

Capturing a pinned input sample, writing the golden test, making output safe to rerun, and the clean-checkout run that comes before any schedule.

## Contents

- Capturing the input snapshot
- The golden test
- Partition-keyed output
- The clean-checkout run

## Capturing the input snapshot

The snapshot is the input the golden test runs on. It must not move.

1. Choose a short historical window the notebook's logic fully covers, such as one week ending on a month boundary, so date logic is exercised.
2. Extract each input the notebook reads, restricted to that window and, if large, to a stable subset of keys (a hash of the key modulo some number, not a random sample, so the subset can be re-derived).
3. Add the edge cases deliberately: rows with nulls in every nullable column the logic touches, the identifiers that manual overrides name, duplicates if the source can contain them.
4. Save as Parquet with the column types preserved. CSV loses types, and a date read back as a string changes the output.
5. Store the snapshot where the test can read it without credentials. If it contains personal data, it does not belong in the repository; use a test bucket with the same access controls as the source, or mask the identifying columns and confirm the output is still meaningful.

## The golden test

Run the notebook (or, later, the pipeline) on the snapshot, sort the output by its key, and save it as the golden file. The test re-runs the pipeline and compares.

```python
import pandas as pd

from mypackage.pipeline import run  # the function extracted in step 4

KEY = ["customer_id", "run_date"]


def test_matches_notebook_output(snapshot_dir, golden_path):
    actual = run(input_dir=snapshot_dir, run_date="2026-09-30")
    golden = pd.read_parquet(golden_path)
    actual = actual.sort_values(KEY).reset_index(drop=True)
    golden = golden.sort_values(KEY).reset_index(drop=True)
    pd.testing.assert_frame_equal(
        actual,
        golden,
        check_exact=False,
        rtol=1e-9,
        atol=1e-12,
        check_like=True,
    )
```

- `check_like=True` ignores column order, which extraction often changes harmlessly; drop it if column order is part of the output contract.
- The tolerances absorb floating-point differences from reordered summation, not real changes. If the test needs a looser tolerance to pass, find out which column moved and why before loosening it.
- Before the first extraction, the "pipeline" is the notebook itself: run it with papermill or nbconvert against the snapshot, read its output file, and compare. Swap in the extracted function once it exists; the golden file does not change.
- When a later change is meant to alter the output (a bug fix), regenerate the golden file in that change and say in the commit which rows changed and why.

## Partition-keyed output

A rerun of a date must replace that date's output, never add to it.

| Target | Pattern |
| --- | --- |
| Files on object storage | Write to `.../run_date=YYYY-MM-DD/` under a temporary prefix, then move or rename into place once complete. Readers ignore the temporary prefix. |
| Spark tables partitioned by date | Set `spark.sql.sources.partitionOverwriteMode` to `dynamic` and write with mode `overwrite`; only the partitions present in the output are replaced. The default, `static`, replaces every partition matched by the write, which can be the whole table. |
| SQL warehouse tables | In one transaction, delete the rows for the run date, then insert the new ones; or `MERGE` on the run date and key. |
| A single file per run | Name it by run date, write to a temporary name in the same directory, rename at the end. |

Finish each run with checks that fail it: row count above zero (and within a range, if history supports one), the key unique, and the run date of every row equal to the requested one.

## The clean-checkout run

Run this from an empty directory, with only the variables the scheduler will set. The example uses `uv`; substitute the equivalent install-from-lockfile command for poetry, pip-tools or conda-lock, and make sure it refuses to re-resolve.

```bash
set -Eeuo pipefail

workdir="$(mktemp -d)"
git clone --depth 1 "$REPO_URL" "$workdir/src"
cd "$workdir/src"

uv sync --locked  # fails when uv.lock is out of date with pyproject.toml
export UV_FROZEN=1  # from here uv run uses the lock as is and never re-locks

uv run python -m mypackage --run-date 2026-09-30 --output "$workdir/out"
# Two empty directories hash identically, so a job that wrote nothing would pass below.
if [ -z "$(find "$workdir/out" -type f -print -quit)" ]; then
  echo "job wrote no output" >&2
  exit 1
fi
first="$(find "$workdir/out" -type f -exec sha256sum {} + | sort | sha256sum)"

uv run python -m mypackage --run-date 2026-09-30 --output "$workdir/out"
second="$(find "$workdir/out" -type f -exec sha256sum {} + | sort | sha256sum)"

if [ "$first" != "$second" ]; then
  echo "rerun changed the output" >&2
  exit 1
fi

if env -u WAREHOUSE_PASSWORD uv run python -m mypackage --run-date 2026-09-30 --output "$workdir/out-nosecret"; then
  echo "job succeeded without its secret" >&2
  exit 1
fi
```

Byte-identical files are the strict form of the check; Parquet writers can embed metadata that differs between runs, in which case compare the read-back frames instead. `WAREHOUSE_PASSWORD` stands for whichever secret the job needs; read the error from the missing-secret run and confirm it names that variable, since a non-zero exit for some other reason proves nothing about secrets. A job that passes all three — runs, reruns identically, fails without its secret — is ready for the scheduler.
