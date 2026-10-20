# The retrieval eval

## Contents

- The file format
- The metrics
- A harness
- Classifying a miss
- Scoring generation
- Keeping the set honest

## The file format

One JSON object per question, in a versioned file such as `evals/retrieval.jsonl`:

```json
{"id": "q-017", "question": "How long do we keep audit logs?", "relevant": ["policy-retention#s3", "policy-retention#s4"], "answerable": true}
{"id": "q-018", "question": "What is the CEO's home address?", "relevant": [], "answerable": false}
{"id": "q-019", "question": "What is the Q3 bonus pool?", "relevant": ["comp-plan#s2"], "answerable": true, "principal": "finance-lead"}
```

`relevant` lists the chunk ids (or document ids plus spans, if the chunker is still changing) that contain the answer. Label at a unit that survives a re-chunk: a document id and a character span into the source text can be mapped onto whichever chunks the current chunker produces, whereas a chunk id from an old chunker cannot. Several passages can be relevant to one question; list them all, and say in the harness whether one hit is enough or every one must appear.

Keep these in the set:

- Questions in the words users use, not the words of the document. Questions copied from the document make every retriever look good.
- Questions whose answer is an identifier, a code or a name, which lexical search should win.
- Questions that paraphrase the answer, which dense search should win.
- Questions that need two passages.
- Unanswerable questions, marked `answerable: false`, for the refusal threshold.
- Questions for callers with different permissions, with the principal recorded, once step 6 exists.

Split off a portion you do not tune against. When the decision is whether to promote a new index on that evidence, hand the comparison to `retrieval-evaluation`, which owns frozen snapshots, paired comparison, sealed holdouts and the leak veto.

## The metrics

State the cutoff `k` and the unit with every number.

- **Recall@k**: for each answerable question, the share of its relevant passages found in the top k results, averaged over questions. When one passage is enough, use the hit rate instead: the share of questions with at least one relevant passage in the top k. Say which.
- **MRR**: the mean over answerable questions of 1 divided by the rank of the first relevant result, counting 0 when none appears within the cutoff.
- **Refusal accuracy**: over all questions, the share where the pipeline answered an answerable question or refused an unanswerable one. Report the two error directions separately, because a wrongful refusal and a wrongful answer cost different things.

Report each as a count over a denominator ("31 of 40 questions"), so a reader can see how few questions moved. With a small set, one question flipping is the resolution of the measurement; do not present a difference of that size as a finding.

## A harness

This runs against any retriever that takes a question and a principal (`None` when the case records none) and returns ranked `(chunk_id, score)` pairs, best first. `threshold` is the score below which the pipeline refuses; the harness applies it to every question, so an unanswerable question that still gets a strong candidate counts as a wrongful answer and an answerable one whose best candidate falls short counts as a wrongful refusal, the two error directions the refusal metric above reports separately. It needs no third-party package.

```python
import json


def load(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def evaluate(questions, retrieve, k, threshold, can_read=None):
    recalls, rr, misses, leaks = [], [], [], []
    wrongful_answers, wrongful_refusals = [], []
    for q in questions:
        principal = q.get("principal")
        ranked = retrieve(q["question"], principal)[:k]  # [(chunk_id, score), ...] best first
        got = [cid for cid, _ in ranked]
        if can_read is not None:
            leaks += [(q["id"], cid) for cid in got if not can_read(principal, cid)]
        answers = bool(ranked) and ranked[0][1] >= threshold
        if not q["answerable"]:
            if answers:  # a strong candidate for a question the corpus cannot answer
                wrongful_answers.append(q["id"])
            continue
        if not answers:
            wrongful_refusals.append(q["id"])
        want = set(q["relevant"])
        if not want:
            raise ValueError(f"{q['id']}: answerable but lists no relevant passages")
        found = [i for i, cid in enumerate(got) if cid in want]
        recalls.append(len({got[i] for i in found}) / len(want))
        rr.append(1 / (found[0] + 1) if found else 0.0)
        if not found:
            misses.append(q["id"])
    if leaks:  # a leak fails the run whatever the recall
        raise AssertionError(
            f"{len(leaks)} chunk(s) returned to a caller who cannot read them: {leaks}"
        )
    n = len(recalls)
    if n == 0:
        raise ValueError("no answerable questions to score")
    return {
        "questions": n,
        "recall@k": sum(recalls) / n,
        "mrr": sum(rr) / n,
        "missed": misses,
        "wrongful_answers": wrongful_answers,
        "wrongful_refusals": wrongful_refusals,
    }
```

`retrieve` takes the question and the principal the case records, so each permission case runs as that caller rather than under whatever identity the harness happens to hold. Pass `can_read(principal, chunk_id)` from the same permission source the production filter uses. The harness raises on any run that returns an unreadable chunk, whatever the recall, so a leaking configuration cannot reach the comparison table: an answer that is right for one caller and shows another caller's chunk beside it is still a leak.

Run it once per configuration (lexical, dense, merged, reranked) and print the table side by side. Write the output file next to the eval version so a later change can be compared with it.

## Classifying a miss

For every question in `missed`, look at the passages and decide which stage owns the failure, then change only that stage.

| Finding | Owner | Change |
| --- | --- | --- |
| The answer is not in the corpus | Corpus | Add the document, or relabel the question unanswerable |
| The answer is split across two chunks, or its heading is in another chunk | Chunker | Chunk on structure; add the section path or a short context line to each chunk |
| The right chunk is in the candidates but below the cutoff | Ranker | Widen the first stage, add or tune the reranker |
| The right chunk never reaches the candidates | Search mode | Add the missing lexical or dense side; check the query embedding mode |
| The right chunk exists and the filter removed it | Filter | Check permission metadata and the principal |

A chunk that gains a short line saying what document and section it comes from before it is embedded and indexed is a published technique; described in <https://www.anthropic.com/news/contextual-retrieval>, where it reduced failed retrievals on the authors' datasets. It costs one model call per chunk at index time, so add it only when the miss table shows chunks that cannot be understood alone.

## Scoring generation

After retrieval is acceptable, score the answers for the same questions on a separate sheet. For each answer record:

- **Supported**: every factual claim is backed by a passage the generator was given, yes or no, with the unsupported claim quoted.
- **Cited correctly**: each cited id exists and its span contains what the claim says.
- **Refusal**: for unanswerable questions, whether it refused and said why.

A person reads a sample of these. If a model grades the rest, calibrate it against the person's labels first; `agent-evaluation` covers judge calibration and applies unchanged.

## Keeping the set honest

Add every production failure to the set with its correct passages. Remove nothing because the pipeline fails it. Record the corpus snapshot and the embedding model with each saved result, since a number without them cannot be compared next month.
