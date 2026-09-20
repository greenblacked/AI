# Drawing the model

Read this at step 1 when the system is large enough that what to include is itself a
decision, or when the diagram keeps growing and nobody can hold it in their head.

## Scope first, elements second

Scope to the change and one hop out. The thing being designed, whatever it talks to, and
whatever talks to it. Everything past that hop is an external entity: a box with a name
and no internals, however much you know about it.

That rule is what keeps a model finishable. The alternative, modelling the estate,
produces a diagram that is written once, never updated, and wrong within a quarter, and
its threats are the generic ones everybody already knows.

## The four element types

**External entity.** Anything you do not control: a user, a third-party API, another
company's service. You cannot place a control inside one, so every threat against it is
handled at the boundary you share.

**Process.** Something that acts on data — a service, a lambda, a job, a consumer.

**Data store.** Something that holds it — a database, a bucket, a queue, a cache, a log.
Logs and caches are data stores and are commonly left off, which is why information
disclosure gets missed.

**Data flow.** The arrow, labelled with what actually travels and over what. "User data"
is not a label; "session cookie over TLS" and "tenant id in an unsigned header" are, and
the second one names its own threat.

## Where trust changes hands

These are the crossings worth marking:

- **Application to its own pipeline.** Anything that can deploy can change the
  application, so the boundary between production and whatever pushes to it is real even
  though both are yours.
- **Service to service inside one estate.** "Internal" is a network fact, not a trust
  fact. If one service would be a useful foothold for reaching another, there is a
  boundary between them.
- **Tenant to tenant.** In anything multi-tenant the most valuable crossing is the one
  between two customers' data, and it usually has no network hop to make it visible.
- **Process to data store.** The database trusts whoever holds the credential. If that
  credential is broader than the process needs, the crossing is where that matters.
- **Unauthenticated to authenticated,** and every place a request can arrive already
  carrying a claim about who it is.
- **Your service to a third party,** in both directions. The response is input.
- **Human to system.** An admin console, a support tool, a break-glass path. Support
  tooling is a boundary crossing with a person on one side, and is easy to leave out
  because it was built for insiders.

## When the diagram is too big

Two rules that keep it honest.

Collapse by trust, not by team. Three services that trust each other completely and sit
behind one boundary can be one process box for this purpose. Two services owned by the
same team that do not trust each other cannot.

Split by boundary, not by feature. If the model will not fit, cut it where a boundary
already is and model the two halves separately, with the shared crossing appearing in
both. Cutting anywhere else hides the crossing you cut through, which is the one thing a
threat model exists to look at.
