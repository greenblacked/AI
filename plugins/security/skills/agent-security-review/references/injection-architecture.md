# Injection architecture

Use this when the review finds an agent that reads untrusted content and holds both
private data and an outbound path, and the answer cannot be "add a tool-side check" alone.
The SKILL.md gates say where policy is enforced; this file covers how to arrange the
agent so that a successful injection has nothing to spend.

The premise is OWASP's: LLMs make no architectural distinction between instructions and
data, so no reliable prevention exists today, and defence is architectural rather than
interceptive ([LLM01:2026 Prompt Injection][owasp-llm01], mitigation strategies). Design
for the case where the model follows the attacker, and ask what that costs.

## Contents

- Threat model: the lethal trifecta
- Capability separation and the dual-LLM pattern
- CaMeL: tracking provenance in an interpreter
- Spotlighting and datamarking: a layer
- Egress: allowlists and what the client renders
- Human approval: show the exact payload, know the limits
- What does not work on its own
- Testing: assert on the action trace
- Sources checked

## Threat model: the lethal trifecta

Simon Willison's lethal trifecta names three capabilities: access to private data,
exposure to untrusted content, and an ability to communicate externally. An agent with all
three has the conditions for high-impact exploitation, and removing any one leg removes
them (as OWASP summarises it in the LLM01:2026 entry above). Meta's Agents Rule of Two,
which OWASP cites, is a variant for budgeting: untrusted input, sensitive data and state
change or external communication; an agent holding all three needs per-action human
approval, and one holding two needs an explicit residual-risk assessment.

Apply it per workflow, not per product. One deployment usually hosts several agent
configurations, and the trifecta is a property of the tools and data one session can
reach together.

1. List the private data the session can read, including what its credentials reach and
   what memory and retrieval return, not only what the task needs.
2. List every untrusted source: web pages, email, issue and pull request text, retrieved
   chunks, tool and MCP output, delegated reports, files. OWASP's trust profile helps
   rank them: untrusted (public web, unknown senders), semi-trusted (issue titles,
   package READMEs, third-party API responses) and trusted (your own repository or
   tickets, where an attacker may have placed text through a low-privilege form).
3. List every outbound path, and do not stop at the obvious tool. Microsoft's catalogue
   of exfiltration channels covers rendered images, clickable links, tool calls that
   write somewhere public and covert channels where whether a tool was called is itself
   observable ([MSRC, July 2025][msrc]). Add commits, comments, calendar invites, DNS and
   anything the sandbox can reach.
4. If all three legs are present, break one by design and record which. A prompt does not
   count as breaking a leg.

| Leg to break | Design change | Cost |
| --- | --- | --- |
| Private data | Run the untrusted-content task in a session with no credential for the sensitive store; pass only the fields it needs | Task may need a second step or a second session |
| Untrusted content | Read only content from an allowlisted, owned source; summarise untrusted material in a separate quarantined step (next section) | Narrower task; extra component |
| Outbound path | Remove the tool, or restrict to declared destinations and enforce it outside the model (egress section) | Some automation becomes a human step |

State the cost in the finding. A leg that is broken only for the happy path, such as a
tool that is "usually" read-only, is not broken.

## Capability separation and the dual-LLM pattern

The structural fix for a session that must read untrusted text and also act is to split it
into two components that never share a context.

- A quarantined reader processes the untrusted content. It has no tools, no credentials
  and no way to cause an effect. Its output is untrusted by definition.
- A privileged planner holds the tools and sees only the user's request and trusted state.
  It never reads the untrusted text.

What crosses between them decides whether this is a control or a diagram. Free text from
the reader into the planner reintroduces the injection through the front door. Pass typed
values instead: an enum member, a boolean, a number inside a bound, an identifier that
trusted code resolves and authorises, or an opaque reference the planner can hand to a
tool without reading. Validate each in application code against a closed schema, not with
a second model call (the OWASP LLM01 entry says the same of structured output).

Be honest about the residual. A typed value limits what the content can say but not
whether it is true or chosen by the attacker: a valid recipient the attacker selected is
still a valid recipient. OWASP's schema guidance has the same caveat, that validation
catches format violations and not semantic manipulation. Pair the split with
tool-side authorisation and, for the choices that matter, a fresh value from the user.

## CaMeL: tracking provenance in an interpreter

CaMeL ("Defeating Prompt Injections by Design", Debenedetti et al., Google, Google
DeepMind and ETH Zurich, [arXiv 2503.18813][camel-paper]) formalises the split. As
OWASP's cheat sheet describes it, a privileged model writes a step-by-step plan as code
from the trusted request alone; a quarantined model with no tool access parses untrusted
data; and a custom interpreter executes the plan, tracks the data flow and enforces
security policy through metadata tags it calls capabilities. A tool call that violates the
configured policy is blocked by the interpreter, not by a prompt.

