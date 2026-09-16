---
name: data-privacy
description: "Handle personal data so the obligations are met before anyone tests them — settle whether you are controller or processor and under which regime first, because that decides whom you tell and on what trigger; classify what is held and why, because retention, access and deletion all follow the class; enforce retention with a job that deletes rather than a document that promises; and make deletion reach the replicas, the search index, the caches and the restore path instead of only the primary row. Use when personal data is being designed into a system, when a retention or deletion policy is being written, when a subject request arrives, or when a breach has to be judged notifiable rather than merely recorded. Not for rotating a leaked credential (secret-rotation), designing authentication (auth-design), reducing IAM permissions (access-review), or reading a DPA, which is contract-reader."
allowed-tools: "Read, Grep, Glob, Write, Edit, Bash(rg:*), Bash(jq:*), Bash(psql:*), Bash(mysql:*)"
---

# Handling personal data

Most privacy defects are not decisions to break a rule. They are a classification nobody
wrote down, a retention policy nobody automated, and a deletion that reached the primary
row and nothing else. The order below exists because each step supplies what the next one
needs, and skipping the first makes every later answer unanswerable.

## This skill states no deadlines

Every duty here runs on a clock set by a regime this skill cannot know: which law binds
you, and whether you are the controller or the processor. Those give different duties,
different triggers and in some cases no fixed figure at all. A processor's obligation is
typically to tell the controller, not the regulator, and carries no hour count of its own.

So no number appears anywhere in this skill or its references. Step 1 establishes who you
are and what binds you, and you take the figure from that authority. A hardcoded deadline
copied from one jurisdiction's controller duty is wrong for most readers, and wrong in the
direction that looks compliant.

## Hard gates

- Do not answer a subject request before verifying identity. Disclosing a person's data to
  someone impersonating them is itself a breach, and it is the most common own-goal here.
- Do not call data anonymous while you hold anything that re-identifies it. If you keep a
  key, a salt or a lookup table, it is pseudonymised, and pseudonymised data is still
  personal data.
- Do not ship a retention policy that only a human enforces. An unautomated policy is a
  statement of intent, and it decays silently.

## Workflow

### 1. Settle role and regime

Write down, in one line each: which law applies, whether you are controller or processor
for this data, and who the counterparty is. If you are a processor, name the controller
you must tell. Every deadline in the rest of this procedure comes from that authority, not
from here.

This is not paperwork. Until it is answered, "who do we notify" and "how long do we have"
have no answer, and the later steps will be built on a guess.

### 2. Classify what is held, and why

For each field: what it is, why it is held, and which class it falls in. The class is what
drives everything downstream — how long it may be kept, who may see it, and what deletion
has to reach. Read [data classes](references/data-classes.md) when you need the taxonomy
and what each class implies.

Two things that defeat classification and need naming explicitly when found:

- **Free-text fields.** A notes column holds whatever a user typed, which over time means
  every class at once. Classify it by the worst thing it can contain, not by its intent.
- **Derived fields.** An inferred attribute can be more sensitive than its inputs. A
  purchase history that implies a health condition inherits that sensitivity.

### 3. Map where it flows

Follow each classified field outward: replicas, the search index, caches, the analytics
warehouse, object storage, third-party processors, and logs. Logs are where personal data
arrives unnoticed, through URLs, error messages and request bodies.

When the material is bulky — a whole-database schema, a table sample, a day of logs, a
dump nobody has opened — hand it to the `pii-reader` subagent instead of reading it here.
It returns the fields, their class and where they flow, and keeps the sample itself out of
this conversation. Reading a large dump inline costs the context the rest of this
procedure needs.

### 4. Set retention per class, and automate it

One period per class, with the reason it is that long. Then build the job that enforces it:

- A dry run that reports what it would delete, runnable against production.
- An audit trail of what it deleted and when, because proving deletion happened is a
  separate requirement from doing it.
- An alert when the job stops running. A retention job that silently stopped looks exactly
  like a retention job with nothing to do, and the gap is only discovered when someone
  asks why a five-year-old record is still there.

### 5. Make deletion reach every surface

Deletion in the primary database is the easy fifth of the work. Walk
[deletion surfaces](references/deletion-surfaces.md) as a checklist and confirm each one.

The restore path is the surface people miss. A backup usually cannot be edited, so a
record erased today returns when that backup is restored tomorrow. The workable answer is
a suppression list the restore consults and re-applies, kept for at least as long as the
oldest backup. An erasure a restore silently undoes is not an erasure, and nobody finds
out until the restore happens.

### 6. Subject requests

Verify identity first, against something you already hold, and never against the data
being requested. Then scope the request: what they asked for, what you hold, and what you
may withhold because it would disclose someone else. Start the clock at receipt, whatever
your own authority says that clock is, and record when it started.

### 7. A breach: capture evidence, then decide

Before anything else, preserve what proves what happened. Logs rotate, sessions expire and
caches clear on their own schedule, which is usually shorter than the time it takes to
decide whether this is reportable. Snapshot what is relevant now and decide later.

Then make one decision explicitly, and write down the reasoning either way: is this
notifiable to your authority, or is it recorded internally and not reported? Both outcomes
need the record. The deadline for the first comes from step 1's authority.

## What people do instead, and why it fails

**Soft-delete as the only delete.** A `deleted_at` column satisfies the product and
nothing else, because the row and its copies are still there. Soft delete is a UX feature.
It is a privacy defect the moment it is also the deletion story.

**Hashing an identifier and calling it anonymous.** Email addresses and phone numbers come
from a small enough space to enumerate, so an unsalted hash of one is reversible by anyone
who wants to. Hashing changes the format, not the identifiability.

**Joining two safe datasets.** Two sets that identify nobody on their own can identify
people together. Check re-identification at the join, not at each table.

**Collecting it because it might be useful.** Every field held is a field to classify,
retain, delete, disclose on request and account for in a breach. The cheapest personal
data to handle is the field you did not collect.

## Output format

Report in this shape, so the next person can act without re-deriving it.

**Role and regime** — which law, controller or processor, who you must tell.

**Inventory** — each field, its class, why it is held, where it flows.

**Retention** — the period per class, the job that enforces it, where its audit trail goes.

**Deletion** — each surface, and how it is reached. Name the ones not yet covered.

**Open questions** — every figure you could not confirm, and the authority that settles it.
