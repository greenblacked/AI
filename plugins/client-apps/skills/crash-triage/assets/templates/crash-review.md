# Crash review: <app> <version>

<!-- One per release. Copy, fill in, and delete the guidance comments. -->

## Metric

Which rate moved (crash-free users or sessions), the source (Crashlytics, Sentry,
Organizer, MetricKit, Play vitals), versions and date range.

## Symbolication

Status per platform: iOS dSYM UUIDs matched, Android R8 mapping.txt for the version code,
native symbols. Any missing upload and the CI step that fixes it for the next build.

## Ranked signatures

| Signature | Affected users | Share of version's users | New or regressed in | Concentrated in (version, OS, device) |
| --- | --- | --- | --- | --- |

## Top signature

Exception, reason, first frame in our code, the split that located it, the cause.

## Fix and expected effect

The change, the cohort it should improve, and the expected number.

## Verification

New version against the previous one at the same days since release, with the number of
users reached when measured.
