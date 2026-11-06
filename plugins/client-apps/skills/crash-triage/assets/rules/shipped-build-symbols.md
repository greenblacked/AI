---
paths:
  - "**/build.gradle"
  - "**/build.gradle.kts"
  - "**/*.xcodeproj/project.pbxproj"
  - "**/fastlane/Fastfile"
---

# Build files that decide whether a shipped crash can be read

- Upload the dSYMs and the R8 `mapping.txt` for every build in CI, keyed by version code,
  because a crash from that build cannot be symbolicated without them.
- Never strip or delete symbols from a build that has shipped; a mapping file replaced
  by the next build's is gone for the first one.
- Name the command or CI step that proves the upload ran, for example the Crashlytics or
  Sentry upload step's log line, and quote it in the change.
