# Lifecycle jobs and the reaper

Read this before writing the deploy and teardown jobs or the reaper. The examples assume
a namespace per preview in a dedicated preview cluster, plus an optional Terraform root
for per-preview cloud resources, one workspace per preview. Adapt names; keep the shape.

## Contents

- Labels the examples use
- GitHub Actions: deploy and teardown
- The up and down scripts
- Argo CD alternative: the pull-request generator
- The reaper: Kubernetes
- The reaper: AWS
- Testing the reaper

## Labels the examples use

| Key | Value | Why |
| --- | --- | --- |
| `env-type` | `preview` | The reaper's first filter; nothing without it is ever touched |
| `preview-id` | the pull request number | Ties a resource to its pull request |
| `repo` | the repository name without its owner | Label values cannot contain a slash |
| `owner` | the pull request author's login, sanitised to label-value characters | Who to ask before deleting by hand |
| `expires-at` | Unix epoch seconds | Label values cannot contain colons, so not an ISO timestamp |

## GitHub Actions: deploy and teardown

```yaml
name: preview
on:
  pull_request:
    types: [opened, reopened, synchronize, closed]

permissions:
  contents: read
  id-token: write

concurrency:
  group: preview-${{ github.event.pull_request.number }}
  cancel-in-progress: false

jobs:
  deploy:
    if: >-
      github.event.action != 'closed' &&
      github.event.pull_request.head.repo.full_name == github.repository
    runs-on: ubuntu-latest
    timeout-minutes: 20
    environment: preview
    steps:
      - uses: actions/checkout@FULL_COMMIT_SHA # pin to a commit SHA, comment the release tag
        with:
          persist-credentials: false
      # Obtain short-lived, preview-only cloud and cluster credentials through OIDC here.
      - name: Deploy preview
        env:
          PREVIEW_ID: ${{ github.event.pull_request.number }}
          OWNER: ${{ github.event.pull_request.user.login }}
          IMAGE_TAG: ${{ github.event.pull_request.head.sha }}
        run: |
          set -Eeuo pipefail
          expires="$(( $(date +%s) + 7 * 24 * 3600 ))"
          ./deploy/preview-up.sh "$PREVIEW_ID" "$OWNER" "$expires" "$IMAGE_TAG"

  teardown:
    if: >-
      github.event.action == 'closed' &&
      github.event.pull_request.head.repo.full_name == github.repository
    runs-on: ubuntu-latest
    timeout-minutes: 20
    environment: preview
    steps:
      - uses: actions/checkout@FULL_COMMIT_SHA # pin to a commit SHA, comment the release tag
        with:
          ref: ${{ github.event.repository.default_branch }}
          persist-credentials: false
      - name: Tear down preview
        env:
          PREVIEW_ID: ${{ github.event.pull_request.number }}
        run: |
          set -Eeuo pipefail
          ./deploy/preview-down.sh "$PREVIEW_ID"
```

Why each choice:

- **`cancel-in-progress: false`** queues a teardown behind a running deploy instead of
  killing either halfway. A half-finished teardown is the leak this design exists to stop.
- **The fork condition** skips forks entirely; their runs get no secrets anyway. If fork
  previews are wanted, add a separate path a maintainer triggers by label after reading
  the change, never `pull_request_target` checking out the fork's head.
- **Teardown checks out the default branch**, so it works after the branch is deleted or
  stops building. The workflow definition itself still comes from the pull request, so a
  same-repository change can edit this job; the scheduled reaper, which runs from the
  default branch, is the control a pull request cannot edit.
- **Values reach `run:` through `env:`**, never by interpolating `${{ }}` into the script,
  so a crafted branch name or title cannot become shell.

## The up and down scripts

Create the namespace with its labels in one request. Creating it bare and labelling it
afterwards fails against an admission policy that requires the labels, and leaves an
unlabelled namespace if the second call never runs.

```bash
#!/usr/bin/env bash
# deploy/preview-up.sh PREVIEW_ID OWNER EXPIRES_AT IMAGE_TAG
set -Eeuo pipefail
id="$1" expires="$3" tag="$4"
# Logins such as dependabot[bot] hold characters a label value cannot; keep [A-Za-z0-9._-],
# start and end alphanumeric, at most 63 characters.
owner="$(printf '%s' "$2" | tr -c 'A-Za-z0-9._-' '-' | sed -E 's/^[^A-Za-z0-9]+//; s/[^A-Za-z0-9]+$//' | cut -c1-63)"
ns="preview-${id}"

kubectl create namespace "$ns" --dry-run=client -o yaml \
  | kubectl label --local -f - -o yaml \
      env-type=preview preview-id="$id" repo=example-app owner="$owner" expires-at="$expires" \
  | kubectl apply -f -

kubectl apply -n "$ns" -f deploy/preview-quota.yaml
helm upgrade --install app ./deploy/chart \
  --namespace "$ns" --set image.tag="$tag" --wait --timeout 10m
```

```bash
#!/usr/bin/env bash
# deploy/preview-down.sh PREVIEW_ID
set -Eeuo pipefail
id="$1"
kubectl delete namespace "preview-${id}" --ignore-not-found --wait=true --timeout=10m

# Only when the preview has its own cloud resources:
terraform -chdir=deploy/preview-infra init -input=false
# List first: a failed `workspace select` for any reason other than "absent" must not be
# read as "nothing to destroy" and skip the teardown. A list that fails aborts the script.
workspaces="$(terraform -chdir=deploy/preview-infra workspace list | sed 's/^[* ]*//')"
if grep -Fxq "pr-${id}" <<< "$workspaces"; then
  terraform -chdir=deploy/preview-infra workspace select "pr-${id}"
  terraform -chdir=deploy/preview-infra destroy -input=false -auto-approve -var "preview_id=${id}"
  terraform -chdir=deploy/preview-infra workspace select default
  terraform -chdir=deploy/preview-infra workspace delete "pr-${id}"
fi
```

