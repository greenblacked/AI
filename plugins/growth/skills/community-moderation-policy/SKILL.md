---
name: community-moderation-policy
description: "Write and operate moderation rules for a forum, chat server or discussions space: short written rules, an enforcement ladder (note, warning, timed mute, removal, ban) that names which behaviours skip steps, a moderation log citing the rule for every action, response targets and an on-call rota, automation for the repetitive layer (new-account limits, link filters, raid mode), an appeal route reviewed by a different moderator, and a quarterly transparency summary. Use whenever someone says \"people are fighting in our Discord\", \"write community guidelines\", \"how do we handle a troll\", \"ban appeal process\" or \"spam wave in our forum\". Not for outage messaging (incident-comms), one-to-one conflict (difficult-conversation), live service operations (game-live-ops), whether the community works (community-health-review) or security reports (vulnerability-disclosure)."
allowed-tools: Read, Grep, Glob
---

# Community Moderation Policy

Done means the rules fit on one page, every moderator can act from a written ladder rather than their mood, each action lands in a log with the rule it cites, and there is a route for the person on the receiving end to be heard by someone else.

The usual failure is moderation by mood: the same behaviour earns a ban from one volunteer and a shrug from another, nobody can say why, and the loudest member learns that complaining works. The second failure is burnout, where one or two people carry every report and quietly leave. A ladder, a log and a rota address both.

## Scope

Use for: drafting community guidelines, building or repairing an enforcement process, handling a repeat offender or a spam or raid wave, setting up appeals.

Do not use for: messaging an outage (`incident-comms`), a private conversation with one person (`difficult-conversation`), running a live game service (`game-live-ops`), judging whether the community is healthy at all (`community-health-review`) or receiving vulnerability reports (`vulnerability-disclosure`).

## Hard gates

1. Every action cites a numbered rule. If no rule fits, write the rule afterwards; do not act on an unwritten one.
2. Every action is written to the moderation log at the time it is taken.
3. No moderator reviews an appeal against their own action.
4. Legal, safety and threat reports leave the community's normal queue and go to the separate escalation path in step 6.

## Workflow

### 1. Find out what exists

Read the current guidelines, pinned messages, bot configuration and any past moderation decisions. List the five to ten incidents that caused the most argument in the last quarter. The rules should answer those, not an imagined worst case. If there is no history, ask what the founders are afraid of.

### 2. Write short rules

Aim for under ten rules, each one sentence of behaviour and one of reason. Describe conduct, not opinion: "do not post other people's private information" is enforceable, "be nice" is not. State the scope (public channels, direct messages between members, off-platform conduct that targets members) and who may act. Use `references/templates.md` for the rule, ladder and log formats.

### 3. Build the enforcement ladder

Steps in order: a private note, a public or private warning, a timed mute, removal of content or the member from a space, a ban. Moderators start at the lowest step that fits. Name the behaviours that skip steps, typically doxxing, credible threats, sexual content involving minors, targeted harassment campaigns and malicious links; those go straight to removal and, where required, escalation. State how long warnings count: a warning that expires after a stated period lets people recover; one that never expires makes every future slip a ban.

### 4. Keep a moderation log

One row per action: date, moderator, member, rule number, step on the ladder, evidence link or quoted text, outcome. The log is how a second moderator sees a pattern, how an appeal is reviewed, and how the quarterly summary is produced. Restrict it to moderators and keep personal data in it to the minimum needed.

### 5. Set response targets and a rota

Targets worth writing down: reports acknowledged within a day, reports describing severe harm looked at within an hour. These are targets for a staffed rota, not promises a lone volunteer can keep, so only publish what the rota can cover. Rotate on-call by shift with a named backup, give each moderator a way to hand off a case they find distressing, and agree that nobody is expected to be reachable outside their shift.

### 6. Separate the escalation path

Legal requests, safety concerns, self-harm, credible threats and reports involving minors do not get decided by volunteers in a public thread. Write down who receives them (an owner, an employee, counsel or the platform's trust and safety contact), how a moderator reaches them, and what the moderator does meanwhile: preserve the evidence, remove the content if the platform allows, say nothing publicly. The exception is suspected child sexual abuse material: do not copy, screenshot or forward it. Record only the message ID or link and the time, report it through the platform's trust and safety channel and to the escalation owner (who reports to NCMEC or IWF as applicable), and remove it where the platform allows. Add a line saying this is community procedure, not legal advice; the people on the path decide what the law requires.

### 7. Automate the repetitive layer

Automation takes the volume so people take the judgement. Typical controls: limits on new accounts (no links or attachments for a short period, slow mode), a link and invite filter, keyword filters that hold messages for review instead of deleting them, and a raid mode that locks sending for new members and is switched off by a human. Check the platform's own tools first (Discord AutoMod and verification levels, Discourse trust levels and watched words, and on Slack the admin controls over who may post and join) before adding a bot. Log automated actions too, and review false positives monthly; a filter nobody audits becomes an unwritten rule.

### 8. Define the appeal route

Anyone with a mute, removal or ban can appeal once, through a stated channel, within a stated period. A different moderator, or a small panel, reads the log entry and the evidence, decides, and replies with the outcome and the rule. Say what is not appealable (for example, bans for behaviours that skip the ladder), and say so before the first case.

### 9. Publish a quarterly transparency summary

Counts by rule and ladder step, median time to acknowledge a report, appeals received and overturned, and automation actions. No names, no screenshots. The overturn rate is the figure to watch: a high rate means the rules or the training are unclear.

## Hand back

The rules, the ladder with skip behaviours, the log format, the response targets and rota, the escalation contact list, the automation settings and the appeal route. Say which of these the team has not yet staffed.

## Anti-patterns

**Rules written to win the last argument.** A rule aimed at one person is read by everyone else as arbitrary.

**Public shaming as a step.** It escalates the dispute and teaches nobody; warn privately unless the content itself must be corrected.

**A ladder with no skips.** It obliges moderators to tolerate a threat until the third warning.

**Appeals handled by the original moderator.** The review becomes a defence of the first decision.

**Targets nobody staffs.** A published one-hour response with one volunteer is a promise that will be broken in public.
