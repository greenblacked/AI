---
name: website-builder
description: Design and build a complete website scaled to the brief — from a single landing page to a full web app — or audit an existing one and deliver prioritized improvements. Building runs an intake, picks the build tier, presents 2-3 design directions to choose from before any code is written, meets a quality floor, and adds deployment artifacts when needed. Auditing covers UI/UX, accessibility, performance, security, SEO, code health, CI/CD, stability and observability, ranks findings by impact and effort, and implements fixes on request. Use whenever the user asks for a website, landing page, portfolio, blog, marketing site, dashboard, web app or any browser-facing UI — "build me a site for X", "I need a page for Y", "make a web app that does Z" — and equally when they point at a site that already exists and ask to review it, improve it, redesign it, make it faster, make it more secure, or fix its pipeline. Not for an isolated UI component, a backend-only service, or a general question about web technology.
---

# Website Builder

Build sites that look like someone designed them for this specific subject and can actually be deployed and maintained afterwards — and, where a site already exists, find what is genuinely costing its owner something and fix that rather than everything.

Two failure modes bracket the build side. One is a beautiful page that nobody can host, has no responsive behaviour below 900px, and breaks on keyboard navigation. The other is a technically sound page that looks like every other generated site — cream background, big serif headline, terracotta accent, three feature cards. This skill exists to avoid both: gate the design before writing code, then build it to a real quality floor and hand it over with the deployment story attached.

## Design direction

The aesthetic thinking — distinct directions, palette construction, type and spacing scales, avoiding default looks, copywriting in interfaces — lives in the "Design direction" section of `references/quality-floor.md`. Read it during step A3 rather than reinventing it here. The rest of this skill owns scoping, tier routing, the build, the quality floor, auditing, and delivery.

## Two modes

Decide which one applies before doing anything else, and say which was chosen.

- **Mode A — Build.** Nothing exists yet, or the user wants a replacement built from scratch. Follow the build workflow below.
- **Mode B — Improve.** A site already exists and the user wants it reviewed, fixed, sped up, hardened, redesigned, or its pipeline improved. Skip to the improve workflow.

A redesign of an existing site usually starts in Mode B — audit first, because the existing site holds the content, the constraints, and the list of things not to repeat — then moves into Mode A step A3 for the new direction. Say when the handover happens.

## Mode A: Build a new site

Steps A1 and A3 are gates. Do not write production code before the user has chosen a design direction — rebuilding a finished site because the direction was wrong wastes far more time than a short pause does.

### Step A1: Intake

Ask in one batch, and ask why as well as what. The reason behind a requirement usually changes the correct answer: someone asking for Kubernetes hosting for a five-page marketing site is describing a habit, not a requirement, and object storage behind a CDN will be cheaper, faster, and less to maintain. Surface that trade-off rather than silently building what was asked for.

Ask about:

- **Subject and job.** What is this for, and what is the single thing a visitor should do? A site with no defined job becomes a template.
- **Audience.** Who lands on it, and what do they already know? This drives tone, density, and vocabulary.
- **Content.** Does real copy, imagery, or data exist, or should it be written? If it must be written, say so up front — invented content shapes the layout.
- **Interactivity.** Read-only, or does it accept input, hold state, call an API, require accounts?
- **Content updates.** Never, occasional hand edits, or frequent enough to need a CMS or a content pipeline?
- **Hosting and constraints.** Where will it live, what already exists, what is the budget and the traffic shape, and why. Also: domain, analytics, compliance obligations.
- **Anything fixed.** Existing brand, colours, fonts, a design system, or a site being replaced. Fixed constraints always win over this skill's preferences.

When the user has already answered most of this in their request, do not re-ask it. Confirm the gaps only, and state assumptions for anything minor.

### Step A2: Classify the tier

The tier decides the stack and the file layout. Choose the lowest tier that satisfies the brief — every step up adds build tooling, dependencies, and maintenance that someone pays for later.

