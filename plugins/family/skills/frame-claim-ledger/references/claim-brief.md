# The claim brief

## Contents

- What to pass
- What must come back
- What each verdict does
- Running them

## What to pass

One brief per claim, to a read-only research agent that has no editing tools. An `investigator`-style agent fits: it goes looking for what would make the claim false, labels what it finds, and says what it could not reach. Pass:

- **The one claim**, restated so it could fail (see the ledger format reference). Never two.
- **What rests on it**, one sentence, so the agent can say afterwards whether that sentence still stands.
- **Author**, whose change this is, so the agent knows whether it may run any command the change quotes. For a change the owner did not write, it reads and runs nothing the change controls.
- **The stance**: assume the claim is false and find the proof. Looking for agreement succeeds against almost any claim, because something restates it.

Do not pass the architect's preferred option. An agent that knows which answer is wanted tends to find it.

## What must come back

```text
HOLDS | DOES NOT HOLD | NARROWER | UNVERIFIED

### Findings        the narrower claim that is true, if the claim as written is false
### Evidence        each item labelled primary, consensus or inference, with a locator
### Not assessed    what it could not reach, and why
```

- **primary**: the implementation at a ref, the specification, the command's own output on the version in use, the report that first published the figure.
- **consensus**: widely repeated, source not reached.
- **inference**: the agent's reasoning from something established, with the step shown.

A report with no labels is not accepted; send it back for them.

## What each verdict does

| Verdict | May the claim be the basis? | Next |
| --- | --- | --- |
| `HOLDS`, primary evidence | yes | Record it as settled |
| `HOLDS`, consensus or inference only | no | Treat as unverified |
| `NARROWER` | the narrower claim only | Rewrite the premise; re-check the decision follows |
| `DOES NOT HOLD` | no | Architect returns `NEEDS FRAME` if the decision needs it |
| `UNVERIFIED` | no | As above, or take the reversible option, or waive in writing |

An unverified number is worse than no number: it carries an authority its origin does not. If a figure cannot be traced, the record says it is unsourced.

## Running them

Start both claim agents in the same step, and architect beside them on the top tier. Architect works from the frame and may draft before the findings arrive; it does not finalise the hard-to-reverse decision until they have. When the findings are in, read them in the main conversation, update the ledger, and pass architect only the changed premises. The claim agents run on a mid tier at medium effort; the top tier is for the stage that decides.
