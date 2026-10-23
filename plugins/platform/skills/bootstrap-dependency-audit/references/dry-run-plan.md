# Scenario reachability and dry runs

Read this in step 3 to see which verbs each down scenario removes, and in step 5 to plan
and record the dry run of each break-glass path.

## Contents

- Which verbs each scenario removes
- Blocking a dependency without breaking it
- What to record per run
- Cadence

## Which verbs each scenario removes

`tsort` finds loops. It does not tell you that losing the IdP also removes `verb:deploy`
three hops away. This standard-library script does: for every node, it prints the verbs
that transitively depend on it. It reads the same `deps.txt` (two names per line,
prerequisite first, verbs prefixed `verb:`).

```python
#!/usr/bin/env python3
"""Print, for each node in deps.txt, the recovery verbs lost when that node is down."""

import sys
from collections import defaultdict

dependents = defaultdict(set)
nodes = set()
with open(sys.argv[1], encoding="utf-8") as handle:
    for number, line in enumerate(handle, 1):
        fields = line.split()
        if not fields:
            continue
        if len(fields) != 2:
            sys.exit(
                f"{sys.argv[1]}:{number}: expected 'prerequisite dependent', got {line.strip()!r}"
            )
        prerequisite, dependent = fields
        dependents[prerequisite].add(dependent)
        nodes.update(fields)

verbs = {node for node in nodes if node.startswith("verb:")}
for down in sorted(nodes - verbs):
    lost, stack = set(), [down]
    while stack:
        for node in dependents[stack.pop()]:
            if node not in lost:
                lost.add(node)
                stack.append(node)
    if lost & verbs:
        print(f"{down} down: {', '.join(sorted(lost & verbs))}")
```

Save it outside the audit's data directory and run it with `python3 -I reachability.py
deps.txt`. Sort the output by how many verbs each line removes: the nodes at the top are
where a break-glass path buys the most.

A node whose loss removes every verb is the one the whole recovery path rests on. It is
usually the IdP. That is not automatically wrong, but it must have a tested path around it.

## Blocking a dependency without breaking it

Block from the operator's side or in a non-production copy. Never block a shared
production system to test an emergency path.

| Dependency | Safe way to make it unavailable for the test |
| --- | --- |
| Identity provider | A clean machine with no existing sessions, the IdP's sign-in hostnames sinkholed in that machine's hosts file |
| VPN or zero-trust proxy | Run the test from a network that does not have it: a separate laptop on a mobile hotspot |
| Secrets store | Use only the offline copy; do not open the store at all during the run, and have a second person watch for that |
| Image registry | In a non-production cluster built the same way, scale the registry to zero, then cordon and drain a node and add a fresh one |
| CI | Build and push the hotfix artefact by the documented manual path without opening the CI system |
| GitOps controller | Pause sync on one non-production application, apply a change directly, and confirm it is not reverted until sync resumes |
| IaC state backend and registries | Run `init` and `plan` from a machine with outbound access to the public registry denied, using the provider mirror |
| DNS provider sign-in | Sign in to the provider and the registrar with the emergency credential only, and read, not change, a record |
| Paging and chat | Run the incident bridge on the documented fallback channel for the duration of the test |

For in-cluster cycles such as a fail-closed webhook served from the cluster, reproduce the
loop in non-production: scale the webhook's backend to zero and try to create a pod it
matches. The refusal proves the cycle; the break-glass step proves the way out.

## What to record per run

| Field | Example |
| --- | --- |
| Path tested | Console sign-in through the emergency account, IdP sinkholed |
| Blocked how | Hosts-file sinkhole on a clean laptop, no SSO cookies |
| People | Operator, custodian holding the second half of the credential, observer |
| Start and finish | Time from "we need in" to the verb succeeding |
| Alert | Where the break-glass alert arrived, how long after use, and whether that route avoids the cycle |
| What broke | Expired password, flat MFA device, a missing permission, a step absent from the runbook |
| Follow-up | Owner and date for each thing that broke |
| Credential state after | Rotated after use, or confirmed unchanged and re-sealed |

Rotate any emergency credential whose secret was revealed during the run, and re-seal it.
A dry run that leaves an emergency password in a chat log or a terminal history has
created a new exposure.

## Cadence

Exercise every path on a fixed interval the owners agree, and again after any change
that adds an edge to it. Credentials expire, MFA devices fail and
custodians change roles on their own schedule, not the audit's. Record the date of the last
successful run beside each path; a path with no date is untested.
