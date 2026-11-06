# The bug record

Use one record per bug. Copy this into the tracker as the issue template so the empty fields are visible.

```markdown
## [Area] [what happens], [where]

- Severity: S1 | S2 | S3 | S4   (reason in one line, citing the scale)
- Progression path: yes | no | unknown   (which quest, level or unlock)
- Build id: [as printed by the game]
- Platform and hardware: [platform, model or GPU and driver, CPU, RAM, OS, storage, input device]
- Save: [attached filename] or [hash] at [archive location]
- Seed: [value] or not applicable
- Input log or replay: [attached filename], starting from the save above
- Repro rate: k/n from the save, [date], [build id]
- Narrowing: [conditions that raise or lower the rate]
- Expected: [one line]
- Actual: [one line]
- Reporter's words: "[quote]"
- Owner: [a person]   Decision: [fix before release | known issue with workaround | defer to patch X]
```

Owner and decision are blank until the bug is S2 or above; the release gate reads them.

## Hooks worth building

A tester who has to type a build id will mistype it, so the game should supply what it can:

- Print the build id, platform and hardware summary on a debug overlay that survives screenshots and video capture.
- Add a "report a bug" key in test builds that writes the current save, the last few minutes of input and the seed into one folder, and prints the folder name. Check how your engine and platform expose the input stream before choosing a format; the requirement is only that replaying it from the save reproduces the run.
- Write the seed at the start of each run and each encounter that uses randomness, not only at launch.
- Hash the save with a fixed algorithm so the record can name it even when the file is too large to attach, and archive the file under that hash.
- On an unattended run, write the same folder on failure; the automated-playthrough skill already specifies the contents.

## Checks before assigning

- Can someone who has not seen the bug get from the save to the failure by replaying the input? If not, the record is not ready.
- Is the build id one that still exists in the build archive?
- Does the hash in the record match the archived file? Compute it again; a copied save is sometimes a different save.
