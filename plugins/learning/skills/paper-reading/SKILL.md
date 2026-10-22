---
name: paper-reading
description: "Read one research paper efficiently and decide what it means for your work. A five-minute triage reads the abstract's claim, the one results table and the limitations: read, skim or skip. The second pass reads figures and tables before the method. The claim is forced into one sentence, on X, method M improves metric Y by Z over baseline B. Then check baseline tuning, seeds and variance, test-set leakage and whether the ablation isolates the contribution. Capped at 45 minutes, ending in an adopt, watch or ignore verdict. Use when someone says \"summarise this arXiv paper and tell me if it's worth implementing\", \"how do I read papers without losing a day\" or \"is this paper's claim believable\". Not for a field survey (literature-scan), notes afterwards (learning-notes) or your own retriever (retrieval-evaluation)."
allowed-tools: Read, Glob, Grep
---

# Paper Reading

A finished read is a one-sentence claim, a short list of checks with answers, and a verdict of adopt, watch or ignore with what would change it, produced in 45 minutes or less.

The usual failure is reading linearly from the abstract to the appendix, absorbing the authors' framing, and finishing with a summary of what the paper says rather than a judgement of whether it is true and useful. The second failure is spending a day on a paper whose results table never supported its headline. This procedure puts the evidence before the explanation, so the method section is read already knowing what it has to account for.

## Scope

Use for: deciding whether one paper is worth acting on; extracting the testable claim from a dense paper; checking a claim before you cite it or build on it.

Do not use for: surveying many papers on a question (`literature-scan`), writing the note afterwards ("add this paper to my notes" goes to `learning-notes`), or evaluating a retrieval system you built (`retrieval-evaluation`).

## Workflow

Keep a clock. The first pass is five minutes, the whole read is capped at 45.

### 1. Five-minute triage

Read three things only: the abstract's claim, the one results table or figure that carries the headline, and the limitations or discussion section. Decide:

- Read: the claim is relevant to your work and the headline result looks substantive.
- Skim: relevant but the evidence looks thin; spend 15 minutes on steps 2 and 3.
- Skip: not relevant, no baseline comparison, or a claim the table does not show. Write one line on why and stop.

Note the venue, the date, whether code or data is released, and whether the authors are comparing against recent methods. A missing baseline comparison is the cheapest bad sign to check.

### 2. Read figures and tables before the method

Read every figure, table and caption in order. Ask of each: what is compared with what, on which data, and what is the unit and the spread. Find the main result and write down the number. Only then read the method, now knowing what it has to explain. Skip proofs unless the claim rests on a theorem you need; if it does, note that you are trusting it or not.

### 3. Force the claim into one sentence

Write: on X, method M improves metric Y by Z over baseline B. Fill every slot with specifics from the paper (dataset, method, metric, size of the gain, the named baseline). If you cannot, the paper makes no testable claim: say so, and treat it as an idea paper, not evidence. Distinguish a claim of improvement from a claim of understanding; both are fine, but only the first can be an adopt.

### 4. Check the evidence

Work through these questions and record the answer, with the page, for each. `references/claim-check-sheet.md` has the longer list and what each answer means.

- Baselines: were they tuned as hard as the proposed method, with the same budget and data? Are they recent and strong, or the weakest published?
- Seeds and variance: how many runs, and is the gain larger than the reported spread? A single run with a one-point gain is not a result.
- Test-set leakage: could the test set overlap pretraining or tuning data? Was the test set used for choosing hyperparameters or checkpoints?
- Ablation: does it remove the claimed contribution alone and show the loss, or does it only remove several things at once?
- Metric: does the metric measure what the title says, and is it the one users care about?
- Scale: does the gain survive across datasets or sizes, or does it hold on one benchmark?

Count what you could not check because the paper did not say. Missing details are a finding.

### 5. Stop and give a verdict

Never re-read from the top; at 45 minutes, write the verdict with what you have. One line: adopt (try it on your own data now), watch (promising, wait for replication or code), or ignore. Add the evidence that would change the verdict: a replication, released code, a result on your kind of data, a stronger baseline. If adopt, name the cheapest experiment that would test it in your setting.

## Hand back

The triage decision, the one-sentence claim, the checklist with answers and page numbers, the verdict line, and what would change it. Mark which statements come from the paper and which from your judgement.

## Anti-patterns

- **Reading in order.** The introduction is the authors' pitch; the table is the evidence.
- **Summarising instead of judging.** A summary is not a verdict.
- **Trusting the abstract's number.** Find it in the table, with its spread.
- **Reading the appendix first because the main text is thin.** If the evidence is only in the appendix, the claim is weaker than it reads.
- **Re-reading to feel thorough.** After 45 minutes the marginal return is low; a verdict with stated uncertainty is the product.

## Reference files

- `references/claim-check-sheet.md` - read at step 4: the evidence questions with what a good and a bad answer looks like, common red flags by paper type, and a verdict template.
