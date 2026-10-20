# Sources

Contents: what each specific claim rests on, what was checked, and what was left out.

Fetched and read on 2026-10-19. Where a source reports a result on its own data, the result is a pointer to a technique, not a number to expect.

## Anthropic, "Introducing Contextual Retrieval"

<https://www.anthropic.com/news/contextual-retrieval>

Supports these statements in this skill:

- BM25 is a lexical ranking function that is effective for queries with unique identifiers or technical terms, and embeddings can miss exact matches such as an error code.
- In the authors' experiments, embeddings combined with BM25 beat embeddings alone.
- Chunk size, chunk boundary and chunk overlap can affect retrieval performance.
- Prepending a short, chunk-specific context line, generated from the whole document, to each chunk before embedding and before building the BM25 index is a technique that reduced failed retrievals on the authors' datasets.
- Their reranking experiment retrieved the top 150 chunks, reranked them, and kept the top 20; reranking was better than no reranking in their tests.
- They measured with 1 minus recall@20 (the share of relevant documents not retrieved in the top 20) and advise running your own evals, since the best number of chunks and the trade-off between latency and cost depend on the use case.

## Anthropic, Citations documentation

<https://platform.claude.com/docs/en/build-with-claude/citations>

- The API parses citations into response blocks and extracts the cited text itself, so citations are guaranteed to contain valid pointers to the provided documents.
- Citations cannot be used together with structured outputs.
- RAG chunks can be supplied as plain text or custom content documents, which sets the granularity of what can be cited.

## Anthropic, Search results documentation

<https://platform.claude.com/docs/en/build-with-claude/search-results>

- Search result content blocks let the model cite your own content, carrying the `source` and title you supply; a source may be a URL or any stable identifier such as an internal id. This is the reason to keep a stable source id per chunk.

## Anthropic, Embeddings documentation

<https://platform.claude.com/docs/en/build-with-claude/embeddings>

- Anthropic does not offer its own embedding model and points to Voyage AI, whose API takes an `input_type` of `query` or `document`; the same page says to assess a variety of embeddings vendors.

## Left out because no primary source could be fetched

When this skill was written only Anthropic's own sites could be fetched, so the following were not checked against their primary sources and carry no figure or attribution in the skill:

- The original RAG paper (Lewis et al., 2020) and any claim about generation quality attributed to it.
- Reciprocal rank fusion (Cormack, Clarke and Buettcher, 2009). The skill describes rank-based merging as the common approach without a constant or a measured gain.
- BEIR (Thakur et al., 2021) and other benchmark comparisons of lexical and dense retrieval.
- Vendor documentation for specific vector databases, rerankers and search engines. The skill says to check that a chosen engine filters on permission metadata during search rather than asserting what any one of them does.
- Lost-in-the-middle position effects. The skill orders passages by rerank score and defers the count and layout to the eval.

Whoever extends this skill with a number or a vendor-specific claim fetches the primary source first and adds it above.
