# Variables, runners, cache and artifacts

Contents: variable scope and protection, masking, OIDC, runners and tags, cache versus artifacts.

Variable and runner features differ by GitLab version and edition. Check docs.gitlab.com
for the version in use; do not rely on remembered limits.

## Why a variable is empty

Work down this list; the first hit is usually the answer.

1. The variable is protected and the pipeline ref is not a protected branch or tag.
   Fix by protecting the ref, or splitting the variable per environment.
2. The variable is scoped to an environment and the job has no matching `environment:`.
3. The variable is set at the group or instance level and the project or a CI setting
   overrides or restricts it.
4. A merge request pipeline from a fork runs in the fork's context; project secrets are
   not available there by design.
5. A job-level or file-level `variables:` entry shadows it. Check precedence in the docs.
6. A typo: an undefined variable expands to an empty string with no error.

Inspect by printing names only in a temporary job (for example
`awk 'BEGIN { for (k in ENVIRON) print k }' | sort`), never values. `env | cut -d= -f1`
is not names-only: it prints the continuation lines of a multi-line value such as a PEM
key. Never turn on `CI_DEBUG_TRACE` to find a value, because it prints secrets
into the log.

## Exposure

- Masked redacts the exact value from logs; it needs a value that fits the masking
  format and does not stop a script from encoding and printing it. It is a log filter,
  not a boundary.
- Prefer `id_tokens:` with OIDC to the cloud provider over a stored key; the token is
  short-lived and bound to project and ref claims the provider can check.
- Use file-type variables for certificates and kubeconfigs rather than echoing them
  into files.
- Rotate on exposure: a value printed in a log, an artifact or a merge request comment
  is leaked until rotated, whatever the masking did. Route to `secret-rotation`.

## Runners and tags

- A job with `tags:` runs only on runners holding all of them. A job waiting
  indefinitely with "no runners available" is usually a tag no online runner has, or a
  runner restricted to protected refs.
- Dedicate runners with deployment credentials to protected refs and protected tags only
  (the runner's protected setting), so an unreviewed branch cannot schedule onto them.
- Pin job images by digest or an immutable tag. `latest` changes under the pipeline.
- Prefer ephemeral or autoscaled runners for untrusted code; a long-lived shell runner
  keeps state between jobs.

## Cache versus artifacts

| Use | Cache | Artifacts |
| --- | --- | --- |
| Purpose | Speed up a job by reusing downloaded dependencies | Pass results between jobs and keep outputs |
| Guarantee | Best effort; may be missing or stale | Stored with the pipeline; reliable |
| Scope | Per runner or distributed store, keyed | Per job, passed via `needs:` or stage order |
| Key | Set `cache:key` from the lockfile (`key:files`) | `expire_in` to bound storage |

Never pass a build result between jobs through the cache: a missing cache turns into a
mystery failure. Do not publish secrets or `.env` files as artifacts; artifacts of a
public project can be downloaded by anyone who can see the pipeline. Set `expire_in`
explicitly, and use `artifacts:reports` for test and coverage reports. Use `dependencies:`
or `needs:` to restrict which earlier artifacts a job downloads.
