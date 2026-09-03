# Leaked credential response

Read this the moment a credential is believed exposed. It covers the revocation-first
timeline, invalidating sessions that outlive the credential, the queries that scope the
exposure window, the persistence hunt, and what rewriting git history actually achieves.

This is containment and investigation procedure. Nothing here is a technique for using a
credential you were not issued.

## Contents

- [The first fifteen minutes](#the-first-fifteen-minutes)
- [Revocation, and why disable beats delete](#revocation-and-why-disable-beats-delete)
- [Sessions outlive the credential](#sessions-outlive-the-credential)
- [Scoping the exposure window](#scoping-the-exposure-window)
- [Hunting for persistence](#hunting-for-persistence)
- [What git history rewriting does and does not do](#what-git-history-rewriting-does-and-does-not-do)
- [Notification](#notification)
- [Closing it out](#closing-it-out)

## The first fifteen minutes

In order. The ordering is the content — every later step is cheaper once the credential is
dead.

1. **Revoke or disable the credential.** Do not wait for confirmation that it was real, for
   the owner to reply, or for a change ticket. A credential disabled in error costs one
   re-enable command.
2. **Invalidate derived sessions**, if the provider mints them from the credential.
3. **Note the exposure window's start** — the commit's author date, the message timestamp,
   the log line. You will need it in step 5 and it becomes harder to establish later.
4. **Open an incident channel and name a lead.** A leak handled in a thread with four
   people and no lead produces three partial investigations.
5. **Scope from audit logs.** Now, with the credential already dead, take the time to do it
   properly.
6. **Rotate**, rejoining the planned path in `SKILL.md` at step 2.
7. **Hunt for persistence**, then write it up.

The temptation is to reorder 1 and 5 — "let me check whether it was actually used before I
break production". Resist it. Scoping takes an hour and the credential works for all of it.

## Revocation, and why disable beats delete

Disable where the provider supports it. A disabled credential still exists as an
identifier, which keeps audit-log correlation straightforward and leaves a path back if you
disabled the wrong one. Delete after the investigation, on the planned path's schedule.

Where there is no disabled state — an Azure client secret, a GitHub PAT, most SaaS keys —
revocation is deletion, so record the credential's identifier before you remove it. You
will need it to search the logs afterwards.

If the exposed value is a private key rather than a token, revocation is at the layer that
trusts the key: delete the public key from the authorised set, revoke the certificate, or
remove the key from the app registration. Rotating the certificate without revoking the old
one leaves the leaked key working.

## Sessions outlive the credential

A long-lived credential is often exchanged for a short-lived session, and killing the
credential does not kill sessions already issued. On AWS, an access key that has been used
to assume a role can hold a session for up to that role's maximum duration.

The documented containment is a deny policy conditioned on the token issue time, attached
to the role or user, which invalidates every session minted before the cut-off while
leaving new, legitimate sessions unaffected:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Action": "*",
    "Resource": "*",
    "Condition": {"DateLessThan": {"aws:TokenIssueTime": "2026-09-03T11:00:00Z"}}
  }]
}
```

Attach it, confirm the effect, and remove it once rotation is complete — an inline deny
policy left behind becomes a mystery outage months later. The equivalent elsewhere: revoke
refresh tokens and sign out all sessions for an identity provider account, revoke OAuth
grants for an application, and restart anything caching a session on your side.

## Scoping the exposure window

Answer four questions in writing. Vague answers here are what turn a contained leak into a
second incident.

- **What did this identity do?** Every action, not only the interesting ones.
- **From where?** Source IPs and user agents, compared against the consumer inventory.
- **Between when and when?** Earliest possible disclosure to revocation.
- **Was any of it unusual for this identity?** A service account that reads one bucket
  every hour and suddenly lists every bucket in the account is the signal; the baseline is
  what makes it visible.

```bash
# AWS — everything this key did, then the same window by source IP
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=AccessKeyId,AttributeValue=EXAMPLE_KEY_ID \
  --start-time 2026-08-01 --end-time 2026-09-03 --max-results 500

# GCP — every call made as the principal, including caller IP
gcloud logging read \
  'protoPayload.authenticationInfo.principalEmail="svc-orders@PROJECT.iam.gserviceaccount.com"
   AND timestamp>="2026-08-01T00:00:00Z"' --format=json

# GitHub — organisation audit log for the actor or the token
gh api /orgs/ORG/audit-log --paginate -X GET -f phrase='actor:EXAMPLE_ACTOR created:2026-08-01..2026-09-03'
```

Two caveats worth stating in the write-up. Data-plane reads are often not logged by default
— S3 object-level and GCS data-access logging are opt-in — so "no evidence of data access"
frequently means "no logging of data access", and those are different sentences. And log
retention may be shorter than the exposure window, in which case say so rather than
implying the earlier period was clean.

If the identity is one whose activity you cannot distinguish from an attacker's, that is
itself the finding: the credential was too broadly scoped, and narrowing it is the
follow-up action.

## Hunting for persistence

Revocation removes the foothold. It does not remove what was built while the credential
worked. Work through the list for the provider in question, bounded by the exposure window.

**Cloud account (AWS, GCP, Azure)**

- New IAM users, roles, service accounts or access keys — especially ones created outside
  your normal tooling or IaC.
- Changed role trust policies or added external principals, including cross-account trust.
- New or changed identity federation and SSO configuration.
- Resource policies opened to the public or to unknown accounts: buckets, snapshots,
  images, queues, container registries.
- New inbound security-group or firewall rules, new VPC peering, new NAT or egress paths.
- Compute in regions you do not use, which is the classic cryptomining tell, and any
  serverless function or scheduled task you did not create.
- Disabled or reconfigured logging: a deleted trail, a paused log sink, an altered
  retention setting. This is the highest-signal item on the list.
- Changed billing contacts, notification addresses, or support-plan details.

**Source control and CI**

- New deploy keys, SSH keys, PATs, or authorised OAuth apps and GitHub Apps.
- New or modified workflow files, self-hosted runners, and repository or organisation
  secrets.
- Changed branch protection or required reviewers.
- Forks and clones of private repositories inside the window.

**Identity and email**

- New mail forwarding rules and filters, which are the most common quiet persistence.
- New MFA devices or recovery methods on any affected account.
- New API tokens issued for the identity in downstream SaaS products.

Anything on this list found inside the exposure window is treated as attacker activity
until proven otherwise, and proving otherwise means finding the change request or the
person who made it — not the absence of anything alarming.

## What git history rewriting does and does not do

State this plainly to whoever asks whether the force-push fixed it.

- The value is public from the moment the push completed. Public push events are streamed
  through the platform's events API and consumed by automated collectors continuously.
  Observed time-to-first-use for a leaked cloud key is measured in minutes.
- A force-push does not delete the object. It remains reachable through forks, cached
  views, pull-request refs, and any clone taken before the rewrite.
- Deleting the repository does not delete forks.
- Rewriting shared history is disruptive to everyone who has cloned it, so the cost is
  real and paid by the whole team.

Rewriting history is worthwhile hygiene *after* revocation — it stops the value being
re-copied out of the repository by legitimate users, and it clears the scanner findings
that would otherwise mask the next real one. It is never containment.

The same logic applies to deleting a chat message, redacting a ticket, or removing a CI
log: it reduces future casual exposure and does nothing about the exposure that already
happened.

## Notification

- **The credential's owner and your security contact**, immediately, with the identifier
  and the exposure window.
- **The provider.** Most cloud and SaaS vendors have a compromised-credential process, and
  several will reverse fraudulent charges when told promptly. Some detect the leak before
  you do and will apply a quarantine policy to the account — expect that and plan around
  it rather than being surprised by it.
- **Legal and privacy**, if any data the identity could reach was customer or personal
  data. Statutory notification clocks start at discovery, not at the end of your
  investigation, so bring them in during scoping.
- **Customers**, on legal's decision and with their wording, not yours.

Do not include the credential value in any of these messages. Reference it by identifier.

## Closing it out

Write the postmortem with the `postmortem` skill, blameless in the usual way. The
productive questions are structural rather than personal:

- Why did a long-lived static credential exist for this workload at all, and what would
  federation or a dynamic credential have cost instead?
- Why was the blast radius as wide as it was — could the identity have been scoped to the
  one bucket, the one table, the one repository?
- What detected it: a provider scanner, a CI check, a pre-commit hook, or a human? If the
  answer is a third party, the follow-up is detection, not training.
- Would the same leak have been caught before the push, and if not, what control is
  missing?
- How long did revocation take from discovery, and what slowed it down? Approval steps in
  front of revocation are a defect worth fixing while the incident is fresh.

The action items that matter are the ones that delete the credential class, not the ones
that ask people to be more careful.