`deploy/preview-quota.yaml` holds the ResourceQuota and LimitRange sized in step 1 of the
skill. Re-applying the expiry on every push means an active pull request keeps its
preview; one with no pushes expires.

## Argo CD alternative: the pull-request generator

Where previews are deployed by Argo CD, an ApplicationSet with the pull-request generator
creates one Application per open pull request and removes it when the pull request closes
or loses the label.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: example-app-previews
  namespace: argocd
spec:
  goTemplate: true
  generators:
    - pullRequest:
        github:
          owner: example-org
          repo: example-app
          labels: [preview]
        requeueAfterSeconds: 300
  template:
    metadata:
      name: 'example-app-pr-{{.number}}'
      finalizers:
        - resources-finalizer.argocd.argoproj.io
    spec:
      project: previews
      source:
        repoURL: https://github.com/example-org/example-app.git
        targetRevision: '{{.head_sha}}'
        path: deploy/chart
        helm:
          parameters:
            - name: image.tag
              value: '{{.head_sha}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: 'preview-{{.number}}'
      syncPolicy:
        automated:
          prune: true
        syncOptions:
          - CreateNamespace=true
        managedNamespaceMetadata:
          labels:
            env-type: preview
            preview-id: '{{.number}}'
            repo: example-app
            owner: '{{.author}}'
```

The finalizer makes deleting the Application delete the resources it deployed. A
namespace created through `CreateNamespace=true` is not one of them, so it outlives the
pull request; keep `managedNamespaceMetadata` as above so it carries the `env-type` and
`preview-id` labels. The generator cannot compute an epoch expiry, so these namespaces
have no `expires-at`: the reaper keeps them on the expiry rule and judges them by the
closed-pull-request rule below, and an admission policy for this path must not demand
`expires-at`. A namespace without `env-type` and `preview-id` is invisible to the reaper.
The reaper still runs: a deleted ApplicationSet, a broken generator token or a stuck finalizer
all leave previews behind. A private repository needs a token for the generator.

## The reaper: Kubernetes

Report first. The loop isolates `kubectl`'s standard input so a command that reads stdin
cannot swallow the rest of the list. A namespace with no numeric `expires-at` is never
treated as expired: defaulting a missing value to 0 would delete every Argo CD preview and
every half-labelled namespace on the first run. Those are listed for a human instead.

```bash
#!/usr/bin/env bash
# reap-namespaces.sh [report|delete]
set -Eeuo pipefail
mode="${1:-report}"
now="$(date +%s)"

kubectl get namespaces -l env-type=preview,preview-id -o json \
  | jq -r --argjson now "$now" '
      .items[]
      | (.metadata.labels["expires-at"] // "") as $e
      | select(($e | test("^[0-9]+$")) and ($e | tonumber) < $now)
      | .metadata.name' \
  | while read -r ns; do
      if [ "$mode" = "delete" ]; then
        kubectl delete namespace "$ns" --wait=false < /dev/null
      else
        echo "would delete $ns"
      fi
    done

# Preview namespaces the expiry rule cannot judge
kubectl get namespaces -l env-type=preview,preview-id -o json \
  | jq -r '.items[]
      | select((.metadata.labels["expires-at"] // "") | test("^[0-9]+$") | not)
      | "no valid expires-at, kept: " + .metadata.name'
```

Add a second rule for previews whose pull request is closed but whose expiry has not
passed: for each `preview-id`, ask the forge for the pull request's state (on GitHub,
`gh pr view "$id" --repo example-org/example-app --json state --jq .state` returns `OPEN`,
`CLOSED` or `MERGED`) and treat `CLOSED` and `MERGED` as expired. Treat an API error as "keep", not as "closed";
a failed read must never become a deletion.

## The reaper: AWS

Tag-based inventory is per region and only sees resources that carry tags, which is why
step 3 of the skill enforces tags at creation.

```bash
#!/usr/bin/env bash
# list-expired-preview-resources.sh REGION
set -Eeuo pipefail
region="$1"
now="$(date +%s)"

aws resourcegroupstaggingapi get-resources --region "$region" \
  --tag-filters Key=env-type,Values=preview \
  --query 'ResourceTagMappingList[].{arn: ResourceARN, tags: Tags}' --output json \
  | jq -r --argjson now "$now" '
      .[]
      | ([.tags[] | select(.Key == "expires-at") | .Value][0] // "") as $e
      | select(($e | test("^[0-9]+$")) and ($e | tonumber) < $now)
      | .arn'
```

A resource with no numeric `expires-at` is not listed as expired, for the same reason as
above; list those separately with the inverse `select` and treat each as a labelling bug.

Delete through the preview's Terraform workspace where one exists, so state and reality
agree; the ARN list is for what no workspace owns any more. Run the same query in every
region the preview account is allowed to use, and use a service control policy to deny
the rest.

## Testing the reaper

1. Create a namespace with every label and an `expires-at` an hour in the past, with no
   pull request behind it.
2. Create one with the labels and an expiry a day ahead.
3. Create one without `env-type=preview`.
4. Run the reaper in report mode. Only the first should be listed.
5. Run it in delete mode and confirm the first is gone and the other two remain.

A reaper that has never deleted anything in a test is a reaper nobody knows works.