| Tier | Fits when | Build as |
| --- | --- | --- |
| 1 — Single page | One page, static content, no routing | One self-contained HTML file with inline CSS and minimal JS |
| 2 — Static site | Several pages, static or build-time content, no user state | Separate HTML/CSS/JS files, shared partials, or a static generator |
| 3 — Client app | Real interactivity, client state, routing, API consumption | Vite + React (or the framework already in use), component structure |
| 4 — Full stack | Accounts, persistence, server-side logic, SEO-critical dynamic pages | Next.js or a framework plus a separate API, with a real data layer |

Announce the tier and the one-line reason before building. If the brief sits between two tiers, choose the lower one and say what would push it up.

For tier 3 and 4, read `references/app-architecture.md` before writing code.

When the deliverable is a previewable artifact inside a chat interface rather than files on disk, keep tier 1 and 2 output to a single self-contained file, and respect that environment's constraints — in Claude.ai artifacts specifically, browser storage APIs are unavailable and only core Tailwind utility classes work.

### Step A3: Present design directions, then stop

Read the "Design direction" section of `references/quality-floor.md` first. Then produce **two or three genuinely different directions**, not one idea in three colourways. Each direction gets:

- **Name and thesis** — one sentence on the point of view, tied to this subject
- **Palette** — 4 to 6 named hex values
- **Type** — display face and body face, named, with the reason for the pairing
- **Layout** — one or two sentences plus a short ASCII wireframe of the hero and first section
- **Signature** — the single element this site would be remembered by
- **Trade-off** — what this direction is worse at, honestly

Then stop and ask which one to build. Do not build all three, do not start coding the one that seems best, and do not merge them into a compromise unless the user asks for a mix.

Before presenting, check each direction against the brief: if a direction is what would be produced for any similar subject, replace it. Two strong distinct directions beat three where one is filler.

### Step A4: Build the chosen direction

Derive every colour, size, and type decision from the chosen direction's tokens. Define them once as CSS custom properties or theme config and reference them everywhere, so a later change is one edit rather than a search.

Use the real subject matter throughout. Lorem ipsum, "Feature One / Feature Two / Feature Three", and stock placeholder headlines all produce layouts that collapse the moment real content arrives. Write real copy for this subject.

Watch CSS specificity when hand-writing styles — competing element-level and class-level selectors cancelling each other out is the most common source of mysterious spacing bugs in generated sites.

### Step A5: Meet the quality floor

Non-negotiable regardless of tier, because retrofitting any of it is disproportionately expensive. The detail and the checks are in `references/quality-floor.md`; read it before finishing the build. In summary: responsive down to 360px, visible keyboard focus and correct semantics, `prefers-reduced-motion` respected, images sized and lazy-loaded below the fold, meta and Open Graph tags present, and no console errors.

### Step A6: Deployment, only if wanted

Ask before producing infrastructure. A user who wanted a landing page does not want a Dockerfile, and a user who has a GitLab runner and a GKE cluster does not want a Cloudflare tutorial.

Ask what they want to deploy to and why, then read `references/deployment.md` for the matching setup — static hosting behind a CDN, a container with nginx or Caddy, a GitLab CI pipeline, or a Kubernetes deployment. That file also covers which option genuinely fits which tier, so an over-specified answer can be pushed back on with a reason.

### Step A7: Hand off

```markdown
## What this is
[The subject, the job of the site, the tier and why.]

## Direction
[The chosen direction, one line, with its palette and type recorded so it can be extended later.]

## Files
[Each file with a one-line purpose.]

## Run it locally
[Exact commands, including the dev server and the production build.]

## Quality checks
[What was verified, what could not be verified in this environment, and the commands to verify it.]

## Deployment
[Only if produced. What it deploys to, what to change, what it costs to run.]

## What to customize
[Only genuinely environment-specific values, each with a reason.]
```

## Mode B: Improve an existing site

The output is a prioritized set of findings the user can act on, not a list of everything that could theoretically be better. A report with forty undifferentiated items gets read once and closed.

### Step B1: Gather what is actually available

