# Reading heap snapshots

Read this in steps 3 and 4, with a snapshot open in the Chrome DevTools Memory panel.

## Contents

- The views
- The columns
- Retainer patterns
- Noise to ignore
- Console helpers

## The views

| View | Use it for |
| --- | --- |
| Summary | Objects grouped by constructor. With the "Objects allocated between Snapshot 1 and Snapshot 2" filter in snapshot 3, this is the three-snapshot result |
| Comparison | Two snapshots side by side, per constructor: `# New`, `# Deleted`, `# Delta`, `Size Delta`. Good for a quick look at which types grew; the three-snapshot filter is more precise because it excludes one-off allocations |
| Containment | The heap from the roots down. Rarely the first view; useful to see what a global object holds |
| Statistics | Totals by kind (code, strings, arrays, typed arrays, system). A typed-array or string share that grows between snapshots narrows the search quickly |

The allocation instrumentation on timeline profile is the other useful tool: record while
repeating the action, and bars that stay blue at the end of the recording are allocations
still alive. Select a bar to see which objects it allocated. It costs more overhead than a
snapshot, so use it once the action is known.

## The columns

- **Shallow size** — the object's own memory. Usually small.
- **Retained size** — what would be freed if this object were collected, including
  everything only it keeps alive. Sort by this to find what matters.
- **Distance** — hops from a garbage-collection root along the shortest path. It tells you
  how long the retainer chain will be to read, not whether the object leaked.

## Retainer patterns

Read the Retainers pane from the selected object upwards. The first entry your code owns
is the one to change.

| Chain ends in | What it means | Fix |
| --- | --- | --- |
| `Window` or `HTMLDocument`, through an event listener and a function's `context` | A listener on a global target closes over the component | Remove it in cleanup, or add it with an `AbortController` signal and abort on unmount |
| An engine root, through a function passed to `setInterval`, `setTimeout` or `requestAnimationFrame` | A timer or frame loop still scheduled | Clear or cancel it in cleanup |
| An observer object (`ResizeObserver`, `IntersectionObserver`, `MutationObserver`) | Observer never disconnected | `disconnect()` in cleanup |
| A store, emitter or socket's listener array | Subscription never released | Call the unsubscribe function returned at subscription |
| A module-level `Map`, `Set` or array | A cache or registry with no eviction | Bound it, evict on unmount, or key it with a `WeakMap` when the key is an object |
| A third-party library's internal registry | An instance never destroyed | Call its destroy or dispose method when the container is removed |
| `context` of a small function held by something long-lived | A closure retaining a sibling closure's variables | Null the large variable after use, or move the long-lived callback out of the scope that holds it |
| A `Detached` element through another `Detached` element | A whole removed subtree held by one reference | Find the single reference into the subtree; the rest follows |

One reference into a detached subtree keeps the entire subtree alive, because every node
references its parent and children. Find the reference from outside the subtree; the
internal ones are not the leak.

## Noise to ignore

- Objects whose count does not scale with repetitions: one-off initialisation, lazily
  loaded modules, interned strings, compiled code.
- `(internal)`, `(system)`, `(compiled code)` and engine hidden classes in a retainer
  chain; read past them.
- Objects retained by DevTools itself: console-logged values, objects selected in the
  Elements panel (`$0`) or stored as console variables. Clear the console and deselect
  before the final snapshot.
- Framework development-mode retention: component stacks and debug metadata kept only in
  development builds. Confirm in a production build.

## Console helpers

These Chrome DevTools console utilities help confirm a suspicion without a full snapshot:

```js
getEventListeners(window)              // listeners on window, grouped by type
getEventListeners(document)
queryObjects(MyComponentClass)         // live instances created by this constructor
```

`queryObjects` logs an array of the live objects whose prototype chain includes that
constructor's prototype. Collect garbage and run it, repeat the action ten times, collect
garbage and run it again: a count that rises by ten confirms the leak for that type.
