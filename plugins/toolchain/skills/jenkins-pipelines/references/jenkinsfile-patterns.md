# Jenkinsfile and shared library patterns

Read when writing a Jenkinsfile, a shared library step, or fixing a CPS error.
Every snippet is a shape to adapt; confirm option names and step signatures against the
documentation for the pinned Pipeline and plugin versions.

## Contents

- A declarative skeleton
- Shared library layout
- Serializable state and `@NonCPS`
- Parallel stages and failure handling
- Cleanup and post conditions
- Testing the pipeline logic

## A declarative skeleton

```groovy
// build-lib v1.4.2, pinned to its full commit SHA because a tag can be moved
@Library('build-lib@<full 40-character sha>') _

pipeline {
  agent none
  options {
    timeout(time: 45, unit: 'MINUTES')
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '30'))
    skipDefaultCheckout(true)
  }
  stages {
    stage('Test') {
      agent { label 'linux && docker' }
      steps {
        checkout scm
        sh 'make test'
      }
      post { always { junit allowEmptyResults: true, testResults: 'reports/*.xml' } }
    }
    stage('Deploy') {
      when {
        beforeOptions true
        branch 'main'
      }
      agent { label 'deployer' }
      options { lock(resource: 'deploy-production') }
      steps {
        checkout scm
        withCredentials([string(credentialsId: 'deploy-token', variable: 'TOKEN')]) {
          sh './deploy.sh'
        }
      }
    }
  }
}
```

Why these choices: `skipDefaultCheckout` with `agent none` avoids a checkout on a node
the pipeline never chose; each stage that needs the sources runs `checkout scm` on its own
agent, because the workspaces are separate. The deploy script reads
`TOKEN` from the environment, so no Groovy string ever holds the value.

## Shared library layout

```text
vars/buildImage.groovy     one global step per file, called as buildImage(...)
vars/buildImage.txt        help text shown in the pipeline syntax pages
src/org/example/Util.groovy  classes; keep them small and serializable
resources/                 files loaded with libraryResource
```

A `vars/` step is the right place for a repeated multi-step sequence. Give it explicit
named parameters, validate them with a clear error, and return plain data. Do not read
credentials by ID inside a library step unless the step's purpose is to bind them and its
caller cannot pass in a different ID to exfiltrate a different secret; a library that
accepts any credential ID from a pipeline author lets that author use every credential
the job can see.

Tag library releases (`v1.4.2`) and keep a changelog; pipelines upgrade by changing one
tag in a reviewed commit. A tag that is moved is the same as an unpinned branch, so
protect tags in the library repository.

## Serializable state and `@NonCPS`

Failing shape:

```groovy
def m = (text =~ /version=(\d+)/)      // Matcher is not serializable
sh 'echo before'                       // step suspends, state is persisted: error
echo m[0][1]
```

Fix by finishing the non-serializable work inside a `@NonCPS` method that returns plain
strings, numbers, lists or maps:

```groovy
@NonCPS
def versionOf(String text) {
  def m = (text =~ /version=(\d+)/)
  return m ? m[0][1] : null
}
def v = versionOf(readFile('build.properties'))
```

Rules that follow from how the transform works: a `@NonCPS` method must not call
pipeline steps, may be slower to debug because it is not stepwise, and should be short.
When the logic is more than a few lines, write it as a script and call it with `sh`.
Prefer the Pipeline Utility Steps plugin's `readJSON` and `readYaml` over parsing in
Groovy, and read the result as a plain map.

## Parallel stages and failure handling

Use declarative `parallel` inside a stage, and set `failFast` only when the siblings
cannot produce useful results after one fails. Each parallel branch needs its own
`agent` or it shares the stage's. A `catchError` or `warnError` step marks the build
unstable or failed while continuing; use it for reporting steps, not to hide a failing
test. Check the pinned docs for the exact `buildResult` and `stageResult` arguments.

## Cleanup and post conditions

`post { always { ... } }` runs even on failure and abort, which makes it the place for
test reports and workspace cleanup (`cleanWs()` from the Workspace Cleanup plugin).
`post` at the pipeline level with `agent none` has no workspace; put the cleanup in the
stage's own `post`. Do not put a deploy or notification that can itself fail in `always`
without considering that its failure changes the build result.

## Testing the pipeline logic

Keep the Jenkinsfile short enough that review replaces testing, and move logic into
scripts and library classes that run under a normal test runner. For library steps, the
Jenkins Pipeline Unit test framework runs `vars/` code without a controller; it mocks
steps, so it proves the control flow, not that the real step accepts the arguments. Run
a real build on a staging controller for anything that changes credentials, agents or
plugin steps.
