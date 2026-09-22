# Google Cloud Delivery Semantics

Use this note only for the named product path. Recheck the linked documentation when a design
depends on a provider guarantee.

## Pub/Sub

[Pub/Sub exactly-once delivery](https://cloud.google.com/pubsub/docs/exactly-once-delivery)
scopes the feature to pull subscriptions and a region. A successful acknowledgement prevents
Pub/Sub from redelivering that message under the documented conditions. It does not create one
transaction containing a database write, payment, email, or other application effect and the
acknowledgement.

Keep the consumer's stable event and business identities, durable completion evidence, and
external-effect strategy even when exactly-once delivery is enabled. Treat a negative
acknowledgement, expired acknowledgement deadline, or failed acknowledgement as a path that can
produce another delivery. Qualify any claim by subscription type, regional topology, client
library behaviour, and the current provider documentation.

## Eventarc Standard

[Eventarc Standard retry events](https://docs.cloud.google.com/eventarc/docs/retry-events)
describes retry behaviour by event source and destination. Record the exact source, trigger type,
destination, delivery path, and applicable retention or retry window before selecting attempt
limits or a dead-letter path. Do not generalise Eventarc Standard behaviour to other Eventarc
products or one destination's retry behaviour to all routes.

Provider retry does not resolve the application crash window around an external effect. Use a
recipient idempotency key or persist an operation state and reconcile an uncertain result before
issuing another call.
