# Streaming and operations

## Contents

- Choosing thresholds
- Streaming designs
- Canned replies
- Block log
- Weekly review

## Choosing thresholds

For a layer that outputs a score per class, sweep the threshold on the validation split and record at each value the miss rate on the violating set and the false-block count per thousand on the benign set. Plot or tabulate the pairs. Pick the point by class:

- severe: the lowest miss rate whose false-block rate the product can absorb, agreed with the product owner in advance;
- moderate: the knee of the curve, where further misses avoided cost many more false blocks;
- minor: the point with false blocks near zero, accepting misses that the log review will catch.

Confirm on the held-out third, not the split used to choose. Record the threshold with the data version and the date.

## Streaming designs

| Design | What the user sees | Added delay | Risk | Fits |
| --- | --- | --- | --- | --- |
| Buffer, filter, then display | Nothing until the whole reply is checked | The full generation time before first text | None for the checked classes | Severe classes, short replies |
| Hold-back window | Text delayed by the last N tokens or the last sentence | Small and constant | A violation straddling the boundary needs a window long enough to contain it | Moderate classes, long replies |
| Display, then retract | Text immediately; replaced if later flagged | None | The user may already have read it, and copies may exist | Minor classes only |

Input checks run before the model call and add their full latency to every request; run independent checks in parallel and take the slowest, not the sum. Measure added latency as the 95th percentile difference in time to first visible text, with and without the filter, under realistic load.

## Canned replies

State what cannot be done in plain words, give a next step, and do not repeat the blocked content. For example, for a topic block: "I cannot help with that here. You can rephrase your question or contact support at the help page." Keep a distinct reply for a filter outage on a fail-closed class ("I cannot answer right now, please try again shortly") so the user does not read an outage as a policy decision.

## Block log

One record per block: timestamp, feature, direction (input or output), class, layer, score, threshold, model and prompt version, and a reference to the content stored under the access rules for that data. Store the content separately with a short retention period when it may contain personal data.

## Weekly review

Sample a fixed number of blocked items per class and a fixed number of passed items, drawn at random. A reviewer who did not build the filter labels them. Blocked items judged benign update the false-block estimate and join the benign set; passed items judged violating update the miss estimate and join the violating set. A rise in either beyond the agreed bound triggers a threshold review before the next release.
