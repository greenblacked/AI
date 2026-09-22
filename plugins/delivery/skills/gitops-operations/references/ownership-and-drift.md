# Ownership and Drift

## Establish ownership

Trace from the live resource upward:

1. Identify the GitOps inventory or tracking metadata.
2. Find the owning Application or Flux Kustomization/HelmRelease.
3. If an ApplicationSet generated the Application, treat its template and generator inputs as the parent authority.
4. Resolve every repository, chart, values file, and generator input to an immutable revision.
5. Render the complete desired result and compare it with the live object.

If two systems claim the same resource, stop the competing write before tuning diff rules. Stable reconciliation requires one declared owner per field.

## Drift decision table

| Difference | Questions | Durable response |
| --- | --- | --- |
| Manual live patch | Who made it, why, and is it still needed? | Port it to Git or remove it |
| Admission mutation | Is the result deterministic and security-relevant? | Model it or narrowly ignore the mutated field |
| Horizontal autoscaler replicas | Which controller owns `/spec/replicas`? | Remove competing ownership from desired state or scope the diff rule |
| Operator-managed child | Is the child meant to be tracked directly? | Track the parent and respect the operator's field ownership |
| Random or time-based render output | Can identical inputs reproduce it? | Remove nondeterminism before reconciliation |
| External secret/config material | Is Git defining the reference or the resolved data? | Declare the ownership boundary and compare only the intended surface |

An ignore rule affects observation; a sync option affects application. Do not use one to compensate for misunderstanding the other.

## ApplicationSet hazards

- Generator cardinality is blast radius. Preview additions and removals of generated Applications.
- A child Application is generated output. Direct edits can be overwritten.
- By default, deleting an ApplicationSet can cascade through its Applications to deployed resources. When retention is intended, configure `spec.syncPolicy.preserveResourcesOnDeletion: true`, then inspect the existing child Applications' owner references and finalizers. Verify the installed Argo CD version's behavior on a representative child before any deletion; changing the setting does not by itself prove that already-generated children are safe. Orphaning a generated Application may leave its resource finalizer in place, so deleting that Application later can still delete its workloads.
- Matrix and merge generators combine inputs; an empty, duplicated, or unexpectedly broad input can affect many destinations.

## Multiple-source hazards

Argo CD combines manifests from all sources. When more than one source emits the same resource identity, the later source takes precedence and Argo CD reports a repeated-resource warning. Treat that warning as a required review, not as harmless noise.

Pin every source. Review the combined render. A new revision in any source can cause the application to reconcile, so disabling self-heal alone does not guarantee that an unrelated live edit will persist.

Use multiple sources for one coherent application, such as a pinned external chart plus organization-owned values. Use separate Applications or an application-of-applications structure when the goal is merely grouping unrelated workloads.

## Official sources

- [Argo CD: Multiple Sources for an Application](https://argo-cd.readthedocs.io/en/stable/user-guide/multiple_sources/)
- [Argo CD: Introduction to ApplicationSet controller](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/)
- [Argo CD: ApplicationSet deletion behavior](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/Application-Deletion/)
- [Flux: Reconciliation](https://fluxcd.io/flux/concepts/)
