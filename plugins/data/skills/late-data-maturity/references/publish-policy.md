# Publish policy

Contents: agreeing the threshold, choosing the restatement policy, and the policy text that sits beside the figure.

## Agreeing the threshold

Ask the person who acts on the figure three questions, and record the answers with their name and the date:

1. What decision does this figure drive, and by when must it be made?
2. How large an error would change that decision? Ask for a number, as a share of the total.
3. Is the error that matters in the count of things or in their money value?

| Consumer | Typical tolerance | Measure on | Consequence for publish time |
| --- | --- | --- | --- |
| Finance close, revenue reporting, billing | Very small; often the close waits | Value | Late; usually needs a freeze policy |
| Executive daily dashboard | A few tenths of a percent | Value or rows | Publish provisional early, final at the curve |
| Operations staffing, order dispatch | Low single-digit percent | Rows | Early; the cost of waiting exceeds the error |
| Experiment readout | Equal completeness across arms matters more than total | Rows per arm | Wait until both arms pass; unequal lag biases the comparison |

The tolerances above are prompts for the conversation, not defaults. The experiment row is the one most often missed: if the variant changes the client, it can change how late its events arrive.

## Choosing the restatement policy

| Policy | What happens to a row that arrives after the window | Fits when | Costs |
| --- | --- | --- | --- |
| Restate in place, no window | The past figure changes, indefinitely | Exploratory analysis; nobody has acted on the old figure | Nobody can cite a number and expect it to hold |
| Restate inside the window, then freeze and book late arrivals to the period they arrive in | Counted in the current period, tagged as a late arrival from an earlier one | Finance and anything reported externally | Period totals differ from an event-time recount; keep both and label which is which |
| Restate inside the window, then freeze and drop | Excluded, counted in a late-arrivals log | Operational counts where tiny tails do not matter | Silent loss unless the log is reviewed |
| Versioned restatement | A new version of the past figure, with the old one kept and a notice sent | Regulated or contractual figures | Needs a version column and a notice process |

Choose the window length from the bad-day curve, not the median: the age past which the 5th-percentile day has, say, 99.9% of its value. Check that every incremental model's lookback or load-time selection covers at least that window.

## Policy text

Publish this beside the figure, in the dashboard's description or the metric's documentation:

```text
Figure: <metric> by <grain>, reporting time zone <zone>.
Provisional until: <age> after the period closes. Before then the figure is shown
  as provisional; on 95% of past days it was at least <threshold> complete at that age.
Final after: <window> after the period closes. Arrivals later than that are
  <booked to the period they arrive in | dropped and logged | issued as a new version>.
Comparisons: period-on-period comparisons use both periods at the same age.
Threshold agreed by: <name, role, date>. Curve last measured: <date>.
```

Revisit the policy when a source changes how it delivers, when the curve moves by more than the agreed tolerance, or when the consumer's decision changes.
