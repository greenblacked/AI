# App architecture (tier 3 and tier 4)

Read this once the tier is 3 or 4. Tier 1 and 2 need none of it, and importing these
patterns into a static site is how a landing page ends up with a build pipeline nobody
asked for.

## Contents

- [Pick the framework from the requirements](#pick-the-framework-from-the-requirements)
- [Project structure](#project-structure)
- [Routing](#routing)
- [State](#state)
- [Data fetching](#data-fetching)
- [Forms and validation](#forms-and-validation)
- [Auth](#auth)
- [API design](#api-design)
- [Persistence and migrations](#persistence-and-migrations)
- [Environment configuration and secrets](#environment-configuration-and-secrets)
- [Backend-as-a-service](#backend-as-a-service)

## Pick the framework from the requirements

The rendering strategy follows from two questions: where the data comes from, and how
much of the page changes without a navigation. Answer those and the framework falls
out. Answering them the other way round — picking Next.js and then discovering the site
has no dynamic data — is how a brochure ends up with a Node process to keep alive.

| Data | Interactivity | Shape | Typical pick |
| --- | --- | --- | --- |
| Known at build time | Links, a menu, a form post | Static generation | Astro, Eleventy, Hugo, plain files |
| Known at build time | Islands of real interactivity | Static plus hydrated islands | Astro with React/Svelte islands |
| Per-request, SEO matters | Moderate | Server rendering | Next.js, Remix, SvelteKit, Rails/Django with Hotwire |
| Per-user, behind a login | High, app-like | SPA against an API | Vite + React/Svelte/Vue |
| Per-request and per-user | High, SEO matters on public pages | Hybrid: SSR public, SPA-ish app | Next.js App Router, SvelteKit |

Two clarifying rules:

- **If it can be rendered at build time, render it at build time.** A CDN serving a
  file is faster, cheaper, and more available than any server you can configure, and it
  cannot have a runtime error.
- **Progressive enhancement is a legitimate answer at tier 4.** A server-rendered app
  with forms that work without JavaScript, plus a small amount of script for the parts
  that benefit, is less code and fewer failure modes than a SPA reimplementing
  navigation, history, focus management and error handling.

Say the choice and the reason in one line before writing code: "Astro, because all
eleven pages are build-time content and only the pricing toggle needs JavaScript."

## Project structure

Organize by feature once the app has more than roughly ten components. Organizing by
kind — `components/`, `hooks/`, `utils/` — reads fine at twenty files and becomes a
scavenger hunt at two hundred, because every change to one feature touches four
directories.

```text
src/
  routes/                 # or app/ or pages/ — one file per URL, thin
  features/
    invoices/
      InvoiceList.tsx
      InvoiceForm.tsx
      api.ts             # data access for this feature only
      schema.ts          # shared client/server validation
      types.ts
  components/ui/          # genuinely generic: Button, Dialog, Field
  lib/                    # framework-agnostic helpers, no React imports
  styles/tokens.css       # the chosen direction's tokens, defined once
```

Route files stay thin: resolve params, call the feature's data layer, render the
feature component. Business logic in a route file cannot be tested or reused.

## Routing

- URLs are the app's public API. `/invoices/2024-03` survives a refactor; `?view=3`
  does not.
- Put filter, sort and pagination state in the query string. It makes the view
  linkable, shareable and back-button-correct for free.
- Every route needs three states designed, not two: loaded, loading, and failed. Add
  the empty state where a list can be empty.
- Code-split at the route boundary. Anything else is premature until a bundle report
  says otherwise.
- Restore focus and scroll on client-side navigation, and move focus to the new page's
  heading — a SPA silently breaks screen-reader navigation otherwise.

## State

Most "state management problems" are data-fetching problems wearing a costume. Separate
the two before reaching for anything:

| Kind | Example | Where it belongs |
| --- | --- | --- |
| Server data | Invoice list, current user | A query cache (TanStack Query, SWR, framework loaders) |
| URL state | Filters, tab, page number | The query string |
| Form state | Field values, dirty, errors | The form library or local component state |
| Ephemeral UI | Dialog open, hovered row | `useState` in the nearest common ancestor |
| Genuine global client state | Theme, feature flags, an editor document | Context, or a store once it is genuinely shared |

A client state library earns its place when the same non-server state is written from
several unrelated parts of the tree and read in several more, and prop drilling or
context has started causing re-render problems you can measure. Until then Zustand,
Redux or Jotai add indirection to solve a problem the app does not have. When you do
reach for one, say what it is holding and why context was not enough.

## Data fetching

Loading and error states are part of the feature, not polish added later. A component
that renders nothing while pending and crashes on failure is unfinished.

```tsx
const { data, isPending, error, refetch } = useQuery({
  queryKey: ['invoices', { status, page }],
  queryFn: () => fetchInvoices({ status, page }),
  staleTime: 30_000,
});

if (isPending) return <InvoiceListSkeleton rows={8} />;
if (error) return <ErrorState message="Could not load invoices." onRetry={refetch} />;
if (data.length === 0) return <EmptyState action={<NewInvoiceButton />} />;
```

Rules that survive contact with production:

- **Key the cache by every input that changes the result.** A missing filter in the key
  serves one user another user's data after a login switch.
- **Skeletons should match the shape of the real content**, otherwise the layout jumps
  when data arrives and you have manufactured a CLS problem.
- **Error states need a retry and a plain-language message.** "Request failed with
  status code 500" is a log line, not UI copy.
- **Cancel or ignore stale responses.** Type-ahead search without cancellation renders
  whichever request happened to finish last.

### Optimistic updates

Use them where the action almost always succeeds and the wait is annoying: toggling a
like, checking a checkbox, reordering a list. Do not use them where failure is plausible
or expensive — payments, deletes, anything with a server-side rule the client cannot
evaluate.

```tsx
useMutation({
  mutationFn: toggleStar,
  onMutate: async (id) => {
    await queryClient.cancelQueries({ queryKey: ['invoices'] });
    const previous = queryClient.getQueryData(['invoices']);
    queryClient.setQueryData(['invoices'], (old) => withStarToggled(old, id));
    return { previous };            // rollback handle
  },
  onError: (_err, _id, ctx) => {
    queryClient.setQueryData(['invoices'], ctx.previous);
    toast('Could not save that. Restored.');
  },
  onSettled: () => queryClient.invalidateQueries({ queryKey: ['invoices'] }),
});
```

The rollback path and the user-visible message are the whole point. An optimistic update
without them is a lie the UI tells that nobody corrects.

## Forms and validation

Validate on the client for speed and on the server for correctness. Share one schema so
the two cannot drift.

```ts
// features/invoices/schema.ts — imported by the form and the route handler
export const InvoiceInput = z.object({
  amountCents: z.number().int().positive().max(100_000_00),
  dueDate: z.coerce.date().min(new Date()),
  note: z.string().max(500).optional(),
});
```

**Client-side-only validation is a security bug, not a UX shortcut.** The client is
attacker-controlled: anyone can post to the endpoint directly with `curl`, and the
validation code you shipped is a hint about the rules, not an enforcement of them.
Every handler re-parses its input server-side and rejects on failure, regardless of what
the form does.

Beyond that:

- Validate on blur and on submit, not on every keystroke — per-keystroke errors tell
  users they are wrong while they are still typing.
- Errors go next to the field, referenced by `aria-describedby`, and the first invalid
  field receives focus on failed submit.
- Disable the submit button only while the request is in flight, never as a substitute
  for showing what is wrong.
- Rate-limit anything that sends mail, creates accounts, or costs money per call.

## Auth

Pick by where the client runs, not by what is fashionable.

| Situation | Use | Why |
| --- | --- | --- |
| Browser app, same site or subdomain as the API | Session cookie | The browser sends it automatically; it can be `HttpOnly`, so script cannot read it |
| Third-party API, mobile client, service-to-service | Bearer token | No cookie jar, no CSRF surface, explicit expiry |
| Browser app against a cross-origin API you control | Cookie on a shared parent domain, or a short-lived token held in memory with a refresh cookie | Avoids persisting anything script can read |

Cookie flags, all three, always:

```text
Set-Cookie: sid=…; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=1209600
```

`HttpOnly` keeps XSS from stealing the session. `Secure` keeps it off plaintext HTTP.
`SameSite=Lax` blocks the cross-site request forgery cases that matter while still
allowing top-level navigation into the site. Use `SameSite=None; Secure` only when a
genuine cross-site flow needs it, and add CSRF tokens when you do.

**CSRF:** any state-changing request authenticated by a cookie needs either
`SameSite=Lax`/`Strict` plus a same-origin check on `Origin`, or a per-session CSRF
token echoed in a header. `GET` must never change state — that is what makes the
`SameSite` guarantee hold.

**Do not store tokens in `localStorage`.** It is readable by every script on the
origin, including anything an injected or compromised dependency runs, and it has no
expiry. A stolen token in `localStorage` is a silent, persistent account takeover. If a
token must live in the browser, hold it in a module-scoped variable for the lifetime of
the page and refresh it from an `HttpOnly` cookie.

Other things that matter more than the token format: hash passwords with argon2id or
bcrypt, rotate the session identifier on login and on privilege change, expire sessions,
and give users a way to revoke them.

## API design

Design the API for the pages that exist. A generic resource API that forces the invoice
page to make five round trips is worse than one endpoint that returns exactly what the
invoice page renders.

- Consistent envelope for errors, with a machine-readable code and a human message.
- Correct status codes: 400 for a malformed request, 401 unauthenticated, 403
  authenticated but not allowed, 404 for a resource that is absent *or* that this user
  may not know exists, 409 conflict, 422 for a semantically invalid body.
- Paginate every list endpoint from day one. Retrofitting pagination breaks clients.
- Version when you have external consumers; do not version an API only your own frontend
  calls, because you can change both at once.
- Authorize per record, not per route. "Is this user logged in" is not "is this user
  allowed this invoice", and the gap between them is the most common real vulnerability
  in an app of this size.

## Persistence and migrations

| Need | Choose |
| --- | --- |
| Relational data, transactions, reporting | Postgres. This is the default; deviate with a reason |
| A single-file store for a small app or a prototype | SQLite (with Litestream or a managed service if it must survive the host) |
| Cache, rate limits, ephemeral session data | Redis |
| Blobs, uploads, generated files | Object storage, never the database |

Schema changes go through checked-in migration files, applied by the deploy pipeline,
never by hand against production:

```bash
npx prisma migrate dev --name add_invoice_due_date   # authoring, local
npx prisma migrate deploy                            # CI, on the way to production
```

Write migrations to be forward-compatible for one release: add a nullable column,
deploy code that writes both, backfill, then make it non-nullable. A migration that
requires code and schema to change in the same instant means downtime or a failed
rollback.

## Environment configuration and secrets

**Anything shipped to the browser is public.** A `NEXT_PUBLIC_`, `VITE_` or `PUBLIC_`
prefix does not protect a value; it marks it as intentionally published. Minification is
not obfuscation — the string is in the bundle, and `view-source` is enough to find it. A
Stripe secret key, a database URL, or an admin API token placed in a client-side
environment variable is disclosed the moment the site deploys.

What is safe to expose: publishable keys designed for it (`pk_live_…`), analytics site
IDs, public API base URLs, feature flags that are not security boundaries. What is not:
anything labelled secret, service role, or private, and anything whose scope you cannot
describe in one sentence.

```ts
// config.ts — parse once at startup and fail loudly, rather than reading
// process.env in twenty places and discovering the gap in production
export const config = ServerEnv.parse(process.env);
```

Keep `.env.example` in the repository with every key and a comment, keep `.env` out of
it, and hold real values in the host's secret store. If a secret ever reaches a client
bundle or a commit, rotate it — deleting the commit does not unpublish it.

## Backend-as-a-service

Supabase, Firebase, Clerk, PocketBase and similar are a good trade when the app is
mostly CRUD plus auth, the team is one person, and time to first deploy matters more
than control. You get auth, a database, storage, and realtime without operating any of
it.

What you give up, stated honestly to the user before choosing:

- **Authorization moves into the vendor's policy language.** Row-level security rules
  are real code with real bugs, and they are the only thing between a public anon key
  and the whole table. Test them like code.
- **Data access from the browser means your query shape is your API**, and it is
  visible. Anything the policy allows, a user can run.
- **Pricing is per-usage and the cliff is steep** once a project outgrows the free tier.
- **Migration is expensive.** The auth system especially — password hashes and user IDs
  are the sticky part.

Take it for internal tools, prototypes, and small products. Avoid it where the domain
logic is the product, where compliance requires data residency you cannot get, or where
the write path needs transactions across several tables.
