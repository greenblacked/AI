# Run log and observer protocol

Read this when recording a clean-room run or running the outsider session. The log is the
evidence the page ships on, so it is kept beside the page source rather than in a chat
thread.

## Contents

- [Run log template](#run-log-template)
- [Stumble classes](#stumble-classes)
- [Observer protocol for the outsider run](#observer-protocol-for-the-outsider-run)
- [Reading a series of runs](#reading-a-series-of-runs)

## Run log template

```markdown
# Clean-room run: <page title>

- Run: <n> · Date: <YYYY-MM-DD> · Runner: <team or role, not a name>
- Page revision: <commit or published version>
- Product version: <version under test>
- Environment: <image and digest, or VM and OS version> · Platform: <os/arch>
- Account: new, created at step <n> · Network: public path, no VPN or mirror
- Target time to first result: <minutes> · Actual: <minutes>
- Stumbles: <count>

| Step | Clock | What the page said | What happened | Class | Minutes lost | Fix | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 00:07 | `sdk init` | `command not found`; page never adds the install dir to PATH | Missing step | 4 | Add PATH step with the shell-specific line | docs |
| 5 | 00:15 | "copy your API key" | Key only visible once, on a screen the page does not mention | Implicit state | 6 | Product: show key again; page: say when it appears | product |
```

Fill the clock column from wall time since the page was opened, so waits for email,
downloads and provisioning show up as gaps between steps rather than vanishing.

## Stumble classes

| Class | Looks like | Usual fix |
| --- | --- | --- |
| Missing prerequisite | A tool, version, permission or account the page never listed | Add it to prerequisites as a check command with expected output |
| Missing step | The author's environment already had it done | Add the step, at the point it is needed |
| Wrong command | Fails, renamed flag, moved path, copied prompt character | Fix and move the sample under test (`code-sample-testing`) |
| Output mismatch | Works, but prints something other than the page shows | Update the shown output, or say which parts vary |
| Invented value | The reader has to choose a name, region or key with no guidance | Give a concrete value, or say where to find it |
| Implicit state or wait | An email, provisioning delay, one-time display, or order dependency | State the wait and its usual length; fix the product if the wait is avoidable |
| Platform difference | Works on one OS or shell and not another | Tabs per platform, or narrow the supported list on the page |
| Ambiguous instruction | Two reasonable readings, one of them wrong | Rewrite to one action per step, condition before action |
| Rendering defect | Smart quotes, wrapped lines, invisible characters in copied text | Fix the source formatting and copy-test the rendered page |
| Product defect | Unclear error, awkward default, broken flow | Route to the owning team; do not document around it |

## Observer protocol for the outsider run

Before the session:

1. Recruit one person who matches the page's stated reader and has not used the product.
   A colleague from the same team knows too much to count.
2. Give them a clean room built from the checklist, not their own machine.
3. Agree the stall limit: how long they may be stuck before the session ends. Pick it
   from the target time, since a stall that eats the whole budget is where a real reader
   leaves.

During the session:

- They read aloud what they are doing and why. You take notes and say nothing.
- No questions in either direction. When they ask one, write it down verbatim as a
  defect and tell them to do what they would do alone.
- Note every re-read, every switch to a search engine, and every place they copied
  something different from what the page shows.

After the session:

- Each question, re-read and stall becomes a row in the run log with class and fix.
- Ask one question only at the end: "where did you nearly give up?" The answer usually
  names a stumble the notes already have, and occasionally one they missed.

## Reading a series of runs

Keep every run's log, not only the last. The series answers what one log cannot: whether
time to first result is converging on the target, which class keeps recurring (a recurring
class is a process defect, such as samples nobody tests), and whether the outsider found
classes the clean-room runs never did — if they did, the clean room was not clean.
