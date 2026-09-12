# Vulnerability class checks

Per-class checks for step 2 of the review. Each section names the sinks to inventory, the
shapes the defect takes per language, and the fix. Everything here is defensive: payload
shapes are named in words so a reviewer recognises the defect, and no usable exploit
string, credential or request appears.

## Contents

- [Broken access control](#broken-access-control)
- [Injection](#injection)
- [Insecure deserialisation](#insecure-deserialisation)
- [Server-side request forgery](#server-side-request-forgery)
- [Secrets and sensitive data exposure](#secrets-and-sensitive-data-exposure)
- [Unsafe defaults](#unsafe-defaults)

## Broken access control

**Sinks to inventory.** Every handler in the diff that reads an identifier from a path
segment, query parameter, body field, header or cookie and uses it to load, update,
delete, export or list a record.

| Shape | What gives it away | Fix |
| --- | --- | --- |
| Direct object reference | The record is fetched by the supplied id, then returned; the ownership comparison is absent or happens after the load | Put the tenancy or ownership predicate in the query that loads the record, so a wrong owner returns nothing rather than being caught afterwards |
| Missing check on the write verb | Read is guarded and update or delete reuses the id without the same predicate | Apply the same predicate on every verb, and make the guarded fetch the only way the handler obtains the object |
| Unscoped list or export | A collection endpoint filters on a status or date but not on the caller's tenant | Scope the collection query on the principal before any other filter, and test with two tenants rather than one |
| Principal taken from the request | An owner, tenant or account id read from the body or a header the client sets | Derive the principal from the session or verified token only; a client-supplied identity is not an identity |
| Fail-open role comparison | An unrecognised role, scope or claim falls through to permit | Invert to deny by default so an unknown value is refused, which is the state of a token minted by another version of the service |
| Static resource path | A file or object key built from user input and served without normalisation | Resolve the path and confirm it remains under the intended root after normalisation; reject rather than trim |

Enumerability changes severity, not presence. A sequential identifier turns a missing
check into bulk extraction; an unguessable one leaves the defect fully present for anyone
who has ever seen a valid id, including a former user.

## Injection

The question is never whether the code escapes. It is whether data the process did not
author can reach a parser as syntax.

| Parser | Sinks to inventory | Safe construction |
| --- | --- | --- |
| SQL | String-built queries, ORM `raw`/`literal`/`expr` escapes, dynamic table, column, `ORDER BY` and `LIMIT` fragments, `IN` lists built by joining | Bound parameters for values; an allow-list mapping input to a fixed set of identifiers for anything a parameter cannot carry, which is every identifier |
| Shell | Any call that runs through a shell, string-built command lines, arguments beginning with a hyphen | Pass an argument vector with no shell, and pass a `--` terminator so a value cannot be read as an option |
| Template | Templates compiled from user-supplied strings, template engines rendering into a context they were not designed for, any server-side template evaluated on request data | Templates are code: load them from disk, never build them from input. Where users must supply text, render it as data in a logic-less context |
| LDAP | Filters built by concatenation, distinguished names assembled from input | Use the library's filter-encoding or assertion API; allow-list attribute names |
| Operating-system path | Paths joined from user segments, archive extraction that trusts entry names | Normalise, then confirm containment under the root; refuse absolute and parent-directory segments outright |
| NoSQL and ORM documents | A query document built from a parsed request body, so an operator can arrive where a value was expected | Coerce each field to its expected scalar type before it reaches the query, and reject documents carrying operator keys |
| Serialisation into another language | Values interpolated into generated SQL, YAML, JSON, HTML attributes or JavaScript | Use the target's own encoder at the point of emission, not a general-purpose sanitiser at the point of input |

The payload shapes worth naming in a review, in words: a single quote terminating the
literal so the remainder is read as statement text; a semicolon or shell metacharacter
introducing a second command; a leading hyphen turning a filename into an option; a
parent-directory segment escaping the intended root; a template delimiter arriving inside
a value. Naming the shape tells the author which boundary is crossed. Writing the string
out turns the review into an artefact somebody can run.

Input validation is worth having and is not the control. It reduces the surface; the
parser boundary is what closes the class.

## Insecure deserialisation

**Sinks to inventory.** Native or language-specific deserialisers, object mappers with
polymorphic or default typing enabled, mapper configurations that resolve a type name
from the payload, marshalling libraries reading a class or module name, and any cache,
queue, cookie or session store whose contents are deserialised into objects.

- A deserialiser that can instantiate arbitrary types turns "reading data" into "choosing
  which code runs", and no amount of validation after the fact helps, because the effect
  happens during construction.
- The fix is to change the format, not to filter it: a data-only format parsed into known
  structures. Where a native format cannot be removed, the fallback is an explicit
  allow-list of permitted types, enforced by the mapper rather than by a wrapper.
- Signing the blob protects integrity only if the key is not reachable from the same
  compromise you are defending against, and it does nothing about a payload your own
  service produced under attacker influence.
- Session and cookie payloads deserialised server-side count. So does anything read from
  a queue another team writes to: another team is still not this process.

## Server-side request forgery

**Sinks to inventory.** Outbound HTTP clients, webhook delivery, URL preview and
thumbnailing, import-from-URL features, PDF and image renderers that fetch remote
resources, XML parsers with external entity resolution, and any library that dereferences
a schema or document reference.

| Check | Why |
| --- | --- |
| Is the destination host constrained by an allow-list of hosts rather than a deny-list of addresses | A deny-list of private ranges misses alternative encodings, redirection and names that resolve differently on the second lookup |
| Is the resolved address checked, and checked again after redirects | A host that passes validation can redirect to one that would not, and each redirect is a fresh destination |
| Are non-HTTP schemes refused | File, gopher and similar schemes turn a fetcher into a reader of local resources |
| Is the response withheld from the caller | Returning body, headers, status or timing to the user turns a blind fetch into a readable one |
| Does the client carry credentials or run inside a network where being inside is itself authority | Instance metadata services and unauthenticated internal endpoints are the reason this class is severe rather than annoying |
| Is XML external entity resolution disabled | The parser default is the vulnerability in most stacks; the fix is one configuration line and it is frequently omitted |

## Secrets and sensitive data exposure

- A literal credential, key, token or connection string in the diff, including in tests,
  fixtures, example configuration, notebooks and comments. Treat a committed secret as
  disclosed the moment it lands, and hand containment to `secret-rotation`; this review's
  job is to stop it merging and to state what needs rotating.
- Tokens, authorisation headers, session identifiers, full request bodies, personal data
  and card or account numbers reaching a log line, a trace attribute, an error report or
  an analytics event. Logging middleware added in the same diff is the usual carrier.
- Error responses echoing stack traces, query text, internal hostnames or version strings
  to a caller.
- A new file or path that bypasses the repository's ignore rules — a `.env`, a dump, a
  service-account JSON, an editor or tooling directory.
- Encryption and hashing choices: a password stored with a general-purpose hash rather
  than a memory-hard password hash, a secret compared with a non-constant-time
  comparison, a nonce or initialisation vector reused, a key checked into configuration
  rather than fetched from a secret store.

## Unsafe defaults

A default is unsafe when omission produces the permissive behaviour, because omission is
what happens at three in the morning in the next service that copies this code.

| Default | Safe form |
| --- | --- |
| Certificate or hostname verification disabled, usually to unblock a local environment | Verification on, with the local case solved by a trusted local certificate rather than by a flag that ships |
| A wildcard cross-origin policy, or one reflecting the request origin, especially with credentials allowed | An explicit origin list; credentials never combined with a reflected origin |
| Debug mode, verbose errors, a profiler endpoint or an administrative console enabled by configuration that defaults on | Off by default, switched on only by explicit opt-in that cannot be set in the production profile |
| A new endpoint added outside the authenticated route group | Authentication applied at the group with an explicit, named opt-out list, so a new route is guarded by omission |
| Cookies without Secure, HttpOnly and SameSite attributes, HttpOnly being the one that keeps injected script from reading a session cookie and the one most often absent from a diff | All three set at the point the cookie is created, not in a wrapper the next caller may not use, with host-only as a fourth wherever no subdomain needs the cookie |
| Temporary files or directories created with broad permissions | Created with the restrictive mode at creation time; a later permission change leaves a window |
| An unbounded request body, page size, upload or recursion depth | A cap, chosen and written down, so that resource exhaustion needs more than one request |
| A new queue, bucket, topic or cache created with open access for convenience | Closed at creation; anything else is a configuration nobody revisits |
