# Pipeline stages

Contents: chunk boundaries, the index record, merging lexical and dense search, reranking, and the change checklist.

## Chunk boundaries

Split on the structure the author already gave the document, in this order of preference:

1. A section under a heading, with the heading path kept as metadata and prepended to the chunk text.
2. Within a section that is still too long, paragraphs, then sentences.
3. A table as its own unit with its header row repeated on each piece, or one row per chunk with the header attached.
4. A code block whole, with the file or function name it belongs to.
5. A question-and-answer pair together.

Choose the size limit from the embedding model's input limit and from what the eval shows, not from a number copied from a tutorial. The vendor of the embedding model documents its input limit; read it for the model you use.

Overlap exists to keep an answer that straddles a boundary from being cut in half. Test it: run the eval with no overlap and with the overlap you are considering, and keep it only if recall@k rises. Anthropic's write-up of this area names chunk size, boundary and overlap as choices that affect retrieval and says to evaluate them (<https://www.anthropic.com/news/contextual-retrieval>). Overlap also produces near-duplicate chunks that compete for the same top-k slots; deduplicate by source span before reranking.

## The index record

Each chunk carries enough to render a citation, enforce permissions and detect staleness:

| Field | Why |
| --- | --- |
| `chunk_id` | Stable across rebuilds where the source did not change; the eval and citations refer to it |
| `doc_id`, `doc_version` or content hash | Detects a source that changed under a stored offset |
| `section_path` | Shown to the user, prepended to the text |
| `start`, `end` | Character offsets into the normalised source text, for highlighting and for checking a cited span |
| `text` | What is embedded and indexed |
| `acl` | Principals or groups allowed to read it, filtered on at query time |
| `embedding_model` | Records which space the vector lives in |
| `indexed_at` | Freshness checks |

Store the normalised source text that offsets refer to, or the offsets drift when the extractor changes. Keep the record in a store that supports filtering on `acl` as part of the search, not afterwards; check that for your engine rather than assuming it. If chunk records live in a relational table, `schema-design` covers the keys and tenancy columns.

## Lexical and dense, merged

Index the same chunk text in a lexical (BM25) index and in a vector index. For each question take the top N from each, then merge by rank. Reciprocal rank fusion is the common rank-based merge: each list contributes a score that falls with rank, and a chunk's contributions add up. Merging by rank avoids having to rescale two score distributions; if you merge by weighted score instead, normalise both and tune the weight on the eval, not by intuition.

Embedding models may expect different handling for queries and documents; the Voyage documentation Anthropic points to shows an `input_type` of `query` or `document` (<https://platform.claude.com/docs/en/build-with-claude/embeddings>). Check the model card for the one you use and embed each side accordingly, or the eval will understate it.

Compare four rows on the eval: lexical, dense, merged, merged and reranked. Keep the simplest row that meets the target. A stage whose row does not beat the one above it is removed.

## Reranking

The first stage retrieves a wide set cheaply; the reranker reads query and candidate together and scores each, then you keep the best few for the generator. Choose the wide cutoff where recall on the eval stops climbing meaningfully, and the narrow cutoff by what the generator can use without being distracted. Anthropic's experiment retrieved 150 candidates and passed the best 20 on, on its own datasets (<https://www.anthropic.com/news/contextual-retrieval>); treat that as an example of the shape, not a setting.

Record the reranker's added latency and per-request cost next to the gain it buys; `llm-cost` covers the budget side.

## The change checklist

Re-run the eval, and re-index first where the row says so.

| Change | Re-index | Re-run eval | Also check |
| --- | --- | --- | --- |
| New embedding model | Whole corpus, into a new index | Yes, both indexes | Query and document modes |
| New chunker or overlap | Whole corpus | Yes | Citation offsets still resolve |
| New reranker or cutoff | No | Yes | Latency and cost |
| Corpus update | Changed documents | Yes, if a labelled passage changed | Deletions and ACL changes propagated |
| Prompt or generator change | No | Generation sheet only | Citations and refusals |
| Permission model change | Metadata for affected chunks | Permission tests | Cache keys |

Switch traffic to a rebuilt index only after the eval on it meets the numbers of the one it replaces. Keep the old index until then so rollback is a pointer change.
