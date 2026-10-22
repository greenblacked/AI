# Hidden state inventory

A notebook's behaviour depends on more than its cells. These searches find the dependencies that a scheduled run will not have, and the table after them says what each becomes.

## Contents

- Searching the notebook
- What the searches miss
- Deciding what each finding becomes

## Searching the notebook

Search the `.ipynb` file itself rather than a converted script, so that outputs are searched too: a credential printed into an output cell is as leaked as one typed into a source cell.

| Looking for | Patterns to search |
| --- | --- |
| Clock-dependent logic | `now(`, `today(`, `utcnow(`, `date.today`, `pd.Timestamp.now`, `time.time(`, `CURRENT_DATE`, `GETDATE(` |
| Absolute or personal paths | `/Users/`, `/home/`, `C:\\`, `~/`, `Downloads`, `Desktop`, `os.chdir(` |
| "Latest" lookups | `latest`, `max(`, `sorted(glob`, `[-1]` on file listings, `ORDER BY` with `LIMIT 1` |
| Credentials | `password`, `passwd`, `secret`, `token`, `api_key`, `apikey`, `Authorization`, `BEGIN PRIVATE KEY`, connection strings with `://user:` |
| Manual overrides | `!=` and `~df[` filters on identifiers, `.drop(` with literal indices, `.loc[` assignments with literal keys, `# remove`, `# hack`, `# temp`, `# fix` |
| Magic numbers | Literal dates, literal thresholds in comparisons, currency rates, `* 1.2`-style adjustments |
| Randomness | `random`, `np.random`, `sample(`, `shuffle`, `train_test_split(` without `random_state` |
| Side-effect writes | `to_csv(`, `to_parquet(`, `to_excel(`, `.write`, `INSERT`, `CREATE TABLE`, `savefig(` |
| Shell and magics | lines starting `!` or `%`, `%run`, `%store`, `%load_ext autoreload` |

Treat each hit as a question, not an answer: a `now()` used only in a plot title is harmless, a `now()` in a filter decides which data the job reads.

## What the searches miss

- **Execution order.** The cell counters (`"execution_count"` in the file) show the order in which cells last ran. Non-monotonic counters mean the saved outputs came from an order other than top to bottom; step 1's headless run is the check that matters.
- **Variables from deleted cells.** A name used but never assigned in the notebook's text was assigned in a cell that no longer exists. The headless run fails on it with a `NameError`.
- **`%store` and `%run`.** Values pulled from another notebook or the IPython store are inputs. Find their origin and make them explicit.
- **Mutating a frame across cells.** A cell that modifies a data frame in place (`df["x"] = ...`, `inplace=True`) gives a different result when re-run. In the extracted code each transform returns a new frame.
- **Implicit environment.** Locale-dependent parsing (decimal commas, date order), the machine's time zone used by naive datetimes, and environment variables set in the author's shell profile.
- **External state read once.** A lookup table loaded from a spreadsheet on a shared drive, or a reference list typed into a cell months ago. Both are inputs with an owner, and both need a pinned version.
- **Installed-but-undeclared packages.** Imports that work only because the author's environment happened to have them. The clean-checkout run in step 9 finds these.

## Deciding what each finding becomes

| Finding | Becomes | Why |
| --- | --- | --- |
| Clock call deciding the data window | Required `--run-date` argument | A backfill or a rerun after an outage must compute the date it was asked for |
| Clock call in a label or log line | Leave, or derive from `--run-date` | Harmless, but deriving keeps reruns byte-identical |
| Absolute path | Argument or configuration | The scheduler's machine does not have the author's home directory |
| "Latest" file or partition | Explicit path derived from `--run-date` | "Latest" changes between a run and its rerun |
| Credential | Environment variable or secret manager, rotated if it was ever in the file | The file's history and every shared copy still hold it |
| Manual filter on identifiers | A named rule with a comment saying who decided and why, or an override table with an owner | An unexplained exclusion is a business rule nobody can review |
| Magic number | Named constant with its source; configuration if it changes by environment | The next person needs to know whether it is a policy, a fact or a guess |
| Randomness | Seed argument, defaulted | Without it the golden test cannot be exact |
| Display cell | Removed from the job; kept in the thin notebook | It costs runtime and memory and produces nothing the job uses |
| Side-effect write | The single output step, or removed | Writes scattered across cells cannot be made idempotent |
| `%run` of another notebook | An import from the package | Two notebooks calling each other are a package without tests |
