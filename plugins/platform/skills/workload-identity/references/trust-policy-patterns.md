# Trust policy patterns

Read this at step 3. Each section gives the trust document or binding for one platform
with the issuer, audience and subject pinned, followed by what the common wildcards
admit. Account ids, cluster ids and names are placeholders.

## Contents

- [Subject formats](#subject-formats)
- [EKS: IRSA](#eks-irsa)
- [EKS: Pod Identity](#eks-pod-identity)
- [GKE: Workload Identity Federation for GKE](#gke-workload-identity-federation-for-gke)
- [AKS: Microsoft Entra Workload ID](#aks-microsoft-entra-workload-id)
- [GitHub Actions into AWS](#github-actions-into-aws)
- [GitHub Actions into Google Cloud](#github-actions-into-google-cloud)
- [GitHub Actions into Azure](#github-actions-into-azure)
- [What each wildcard admits](#what-each-wildcard-admits)

## Subject formats

| Issuer | Subject | Example |
| --- | --- | --- |
| Kubernetes service-account token (EKS, AKS, self-managed) | `system:serviceaccount:NAMESPACE:SA` | `system:serviceaccount:payments:payments-api` |
| GKE workload pool | `ns/NAMESPACE/sa/SA` inside a `principal://` identifier | see below |
| GitHub Actions, job with an environment | `repo:OWNER/REPO:environment:NAME` | `repo:my-org/payments-api:environment:production` |
| GitHub Actions, push to a branch | `repo:OWNER/REPO:ref:refs/heads/BRANCH` | `repo:my-org/payments-api:ref:refs/heads/main` |
| GitHub Actions, tag | `repo:OWNER/REPO:ref:refs/tags/TAG` | |
| GitHub Actions, pull request | `repo:OWNER/REPO:pull_request` | never on a role that can write |

A job that names an environment gets the environment subject, not the ref subject, so a
trust condition written for `ref:refs/heads/main` stops matching the moment someone adds
`environment: production` to the job. Decide which form each role uses and keep the
workflow and the trust policy in the same review.

## EKS: IRSA

The `Federated` principal pins the cluster's issuer; the conditions pin audience and
subject.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "arn:aws:iam::111122223333:oidc-provider/oidc.eks.eu-west-1.amazonaws.com/id/EXAMPLE0123456789"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {"StringEquals": {
      "oidc.eks.eu-west-1.amazonaws.com/id/EXAMPLE0123456789:aud": "sts.amazonaws.com",
      "oidc.eks.eu-west-1.amazonaws.com/id/EXAMPLE0123456789:sub": "system:serviceaccount:payments:payments-api"
    }}
  }]
}
```

The service account carries `eks.amazonaws.com/role-arn`. That annotation is a request,
not a control: anyone who can create a service account can annotate it with any role
ARN, and only the trust policy's `sub` condition stops them.

## EKS: Pod Identity

The trust policy names the EKS service, not the cluster or the workload:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "pods.eks.amazonaws.com"},
    "Action": ["sts:AssumeRole", "sts:TagSession"]
  }]
}
```

```bash
aws eks create-pod-identity-association --cluster-name "$CLUSTER" \
  --namespace payments --service-account payments-api --role-arn "$ROLE_ARN"
aws eks list-pod-identity-associations --cluster-name "$CLUSTER"
```

Because the trust is service-wide, the binding to one workload is the association
itself. Control who may create associations (`eks:CreatePodIdentityAssociation` together
with `iam:PassRole` on the role), audit the list per cluster, and, where a role must be
usable only from one namespace, condition its permissions on the session tags Pod
Identity attaches, such as `aws:PrincipalTag/kubernetes-namespace` and
`aws:PrincipalTag/kubernetes-service-account`.

## GKE: Workload Identity Federation for GKE

```bash
gcloud container clusters update "$CLUSTER" --location="$LOCATION" \
  --workload-pool="$PROJECT_ID.svc.id.goog"
gcloud container node-pools update "$POOL" --cluster="$CLUSTER" --location="$LOCATION" \
  --workload-metadata=GKE_METADATA
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" \
  --role=roles/storage.objectViewer \
  --member="principal://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$PROJECT_ID.svc.id.goog/subject/ns/payments/sa/payments-api"
```

Bind on the resource rather than the project where the resource supports it. The pool is
per project, not per cluster: the same namespace and service-account name in any cluster
of that project is the same principal.

The older pattern, binding `roles/iam.workloadIdentityUser` on a Google service account
for `serviceAccount:PROJECT_ID.svc.id.goog[NAMESPACE/KSA]` and annotating the Kubernetes
service account with `iam.gke.io/gcp-service-account`, also pins namespace and service
account exactly and remains valid.

## AKS: Microsoft Entra Workload ID

```bash
az aks update --resource-group "$RG" --name "$CLUSTER" \
  --enable-oidc-issuer --enable-workload-identity
ISSUER=$(az aks show --resource-group "$RG" --name "$CLUSTER" \
  --query oidcIssuerProfile.issuerUrl -o tsv)
az identity federated-credential create --name payments-api \
  --identity-name payments-api-id --resource-group "$RG" \
  --issuer "$ISSUER" \
  --subject system:serviceaccount:payments:payments-api \
  --audiences api://AzureADTokenExchange
```

The service account carries `azure.workload.identity/client-id`, and the pod carries the
label `azure.workload.identity/use: "true"`. A federated identity credential matches its
subject exactly, so the wildcard mistake is harder to make here; the equivalent mistake
is one managed identity with many federated credentials for unrelated workloads.

## GitHub Actions into AWS

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "arn:aws:iam::111122223333:oidc-provider/token.actions.githubusercontent.com"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {"StringEquals": {
      "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
      "token.actions.githubusercontent.com:sub": "repo:my-org/payments-api:environment:production"
    }}
  }]
}
```

```yaml
jobs:
  deploy:
    environment: production
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: aws-actions/configure-aws-credentials@FULL_COMMIT_SHA # vX.Y.Z
        with:
          role-to-assume: arn:aws:iam::111122223333:role/payments-api-deploy
          aws-region: eu-west-1
```

## GitHub Actions into Google Cloud

Map the subject, and reject tokens from other owners at the provider with an attribute
condition on the numeric owner id, which does not change when an organisation is
renamed:

```bash
gcloud iam workload-identity-pools create github --location=global
gcloud iam workload-identity-pools providers create-oidc github-actions \
  --location=global --workload-identity-pool=github \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository_id=assertion.repository_id" \
  --attribute-condition="assertion.repository_owner_id=='$GITHUB_ORG_ID'"
```

Then grant the role to one subject, not to an attribute set covering the whole
repository:

```text
principal://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github/subject/repo:my-org/payments-api:environment:production
```

The job uses `google-github-actions/auth`, pinned to a commit SHA, with the provider's
full resource name.

## GitHub Actions into Azure

Create a federated credential on the app registration or managed identity with issuer
`https://token.actions.githubusercontent.com`, audience `api://AzureADTokenExchange`,
and the exact subject, for example `repo:my-org/payments-api:environment:production`.
One credential per subject; add a second credential for a second environment rather than
widening the first.

## What each wildcard admits

| Condition | Admits |
| --- | --- |
| No `sub` condition on a GitHub trust | Every GitHub Actions job in every repository on GitHub, because they share one issuer |
| `repo:my-org/*` | Every repository in the organisation, including ones created later by anyone allowed to create repositories |
| `repo:my-org/app:*` | Every branch, tag, environment and pull-request run in that repository |
| `repo:my-org/app:ref:refs/heads/*` | Any branch anyone with push access creates |
| `system:serviceaccount:payments:*` | Any service account in the namespace, including ones created by anyone with edit rights there |
| `system:serviceaccount:*` | Any pod in the cluster |

GitHub subjects are built from names. Where repository renames or deletions are a
concern, GitHub can customise the subject template for an organisation or repository to
include `repository_owner_id` and `repository_id`; if you adopt that, update every trust
condition in the same change, because every existing subject stops matching.
