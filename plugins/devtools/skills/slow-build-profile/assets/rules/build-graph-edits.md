---
paths:
  - "**/CMakeLists.txt"
  - "**/*.cmake"
  - "**/tsconfig*.json"
  - "**/Cargo.toml"
  - "**/build.gradle"
  - "**/build.gradle.kts"
  - "**/settings.gradle.kts"
---

# Editing a build definition

A build file decides what rebuilds when something changes, so a careless edit spreads cost
downstream. Keep the edit to the cause the profile named.

- Write no timestamp, git SHA or absolute path into a file a downstream step reads; each one
  changes every run and rebuilds everything that depends on it.
- Make a generator write its output only when the content changed, so unchanged output keeps
  its modification time.
- Do not add a barrel re-export that drags a whole package into each import.
- Do not widen a glob or include path until it reaches build output.
- After the change, re-run the three timings the skill specifies (clean, incremental, no-op)
  and compare with the baseline.
