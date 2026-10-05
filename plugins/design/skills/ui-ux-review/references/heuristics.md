# Heuristics, states, severity and platform sizes

Read this during a review of a screen or flow, at steps 4 to 6 of `SKILL.md`.

## Contents

- The state matrix
- Nielsen's ten heuristics, and what each looks like on a screen
- The severity scale
- Platform control sizes
- Finding template

## The state matrix

Walk each control on the primary task path through every row. Mocks show the resting state with good data, so a row you cannot see is a row to ask for, not to skip.

| State | What to check | A finding looks like |
| --- | --- | --- |
| Rest | Does the control look operable, and is its label a verb or a noun the user would use? | A button styled as plain text that users do not recognise as clickable. |
| Hover | Does the pointer change what the user expects it to? Is there a touch equivalent? | Information or an action that only appears on hover, with nothing on touch. |
| Focus | Can you see where keyboard focus is at every step of the path? | Focus ring removed and not replaced. Conformance belongs to `accessibility-audit`; the usability consequence belongs here. |
| Pressed | Does the control acknowledge the press within a moment? | A submit that gives no sign it registered, so the user presses it twice. |
| Disabled | Does the user learn why it is disabled and what enables it? | A disabled primary button with no stated reason. |
| Loading | Is the wait shown, and can the user tell progress from a hang? | A spinner with no end state and no timeout message. |
| Empty | Does a screen with no data say what belongs here and how to add it? | A blank panel that looks like a rendering failure. |
| Error | Does the message say what happened, where, and what to do next, in the user's words? | A code or a generic failure, with the entered data lost. |
| Success | Is the outcome confirmed, and is the next step clear? | The form clears and returns to the start with no confirmation. |

## Nielsen's ten heuristics, and what each looks like on a screen

The ten are Jakob Nielsen's usability heuristics, published by Nielsen Norman Group at <https://www.nngroup.com/articles/ten-usability-heuristics/>. They are broad rules of thumb for finding problems, not a specification, and the third column is this repository's opinion on where each shows up.

| No. | Heuristic | Where to look |
| --- | --- | --- |
| 1 | Visibility of system status | Loading, saving, progress, selected and current-location indicators, and whether anything changed after a press. |
| 2 | Match between the system and the real world | Labels, units, icons and error text in the user's language, not the database's. |
| 3 | User control and freedom | Back, cancel, undo and close on every step, especially after a destructive or long action. |
| 4 | Consistency and standards | The same control looking and acting the same, and platform conventions followed. |
| 5 | Error prevention | Constraints, sensible defaults, confirmation only where the action cannot be reversed, validation before submit where it can be done. |
| 6 | Recognition rather than recall | Options visible on the screen, the information from the last step carried to the next, recent items offered. |
| 7 | Flexibility and efficiency of use | Shortcuts, saved choices and bulk actions for the repeat user that do not get in the novice's way. |
| 8 | Aesthetic and minimalist design | Competing calls to action, information that does not serve the task, decoration that pushes the primary action below the fold. |
| 9 | Help users recognize, diagnose, and recover from errors | Plain-language message, the cause, and a way forward in the same place the error appeared. |
| 10 | Help and documentation | Help reachable from the point of need, short and task-shaped, searchable if long. |

Cite the number with the finding, for example "heuristic 9". If a problem fits none of them cleanly, check that it is a problem for the user rather than a preference.

## The severity scale

The scale is Nielsen Norman Group's, from <https://www.nngroup.com/articles/how-to-rate-the-severity-of-usability-problems/>.

| Rating | Meaning | What you do with it |
| --- | --- | --- |
| 0 | Not a usability problem at all | Do not list it as a finding. |
| 1 | Cosmetic problem only | Fix if time permits. |
| 2 | Minor usability problem, low priority | Schedule it. |
| 3 | Major usability problem, high priority | Fix before the next release. |
| 4 | Usability catastrophe, imperative to fix before release | Stop the release. |

Severity combines three things: how frequent the problem is, how much it hurts when someone meets it, and how persistent it is, meaning whether people can get past it once they know. A problem on the primary task path that every user meets and none can avoid is a 3 or 4 whatever it looks like. The same visual flaw on a page few people reach is a 1. Say which of the three drove the rating when it is not obvious.

## Platform control sizes

Apple's Human Interface Guidelines list default and minimum control sizes per platform. Use them when the screen ships on an Apple platform.

| Platform | Default | Minimum |
| --- | --- | --- |
| iOS and iPadOS | 44 by 44 pt | 28 by 28 pt |
| macOS | 28 by 28 pt | 20 by 20 pt |
| tvOS | 66 by 66 pt | 56 by 56 pt |
| visionOS | 60 by 60 pt | 28 by 28 pt |
| watchOS | 44 by 44 pt | 28 by 28 pt |

44 pt is the iOS default, not its minimum, so a 36 pt control on iOS is below the default but above the minimum. Report it as a consequence on a thumb-driven task path rather than as a violation.

On the web, WCAG 2.2 sets a minimum target size of 24 by 24 CSS pixels (success criterion 2.5.8, Level AA, with exceptions) and an enhanced 44 by 44 (2.5.5, Level AAA). A conformance call is `accessibility-audit`'s. In a usability review, use the sizes to explain a consequence: small targets next to each other on a narrow screen produce mis-taps.

For Material Design 3, the filled button has a container height of 40 px and a fully rounded shape. Material Web's button implementation enforces a 48 px touch target. Treat that 48 px as a property of that implementation, not as a Material token.

## Finding template

```text
[severity 0-4] One-line problem (heuristic number)
Evidence: screenshot file and viewport, or frame name, or file:line; the exact selector or component; the state.
Consequence: what the named user does or fails to do because of it.
Fix: the smallest change that removes the consequence.
```
