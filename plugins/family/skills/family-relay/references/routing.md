# Routing

## Contents

- Every verdict and where it goes
- Who owns a NOT READY
- The two-strike rule, stage by stage
- Waived stages
- Reports that do not fit

## Every verdict and where it goes

| Stage | Verdict | Goes to | Why there |
| --- | --- | --- | --- |
| framer | `FRAMED` | main conversation accepts the slice, then architect | The slice is a decision, not an output |
| framer | `NEEDS INPUT` | main conversation, then framer again | Only a person knows the missing fact |
| framer | `NOT FRAMED` | main conversation | No frame could be made from the request; a person decides whether to restate it, split it or drop it |
| architect | `PROPOSED` | main conversation accepts the approach, then maker | The approach is a decision, not an output |
| architect | `NEEDS FRAME` | framer, with what architect said was missing | An approach without a problem is a preference |
| architect | `BLOCKED` | main conversation | The blocker is a constraint or a choice only a person owns |
| maker, plan | `PLAN READY` | build | The plan is the builder's contract |
| maker, plan | `BLOCKED` | main conversation, which routes it to the stage that owns the blocker | The reason names the owner |
| maker, check | `ON PLAN` | inspector | Shape is settled, so inspection can judge correctness |
| maker, check | `DIVERGED` | architect | Maker would amend the plan to fit the code |
| inspector | `PASS` | launcher, after the go or no-go question | A pass is evidence, not a decision to ship |
| inspector | `FIX`, with `FAILS` lines | build, the `FAILS` lines only | Each is a defect in the change |
| inspector | `FIX`, `NOT ASSESSED` only | the Inspect owner, to run the listed checks | There is nothing for the builder to fix; sending it to build loops forever |
| inspector | `STOP` | a person | It found something only a person can weigh |
| launcher | `READY` | the release owner, then yielder with the measured signal | Launcher plans the release and does not run it; yielder needs an outcome to measure |
| launcher | `N-A` | yielder | Nothing was released, so there is still an outcome to learn from |
| launcher | `NOT READY` | the owner of the missing piece | See below |
| yielder | `YIELDED` | framer, next slice as the request | The loop closes into Frame |
| yielder | `INSUFFICIENT EVIDENCE` | main conversation | Someone has to measure the outcome |

## Who owns a NOT READY

Launcher returns `NOT READY` only by naming a missing go/no-go, release path, signal or rollback. Route by what it names:

- **No go/no-go, or a no-go:** the Inspect owner. `READY` is never routed to release without a go, so this is the gap that keeps Inspect from being skipped.

- **No rollback, or one that cannot work with this approach** (an irreversible migration, a one-way data change): architect, because the approach has to change.
- **No signal, or no way to tell it worked:** the build, when the change needs code or configuration to emit one; architect when the approach leaves nothing to measure.
- **No release path** (nobody owns the release, no route to users): the main conversation, which names an owner or waives Launch in writing.

A `NOT READY` that names none of the four, for example "not enough testing", is a question. It returns to the conversation, which decides whether it is an inspection gap and sends it to inspector.

## The two-strike rule, stage by stage

The same verdict from the same stage twice means the stage before it is wrong. The first strike takes the table's hop. The second goes one stage further back; for a repeated `FIX` that is architect, past maker, because a plan cannot repair an approach.

| Repeated verdict | First strike | Second strike | What it usually means |
| --- | --- | --- | --- |
| inspector `FIX` on the same finding | build | architect | The approach is wrong, not the plan: a symptom was fixed twice. `fresh-inspector-rounds` reopens Architect with the finding as a constraint |
| maker check `DIVERGED` | architect | framer | The approach keeps meeting a slice it cannot hold |
| architect `NEEDS FRAME` | framer | main conversation | The request, not the frame, is under-specified |
| framer `NEEDS INPUT` | main conversation | the person who owns the request | The question was asked but not answered |
| launcher `NOT READY`, same gap | owner of the gap | the stage before that owner | The gap is structural |
| inspector `STOP` | a person | a person, with the history | Do not loop a stop |

"Same" means the same finding or the same named gap, not the same word with a different cause. Count per slice and reset when the slice changes.

## Waived stages

Architect and Launch can be waived, in writing, with the reason and the risk. The relay skips the hop: `FRAMED` goes straight to maker, `PASS` straight to yielder. Record the waiver at the point where the hop would have been, so a reader of the run sees a decision rather than a gap. Frame, Make, Inspect and Yield are not waivable.

## Reports that do not fit

- **No verdict line.** A question. It returns to the conversation, which asks the stage to restate its report with a verdict.
- **A verdict word from another stage.** Treat it as no verdict.
- **Two verdicts.** The stage has hedged. Ask which one it means.
