# Verification and retirement

Read this at steps 6 and 7: how to show the federated path is the one in use, how to show
an unlisted caller is refused, and how to retire the static keys without an outage.

## Contents

- [Positive evidence](#positive-evidence)
- [Negative tests](#negative-tests)
- [Retiring the keys](#retiring-the-keys)
- [Stopping new keys](#stopping-new-keys)

## Positive evidence

Prove it from the provider's audit log, not from the workload's success: a workload that
still holds the old key also succeeds.

| Platform | Event or field |
| --- | --- |
| AWS, IRSA or GitHub OIDC | CloudTrail `AssumeRoleWithWebIdentity` for the role; the event's `userIdentity` block records the identity provider and the token's subject |
| AWS, EKS Pod Identity | CloudTrail `AssumeRoleForPodIdentity` from the EKS Auth service |
| Google Cloud | Data access or admin activity logs, `protoPayload.authenticationInfo.principalSubject` showing the federated principal |
| Azure | Microsoft Entra sign-in logs for the managed identity or service principal |

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRoleWithWebIdentity \
  --start-time "$START" --query 'Events[].CloudTrailEvent' --output json \
  | jq -r --arg role "$ROLE_ARN" '.[] | fromjson
      | select(.requestParameters.roleArn == $role)
      | [.eventTime, (.userIdentity.userName // .userIdentity.principalId),
         .requestParameters.roleArn] | @tsv'
aws iam get-access-key-last-used --access-key-id "$OLD_KEY_ID"
```

`--output text` would join every event onto one line and break the parse, and the `select`
keeps other roles' assumptions out of the evidence. An empty result is not proof: check the
window and the region, then count the events before the `select`.

The two halves together are the evidence: federated assumptions arriving for the
expected subject, and the old key's last-used timestamp no longer advancing.

## Negative tests

Run one per identity, from something deliberately not on its list, and record the
refusal. Each test must fail on the trust condition, not on something incidental such as
a missing permission in the test job.

| Platform | Test | Expected refusal |
| --- | --- | --- |
| GitHub into AWS | A throwaway workflow in another repository of the organisation, and one on an unpinned branch of the same repository, each trying to assume the role | `Not authorized to perform sts:AssumeRoleWithWebIdentity` |
| GitHub into Google Cloud | The same two workflows authenticating through the provider | Token exchange rejected by the attribute condition, or permission denied on the resource |
| GitHub into Azure | The same two workflows logging in with the app's client id | `AADSTS70021`: no matching federated identity record |
| IRSA | A pod in the same namespace under a different service account, annotated with the same role ARN | `AccessDenied` on `AssumeRoleWithWebIdentity` |
| EKS Pod Identity | A pod under a service account with no association | No credentials offered; calls fall through to the node role, which should itself be denied the resource |
| GKE | A pod under a different service account calling the resource | 403 from the resource |
| AKS | A pod under a different service account annotated with the same client id | `AADSTS70021` |

The IRSA and AKS tests matter most because they show the annotation is not the control:
anyone with rights to create a service account can write the annotation, and only the
trust condition refuses them. Delete the test workflows and service accounts afterwards.

## Retiring the keys

Disable, wait, then delete. Disabling is reversible in seconds when an undocumented
consumer appears; deletion is not. Azure is the exception: an app registration's client
secrets and certificates cannot be disabled, only deleted, so the Azure step below is
irreversible and has no wait-and-watch stage of its own.

```bash
aws iam update-access-key --user-name "$IAM_USER" --access-key-id "$OLD_KEY_ID" --status Inactive
gcloud iam service-accounts keys disable "$KEY_ID" --iam-account="$SA_EMAIL"
```

Wait past the provider's last-used reporting lag and through at least one full cycle of
the slowest scheduled consumer, watching for authentication failures from anything still
holding the key. For Azure, first confirm there have been no sign-ins with the secret or
certificate over that same window, using the Microsoft Entra sign-in logs for the service
principal that the positive-evidence table names. Any sign-in means a consumer still
depends on it; stop and find it, because the delete cannot be undone. Then:

```bash
aws iam delete-access-key --user-name "$IAM_USER" --access-key-id "$OLD_KEY_ID"
gcloud iam service-accounts keys delete "$KEY_ID" --iam-account="$SA_EMAIL"
az ad app credential delete --id "$APP_ID" --key-id "$CREDENTIAL_KEY_ID"
```

Delete the CI secrets that held the values in the same change, at repository,
environment and organisation level. An IAM user that existed only to hold the key is
deleted too, so it cannot be issued a new one.

## Stopping new keys

Without a preventive control, the next team under deadline creates a key again.

- **AWS:** a service control policy that denies `iam:CreateAccessKey` in the accounts in
  scope, with named exceptions:

  ```json
  {
    "Effect": "Deny",
    "Action": "iam:CreateAccessKey",
    "Resource": "*",
    "Condition": {"ArnNotLike": {"aws:PrincipalArn": "arn:aws:iam::*:role/break-glass-admin"}}
  }
  ```

- **Google Cloud:** enforce the organisation policy constraint
  `iam.disableServiceAccountKeyCreation` on the organisation or folder, with exceptions
  set on specific projects.
- **Azure:** restrict who may add client secrets to app registrations, and prefer managed
  identities, which have no secret to add.

List each exception with an owner and a reason, and review the list with the next
access review rather than letting it grow quietly.
