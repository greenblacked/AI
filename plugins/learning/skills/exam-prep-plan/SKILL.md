---
name: exam-prep-plan
description: "Work backwards from a fixed certification or exam date such as CKA, AWS, CISSP or a university module to a study schedule. Day 0 is a full-length practice exam scored by blueprint weight; weight times miss rate ranks domains and sets hours. Schedule backwards in three blocks (gap closing, mixed practice, rehearsal). An error log gives every miss a cause and retests it at 1, 3, 7 and 14 days. Two timed mocks at T-14 and T-5, no new material after T-5, and a go/no-go gate of pass mark plus 10 percentage points on two consecutive mocks, else reschedule while the fee policy allows. Use when someone says \"my exam is in 6 weeks\", \"how do I study for the Kubernetes admin cert\" or \"I failed the first attempt, what now\". Not for card writing (learning-notes), learning with no date (skill-acquisition-plan), live-coding interview loops (technical-interview-prep) or a study routine (habit-change)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Exam Prep Plan

A finished plan has a diagnostic score by domain, an hours budget that follows the blueprint weights, a dated block schedule, a running error log, two dated mocks, and a stated pass mark for going ahead with the exam on the booked date.

The usual failure is studying what is pleasant. People re-read the chapter they already know and avoid the one that frightens them, then discover on the day that the heaviest-weighted domain was the weakest. The second failure is covering new material right up to the exam, with no rehearsal of the conditions: the clock, the interface, the question style. The plan below lets the data pick the topics and fixes the last days for rehearsal rather than reading.

## Scope

Use for: a certification or exam with a fixed date and a published syllabus or blueprint; a retake after a failed attempt; a university module exam with a known weighting.

Do not use for: writing and reviewing flashcards as such (`learning-notes`), open-ended learning with no date or exam (`skill-acquisition-plan`), preparing for a live-coding interview (`technical-interview-prep`), or keeping a study routine going (`habit-change`).

## Workflow

### 1. Gather the facts that constrain the plan

Write down: the exam date and time, the pass mark and how it is scored, the published blueprint with each domain's weight, the format (multiple choice, hands-on lab, essay), the time limit, the fee and the rescheduling and retake policy including the deadline for changing the date without cost. Take these from the exam provider's current page, not a forum post; blueprints are revised, and studying an old one wastes weeks. Count the real study hours available per week, after work and fixed commitments, and be pessimistic.

For a retake, get the score report by domain first; it replaces the guesswork in step 2 for the domains it covers.

### 2. Day 0: take a full-length practice exam cold

Use an official or provider-endorsed practice exam, under real time conditions, before studying. Score it by blueprint domain. Rank domains by weight times miss rate: a domain worth 30 per cent of the exam where you miss half beats a domain worth 5 per cent where you miss everything. Allocate study hours in proportion to that ranking, and drop the domains where you scored well and the weight is small to a light review. Read `references/schedule-and-scoring.md` for the scoring sheet and a worked allocation.

If the cold score is already above the pass mark plus 10 percentage points, the plan shrinks to mixed practice and rehearsal; say so rather than filling the weeks.

### 3. Schedule backwards from the exam

Place the fixed points first, then fill. Work from the exam date backwards:

| Block | Position | Content |
| --- | --- | --- |
| Rehearsal | Last days | Timed mocks, error log review, logistics check; nothing new after T-5 |
| Mixed practice | Middle | Questions or labs across all domains, interleaved, under time pressure |
| Gap closing | First | Study of the top-ranked domains from step 2, each ending with a topic quiz |

Give gap closing roughly the first half to two thirds of the time, depending on the diagnostic; a four-week plan falls a little below half, because the mocks and rehearsal need their fixed days. For hands-on exams (labs, a command line), practice must be hands-on from day one; reading about commands does not train typing them under a clock.

### 4. Keep an error log from the first practice question

Every miss gets a row: the question or lab, the domain, the cause, and the fix. Use three causes: did not know, misread the question, ran out of time. They need different remedies. Did not know means study. Misread means slow down and underline the constraint words. Ran out of time means timed drills and a skipping rule. If one cause dominates, change method before adding hours.

Retest each logged item after 1, 3, 7 and 14 days, from the date it was logged. Retest by answering a fresh question on the same point or redoing the lab from scratch, not by rereading the answer. An item retested correctly at 14 days leaves the log.

### 5. Timed mocks at T-14 and T-5

Two full mocks under real conditions: same duration, same interface where possible, no notes, no pauses. Take the first at T-14 (14 days before the exam) and the second at T-5. After each, score by domain and add every miss to the log. Stop new material at T-5; the days after the second mock are for the log, the weakest domains' retests and sleep.

### 6. Go/no-go gate

Before the date at which rescheduling stops being free, decide. The margin is 10 percentage points on the practice exam's raw percentage score. Go if the score on two consecutive mocks is at least the pass mark, expressed as a percentage, plus 10. For an exam with a scaled score, divide the scaled pass mark by the top of the scale as a rough conversion (700 of 1000 is 70 per cent), and prefer the practice exam's own percentage where it reports one. Scaled scores are not a straight percentage of questions answered, so the conversion is approximate and the margin is what absorbs the error. Ten points on the scaled number itself would be about 1 per cent and test nothing.

If the free-reschedule deadline falls before T-5, two consecutive mocks cannot exist by the decision date. Bring the second mock forward so both fall before the deadline, with at least two or three days between them for error-log work, or decide on one mock and state the margin used, for example the same 10 points on a single score, accepting that one result is a noisier signal.

If the gate fails and the policy allows moving the exam without losing the fee, move it and extend gap closing on the domains the mocks show. Practice exams are usually easier or harder than the real one in unknown ways, which is why the margin is 10 points and not zero. Where the provider gives no free rescheduling, say that the margin is the only protection and decide with the fee in view.

### 7. Final checklist

Complete two days before: identification document valid and matching the booking name; for a proctored online exam, run the provider's system test on the exact machine and network, clear the desk and room to the rules, and check permitted items; for a test centre, route, arrival time and permitted items; allowed breaks and food; the time of day you perform best against the booked slot. Prepare the machine's keyboard layout and shell settings for a hands-on exam.

## Hand back

The facts sheet, the cold diagnostic by domain with the ranking, the dated schedule in three blocks, the error log template with the retest dates, the mock dates, the go/no-go decision date and rule, and the checklist. For a retake, include the cause analysis of the earlier failure.

## Anti-patterns

- **Studying in the order of the syllabus.** The data picks the order.
- **Rereading as review.** Retest by answering.
- **New material in the last five days.** It displaces consolidation and raises anxiety.
- **Untimed mocks.** Time is a skill on its own and ran out for many people who knew the content.
- **Booking the date and then never checking the fee policy.** The reschedule deadline is a decision point.

## Reference files

- `references/schedule-and-scoring.md` - read at steps 2 to 4: the diagnostic scoring sheet, a worked hours allocation, a week-by-week skeleton for 4, 6 and 8 weeks, and the error log template with retest dates.
