# Scan log and table

## Contents

- [Search log](#search-log)
- [Candidate screening sheet](#candidate-screening-sheet)
- [Family table example](#family-table-example)

## Search log

| Date | Source | Query or snowball step | Filters | Screened | Kept |
| --- | --- | --- | --- | --- | --- |

Record the exact string including quotes and operators, and the source (a scholarly index,
a preprint server, a code host, a blog search). Record snowball steps as, for example,
"cited-by of seed 2, last five years". The point is repeatability: someone running the same
rows a month later should reach the same set, give or take new papers.

## Candidate screening sheet

| Round | Candidate | Passes scope? | Cited by how many selected papers (backward) or cites how many selected (forward) | New family or meets citation test? |
| --- | --- | --- | --- | --- |

A candidate meets the test only if it passes scope and either adds an approach family not yet in
your notes, or meets the citation test: a backward candidate is cited by three or more papers
already selected, and a forward candidate, which is newer than the selected papers and cannot be
cited by them, cites three or more of them. A yes here means the scan has not saturated. A round of ten with none meeting the test is a quiet round; two quiet rounds
in a row end the scan. If you find yourself adding papers only because a title sounds relevant,
the rule is working: they are peripheral.

## Family table example

For consistent hashing with bounded loads:

| Family | Core idea | Evidence | Needs | Maturity |
| --- | --- | --- | --- | --- |
| Bounded-load consistent hashing | Cap each node's load at a multiple of the average and forward overflow to the next node on the ring | Theory with proofs, plus production reports | Per-node load counters | Implemented in open-source proxies |
| Multiple-choice hashing | Hash to several candidates, place on the least loaded | Strong theory | Load information at placement | Widely used in other settings |
| Rendezvous hashing | Pick the node with the highest hash score for the key | Theory and production use | Score per node per key | Widely deployed |

Treat the rows as an illustration of shape; the contents of a real scan come from its own log.
Follow with the unsettled list, for example "behaviour under rapid membership churn is
reported by one group only".
