# Audit procedure (Mode B)

The job is to find what is genuinely costing the owner something and say so with
evidence. An audit that lists everything imaginable is easy to produce and impossible to
act on; the value is entirely in the ranking and the honesty about coverage.

## Contents

- [Gather evidence](#gather-evidence)
- [What makes a finding actionable](#what-makes-a-finding-actionable)
- [Dimension checklists](#dimension-checklists)
- [Ranking](#ranking)
- [Problem or preference](#problem-or-preference)
- [Stating coverage honestly](#stating-coverage-honestly)

## Gather evidence

### With only a URL

Everything below is observable from outside. Run it before forming any opinion.

Run the audit tools from a locked install, never through `npx`: when a package is not
already installed, `npx` fetches whatever the registry serves today and runs it, and
npm skips the prompt whenever standard input is not a terminal. Install them once, at
exact versions, into a directory of your own outside the project being audited, and
keep that directory's `package.json` and `package-lock.json` under your own version
control. Outside matters: `--prefix` makes the directory the npm project, so an `.npmrc`
the audited repository planted there could send the install to another registry. This set needs Node 22.22.2 or later on the 22
line, or 24.15 or later; Lighthouse and npm-check-updates set that floor:

```bash
T="${XDG_DATA_HOME:-$HOME/.local/share}/audit-tools"   # never inside the audited tree
npm install --prefix "$T" --save-exact --ignore-scripts \
  lighthouse@13.5.0 @axe-core/cli@4.14.0 pa11y@10.0.0 unlighthouse@0.19.1 \
  depcheck@1.4.7 npm-check-updates@23.1.1 source-map-explorer@2.5.3 webpagetest@0.7.6
npm ci --ignore-scripts --prefix "$T"              # every later run installs exactly that tree or fails
A="$T/node_modules/.bin"
CHROME=/usr/bin/chromium CHROMEDRIVER=/usr/bin/chromedriver   # paths vary by distribution
export CHROME_PATH="$CHROME"                                  # Lighthouse and unlighthouse
printf '{"chromeLaunchConfig": {"executablePath": "%s"}}\n' "$CHROME" > "$T/pa11y.json"
```

`--ignore-scripts` also skips the browser and driver downloads, so every browser tool
below is pointed at an installed Chrome: `CHROME_PATH` for Lighthouse and unlighthouse,
`chromeLaunchConfig.executablePath` in the `pa11y.json` written beside the tools, and
`--chrome-path` with a `--chromedriver-path` of the same `MAJOR.MINOR.BUILD` for axe,
which a browser and driver from one distribution release or one Chrome for Testing
version give you.

```bash
curl -sI https://example.com                          # status, headers, server
curl -s https://example.com | head -c 4000            # is it server-rendered at all
$A/lighthouse https://example.com --form-factor=mobile --throttling-method=simulate \
  --output=json --output-path=./lh.json
$A/axe https://example.com --chrome-path "$CHROME" --chromedriver-path "$CHROMEDRIVER"
$A/unlighthouse --site https://example.com            # whole-site sweep, if it is small
curl -s https://example.com/robots.txt
curl -s https://example.com/sitemap.xml | head -40
```

Then, in the browser: DevTools Network with cache disabled and throttling on, Console for
errors, Coverage for unused CSS and JS, Elements for the heading and landmark structure,
and Application → Storage for tokens sitting where script can read them. Search the
built JavaScript for credentials that should not be there:

```bash
# pull every script the page loads, then look for credentials in them
curl -s https://example.com | grep -oE 'src="[^"]+\.js"' | cut -d'"' -f2 |
  while read -r f; do curl -s "https://example.com/${f#/}"; done | grep -oE \
  '(sk_live_|rk_live_|AKIA|ghp_|xox[baprs]-|AIza)[A-Za-z0-9_-]{8,}'
```

What a URL cannot tell you: code quality, dependency health, pipeline practice, test
coverage, error rates, cost, and anything about a page behind a login. Say so rather
than inferring.

### With the repository

```bash
cloc .                                    # size and language mix
npm audit --audit-level=moderate
$A/depcheck                               # dependencies imported nowhere
$A/ncu                                    # how far behind
git log --oneline -20                     # release cadence and message quality
git log --format='%ad' --date=short -1    # is this maintained
ls .github/workflows .gitlab-ci.yml 2>/dev/null
npm run build && du -sh dist && $A/source-map-explorer 'dist/**/*.js'
grep -rInE '(api[_-]?key|secret|password|token)\s*[:=]' --include='*.{js,ts,tsx,env}' .
git log --all -p -S 'BEGIN PRIVATE KEY' | head    # secrets in history
```

Read the build config, the host config (`_headers`, `vercel.json`, `nginx.conf`,
`Dockerfile`), and the CI workflow. Those three files carry most of the security and
deployment findings.

### With runtime access

Ask for: error rates and top errors by volume, p50/p95 latency, uptime over 90 days,
the last three incidents and what caused them, the monthly bill by line item, and
whether backups have ever been restored. That last question finds more real risk than
any scanner.

## What makes a finding actionable

Four parts. A finding missing any of them gets sent back to be finished rather than
shipped.

| Part | Means | Bad | Good |
| --- | --- | --- | --- |
| Observation | What was seen, with the evidence attached | "Images could be optimized" | "`hero.png` is 2.4 MB, served at 1200px wide from a 4000px source" |
| Impact | The cost in the owner's terms, not the auditor's | "Hurts performance" | "LCP is 5.8s on a throttled mobile connection; this image is 71% of it" |
| Effort | S / M / L, with the reason if it is not obvious | "Should be fixed" | "S — one conversion command and a `srcset`" |
| Fix | The specific change, not the category | "Optimize images" | "`cwebp -q 80 hero.png -o hero.webp`, add `width`/`height` and `fetchpriority=high`" |

The impact line is where audits usually fail. "No CSP header" means nothing to a site
owner. "No CSP header, so any script injected through a comment field or a compromised
dependency can read the session and exfiltrate it — this is the control that limits the
blast radius of every other frontend vulnerability" is a decision they can make.

## Dimension checklists

Audit only the dimensions agreed in step B2. For each item, the evidence comes from the
command or tool named — not from reading the code and forming an impression.

### UI/UX and visual design

- First impression at 360px and at 1440px: is the job of the page obvious in five
  seconds, and is there one clear primary action?
- Visual system: is there a type scale and a spacing scale, or ad-hoc values? (Inspect
  computed styles on five headings and five gaps.)
- Consistency of buttons, links, form fields and states across pages.
- Content: real copy or placeholder residue; heading text that describes the section.
- Interaction states present — hover, active, focus, disabled, loading, empty, error.
- Evidence: screenshots at each breakpoint, and the specific selectors involved.

### Accessibility

Full standard in the quality-floor reference the skill lists; a failure there is a finding by
definition.

```bash
$A/axe https://example.com --tags wcag2a,wcag2aa,wcag22aa \
  --chrome-path "$CHROME" --chromedriver-path "$CHROMEDRIVER"
$A/pa11y --config "$T/pa11y.json" --standard WCAG2AA https://example.com
```

Plus the manual pass automation cannot do: tab the page end to end, confirm focus is
always visible and ordered, open and close a dialog with the keyboard, zoom to 200%,
check contrast on the three worst-looking pairs with a picker.

### Performance

```bash
$A/lighthouse https://example.com --form-factor=mobile --throttling-method=simulate
$A/webpagetest test https://example.com --location Dulles:Chrome --connectivity 3GFast
```

Report field data (Chrome UX Report, if the site has enough traffic) alongside lab data,
and say which is which — lab numbers are reproducible, field numbers are true. Check LCP
element identity, CLS sources, long tasks over 50ms, total transfer, render-blocking
resources, and unused bytes from the Coverage panel.

### Security

```bash
curl -sI https://example.com | grep -iE 'content-security|strict-transport|x-content|referrer|permissions'
npm audit --audit-level=high
```

Also: cookie flags on anything session-shaped, tokens in `localStorage`, secrets in the
bundle, `target="_blank"` without `rel="noopener"`, mixed content, `dangerouslySetInnerHTML`
or `innerHTML` on user data, forms posting cross-origin, exposed `.git`, `.env`,
`/admin`, source maps in production, and version headers volunteering the stack.
Grade the headers with MDN's HTTP Observatory or securityheaders.com in a browser; the
old `observatory-cli` package calls an API Mozilla has retired.

Do not run authenticated, intrusive or load-generating tests without written permission
from someone who owns the system. Say that plainly when the user asks for a
"penetration test".

### SEO and metadata

Crawl rather than sampling one page — duplicate titles across a site are invisible from
a single URL.

```bash
$A/unlighthouse --site https://example.com
curl -s https://example.com/sitemap.xml | grep -c '<loc>'
```

Check: unique title and description per page, canonical tags, Open Graph with an
absolute image URL, `robots.txt` not blocking anything important, sitemap listing live
URLs only, heading structure, internal linking, and structured data validated against
what is actually on the page.

### Code health and maintainability

- Test coverage and, more usefully, whether the tests assert anything meaningful.
- Dependency count, age, and how many are unused (`depcheck`).
- Type coverage; `any` density in a TypeScript project.
- Duplication, files over ~400 lines, functions over ~50.
- Dead code, commented-out blocks, and `TODO`s older than a year.
- Whether a new developer can run it: is there a README with working commands, and does
  a clean `npm ci && npm run build` succeed?

### CI/CD and supply chain

- Does a pipeline exist, does it gate merges, and does it run the checks it claims to?
- Is the deployed artifact the one that was tested, or a rebuild?
- Are action and image versions pinned? Are secrets scoped and rotated?
- Is there a lockfile, and is `npm ci` used rather than `npm install`?
- Is there a rollback path that does not rebuild? Has it ever been used?
- Preview deployments per pull request?

### Stability and resilience

- What happens when a dependency is down: does the page render, degrade, or blank out?
- Single points of failure — one instance, one region, one API key.
- Backups: existence, frequency, and whether a restore has been tested.
- Error handling on the request path; unhandled promise rejections in the console.
- Rate limits and abuse controls on anything that costs money per call.

### Observability and cost

- Is there error reporting, and is anyone reading it? What is the top error by volume?
- Uptime checks, and where alerts go.
- Logs: retained, searchable, free of PII.
- The bill by line item, with the largest line explained. Bandwidth, function
  invocations and always-on instances are the usual surprises.

## Ranking

Score impact and effort, then order by the ratio. Lead with the high-impact, low-effort
set — those are what the owner does this week, and shipping them buys credibility for
the larger items.

| | Low effort | High effort |
| --- | --- | --- |
| **High impact** | Fix first. Usually 3-6 items | Plan and schedule. Give a cost estimate |
| **Low impact** | Do while the file is open | Defer, and say why it is not worth it |

Severity is a claim about the present, not a wish about priority:

- **High** — actively harming users, security, or revenue right now.
- **Medium** — real cost, no immediate damage.
- **Low** — worth doing when the file is open anyway.

Inflating everything to High destroys the ranking, and the owner responds by ignoring all
of it. If a report has fifteen High findings, either the site is on fire or the severities
are wrong; say which.

## Problem or preference

Before writing any finding, answer: what does this cost, and who pays it?

| Preference | Problem |
| --- | --- |
| "The button radius should be 8px, not 4px" | "The button has no focus ring, so keyboard users cannot see where they are" |
| "Tailwind would be cleaner than this CSS" | "The same colour is hardcoded in 34 places, so a rebrand is a 34-file change with no single source of truth" |
| "This should be rewritten in Next.js" | "The product pages are client-rendered, so search engines index an empty shell — measurable in the crawl below" |
| "The copy could be punchier" | "The hero does not say what the product does; five of eight test readers could not name the category" |

Preferences are allowed, but they go in a clearly marked "Optional / taste" section
below the findings, without severity labels. Mixing them into the ranked list is how a
report loses the reader's trust: one arguable item makes them discount the rest.

Two specific disciplines:

- **A rewrite is not a finding.** "Rebuild this in Next.js" is a proposal with a cost,
  a risk and a migration plan. State it as one, separately, with an estimate.
- **A stack the auditor would not have chosen is not a defect.** jQuery in 2026 is a
  finding only if something concrete follows from it — an unpatched CVE, a bundle cost
  you measured, a bug it causes.

## Stating coverage honestly

Every report ends with what was not assessed and why. This is not a disclaimer; it is
the thing that makes the rest of the report trustworthy, because a reader who knows the
boundary can rely on what is inside it.

```markdown
## Not assessed
- **Authenticated areas** — no test account provided. Roughly 60% of the app by route
  count is unreviewed. To include it, provide a login and re-run.
- **Real-user performance** — the site has too little traffic for Chrome UX Report data,
  so all numbers here are lab measurements on simulated 4G. Field data would need RUM.
- **Backup restore** — confirmed backups are configured; nobody could confirm a restore
  has ever succeeded. Test one: `pg_restore` the latest snapshot into a scratch database.
- **Load behaviour** — no load test was run; running one against production without
  permission would be irresponsible.
```

Never write a finding from something not seen. "No CSP" requires having read the
headers. "Probably no CSP" is a suspicion, and suspicions belong in this section with
the command that would resolve them.
