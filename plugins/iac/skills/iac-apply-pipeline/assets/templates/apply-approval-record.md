# Apply approval record

<!-- One record per apply. Leave out secrets and plan values; record identifiers and digests only. -->

## Target

- Trusted repository and commit:
- Root module directory:
- Engine and provider versions:
- Backend and state key, or managed workspace:
- Terraform workspace:
- Account, project and region, one line per provider alias:

## Producing run

- Run identifier and workflow:
- Plan digest:
- Artifact identifier:
- Plan exit code (0, 1 or 2):

## Approval

- Approver:
- Approved at, and expiry:
- What the approval was bound to (digest, not text):

## Consumption-time checks

| Check | Result |
| --- | --- |
| Artifact digest equals the approved digest | |
| Target tuple in the apply job equals the approved tuple | |
| No new plan, input, dependency or lock-file change since approval | |
| No state write since the plan | |
| Approval not expired; state queue held | |

## Apply result

- Result (applied, failed, cancelled, partial):
- Evidence location (sanitized log or run link):
- Follow-up owner if uncertain, and hand-off to `terraform-state`:
