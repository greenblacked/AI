---
name: workshop-design
description: "Design a hands-on technical workshop of two to eight hours for colleagues or a public audience so it stays a workshop and does not turn into a lecture. Three outcomes written as observable tasks, each verified by a closing check; hands-on time of at least 60 per cent with no lecture segment over ten minutes; every segment a card with expected and slow-pair times; 20 per cent buffer with tiered stretch tasks; a cap of 25 participants with one helper per eight; pre-work sent a week early with a verification command; and a full dry run on a clean machine whose stall list gets fixed. Use when someone says \"I'm running a Terraform workshop next month\", \"how do I structure a half-day training\" or \"my workshops turn into lectures\". Not for a one-way talk (conference-talk), a single exercise (exercise-design), a programme spanning weeks (team-training-curriculum) or checking training worked (training-effectiveness-check)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Workshop Design

A workshop design is finished when every participant can perform three named tasks without help, the schedule has been run end to end by someone from the real audience on a clean machine, and the stalls from that run have been fixed.

The usual failure is a talk with a lab attached. The instructor knows the material, so the schedule is sized to the instructor's speed, the environment works on the instructor's laptop, and the three people who failed to install the tooling spend the first hour watching. Time, setup and verification are where workshops fail, not content.

## Scope

Use for: a hands-on session of two to eight hours, for colleagues or a public audience, where participants build, configure or operate something.

Do not use for: a one-way presentation, where the question is how to give a 60-minute talk (`conference-talk`); writing the individual exercises in depth (`exercise-design`); a programme spanning weeks (`team-training-curriculum`); or measuring whether training changed anything afterwards (`training-effectiveness-check`).

## Workflow

### 1. Write three outcomes as observable tasks

Each outcome is something a participant does, phrased so a helper can see whether it happened: "deploy the sample service to the shared cluster without help", not "understand deployments". Three is the limit that fits a day. Next to each, write the closing check: a command, a URL that responds, or a test that passes. Every participant runs the check at the end of the relevant block, and a helper looks at those that fail. An outcome with no check is a hope.

State the audience profile in a few lines: what they already do daily, what they have installed, what operating systems they use. Everything below is judged against that profile, not against the instructor.

### 2. Budget the time

Hands-on time is at least 60 per cent of the total, and no lecture segment runs over ten minutes. Count it honestly: time spent watching the instructor type is not hands-on. If the schedule fails the 60 per cent, cut content, not practice.

Hold back 20 per cent of the schedule as buffer, placed in several small pieces and not one lump at the end. Add a break every 75 minutes; this is a working rule of thumb, not a researched threshold, and a break is also the moment when slow pairs catch up.

### 3. Write each segment as a card

Every segment gets a card with: the task, the expected time for a typical pair, and the time a slow pair needs (1.5 times the expected time). Plan the schedule so a slow pair still finishes the core of the block inside the allotted time. Add a tiered stretch task for fast finishers, in two or three steps of increasing difficulty, so they stay busy without asking for the next step. Read `references/segment-card-and-schedule.md` for the card layout and a worked schedule.

For the exercises themselves, including hints and checks, use `exercise-design`.

### 4. Set the room and the staffing

Cap the group at 25 participants. Beyond that, helpers cannot reach a stuck person before the rest have moved on. Provide one helper per eight participants, and brief them: what the common stalls are, what to hint and what to leave alone, and how to signal that a pair is stuck. Arrange pairs rather than singles where the task allows; a pair debugs aloud and the weaker setup is shared.

For an online workshop, add a chat channel monitored by a helper, breakout rooms for pairs, and a rule for screen sharing when someone needs help.

### 5. Send pre-work a week early, with a check

Pre-work installs and configures everything the day needs: tools, accounts, access, a repository clone. End it with one verification command whose output the participant compares with the stated expected output, and ask them to reply if it differs. A week gives time to resolve account and permission problems, which are the ones that take days. Chase non-replies two days before. Provide a fallback environment, such as a hosted workspace or a prepared virtual machine, for people whose machines cannot be fixed in time.

### 6. Run a full dry run

Find someone from the real audience profile, not a colleague who knows the topic, and have them do the whole workshop on a clean machine, following only the pre-work and the cards. Time each segment. The output is a stall list: every place they stopped, guessed or asked. Fix the cause of each stall in the materials, then re-run the affected segments. Update the slow-pair times from what you observed.

### 7. Run it and close it

Open with the three outcomes and the closing checks so participants know what done looks like. During the day, keep a running list of stalls and questions. At the end, collect how many participants passed each closing check; that count, not a satisfaction score, says whether the workshop worked. Publish the materials and the solution so people can finish later.

## Hand back

The outcomes with their closing checks, the audience profile, the timed schedule with segment cards and buffer, the pre-work with its verification command, the staffing plan, the dry-run stall list with fixes, and the fallback environment. Report the hands-on percentage and the buffer percentage as computed, not as intended.

## Anti-patterns

- **Sizing to the instructor.** Your speed is a lower bound. Use the slow-pair time.
- **Slides first.** Start from the tasks and add explanation only where a task cannot be done without it.
- **Setup in the room.** Installing during the session spends the first hour and loses the quickest participants.
- **No closing check.** Without one, "it went well" is a feeling.
- **Dry run with a friend who knows the topic.** They fill gaps without noticing. Use someone from the audience.

## Reference files

- `references/segment-card-and-schedule.md` - read at steps 2 and 3: the segment card layout, a worked half-day schedule with the percentages worked out, the pre-work checklist and the dry-run stall log.