Use it as a design reference for what a stronger answer looks like, not as a component to
adopt:

- The released code is a research artefact. Its README warns that the interpreter
  probably contains bugs, might not be fully secure, is not a Google product, and will not
  be supported or maintained ([google-research/camel-prompt-injection][camel-repo]).
- Its protection is bounded by its policies and its dependency tracking. OWASP's summary
  of the paper's own threat model notes that it assumes a trusted user prompt and
  uncompromised memory, does not stop misleading summaries or phishing text that leave
  protected data flows unchanged, and discusses side-channel risk.

What to take from it into a review: every value that reaches a tool argument should carry
where it came from, and policy should be a function of that provenance and the tool, not
of how persuasive the surrounding text is. SKILL.md step 2 asks for the same thing as a
review practice; CaMeL is the version a machine enforces.

## Spotlighting and datamarking: a layer

Spotlighting (Hines et al., [arXiv 2403.14720][spotlighting]) transforms untrusted text so
the model can tell it apart from the user's instructions. Microsoft describes three modes:
delimiting with a randomised marker around the text, datamarking by interleaving a special
token throughout it, and encoding it with an algorithm such as base64 that the model can
read. In each, the system prompt tells the model not to follow instructions inside the
marked text. Microsoft classes it as a probabilistic preventive technique ([MSRC][msrc]).

Treat it as a layer that lowers the rate of bad proposals:

- OWASP records that a separate, provenance-labelled channel reduces attack success in
  non-adaptive tests only, because an attacker who knows the marking scheme can mimic it,
  and that StruQ, a related structured-query approach, was bypassed under adaptive attack.
- Remove or escape the marker, delimiter and any look-alike characters from untrusted
  text before marking it, so the content cannot close its own wrapper.
- Strip invisible characters (tag block, variation selectors, zero-width characters) at
  ingest and render boundaries, as OWASP recommends. Stripping does not stop visible
  payloads.
- Never let marking stand in for a gate. A review that accepts "the content is delimited"
  as the control has accepted a probabilistic defence for a deterministic one.

## Egress: allowlists and what the client renders

Exfiltration needs a channel, and the model's output is one. Close both the tools and the
renderer.

- Allow outbound requests by destination and protocol for the task, enforced in the
  sandbox or network layer rather than in the prompt. Resolve and check the destination
  after redirects. SKILL.md step 4 sets the rule; here, test that a model-chosen URL
  cannot widen it.
- Do not give the agent a generic HTTP, fetch or browser tool when a narrow one will do.
  A URL the model composes can carry data in its host, path or query string.
- Do not render external images, link previews or iframes from model output. OWASP's
  LLM10:2026 entry says to disable auto-rendering of Markdown images, link previews and
  iframes by default, and where rendering is required to restrict fetches to an explicit
  allowlist of origins or proxy them through a server-side fetcher that strips
  data-bearing query parameters ([LLM10:2026 Improper Output Handling][owasp-llm10]).
  Microsoft fixed a reported Markdown-image exfiltration by deterministically blocking
  that technique and then the wider class, including certain untrusted links ([MSRC][msrc]).
- Treat a clickable link as an outbound path too: it needs a user click, but a link with
  context encoded in it still discloses on click.

## Human approval: show the exact payload, know the limits

Bind approval to the normalised action as [the approval contract](approval-contract.md)
specifies. Two limits apply on top of that.

- Show the exact rendered action, not a summary. OWASP's reason is that invisible-character
  smuggling can make the displayed action differ from the executed one, so the preview
  has to be generated from the same canonical bytes that execute, after the stripping
  above.
- Approval fatigue erodes the control. Both OWASP's LLM01 entry and its prompt-injection
  cheat sheet say reviewers degrade at volume. Keep approval for consequential actions, so
  a person sees few prompts, and monitor approval behaviour for drift, as OWASP's AI Agent
  Security Cheat Sheet advises.

Microsoft adds a design consideration: where an action cannot be sufficiently detected or
mitigated, have the user perform the final step themselves. Its example is a draft the
user must approve and send, so the model produces text and a person owns the effect.

## What does not work on its own

Each of these may belong in the stack as a layer. None may be the answer to "what stops
this".

- **Instructions in the prompt.** Declarative allow and deny statements are a partial
  control: OWASP notes an attacker who infers the prompt can bypass it.
- **Delimiters and structured prompt templates.** Labels the model has been asked to
  respect are not an enforcement boundary. The OWASP cheat sheet says template examples
  establish formatting only, not resistance, and to enforce permissions at the tool
  boundary.
