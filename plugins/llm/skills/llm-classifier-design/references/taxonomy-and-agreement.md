# Taxonomy and agreement

## Contents

- Class template
- Double-labelling protocol
- Cohen's kappa
- Reading disagreements

## Class template

One block per class, kept in a versioned file next to the prompt:

```markdown
### refund_request
Definition: the customer asks for money back for a purchase already paid.
Positive: "I was charged twice, please return the second payment."
Near-miss negative: "Why was I charged twice?" (a billing question until a refund is requested.)
Tie-break: if a refund is requested and the product is also reported broken, label refund_request.
```

Include `other`: "none of the above, or the text is too short or unrelated to decide". Record a version number and change it whenever a definition changes; labels are only comparable within one version.

## Double-labelling protocol

1. Draw 100 real items, stratified lightly so each class appears at least a few times.
2. Two labellers work independently from the written taxonomy only, with no discussion.
3. Record both labels per item in a file with one row per item.
4. Compute agreement, then meet to resolve each disagreement and write the rule that would have prevented it into the taxonomy.
5. Relabel a fresh 100 under the new version if kappa was low.

## Cohen's kappa

Observed agreement po is the share of items where both labels match. Expected agreement pe is the sum over classes of (share labelled c by A) times (share labelled c by B). Then kappa = (po - pe) / (1 - pe).

```python
from collections import Counter


def cohens_kappa(a, b):
    if len(a) != len(b) or not a:
        raise ValueError("label lists must be the same non-zero length")
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in set(ca) | set(cb))
    return (po - pe) / (1 - pe) if pe < 1 else 1.0
```

Interpret it against the use, not a published band: a moderation action with legal consequences needs a high value and a triage tag may tolerate less. With three or more labellers use Fleiss' kappa or Krippendorff's alpha instead.

## Reading disagreements

Group the disagreement rows by the pair of labels. A pair that recurs means a missing tie-break or overlapping definitions; merge the classes if no rule separates them. A single labeller who differs from everyone suggests they misread the instructions. Disagreements on very short or empty texts argue for routing those to `other` by rule before the model sees them.
