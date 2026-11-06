# From a failure to a record

## Worked example: a playtest note

Note from a session: "froze in the market, had to quit, lost a bit."

1. Ask which build and device. The tester's machine reports build 4812 on a handheld PC with 16 GB of RAM.
2. Fetch the save and recording from the session folder. The save is from the end of the second chapter.
3. Load the save and replay the logged input. It freezes on 3 of 10 attempts, always when opening the vendor menu while an NPC is walking past.
4. Check the progression path: the vendor sells the key item for chapter three. Progression path: yes.
5. Severity: a hang with progress loss on the progression path is S1.

The record title becomes "Hang opening the vendor menu with a passing NPC, market, chapter 2". The tester's sentence stays as the reporter's words. Whether the vendor menu is the cause is not yet known; the title states the observation.

## Worked example: an automated-playthrough failure

The run's failure folder holds the build id, the seed, the last 500 log lines, a screenshot and the final state.

1. Compare the last log lines with open bugs. Two other failures end with the same line. Group the three as one bug, count 3, and keep the three seeds.
2. Re-run from the earliest seed to get k/n. Say 7 of 20.
3. The run reached the bridge level, which is on the route to the ending. Severity S1 if it is a crash or hang; a timeout with no input accepted is treated as a soft-lock until a person checks.
4. Add the platform and hardware of the runner, since the bot's machine is a test rig and not a player's.

## A script that fills the mechanical fields

This reads a failure folder and prints the mechanical part of the record. It assumes the folder holds `meta.json` with `build`, `seed` and `platform`, and a `save.dat`; adapt the names to what your harness writes.

```python
#!/usr/bin/env python3
"""Print the mechanical fields of a bug record from a failure folder."""

import hashlib
import json
import sys
from pathlib import Path


def main(folder: str) -> int:
    root = Path(folder)
    meta = json.loads((root / "meta.json").read_text())
    save = root / "save.dat"
    digest = hashlib.sha256(save.read_bytes()).hexdigest() if save.exists() else "missing"
    print(f"- Build id: {meta.get('build', 'unknown')}")
    print(f"- Platform and hardware: {meta.get('platform', 'unknown')}")
    print(f"- Save: sha256 {digest}")
    print(f"- Seed: {meta.get('seed', 'not applicable')}")
    print("- Repro rate: fill in k/n after replaying from the seed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
```

Run it as `python3 record_fields.py path/to/failure-folder`. The repro rate and severity stay manual because they need a person's judgement.
