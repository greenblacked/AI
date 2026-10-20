---
name: rag-design
description: "Design a retrieval-augmented generation pipeline you can show retrieves the right passages: build a small labelled eval of questions mapped to answering passages before tuning anything, score retrieval (recall@k, MRR) apart from answer faithfulness, chunk by document structure keeping source ids and offsets for citations, start with hybrid lexical plus dense search, rerank a wide candidate set, filter by permission inside the retrieval query not after generation, and refuse on empty or weak retrieval. Use for \"answer questions over our docs\", \"the bot cites the wrong page\", or picking chunk size or embedding model. Not for benchmarking a retriever on a sealed holdout (retrieval-evaluation), judging an agent (agent-evaluation), token spend (llm-cost), data caching (application-caching), table design (schema-design), JSON output (structured-output) or a model move (model-migration)."
allowed-tools: Read, Glob, Grep
---

# RAG Design

A retrieval-augmented generation pipeline is done when you can show, on questions with known answers, that the right passages come back, that the answer says only what those passages support, and that nobody receives a passage they may not read.

The usual failure is a pipeline tuned by reading a few good answers. The generator papers over a bad retriever with plausible text, so a wrong chunk size or a missing exact-match path looks like a model problem and gets fixed with a longer prompt. Measure the retriever on its own first; everything after it is only as good as what it was handed.

## Scope

Use for: designing a new question-answering pipeline over your own documents; deciding chunking, search mode, reranking, permission filtering and citation format; diagnosing a bot that cites the wrong page or answers from nothing; planning what to re-run when the corpus or embedding model changes.

Do not use for: comparing two retrievers on a frozen benchmark with a sealed holdout and a promotion decision, which is `retrieval-evaluation`; grading an agent's tool use, which is `agent-evaluation`; cutting token spend, which is `llm-cost`; caching application data, which is `application-caching`; modelling the tables that hold documents, which is `schema-design`; forcing a JSON shape on the answer, which is `structured-output`; moving the feature to a new model, which is `model-migration`; deciding who may read what in the application, which is `authorization-design`.

## Workflow

### 1. Write the retrieval eval before anything else

Collect real questions, from support tickets, search logs or the people who will use the bot. For each, record the passage ids that answer it, by reading the corpus yourself. Add questions the corpus cannot answer and mark them as such, because the refusal path needs them. Use a model to draft candidate questions if you must, but a person confirms every label: a model labelling its own retriever's output grades its own homework.

Keep the set in a versioned file beside the code, with a stable id per question. Grow it from every failure found later. Read `references/retrieval-eval.md` when writing the file format, the metrics or the harness.

### 2. Score retrieval and generation separately

Retrieval is scored on the eval without calling a generator: recall@k (did a passage that answers the question appear in the top k) and MRR (how near the top). Generation is scored afterwards on what the retriever returned: is every claim supported by a cited passage, and does a citation point at the text that supports it. A single end-to-end "answer quality" number cannot tell you which half broke.

When the retrieval numbers are poor, fix retrieval; do not touch the prompt. Classify each miss as not in the corpus, chunked apart, ranked too low, or filtered out, and change the stage that owns it.

### 3. Chunk by structure and keep the way back to the source

Split on the document's own boundaries: headings and their sections, list items, table rows with the header repeated, code blocks, question and answer pairs. Fall back to size only inside a section that is too long. Decide overlap by running the eval with and without it; an overlap that does not move recall@k is index size and duplicate hits for nothing.

Give every chunk a stable id, the source document id and version, the section path and the character offsets into the source text, plus the permission metadata step 6 needs. A citation that cannot be traced to a document and a span is not a citation. Read `references/pipeline-stages.md` when choosing chunk boundaries, the index record, or what to re-run after a change.

### 4. Search with lexical and dense together

Run a lexical index (BM25) and a dense embedding index over the same chunks and merge the two ranked lists by rank, not by raw score, because the scores are on different scales. Lexical search finds the error code, product name or identifier that embeddings blur; dense search finds the paraphrase that shares no words. Measure lexical alone, dense alone and the merge on the eval, and keep the merge only if it beats the better single index on recall@k.

Try hybrid before anything exotic: query rewriting, multi-hop agents and larger models each add a stage that needs its own eval. Reach for one only when the miss classification in step 2 says the current stages cannot reach the passage. Where the embedding model distinguishes queries from documents, embed each side in the correct mode.

