---
paths:
  - ".gitlab-ci.yml"
  - "**/*.gitlab-ci.yml"
  - ".gitlab/ci/**/*.yml"
---

# GitLab CI rules

Each line says why, so a change that breaks one is a decision rather than a drift.

- Write `rules:`, not `only:` or `except:`. The two cannot be mixed in a job, and the legacy refs semantics differ for merge request pipelines.
- Keep a top-level `workflow:rules` that names which pipeline types exist. Without it a push to a branch with an open merge request can create two pipelines.
- Put `when: never` rules before the rule that includes a job; the first match wins, and a job with no match is silently not created.
- Mark a `needs:` entry `optional: true` when the needed job exists only under some rules; otherwise pipeline creation fails.
- Keep deployment credentials in protected, environment-scoped variables, and run deploy jobs only from protected branches and tags.
- Give every deploying job a `resource_group` named for its environment, so two pipelines cannot deploy at once.
- Set `interruptible: true` on build and test jobs and leave deploy jobs alone, so a cancel never stops a deploy halfway.
- Pin images by digest or immutable tag, and `include:` by tag or SHA, never `latest` or a moving branch.
- Lint with `glab ci lint` or the project's CI Lint endpoint before pushing, and record the change with `pipeline-change-record.md`.
