# Escalation paths and weak trust boundaries

Read this when a finding is about what an identity could *become* rather than what it
did. Each pattern below is described so you can find it in your own estate and close it:
what it looks like in a policy, why it is equivalent to holding more privilege than the
policy appears to grant, the condition or guard rail that closes it, and how to surface
it across an account.

This is review material. It deliberately stops at recognition and remediation rather than
providing exploitation steps, and every identifier is a placeholder.

## Contents

- How to think about reachability
- Self-modification of policy
- Passing or assuming a stronger identity
- Minting credentials for a stronger identity
- Compute as a privilege boundary
- Cross-account and third-party trust
- Approval loops and self-review
- Kubernetes-specific paths
- Closing the path

## How to think about reachability

Line-by-line review asks "is this permission needed?" and answers yes to each of a set
that is collectively administrative. The question that finds the real exposure is
different: **starting from this identity, what set of identities can it reach, and what
does the union of those reach?** Model it as a graph — identities are nodes, and a
permission that lets one identity act as, modify, or issue credentials for another is an
edge — and the finding is the path, not any single permission on it.

Treat any identity with a path to a stronger one as already holding the stronger one.
That reframing is what makes the risk arguable with the identity's owner, who will
otherwise defend each permission individually and correctly.

## Self-modification of policy

**Looks like:** permissions to attach, create, put or version policies, or to edit a
role's inline policy, held by an identity that those policies apply to. In AWS terms:
`iam:PutRolePolicy`, `iam:AttachRolePolicy`, `iam:CreatePolicyVersion`,
`iam:SetDefaultPolicyVersion` scoped to `*`. In GCP: `setIamPolicy` on the project or on
its own service account. In Kubernetes: the `escalate` or `bind` verbs on roles.

**Why it matters:** the effective ceiling of that identity is not its current policy but
every policy it could give itself, which is everything. A quarterly review of the policy
text will report it as narrow.

**Closes with:** a permissions boundary or an organisation-level guard rail (service
control policies, or GCP organisation policy) that no policy edit can exceed; scoping the
policy-management permission to a specific path or resource; separating the identity that
manages IAM from the identities that do the work; and an alert on any policy change, which
is low volume and high signal.

## Passing or assuming a stronger identity

**Looks like:** `iam:PassRole` with a wildcard resource, `sts:AssumeRole` allowed against
roles it should not reach, or an unscoped `iam.serviceAccounts.actAs` on GCP.

**Why it matters:** passing a role is how a workload receives an identity, so an unscoped
pass permission is permission to run code as anything the platform will accept. The
policy naming the pass looks administrative-adjacent rather than administrative.

**Closes with:** scoping `PassRole` to specific role ARNs, or to a path prefix reserved
for roles that workload is entitled to run as; adding an `iam:PassedToService` condition
so the role can only be handed to the intended service; and reviewing role trust policies
from the other direction — who may assume this role — rather than only from the caller's
side.

## Minting credentials for a stronger identity

**Looks like:** creating access keys or service-account keys, resetting a user's password
or console access, adding credentials to an application registration, creating a token
for a service account.

**Why it matters:** the new credential carries the target identity's privileges and often
outlives the review that would have found it. It is also the quietest of these paths,
because creating a key is an ordinary operational action.

**Closes with:** removing key-creation permission wherever federation is available;
organisation policy that disables service-account key creation outright; conditions that
restrict credential creation to identities within a defined path; and alerting on key
creation for any identity above a privilege threshold. `secret-rotation` covers the
credential lifecycle once one exists.

## Compute as a privilege boundary

**Looks like:** permission to create or modify a compute resource — a function, a task
definition, an instance, a build job, a pipeline definition — that runs with an attached
role, without a corresponding restriction on which role may be attached.

**Why it matters:** the ability to run code as an identity is equivalent to that
identity. This is the most common escalation path in practice because deploy permissions
are handed out as an ordinary part of delivery, and the attached-role question is rarely
asked.

**Closes with:** pairing every compute-creation permission with a scoped `PassRole` or
`actAs`; keeping the deploy identity distinct from the runtime identity so a pipeline
cannot grant itself the runtime's privileges; and treating a change to a pipeline
definition as a change to a security control, reviewed accordingly.

## Cross-account and third-party trust

**Looks like:** a role trusting an entire external account (`"AWS": "111122223333"`) or a
vendor's account with no external id and no conditions; an OAuth grant with
organisation-wide scopes; a federated trust with a broad subject claim, such as a CI
provider trust that accepts any repository in any organisation rather than one repository
and one branch.

**Why it matters:** the trust is only as strong as the weakest identity on the other side,
which you do not control and cannot review. Without an external id, a vendor who is
tricked into using your identifier can act against your account — the confused-deputy
problem that external ids exist to prevent.

**Closes with:** an external id required by the trust policy and treated as a shared
secret with the vendor; conditions on source account, organisation id, or source
identity; and for OIDC federation, a subject condition pinned to the exact repository,
environment and branch rather than a prefix match. Review these on a fixed cadence
regardless of usage, because a trust relationship generates no traffic of its own until
it is used.

## Approval loops and self-review

**Looks like:** an identity that can approve its own change — merge to a protected branch
plus administrative override, raise and approve its own access request, disable the
control that would have blocked it, or edit the audit configuration that records it.

**Why it matters:** it turns every other control into a suggestion, and it is invisible
in a permission list because the individual permissions are ordinary.

**Closes with:** platform-enforced separation for the small set of operations in the
skill's separation-of-duties list; removing administrative override from the people who
routinely need to merge; and alerting on override use rather than trying to eliminate it,
since the emergency it exists for is real.

## Kubernetes-specific paths

- **Secret read across namespaces** is equivalent to holding every credential stored in
  them, including service-account tokens.
- **Pod creation in a namespace hosting a privileged service account** lets a workload be
  scheduled with that identity; pod creation is not a lesser permission than the strongest
  service account in the namespace.
- **`escalate` and `bind`** on roles allow granting privileges the granter does not hold,
  which is exactly the self-modification pattern above.
- **Node or `nodes/proxy` access** and the ability to modify admission or webhook
  configuration are cluster-level controls wearing ordinary names.

Close these with namespace separation, scoped role bindings rather than cluster-wide ones,
admission policy that constrains which service accounts a workload may use, and audit
logging at a level that records the requests rather than only their metadata.

## Closing the path

For each path found, record four things in the review: the start identity, the identity it
reaches, the edge that makes it possible, and the guard rail applied. Then verify the
closure the same way as any other reduction — apply it in audit mode, confirm nothing
legitimate depended on the edge, enforce, and keep the alert.

Prefer guard rails that hold regardless of policy edits — permissions boundaries, service
control policies, organisation policy constraints, admission policy — over narrowing an
individual policy. A narrowed policy is one `PutRolePolicy` away from being wide again,
and if the identity holds that permission you have closed nothing.
