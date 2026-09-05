# Proposal Craft

Read this while writing or rewriting a CFP submission. The talk and the proposal are
different pieces of work, and a good talk with a weak proposal does not get given.

## Contents

- [How a committee actually reads](#how-a-committee-actually-reads)
- [The abstract](#the-abstract)
- [The outline](#the-outline)
- [The bio](#the-bio)
- [Notes to the committee](#notes-to-the-committee)
- [Choosing which idea to submit](#choosing-which-idea-to-submit)
- [Submitting](#submitting)
- [Rejection](#rejection)

## How a committee actually reads

Assume a reviewer with two hundred submissions, a schedule with gaps of specific shapes,
and a few minutes per entry. In that first pass they are answering three questions:

1. What is this talk about, specifically enough that I can picture the room?
2. Is there a reason it is this speaker giving it?
3. Does the outline convince me the talk already exists?

Anything that makes those slower to answer costs you. A title that hides the subject, an
abstract that spends its first sixty words on context everyone shares, an outline of four
nouns — each of them pushes the reviewer to the next submission.

The second pass is comparative. Yours is now next to three others on a related subject,
and the tiebreak is usually specificity: the one with the real system, the real number and
the stated takeaway wins over the one that promises an overview.

## The abstract

150 to 250 words unless the CFP says otherwise. Audience-facing: it will be printed in the
programme, so write it in the voice you will speak in, not in the voice of a grant
application.

A shape that works:

1. The specific problem, stated as a situation the reader recognises. One or two sentences.
2. What happened — the attempt, the surprise, the constraint that turned out to govern it.
3. What the audience will be able to do or decide afterwards.
4. Who it is for, said plainly.

### Before

> Observability is more important than ever in modern distributed systems. In this talk we
> will explore the three pillars of observability and discuss best practices for
> instrumenting microservices, including tracing, metrics and logging. Attendees will
> learn how to improve their observability posture and gain insights into their systems.

Nothing here could not have been written without giving the talk. No claim, no speaker, no
audience.

### After

> Our checkout service had a 4.2 second p99 against a 300 millisecond SLO, and it had been
> that way for five months while every dashboard stayed green. This talk is the story of
> what we were measuring instead, why three separate alerts were technically firing
> correctly the whole time, and the two changes to our instrumentation that made the
> problem visible in an afternoon. If you own a service with good dashboards and users who
> complain anyway, you will leave with a specific method for finding what your metrics are
> averaging away.

Same subject area. It has a claim, a system, a number, an audience and a takeaway.

## The outline

The part reviewers use to distinguish a shaped talk from an intention, and the part most
submissions treat as an afterthought.

Give sections with minutes and a one-line purpose:

```text
1. The green dashboard and the angry user (4 min)
   The situation, the numbers, why nobody spotted it.
2. What an average hides (8 min)
   The mechanism. Worked example with real percentile data.
3. Three alerts that fired correctly and told us nothing (10 min)
   Why alert design and instrumentation are the same problem.
4. The two changes, and what they cost (8 min)
   What we did, what we would do differently, what does not transfer.
5. How to find yours (4 min)
   The method, restated as something to run on Monday.
```

The minutes must add to less than the slot. A reviewer who adds them up and gets the slot
length exactly knows the talk will overrun, because every talk does.

## The bio

Two or three sentences. Establish standing for this specific talk and stop.

- Weak: a career summary that lists five employers and no relevance to the subject.
- Weak in the other direction: inflated titles or implied scale you would not defend in
  the corridor. The bio sets the bar the talk is then measured against.
- Strong: what you built or run, at roughly what scale, for how long, plus one line of
  personality if the conference has that tone.

If the talk rests on an experience at a previous employer, say which one and when. Vague
attribution reads as either modesty or concealment, and reviewers cannot tell which.

## Notes to the committee

Not audience-facing, and underused. Put here:

- Whether the talk has been given before, where, and what is different this time. Many
  conferences accept repeats; almost all of them resent finding out afterwards.
- What is built already and what is still being written. Honest in-progress is fine.
- A recording or slides from a previous talk, if you have one. This is the single most
  effective thing a first-time speaker can attach.
- Anything the committee should know about scheduling, accessibility or format needs.

## Choosing which idea to submit

| Signal | Reading |
| --- | --- |
| You have told this story three times in a pub and people asked questions | Strong candidate; the structure already survived contact |
| The material comes from documentation and other people's talks | The committee has already seen it, better told |
| You would have to invent the numbers | Not this talk, under the honesty rules |
| The scars are yours but the subject is niche | Submit it; specific beats broad, and committees need range |
| It is a product or a tool you sell | Most conferences reject it, and the ones that do not have a sponsor track |

## Submitting

- Multiple conferences, deliberately. Acceptance rates are low enough that a single
  submission is mostly a lottery ticket.
- Adapt the abstract per conference. A committee can tell when they are reading a form
  letter, and audience assumptions differ between events.
- Read the accepted talks from the last two years. It tells you the level, the tone and
  what they already have.
- Meet the deadline early. Late submissions to a full schedule are compared against
  accepted talks rather than against the pool.

## Rejection

Most rejections are scheduling and framing, not quality: the track was full, another
submission covered the same ground, the outline did not convince, the abstract was too
broad to place. None of that is a verdict on the talk.

What to do with it:

1. Ask for feedback where the conference offers it. Some do.
2. Reread the abstract and find the claim. If you cannot state it in one sentence, that
   was the problem.
3. Narrow it. The commonest fix is a talk that was pitched to everyone being re-pitched to
   one specific role in one specific situation.
4. Submit it elsewhere within the month, while the material is still fresh.
5. Consider a local meetup first. It is a real audience, it produces the recording that
   makes the next submission stronger, and it is where the timing problems surface
   cheaply.
