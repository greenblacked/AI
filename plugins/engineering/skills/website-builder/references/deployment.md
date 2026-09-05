# Deployment

Read this after step A6 has established where the site should live and why. The goal is
a site the owner can operate without the person who built it: deployed by a pipeline,
rolled back without a rebuild, and documented in a runbook short enough to actually be
read.

## Contents

- [Choosing a host](#choosing-a-host)
- [Build output and caching](#build-output-and-caching)
- [Domains, DNS and TLS](#domains-dns-and-tls)
- [Environments and secrets](#environments-and-secrets)
- [Preview deployments](#preview-deployments)
- [CI/CD](#cicd)
- [Rollback](#rollback)
- [Analytics and error reporting](#analytics-and-error-reporting)
- [Uptime checking](#uptime-checking)
- [The runbook](#the-runbook)

## Choosing a host

Match the host to what the build actually needs. The most common mistake in this step is
buying capability the site will never use and paying for it in complexity every month
afterwards.

| Need | Host shape | Examples | Cost shape | Trade-off |
| --- | --- | --- | --- | --- |
| Tier 1-2, static files | Object storage behind a CDN | Cloudflare Pages, Netlify, GitHub Pages, S3 + CloudFront | Free to a few dollars; bandwidth-metered at scale | No server logic at all; forms and search need a third party |
| Tier 2-3, static plus a little dynamic | CDN plus edge functions | Cloudflare Workers, Netlify/Vercel functions | Free tier, then per-million-requests | Constrained runtime, no long-lived connections, cold starts, vendor-shaped APIs |
| Tier 4, a real server process | Managed container platform | Fly.io, Railway, Render, App Runner | Per-instance per-month, roughly $5-25 for a small app | You own the image, the health checks and the restarts |
| Tier 4 with unusual dependencies, or a hard cost ceiling | A VPS you administer | Hetzner, DigitalOcean, Lightsail | Flat $5-40/month, predictable | You own patching, TLS renewal, backups, monitoring, and the 3am reboot |
| Existing platform team, existing cluster | Whatever they already run | Kubernetes, ECS, an internal PaaS | Already paid for | Their conventions win; do not introduce a second way of deploying |

Two honest observations to offer the user:

- A static site behind a CDN is the cheapest, fastest and most available option
  available, and it has no runtime to be compromised. If the brief fits it, say so even
  when the user asked for something larger.
- A VPS is not cheaper than a managed platform once the owner's time is priced in. It is
  cheaper in cash and more expensive in attention. That is the right trade for some
  people and the wrong one for most.

## Build output and caching

The caching rule that matters: **hashed assets are immutable and cached forever; HTML is
never cached.** Get this backwards and either users see a stale site for a year, or the
CDN is bypassed on every request.

```text
# Netlify / Cloudflare Pages: _headers
/assets/*
  Cache-Control: public, max-age=31536000, immutable

/*.html
  Cache-Control: public, max-age=0, must-revalidate

/
  Cache-Control: public, max-age=0, must-revalidate
```

```nginx
location ~* \.(js|css|woff2|avif|webp|png|svg)$ {
    add_header Cache-Control "public, max-age=31536000, immutable";
}
location / {
    add_header Cache-Control "public, max-age=0, must-revalidate";
    try_files $uri $uri/ /index.html;
}
```

Bundlers emit `app.4f3a91c2.js` by default; keep that on. The hash is what makes
`immutable` safe — a changed file gets a new name, so there is nothing to invalidate.
Purge the CDN for HTML on deploy if the platform does not do it automatically, and set
the security headers from the quality-floor reference in the same configuration file
while you are in it.

For a container, serve with nginx or Caddy from a small final image:

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
HEALTHCHECK CMD wget -qO- http://localhost/ >/dev/null || exit 1
```

## Domains, DNS and TLS

| Record | Use |
| --- | --- |
| `A` / `AAAA` | Apex domain to an IP. Needed for a VPS |
| `CNAME` | Subdomain to a platform hostname (`www` → `site.pages.dev`) |
| `ALIAS` / `ANAME` / CNAME flattening | Apex domain to a platform hostname, where the registrar supports it |
| `TXT` | Domain verification, SPF/DKIM if the site sends mail |
| `CAA` | Restricts which CAs may issue for the domain. Cheap, worth setting |

Pick one canonical host — `www` or apex — and 301 the other to it, permanently.
Serving both means split analytics, split SEO signals, and cookie scope surprises.

TLS: every managed platform issues and renews automatically; leave it alone. On a VPS,
Caddy does it with no configuration, and certbot does it with a renewal timer that must
be verified rather than assumed:

```bash
sudo certbot --nginx -d example.com -d www.example.com
sudo certbot renew --dry-run          # confirm renewal actually works
systemctl list-timers | grep certbot  # confirm the timer is enabled
```

An expired certificate is the single most common self-inflicted outage on a
self-managed host. Add expiry to the uptime check, not just reachability.

## Environments and secrets

Three environments is the useful number: local, preview (per pull request), production.
A staging environment that nobody keeps current is worse than none, because it produces
confident answers about a system that no longer exists.

| Value | Where it lives |
| --- | --- |
| Local development | `.env.local`, gitignored, generated from `.env.example` |
| Preview and production | The host's or CI provider's secret store |
| Anything in the client bundle | Public by definition — see the app-architecture reference |

Rules worth stating to the owner: production credentials never appear in a preview
environment, because previews run untrusted branch code; secrets are set once in the
platform and referenced by name in CI, never pasted into a workflow file; and any secret
that reaches a commit, a log line, or a client bundle is rotated rather than deleted.

```bash
gh secret set DEPLOY_TOKEN --body "$(pbpaste)"    # not committed, not echoed
```

## Preview deployments

Every pull request gets its own URL, built from that branch. This changes review quality
more than any process change available: a reviewer clicks a link and uses the thing,
instead of reading a diff and imagining it. Non-technical stakeholders can review without
running anything. Visual regressions get caught by people, before merge, which is where
they are cheap.

Cloudflare Pages, Netlify and Vercel do this by default once the repository is
connected. On other hosts, deploy the branch to a path or subdomain keyed by PR number
and post the URL as a comment. Add `X-Robots-Tag: noindex` to preview deployments so
they never appear in search results.

## CI/CD

Minimum viable pipeline: build, run the quality checks, deploy on merge to the default
branch. If checks do not gate the deploy, they are documentation.

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push: { branches: [main] }
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '22', cache: 'npm' }
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm test -- --run
      - run: npm audit --audit-level=high
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with: { name: dist, path: dist/, retention-days: 30 }

  a11y-and-perf:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: treosh/lighthouse-ci-action@v12
        with:
          urls: ${{ github.event_name == 'pull_request'
                    && needs.build.outputs.preview_url || 'https://example.com' }}
          budgetPath: ./lighthouse-budget.json
          uploadArtifacts: true

  deploy:
    needs: [build, a11y-and-perf]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/download-artifact@v4
        with: { name: dist, path: dist }
      - run: npx wrangler pages deploy dist --project-name=example
        env:
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
```

The same shape in GitLab CI is `stages: [build, verify, deploy]` with `only: [main]` on
the deploy job and artifacts passed between stages. Pin action versions, scope the deploy
token to one project, and deploy the artifact that was tested rather than rebuilding in
the deploy job — a rebuild is a different set of bits than the one the checks passed.

## Rollback

**The rollback path must not depend on rebuilding.** A rebuild takes minutes, needs the
build to still be reproducible, and can fail for reasons unrelated to the bad deploy —
all while the site is broken.

| Host | Rollback |
| --- | --- |
| Cloudflare Pages / Netlify / Vercel | Promote the previous deployment in the dashboard or CLI; each build is retained and immutable |
| Container platform | Redeploy the previous image tag or digest, which still exists in the registry |
| VPS | Symlink the document root to the previous release directory |

```bash
# keep-last-5 release layout on a VPS
/srv/site/releases/2026-08-04T1210Z/
/srv/site/current -> releases/2026-08-04T1210Z
ln -sfn /srv/site/releases/<previous> /srv/site/current && systemctl reload nginx
```

Tag every production release and record which commit is live. "Roll back to the last
good version" is only actionable if someone can name it. Where the deploy included a
database migration, the rollback plan covers the schema too — which is why migrations
should be forward-compatible for one release.

## Analytics and error reporting

Choose tools that answer a question the owner actually has. "How many people read the
pricing page" needs page views; it does not need a session recorder or a cross-site
identity graph.

- **Analytics:** Plausible, Fathom, Umami, or Cloudflare Web Analytics. Cookieless,
  aggregate, roughly 1 KB of script, and in most jurisdictions no consent banner is
  required because no personal data is stored. Google Analytics brings a consent
  obligation, a heavier script, and a data-sharing question the owner has to answer.
- **Errors:** Sentry or GlitchTip. Turn off session replay unless it is genuinely needed,
  scrub PII before send, upload source maps in CI and do not serve them publicly.

```js
Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  tracesSampleRate: 0.1,
  sendDefaultPii: false,
  beforeSend: (event) => (stripQueryStrings(event)),
});
```

Whatever is chosen, name it in the privacy policy and describe what it collects. A site
that measures its visitors without saying so is a legal problem before it is an ethical
one.

## Uptime checking

An external check, not a check that runs on the machine being checked. Free tiers from
UptimeRobot, Better Stack or Cloudflare health checks are enough for a small site.

Check the thing that matters, not just a 200: request a URL that exercises the real path
(a page that reads the database, for an app), assert on content, alert on certificate
expiry, and send alerts somewhere a human will see them at the time of day the site
matters.

```bash
# minimal self-hosted equivalent, run from elsewhere
curl -fsS --max-time 10 https://example.com/health | grep -q '"ok":true' \
  || notify "example.com health check failed"
```

## The runbook

Ship this with the site, in the repository, as `RUNBOOK.md`. It is the difference
between a site the owner controls and one they depend on you for.

```markdown
# Runbook — example.com

**Live at:** https://example.com  |  **Host:** Cloudflare Pages, project `example`
**Repository:** github.com/owner/example  |  **Domain registrar:** …
**Owner contact for billing/DNS:** …

## Deploy
Merge to `main`. The pipeline builds, runs checks, and deploys. Takes ~3 minutes.
Watch: github.com/owner/example/actions

## Roll back
Cloudflare dashboard → Pages → example → Deployments → previous → "Rollback".
Takes ~30 seconds and does not rebuild.

## Edit content
[Where the content lives and how to change it — a file path, a CMS URL, or "ask a
developer" if that is honestly the answer.]

## Certificates
Managed by the host, renewed automatically. Nothing to do.

## When something is wrong
1. Is it up? https://example.com — and check the status page for the host.
2. Recent deploy? Roll it back first, diagnose afterwards.
3. Errors: [Sentry project URL]
4. Traffic anomaly: [analytics URL]

## Costs
Hosting $0/month up to 100k requests. Domain $12/year, renews [date].
Sentry free tier, 5k events/month.

## Who to contact
[Name, and what they own.]
```