Access determines how much can be assessed, so establish it first and be explicit about the limits.

| What the user provides | What can be assessed |
| --- | --- |
| A public URL | Rendered UI/UX, accessibility, performance, response headers, SEO, exposed client-side secrets |
| The repository | All of the above plus code health, dependencies, config, build setup |
| Repository and pipeline config | All of the above plus CI/CD, supply chain, release and rollback practice |
| Plus runtime access — logs, dashboards, infra | Stability, observability, cost, real traffic behaviour |

Never infer a finding from something not seen. "No CSP header" requires having checked the headers; "probably no CSP" is not a finding. When something cannot be checked, list it as unassessed with the command the user can run.

### Step B2: Agree the dimensions

Do not audit all nine dimensions by default — an unfocused audit buries the thing they actually care about. Ask which matter, and suggest a starting set from what they said. A "site feels slow" complaint starts with performance, stability, and hosting; "we're going through a security review" starts with security, supply chain, and CI/CD.

The dimensions, with what each covers, are in `references/audit.md`:

1. UI/UX and visual design
2. Accessibility
3. Performance
4. Security
5. SEO and metadata
6. Code health and maintainability
7. CI/CD and supply chain
8. Stability and resilience
9. Observability and cost

### Step B3: Audit

Work through the agreed dimensions using the checklists in `references/audit.md`. `references/quality-floor.md` is the baseline standard — a site failing an item there is a finding by definition.

Run real checks rather than reading the code and guessing. State which tools ran and which could not.

Record each finding with evidence: the file and line, the header that is missing, the measured number. A finding without evidence cannot be verified or argued with.

### Step B4: Report, ranked

Rank by impact against effort, and lead with what to do first. Use severity honestly — inflating everything to high destroys the ranking's usefulness.

```markdown
## Summary
[3-4 sentences: overall state, the single most important thing, what was and was not assessed.]

## Fix first
[Findings that are high impact and low effort. Usually 3-6 items.]

## Findings by dimension
### [Dimension]
**[Severity] — [One-line finding]**
- Evidence: [file:line, measured value, missing header]
- Impact: [what this costs in practice]
- Fix: [the specific change]
- Effort: [S / M / L]

## Deferred
[Real findings not worth acting on now, with the reason.]

## Not assessed
[What could not be checked and why, with the commands to check it.]
```

Severity means: **High** — actively harming users, security, or revenue now. **Medium** — real cost, no immediate damage. **Low** — worth doing when the file is open anyway.

### Step B5: Implement, on request

Ask which findings to act on before changing anything. Then work in reviewable batches grouped by area rather than one large sweeping change, so each batch can be verified and reverted independently.

Re-run the same checks after each batch and report the before and after numbers. An improvement claimed without a measurement is not an improvement.

Where a fix touches the visual design beyond small corrections, hand over to step A3 and present directions rather than redesigning unilaterally.

## Anti-patterns

**Building before the direction is chosen.** The most expensive mistake available here.

**Auditing everything at once.** Nine dimensions of undifferentiated findings is a document nobody acts on.

**Findings without evidence.** If it was not measured or seen, it is a suspicion, and it belongs under "not assessed".

**Rewriting instead of fixing.** "This should be rebuilt in Next.js" is rarely a finding. It is a separate proposal with its own cost, and it should be stated as one.

**The default AI look.** Cream background with high-contrast serif and terracotta accent; near-black with one acid accent; hairline-ruled broadsheet. Each is fine when the brief asks for it and a tell when it appears by default.

**Numbered markers on content that is not a sequence.** `01 / 02 / 03` on three unrelated features is decoration pretending to be structure.

**Placeholder content.** It hides the layout problems real content will expose.

**Reaching for a framework the brief does not need.** A five-page static site built as a React SPA loses SEO, adds a build step, and gains nothing.

**Animation everywhere.** Scattered scroll reveals on every element read as generated. One orchestrated moment lands harder.

**Skipping the mobile pass.** Most traffic is mobile; a desktop-only layout is unfinished, not merely imperfect.
