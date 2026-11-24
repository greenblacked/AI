# Coverage import

SonarQube reads a coverage report the build wrote; it does not measure coverage. Property
names, accepted formats and path handling differ per language and version, so confirm them
in the official analysis-parameters documentation for the pinned scanner and server.

## Contents

- Diagnostic order
- Property families by language
- Path mismatch
- Passing the report between jobs

## Diagnostic order

1. Open the scanner log and find the coverage sections of the language sensors. Note which
   report files it read, which it skipped and any warning about files not found or lines
   out of range.
2. Confirm the report exists in the job's workspace at that moment, is non-empty, and was
   written by this run rather than restored from a stale cache.
3. Compare one file path inside the report with the same file's path relative to the
   project base directory.
4. Confirm the format matches what the property expects.
5. Only then look at exclusions.

## Property families by language

The names below are the families to look up, not a promise about the pinned version.

| Language family | Usual report | Property family |
| --- | --- | --- |
| Java and Kotlin | JaCoCo XML | `sonar.coverage.jacoco.xmlReportPaths` |
| JavaScript and TypeScript | LCOV | `sonar.javascript.lcov.reportPaths` |
| Python | Cobertura-style XML from coverage.py | `sonar.python.coverage.reportPaths` |
| C# and .NET | OpenCover, dotCover or Visual Studio coverage XML (emit OpenCover from coverlet; Cobertura is not read) | `sonar.cs.*` families |
| Go | Go cover profile | `sonar.go.coverage.reportPaths` |
| Generic | Sonar generic coverage XML | `sonar.coverageReportPaths` |

When a toolchain emits a format the language sensor does not accept, convert to the
generic coverage format rather than disabling the check.

## Path mismatch

Symptoms: the report is read without error yet every file shows 0%, or only some. Causes:
tests ran in a container with sources at a different absolute path; a monorepo module
reports paths relative to its own directory while the scanner base directory is the
repository root; or a build tool rewrote source roots.

Fixes, in order of preference: run tests and analysis against the same checkout layout;
set the module's `sonar.projectBaseDir` and `sonar.sources` to match the report; rewrite
the paths in the report with a small, reviewed script in the pipeline. Do not paper over
it by lowering the coverage threshold.

## Passing the report between jobs

If tests and analysis are separate jobs, publish the coverage files as artifacts from the
test job and make the analysis job depend on that job (a needs relationship on GitLab, a
stash and unstash in Jenkins). Set a short expiry, and make the analysis job fail when the
file is missing instead of analysing without coverage, which would report a drop that is
really an absent report.
