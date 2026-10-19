# Grounding, permissions and refusal

Contents: filtering by permission, the context layout, checking citations, setting the refusal threshold, and retrieved text as an attack surface.

## Filtering by permission

Three places a filter can sit, and what each costs:

- **Inside the retrieval query** (correct). The index applies the principal's allowed set while searching, so every candidate is readable and the top k is full.
- **After retrieval, before generation.** Nothing unreadable reaches the model, but the top k may have been spent on unreadable chunks, so a permitted caller gets a short or empty list and a wrongful refusal.
- **After generation.** The model has already read the text and can paraphrase it into the answer; removing a citation does not remove the content. This is a leak, not a filter.

Checks to run before launch:

1. A principal with no access gets zero candidates and a refusal, not a generic answer built from other material.
2. A principal with access to a single document gets only that document's chunks, including from the lexical index and from the reranker's input.
3. A document whose permissions were just revoked stops appearing after the index propagates the change; measure how long that takes and state it.
4. The principal comes from the authenticated session. A question that says "I am an administrator" changes nothing.
5. Any cache over retrieval results, embeddings of queries or final answers is keyed by principal as well as question; see `application-caching`.

Which principals may read which documents is an authorization decision made elsewhere; `authorization-design` covers it. The pipeline's job is to enforce the decision at query time and to prove it with the tests above.

## Context layout

Give the generator each passage as quoted material with its id, and the instruction separately:

```text
<passages>
<passage id="policy-retention#s3" source="Retention policy, section 3">
...text...
</passage>
</passages>
Answer using only the passages. After each claim cite the passage id in square brackets.
If the passages do not contain the answer, say so and stop.
```

Order passages by rerank score, and keep the count to what the eval showed helps. If the provider offers native citations, use them: Anthropic's citations feature returns the cited text and a location in the document you supplied, and its documentation states that citations are guaranteed to contain valid pointers to the provided documents (<https://platform.claude.com/docs/en/build-with-claude/citations>). The same documentation says citations cannot be used together with structured outputs, so a design that needs both an enforced JSON shape and native citations has to pick one or carry ids in the schema itself; `structured-output` covers that choice.

## Checking citations in code

Whether you use native citations or your own bracketed ids, verify:

1. Every cited id is among the ids supplied for this request.
2. If the model quotes text, the quote is a substring of the cited chunk after whitespace normalisation.
3. Every sentence that asserts a fact has at least one citation; flag the answer when one does not.
4. The citation maps back to a document id, version and span the user can open.

A failed check is a retry with the failure stated, or a refusal. It is never a silent pass.

## The refusal rule

Two refusals, decided in code before and after the generator:

- **Before:** retrieval returned no candidates, or the best candidate's score is below the threshold. Do not call the generator. Return a message that says no supporting passage was found, and offer the nearest next step (rephrase, contact a person).
- **After:** the generator reports the passages do not answer, or the citation check fails twice.

Set the threshold from the eval. Run all questions, collect the top score for the answerable and the unanswerable ones, and place the cutoff where wrongful refusals and wrongful answers balance the way the product needs. State the two counts. Scores from a reranker and from a vector similarity are on different scales and change with the model, so redo this whenever the scorer or embedding model changes. Choose on the development questions and confirm on questions you did not tune on.

Where a lexical hit with an exact identifier match exists, a low dense score should not trigger refusal on its own; this is a reason to threshold the merged or reranked score rather than one side.

## Retrieved text is data

A passage may contain text that addresses the model ("ignore the above and ..."), put there by an author or an attacker with write access to a source. Present passages inside delimiters as quoted material, tell the model they are not instructions, and give the generator no tools it does not need. If the pipeline can take actions based on what it reads, treat the corpus as untrusted input and review it with `agent-security-review`.