- **Classifiers and filters as the only control.** They are probabilistic. Microsoft
  describes its classifier, Prompt Shields, as one layer and notes that deterministic
  detection of indirect injection is still an open research problem. OWASP notes semantic
  filters are evadable by rephrasing or encoding, and that low-resource-language and
  encoded inputs degrade them. A filter also fails silently: the attack that gets through
  is the one it did not recognise.
- **Asking the model whether an action is safe.** A guardrail model is itself an LLM and
  is susceptible to injection, per OWASP's cheat sheet, which also warns that task-alignment
  checks can miss attacks and block benign actions. A second opinion from the same
  family shares the first one's failure modes.
- **A static attack set.** Nasr et al., "The attacker moves second" ([arXiv 2510.09023][nasr]),
  as OWASP reports it, found static attack success near zero while adaptive attack success
  exceeded 90% for most of 12 recent defences. A defence evaluated only against known
  strings has not been evaluated.

## Testing: assert on the action trace

A reply that reads as a refusal does not show that nothing happened, and a reply that
reads as compliance does not show that anything did. Grade what the agent did.

1. **Assert on the trace.** After each run, check the recorded tool calls and mock state:
   no call to a destination outside the allowlist, no private read followed by an outbound
   send in the same session, no write to a forbidden field, no state change in the mock.
   OWASP's cheat sheet makes the same point: a refusal in the final response does not undo
   an action already taken, and a clean text response does not establish that nothing left
   through another channel.
2. **Version the corpus.** Keep the fixtures in the repository with a revision, keyed by
   delivery surface (page, email, tool output, memory, delegated report) and by the leg of
   the trifecta each is meant to test. Use benign sentinels, as
   [the benign test matrix](benign-test-matrix.md) requires. Record the corpus revision
   with every result so two runs compare like with like.
3. **Repeat the trials.** Model output varies, so one pass proves little. Run each case
   several times and report counts with their denominators. OWASP's cheat sheet advises
   repeating tests for this reason and, when comparing two defences, using the same cases
   with paired outcomes.
4. **Report attack success and task completion together.** A defence that blocks
   everything is not a defence. Include the ordinary tasks from the benign matrix and
   report their completion beside the attack results.
5. **Use a benchmark for the baseline.** AgentDojo (Debenedetti et al., ETH Zurich and
   Invariant Labs, [arXiv 2406.13352][agentdojo]) is an environment for evaluating
   injection attacks and defences against agents; its README shows running a chosen
   defence against a chosen attack, and warns that its API is still under development.
   OWASP names it, with JailbreakBench, as a baseline, and then asks for red-teaming by
   testers who have the full defence specification.
6. **Re-run on every model, prompt and tool change.** A control that held on one model
   version has no standing on the next. Treat the corpus as a regression suite.

## Sources checked

- [OWASP Top 10 for LLM Applications 2026][owasp-llm01]: LLM01 Prompt Injection (the
  baseline for most statements above), with LLM02 Sensitive Information Disclosure and
  LLM03 Excessive Agency as the entries it separates itself from, and
  [LLM10 Improper Output Handling][owasp-llm10].
- [OWASP LLM Prompt Injection Prevention Cheat Sheet][owasp-cheat].
- [Microsoft Security Response Center, indirect prompt injection defence (July 2025)][msrc].
- [CaMeL research repository][camel-repo] and [AgentDojo repository][agentdojo-repo].

The arXiv papers and the Willison and Meta posts named above were not fetched while
writing this file. Claims about them are limited to what the sources listed here state,
and each says so where it makes one.

[owasp-llm01]: https://github.com/GenAI-Security-Project/GenAI-LLM-Top10/blob/main/2026/final/LLM01_PromptInjection.md
[owasp-llm10]: https://github.com/GenAI-Security-Project/GenAI-LLM-Top10/blob/main/2026/final/LLM10_ImproperOutputHandling.md
[owasp-cheat]: https://github.com/OWASP/CheatSheetSeries/blob/master/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.md
[msrc]: https://www.microsoft.com/en-us/msrc/blog/2025/07/how-microsoft-defends-against-indirect-prompt-injection-attacks
[camel-paper]: https://arxiv.org/abs/2503.18813
[camel-repo]: https://github.com/google-research/camel-prompt-injection
[spotlighting]: https://arxiv.org/abs/2403.14720
[nasr]: https://arxiv.org/abs/2510.09023
[agentdojo]: https://arxiv.org/abs/2406.13352
[agentdojo-repo]: https://github.com/ethz-spylab/agentdojo
