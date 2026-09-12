# Scoring Signals and How to Combine Them

The detail behind step 3 and the action table in step 5 of `SKILL.md`. Read before ranking a queue, before setting an internal SLA, or before arguing with someone about whether a 9.8 is really a 9.8.

The single idea: **a severity score describes the vulnerability; only you can describe your exposure.** Every signal below is either a property of the flaw, a property of the world's attackers, or a property of your deployment, and confusing the three is what makes a queue unworkable.

## Contents

- [The four families of signal](#the-four-families-of-signal)
- [CVSS: base, threat and environmental](#cvss-base-threat-and-environmental)
- [EPSS](#epss)
- [CISA KEV](#cisa-kev)
- [Identifiers: CVE, GHSA, OSV, GO and MAL](#identifiers-cve-ghsa-osv-go-and-mal)
- [Why two scanners give you two severities](#why-two-scanners-give-you-two-severities)
- [Combining them into an order](#combining-them-into-an-order)
- [Worked examples](#worked-examples)
- [Setting an internal SLA](#setting-an-internal-sla)

## The four families of signal

| Family | Example | Describes | Changes when |
| --- | --- | --- | --- |
| Severity | CVSS base score | The flaw under assumed-worst conditions | Essentially never, after publication |
| Threat activity | EPSS, CISA KEV | What attackers are doing in the world | Daily |
| Exposure | Reachability, network position, data sensitivity | Your deployment | When your code or config changes |
| Fixability | Patched version available, size of the bump | The cost of acting | When upstream releases |

A queue sorted on the first family alone is sorted by a number that is identical for every organisation on earth. That is the defect at the root of most unread alert backlogs.

## CVSS: base, threat and environmental

CVSS defines metric groups, and the score almost everyone quotes is only the first of them.

**Base metrics** capture the intrinsic characteristics of the vulnerability: attack vector, attack complexity, privileges required, user interaction, scope or the v4.0 equivalents, and the impact metrics. They are constant over time and across environments, and they are deliberately scored as though the affected component were deployed in the worst reasonable configuration. This is the number NVD publishes and the number that appears in your alert.

**Threat metrics** (CVSS v4.0; called Temporal metrics in v3.1) adjust for the maturity of exploitation — whether proof-of-concept or weaponised exploit code is known to exist. Few sources populate these consistently, which is part of why EPSS filled the gap.

**Environmental metrics** are where your deployment enters. Two mechanisms:

- *Modified base metrics*: restate any base metric as it actually applies to you. A vulnerability scored network-accessible is `Modified Attack Vector: Adjacent` or `Local` if the component is only reachable from inside a private network — often a two-point swing.
- *Security requirements* (`CR`, `IR`, `AR`): declare how much confidentiality, integrity and availability matter for this asset, scaling the corresponding impact metrics. A service holding no personal data legitimately scores lower on confidentiality impact.

The practical points to carry:

1. **Nobody computes your environmental score for you.** NVD publishes base only. Every vendor dashboard showing "critical" is showing a base score, which is why the queue looks uniformly alarming.
2. **The environmental score is the one that should drive your decision**, and computing it by hand for every alert is not realistic. Reachability plus the scope split in `SKILL.md` step 2 is the cheap approximation: it captures the same information as a modified attack vector and modified privileges-required without the calculator.
3. **Compute it explicitly for the small number of alerts that matter** — anything you are considering treating as an interrupt, and anything where you are about to argue for an exception. Recording "base 9.8, environmental 5.4 because the component is not internet-reachable and holds no customer data" is what makes an exception reviewable later.
4. **Version matters.** A v3.1 score and a v4.0 score for the same flaw are not comparable; v4.0 changed the metric set and the formula. Record which version a number came from.

## EPSS

The Exploit Prediction Scoring System, published by FIRST, gives each CVE a **probability between 0 and 1 that it will be exploited in the wild in the next thirty days**, and the **percentile** of that probability against all scored CVEs. Scores are regenerated daily from observed exploitation telemetry and vulnerability metadata.

```bash
curl -s 'https://api.first.org/data/v1/epss?cve=CVE-2021-44228' \
  | jq -r '.data[] | [.cve, .epss, .percentile, .date] | @tsv'

# several at once
curl -s 'https://api.first.org/data/v1/epss?cve=CVE-2024-3094,CVE-2023-44487' \
  | jq -r '.data[] | [.cve, .epss, .percentile] | @tsv'
```

How to read it:

- **It is a forecast of attacker activity, not a measure of severity and not a measure of impact on you.** A 0.97 EPSS on a vulnerability in a component you do not deploy is still not your problem.
- **The distribution is extremely skewed.** The large majority of CVEs sit far below one percent. That is what makes the signal useful: a small set of outliers carries most of the observed exploitation.
- **Use the percentile for ranking and the probability for a threshold.** Percentile is stable to compare across a queue; probability is what you can reason about in a sentence ("a one-in-three chance of exploitation activity in the next month").
- **It re-scores daily.** A finding that was quiet in January can move sharply when exploitation starts. Re-joining the open queue against EPSS is one of the cheapest things a weekly cadence does.
- **Do not invert it.** Low EPSS means no observed activity yet, not safety. Vulnerabilities in software with few users — including yours — have little telemetry by construction, and anything not yet scored gets no row at all.

## CISA KEV

The Known Exploited Vulnerabilities catalogue lists vulnerabilities for which CISA has reliable evidence of **active exploitation in the wild**. It is deliberately small — low thousands of entries against hundreds of thousands of published CVEs — and the inclusion criteria are strict, which is what gives it its precision.

```bash
curl -s https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json \
  | jq -r '.vulnerabilities[]
           | [.cveID, .vendorProject, .product, .dateAdded, .dueDate,
              .knownRansomwareCampaignUse] | @tsv' > kev.tsv

# join your open queue against it
gh api --paginate "repos/OWNER/REPO/dependabot/alerts?state=open&per_page=100" \
  --jq '.[].security_advisory.cve_id' \
  | grep -Fxf <(cut -f1 kev.tsv)
```

Fields worth knowing: `dateAdded`, `dueDate` — the remediation deadline BOD 22-01 binds US federal civilian agencies to, and a defensible default for everyone else — `requiredAction`, and `knownRansomwareCampaignUse`, which is the field to escalate on hardest.

Two caveats. KEV is a lagging indicator: entry follows confirmed exploitation, so absence from KEV says nothing about tomorrow. And KEV skews towards internet-facing products and widely deployed software, so a library vulnerability exploited in a narrow campaign may never appear.

## Identifiers: CVE, GHSA, OSV, GO and MAL

Deduplicating a queue requires knowing which identifiers refer to the same thing.

| Prefix | Issued by | Notes |
| --- | --- | --- |
| `CVE-YYYY-NNNNN` | MITRE and its CNAs | The lingua franca. Some ecosystem advisories never get one |
| `GHSA-xxxx-xxxx-xxxx` | GitHub Security Advisory database | What Dependabot reports. Carries a `cve_id` when one exists, and its own severity |
| `OSV` records | OSV.dev, aggregating many sources | The one with precise affected-version ranges per ecosystem, which is what a scanner actually needs |
| `GO-YYYY-NNNN` | Go vulnerability database | What `govulncheck` matches on; maps to CVE and GHSA where they exist |
| `RUSTSEC-YYYY-NNNN` | RustSec advisory database | What `cargo audit` matches on |
| `PYSEC-YYYY-NNN` | Python packaging advisory database | Surfaced through `pip-audit` and OSV |
| `MAL-YYYY-NNNN` | OpenSSF malicious-packages, via OSV | **Not a vulnerability.** A package that is malicious. Different response entirely — `SKILL.md` step 9 |

Key the queue on the CVE where one exists and on the ecosystem identifier where it does not. GHSA records carry their aliases, so `.security_advisory.cve_id` from the Dependabot API is usually enough to deduplicate across tools.

## Why two scanners give you two severities

This causes more wasted argument than any other part of triage, and the explanation is short.

- **NVD publishes a base score assigned by NVD analysts.** It has had well-documented backlogs, so an entry can sit unscored or carry a score that predates a better understanding of the flaw.
- **The numbering authority that issued the CVE — often the vendor — may publish its own base score**, and it frequently differs from NVD's, sometimes substantially. Neither is authoritative in a way that settles the argument.
- **GitHub assigns its own severity to a GHSA**, informed by the CVSS vector but expressed as low/moderate/high/critical, and it is scoped to the ecosystem package rather than the upstream product.
- **Affected version ranges differ too**, which matters more than the severity: OSV records are usually the most precise per ecosystem, and a scanner using a coarser range produces false positives that look exactly like real findings.

The resolution is not to pick a winner. Record which source produced the number, and when the sources disagree materially, read the advisory text and decide — the disagreement itself is usually a signal that the flaw's preconditions are unusual, which is useful information for the reachability question.

## Combining them into an order

The ordering that actually survives a weekly session. Apply top to bottom and stop at the first row that matches.

| # | Condition | Treatment |
| --- | --- | --- |
| 1 | In KEV, package deployed | Today. Interrupt-driven, with a named owner |
| 2 | `MAL-` identifier, or otherwise malicious | Incident, not triage. `SKILL.md` step 9, and start credential rotation in parallel |
| 3 | Reachable, runtime, EPSS percentile high or CVSS critical with a fix | This week, as its own change |
| 4 | Reachable, runtime, fix available | Next batch |
| 5 | Reachable, no fix available | Compensating control plus a dated exception |
| 6 | Not reachable, runtime | Batch. No exception needed when a fix exists and you take it |
| 7 | Build-only, runs in CI with credentials | Treat as row 3 or 4 by the same tests |
| 8 | Build-only, developer machines only | Batch |
| 9 | Not reachable, no fix available | Dated exception with the reachability sentence as its reason |

Note what is missing: a row that says "critical, therefore urgent". Severity enters only in row 3, as a tiebreaker among things already established as reachable. That is the whole point.

## Worked examples

**A 9.8 nobody should drop everything for.** A critical deserialisation flaw in a transitive library, reachable only through an XML parsing entry point your service does not expose; `govulncheck` reports the module present with no affected symbol called; EPSS 0.002 at the 35th percentile; not in KEV; a patched version exists. Rows 1 through 5 do not match; row 6 does. It goes into the weekly batch with the other patch bumps and takes about four minutes of anyone's attention.

**A 5.3 that is this morning's work.** A medium-severity request-smuggling flaw in your HTTP proxy library, on the path that handles every inbound request, added to KEV last week with a due date fourteen days out and `knownRansomwareCampaignUse` true. Row 1. The base score never entered the decision.

**No fix available.** A high-severity flaw in an unmaintained library, reachable, no patched version and no active upstream. Row 5: put input validation in front of the vulnerable call, record the control, open an issue to replace the library, and set an exception with a ninety-day review. The exception is the honest artefact here — pretending the alert is closed is what the next auditor will find.

**A dev dependency that is not one.** A code-execution flaw in a test reporter that runs on a self-hosted runner holding a registry publish token. It never reaches production, and it is row 7 treated as row 3, because the credential the runner holds is more valuable than the service the flaw could reach.

## Setting an internal SLA

If you write down deadlines, write them against the combined order rather than against severity, or you will have an SLA that is unmeetable and ignored within two quarters.

| Class | Target | Why |
| --- | --- | --- |
| KEV, deployed | 72 hours, or the KEV `dueDate` if sooner | Confirmed exploitation; the window is not yours to choose |
| Malicious package | Same day, containment first | Code has already run |
| Reachable, runtime, fix available | 14 days | Long enough to batch and test, short enough to stay true |
| Not reachable, fix available | Next scheduled sweep | Cost of acting is near zero, so the deadline can be lax |
| No fix available | Control in place within 14 days, review every 90 | The deadline is on the control, not on a version bump |

A target that is missed every month is worse than no target, because it trains everyone to read the report as decoration. Set the deadlines you can actually hit, measure the exception count rather than the alert count, and revisit the numbers once you have a quarter of real data.
