# Failed job record

One failed Slurm job or array. Fill in every field from the scheduler's record before the
log; delete the guidance in brackets.

## Job

- Job ID or array job ID: [number]
- Cluster, partition and QOS: [names]
- Submitted by and script path: [user, path]
- Request: [nodes, tasks, CPUs, GPUs, `--mem` or `--mem-per-cpu`, `--time`]

## Scheduler record

Paste the `sacct -j JOBID --format=JobID,JobName%20,State,ExitCode,DerivedExitCode,Elapsed,Timelimit,ReqMem,MaxRSS,AllocCPUS,NodeList -P` rows, one per step.

| Step | State | ExitCode | Elapsed / Timelimit | MaxRSS / ReqMem | Node |
| --- | --- | --- | --- | --- | --- |
| [JOBID.batch] | [state] | [code:signal] | [time] | [memory] | [node] |
| [JOBID.0] | [state] | [code:signal] | [time] | [memory] | [node] |

## Verdict

- State class: [OUT_OF_MEMORY / TIMEOUT / NODE_FAIL / CANCELLED / DEADLINE / FAILED]
- Who ended the job: [scheduler / kernel / node / a person / the program]
- Step row that decided it: [step and the fields that show it]

## First failure

- First failing array index or rank: [index or rank]
- Node and input: [node, file or parameters]
- Earliest error line: [file:line and the quoted line, or "none; the scheduler ended it"]
- Failures sharing a cause: [count and the shared node, input, size or time]

## Resubmission

| Changed | From | To | Why |
| --- | --- | --- | --- |
| [memory / time / node / input] | [old] | [new] | [the measurement that justifies it] |

- Indices to rerun: [list or "all"]
- What to check if it fails again: [one thing]