### 5. Rerank a wide candidate set

Retrieve more candidates than you will use, score each against the query with a reranker, and pass only the best few to the generator. The first stage is fast and approximate and the reranker is slower and sharper, so the order of work matters: widen the first stage until recall at the wide cutoff is high on the eval, then rerank to the narrow cutoff. Measure the gain on the eval before keeping the stage, and record its latency and cost.

### 6. Filter by permission at query time

Apply the caller's permissions inside the retrieval query, as a filter on stored permission metadata, so a passage the caller may not read is never a candidate. Filtering the results after generation is too late (the text is already in the prompt and can surface in the answer); filtering the top k after retrieval returns a short or empty list for a caller who can read plenty. Derive the principal from the authenticated session, never from the question text or the model.

Test it with a principal who may read nothing and one who may read a single document. Include the principal in any cache key over retrieval results. Read `references/grounding-and-refusal.md` for the checks.

### 7. Require citations and refuse when retrieval is weak

Give the generator the retrieved passages labelled with their chunk ids and instruct it to answer only from them and to cite the id for each claim. Verify citations in code: every cited id must be among the ids you supplied, and the cited span must exist. Prefer a provider's native citation feature where it offers one, since it returns pointers into the documents you supplied.

Refuse, with a stated reason, when retrieval returns nothing, or when the best score is below a threshold you chose from the eval's answerable and unanswerable questions. Never let the model improvise from its training data to fill the gap. Read `references/grounding-and-refusal.md` when setting the threshold, the context layout or the faithfulness check.

### 8. Re-index and re-run the eval on every change

A new embedding model, chunker, reranker, corpus snapshot or prompt changes what the eval measures. Re-embed the whole corpus with a new embedding model, because vectors from different models do not share a space; build the new index beside the old one, run the eval on both, and switch only when the numbers hold. Propagate deletions and permission changes from the source system into the index. Read `references/pipeline-stages.md` for the change checklist.

## Output format

Hand back a design note:

```markdown
## Eval
[Question count, how labels were made, answerable and unanswerable split, file path.]

## Retrieval results
[Recall@k and MRR for lexical, dense, merged and reranked, with the k used.]

## Pipeline
[Chunking rule and overlap, index record, search mode, rerank depth, permission filter.]

## Answering
[Context layout, citation check, refusal rule and threshold, faithfulness result.]

## Change control
[What triggers a re-index and re-run, and who owns it.]
```

## Anti-patterns

**Tuning on impressive answers.** A fluent reply hides a retriever that returned the wrong page. Score retrieval on labelled questions and read the passages, not the prose.

**One end-to-end score.** When the number drops there is no way to tell whether search, chunking or the prompt moved. Keep the two halves separate.

**Fixed-size chunks with a guessed overlap.** A cut through a table or a sentence splits the answer from its heading. Chunk on structure, justify overlap with the eval.

**Dense search alone.** Exact identifiers, error codes and names are where embeddings are weakest. Add lexical search before adding anything clever.

**Permissions after generation.** Filtering the answer, or the retrieved list, once the model has seen the text leaks it. Filter in the query.

**Answering from an empty result.** With nothing retrieved the model answers from memory and cites nothing real. Refuse in code before the generator is called.

**Retrieved text treated as instructions.** A passage can contain text that tells the model what to do. Present passages as quoted data; for agents that act on them see `agent-security-review`.

**An old index after a model change.** Mixing vectors from two embedding models, or keeping the eval from before a corpus change, gives numbers that describe a system that no longer exists.

## Reference files

- `references/retrieval-eval.md` — read at step 1 and step 2: the eval file format, recall@k and MRR defined, a stdlib harness, classifying misses, and the faithfulness sheet.
- `references/pipeline-stages.md` — read at steps 3 to 5 and step 8: chunk boundaries, the index record, lexical and dense merge, reranking depth, and the change checklist.
- `references/grounding-and-refusal.md` — read at steps 6 and 7: permission filtering tests, context layout, citation verification, refusal thresholds and prompt-injection handling.
- `references/sources.md` — read before quoting a claim from this skill to someone else: the primary sources behind each specific claim, and the claims that were left out because no primary source could be checked.
