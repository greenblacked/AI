# Hidden edges

Read this while tracing the graph. Each row is an edge that audits routinely miss, with
the question that surfaces it. A "yes" to the question is an edge to write down; whether
it forms a cycle is for `tsort` to say.

## Contents

- Identity and sign-in
- Network reach
- Secrets and keys
- Artefacts and packages
- Build and deploy
- Infrastructure as code
- DNS and certificates
- Coordination and runbooks

## Identity and sign-in

| Question | Why it matters |
| --- | --- |
| Is the IdP self-hosted, and if so where does it run? | A Keycloak or Dex on the production cluster cannot be used to sign in to fix that cluster |
| Is the IdP admin console reachable only over the VPN? | If the VPN authenticates through the IdP, a broken IdP configuration cannot be corrected |
| Does cluster API access go through OIDC to the IdP? | Every kubeconfig then stops working with the IdP; keep one cluster-admin path that does not |
| Are emergency cloud accounts excluded from federation and from policies that require it? | An emergency account forced through the federated IdP is not an emergency account |
| Where are the MFA devices for emergency accounts, and who can physically reach them? | A hardware key in a closed office is unreachable on a weekend |
| Do sign-in tokens or TOTP depend on correct time on the operator machine? | Rarely a cycle, but a fresh laptop with a wrong clock fails sign-in in confusing ways |

## Network reach

| Question | Why it matters |
| --- | --- |
| Does the VPN concentrator or zero-trust proxy run in the network it grants access to? | Losing that network then removes the way in to repair it |
| Does the bastion pull its configuration or keys from a service inside the private network? | A rebuilt bastion cannot come up without what it is meant to reach |
| Is the admin path resolved by an internal resolver that runs on the cluster? | Name resolution for the way in fails with the cluster |
| Do cloud API calls from the operator path go through a proxy or VPC endpoint that is itself managed by IaC behind CI? | Fixing the proxy needs the pipeline that needs the proxy |

## Secrets and keys

| Question | Why it matters |
| --- | --- |
| Where are the break-glass credentials stored, and does opening that store need SSO? | The most common loop in this whole audit |
| Is the secrets store sealed by a cloud KMS key, and which identity can use that key? | With auto-unseal, recovery keys authorise operations but cannot unseal; the KMS path is the dependency |
| Do workloads fetch secrets at start-up from a store that runs on the same cluster? | Pods cannot start without the store, and the store's pods may be among those not starting |
| Is the KMS key policy editable only by a role that signs in through the IdP? | A key policy mistake can then only be fixed through the thing that is broken |

## Artefacts and packages

| Question | Why it matters |
| --- | --- |
| Which registry hosts the images for the CNI, DNS, ingress and autoscaler? | A replacement node cannot join without them, and these are the first images it needs |
| Is the registry, or its pull-through cache, running on the cluster it serves? | The registry cannot pull its own image onto a fresh node |
| Do builds fetch base images and packages from public registries with rate limits? | An emergency rebuild at scale can be throttled by the public source |
| Is there a mirror outside the primary failure domain, and do nodes know how to use it? | A mirror nobody can point pulls at does not shorten an outage |

## Build and deploy

| Question | Why it matters |
| --- | --- |
| Is CI a SaaS, and is there a documented way to build and push without it? | A hotfix that can only ship through a down SaaS waits for the vendor |
| Do self-hosted runners run on the production cluster? | Deploying to fix the cluster needs runners the cluster no longer runs |
| Does the GitOps controller sign in to Git and to its own UI through the IdP? | Pause and override need a path that does not |
| Is there an admission webhook with `failurePolicy: Fail` whose backend runs in the cluster it guards? | Pod creation it matches is refused while the backend is down, including its own replacement |
| Does the deploy pipeline need a secret from the store that the deploy is meant to repair? | A pipeline that cannot read its credentials cannot fix the store |

## Infrastructure as code

| Question | Why it matters |
| --- | --- |
| Is the state backend in the account or region you are recovering? | Plans cannot run without state, and the state is in the outage |
| Which credential reads the backend, and is it only issued to CI through OIDC? | If CI is down, no human can run a plan |
| Does `init` need the public provider and module registries? | A mirror built with `terraform providers mirror` and used with `-plugin-dir` removes the edge |
| Are modules sourced from a Git host that signs in through the IdP? | The module fetch fails with the IdP even when the cloud is healthy |

## DNS and certificates

| Question | Why it matters |
| --- | --- |
| Do the registrar and DNS provider accounts sign in through the IdP? | Correcting a delegation during an IdP outage is then impossible |
| Is the registrar account's recovery email on the domain it controls? | Losing the domain loses the mailbox that recovers it |
| Are internal certificates issued by a CA running on the cluster? | Expired internal certificates cannot be renewed while the CA is down |

## Coordination and runbooks

| Question | Why it matters |
| --- | --- |
| Where are the runbooks hosted, and does reading them need SSO? | A runbook you cannot open is not a runbook |
| Do paging and chat sign in through the IdP? | The incident cannot be coordinated in the usual channels; name the fallback |
| Does the status page update through a tool behind SSO? | Customers hear nothing until the IdP returns |
| Does the break-glass alert route through any node in the cycle it guards? | The alarm is silent exactly when it matters |
