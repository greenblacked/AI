---
paths:
  - "**/Gameplay/**"
  - "**/gameplay/**"
  - "Assets/Scripts/**"
  - "Source/**/Gameplay/**"
  - "src/game/**"
---

# Working on gameplay code

Three rules that keep a game tunable, frame-rate independent and testable.

- Tuning values (speeds, damage, costs, drop rates, timers) come from data files, not literals in code. A designer or a balance script can then change a number without a rebuild, and the number has one home to search.
- Anything that moves, accelerates or counts down per frame scales by delta time, or runs in the fixed-timestep update. A per-frame constant plays at a different speed on every display refresh rate; test by capping the frame rate at 30 and then 144 and comparing a jump or a timer.
- Gameplay logic never reads UI state. A health check that reads the health bar's width, or a pause that reads whether a menu is visible, breaks the day the UI is redesigned or hidden. The UI reads the game state and the game state never reads the UI.
