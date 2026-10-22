# Provider responses

What APNs and FCM HTTP v1 return and what the sending server must do with each. Check the
current provider documentation for new reason strings; the actions below are what matters.

## Contents

- APNs
- FCM HTTP v1
- What to log per request

## APNs

Requests go over HTTP/2 to the production or the development host; a token belongs to one
environment. The status is in the response and the reason in a JSON body.

| Status | Reason | Action |
| --- | --- | --- |
| 200 | — | Accepted. Record the `apns-id`; this is not proof of delivery |
| 400 | `BadDeviceToken` | First check the environment (development token sent to production or the reverse). If the environment is right, delete the token |
| 400 | `DeviceTokenNotForTopic` | The `apns-topic` is not the app the token belongs to; fix the request or the token's app mapping |
| 400 | `BadCollapseId`, `BadExpirationDate`, `BadPriority`, `BadTopic`, `MissingTopic`, `InvalidPushType`, `PayloadEmpty` | Fix the request; do not retry unchanged |
| 403 | `ExpiredProviderToken`, `InvalidProviderToken` | Regenerate the signed provider token. Apple asks for it to be refreshed no more often than every 20 minutes and at least once an hour |
| 410 | `Unregistered` | Delete the token if the response's timestamp is later than when the device last sent you this token; otherwise a fresh registration raced the response and the token may be valid |
| 413 | `PayloadTooLarge` | Shrink the payload; send an ID and fetch the content |
| 429 | `TooManyRequests` | Too many pushes to one device; back off for that token |
| 429 | `TooManyProviderTokenUpdates` | The provider token is being regenerated too often; cache it |
| 500, 503 | `InternalServerError`, `ServiceUnavailable`, `Shutdown` | Retry with backoff, on a new connection for `Shutdown` |

## FCM HTTP v1

Requests go to `https://fcm.googleapis.com/v1/projects/<project-id>/messages:send` with an
OAuth 2.0 access token from a service account. The legacy send APIs were shut down; a
server still calling them sends nothing.

| Error code | HTTP | Action |
| --- | --- | --- |
| — | 200 | Accepted; record the returned message `name` |
| `UNREGISTERED` | 404 | Delete the token: the app was uninstalled, the token expired or was replaced |
| `INVALID_ARGUMENT` | 400 | Read the details. If they point at the registration token, delete it; otherwise the payload is malformed — fix it and do not retry unchanged |
| `SENDER_ID_MISMATCH` | 403 | The token belongs to a different Firebase project; fix the project or the token mapping |
| `THIRD_PARTY_AUTH_ERROR` | 401 | For iOS through FCM: the APNs key or certificate in the Firebase project is missing, expired or for the wrong environment |
| `QUOTA_EXCEEDED` | 429 | Back off, honouring `Retry-After`; check whether the quota is per project, per device or per topic |
| `UNAVAILABLE` | 503 | Retry with exponential backoff, honouring `Retry-After` |
| `INTERNAL` | 500 | Retry with exponential backoff |

Firebase also documents that tokens go stale when a device has not connected for a long
period. Store when each token was last refreshed by the app and prune tokens the app has
not re-sent for months, rather than waiting for errors.

## What to log per request

| Field | Why |
| --- | --- |
| Provider ID (`apns-id` or FCM message `name`) | Ties the request to the provider's own delivery tools |
| A hash of the token, plus user and device IDs | Joins failures to devices without spreading raw tokens through logs |
| App ID and environment | Exposes the development-versus-production mismatch |
| Push type, priority, collapse key, expiry or TTL | The fields most often wrong |
| Status and reason or error code | Without it the investigation starts at the device |
| App version and platform from the token record | Lets a failure be sliced by release |
