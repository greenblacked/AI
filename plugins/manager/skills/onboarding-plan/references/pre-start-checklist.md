# Pre-Start Checklist

Read this when a start date is confirmed. The point of working backwards from the date is
that several of these have a lead time measured in days or weeks, and every one that is
late is spent by the new person waiting rather than working.

An item counts as done when someone has confirmed it works, not when it has been
requested. "Raised a ticket for it" is the state that produces a first week of waiting,
because the ticket queue does not know the start date.

## Owners

Name a person against every line. An item owned by a team is owned by nobody, and the
gaps only become visible on day one, when they are expensive.

| Area | Typical owner |
| --- | --- |
| Accounts, identity, group membership | IT or whoever administers the identity provider |
| Repository, cloud and data access | The team's own engineers, via whatever grants access |
| Hardware and toolchain | IT, with the team verifying the toolchain specifically |
| Buddy, first task, calendar, context | The hiring manager, and nobody else |

## Access

Work out the full list from what the role does in its first month, not from copying
whoever left most recently. A cloned permission set is how standing production access
spreads silently through a team; `access-review` covers the review that eventually has to
undo it.

- [ ] Identity account created and the person can sign in.
- [ ] Group and role membership set to what the first month needs.
- [ ] Source control: the specific repositories, at the level required to open a pull
      request and be reviewed.
- [ ] CI: can see runs, can re-run a failed job.
- [ ] Cloud or platform console: read access to the environments they will debug in.
- [ ] Production: deliberately deferred by default, granted when there is a reason.
      Write down what that reason will be rather than granting it now for convenience.
- [ ] Observability: dashboards, logs, traces, error tracking.
- [ ] Incident tooling: the paging system, at a level that can see incidents before they
      are on the rotation.
- [ ] Ticket tracker, documentation and wiki, design tooling.
- [ ] Chat, with the team channels pre-joined rather than left to discovery.
- [ ] Any vendor or third-party console the team uses daily.
- [ ] Secrets and credential store, scoped to what they need in week one.

For each grant, record who approved it and why. That record is what makes the first
access review cheap rather than archaeological.

## Hardware and environment

- [ ] Machine ordered with enough lead time to arrive, be imaged, and be tested.
- [ ] Shipping address confirmed with the person, for remote joiners, and a tracked
      delivery date that precedes the start date by several days.
- [ ] Peripherals, and whatever the local policy is on a desk setup.
- [ ] The setup script or documented setup path run end to end on a clean machine, by a
      colleague, this quarter. If nobody has run it since the last toolchain change, it
      does not work and you do not yet know how.
- [ ] The build passes and the test suite runs on that clean machine, with the time it
      took recorded. A forty-minute first build is fine if it is expected and surprising
      if it is not.
- [ ] Local development against a real dependency: whatever staging, fixtures or seeded
      data is needed to run the thing rather than only compile it.

## People and plan

- [ ] Buddy asked, confirmed, and briefed on what the role is — daily availability in
      week one, questions of any size, nothing reported upwards.
- [ ] The buddy's other commitments reduced for two weeks, in writing, with whoever
      depends on them told.
- [ ] First task chosen: small, real, all the way through to deploy, and left unassigned
      so nobody else picks it up.
- [ ] A second and third task identified, so week two does not start with a search.
- [ ] Calendar for week one: pairing blocks, system walkthroughs, the team's standing
      meetings, the manager one-to-one, and the introduction calls.
- [ ] Introduction calls booked with each person they will work with, each with a stated
      reason for the meeting rather than a bare invitation.
- [ ] Ownership list written down: which system, who owns it, who to ask when that person
      is away.
- [ ] 30/60/90 expectations drafted, ready to share and discuss in week one.

## Announcement and arrival

- [ ] The team told who is joining, when, what they will work on, and who the buddy is.
- [ ] The wider group that will encounter them told, at least in the channel.
- [ ] Day one has a written shape and someone is visibly free for it. A first day where
      the manager is in back-to-back meetings is a first day spent alone.
- [ ] The first thing on day one is a person, not a form.

## Verification pass, the day before

Go down the list and check the state rather than the intent. The three that reliably fail
quietly:

1. An access grant that was requested and approved but applies to the wrong group.
2. A setup path that works on machines that already have an older toolchain installed and
   fails on a clean one.
3. A buddy who agreed three weeks ago and has since been pulled onto an incident.

Anything unresolved at this point gets a plan for the first week that does not depend on
it, and the person is told what is missing and when it will land. Being told is a
different experience from discovering it.
