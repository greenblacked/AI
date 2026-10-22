---
name: browser-memory-leak-hunt
description: "Find and fix a memory leak in a long-lived browser page: confirm the growth is JavaScript heap or DOM rather than images or GPU, run the three-snapshot technique (warm up, snapshot, repeat the action ten times, snapshot, repeat, snapshot) keeping only objects allocated between the first two snapshots that survive into the third, read retainer chains for detached DOM nodes, listeners, closures, timers and observers, and confirm the fix as a flat sawtooth after forced garbage collection. Use when someone says \"the tab grows to 2GB\", \"the dashboard crashes after a day open\", \"Aw, Snap out of memory\", \"detached DOM nodes in the heap snapshot\" or \"memory climbs every time I open the modal\". Not for slow code with stable memory (profiling), a server process that leaks (debugging), or poor field vitals (web-vitals-triage)."
allowed-tools: "Read, Grep, Glob"
---

# Browser Memory Leak Hunt

Done means you can name the user action that leaks, the object type that accumulates, the retainer chain that keeps it alive and the line that creates that reference, and show that after the fix repeating the action and forcing garbage collection returns the heap and DOM node count to the same floor every time.

Leaks in long-lived pages — dashboards, editors, trading screens, kiosks, single-page apps left open for days — are slow and silent. A few hundred kilobytes per route change becomes two gigabytes by the end of a shift and a crashed tab. The common mistake is reading one heap snapshot: it shows what is large, and large is usually caches and frameworks doing their job. A leak is what grows with repetition and never comes back, which only a comparison across repeated actions shows. The second mistake is assuming it is JavaScript at all: decoded images, canvases, video and blob URLs grow a tab's memory without touching the JavaScript heap, and no heap snapshot will find them.

## Scope

Use for: a browser tab whose memory grows over hours or days; a crash with an out-of-memory error page; heap snapshots full of detached DOM nodes; memory that rises each time a modal, route, chart or panel opens and closes; adding a leak check to CI.

Do not use for: code that is slow while memory is stable (`profiling`); a Node.js, JVM or other server process that grows (`debugging`); poor LCP, INP or CLS (`web-vitals-triage`), though a leak that triggers constant garbage collection does make interactions slower.

## Workflow

### 1. Find which memory is growing

Open Chrome's Task Manager (Shift+Esc on Windows and Linux, Window then Task Manager on macOS) and enable the JavaScript memory column if it is hidden. Leave the page doing what users do and watch two numbers: the tab's memory footprint, and its JavaScript memory.

| Task Manager shows | Meaning |
| --- | --- |
| Footprint grows, JavaScript memory grows | A JavaScript or DOM leak: continue with step 2 |
| Footprint grows, JavaScript memory flat | Native memory: images, canvas and WebGL contexts, video, `ArrayBuffer` backing stores, blob URLs never revoked with `URL.revokeObjectURL`. Look at what the page creates for each repeated action outside the heap |
| JavaScript memory saw-tooths back to the same floor | Not a leak; high allocation churn. That is a performance question for `profiling` |

The DevTools Performance monitor (from the Command Menu, "Show Performance monitor") shows JS heap size, DOM nodes and JS event listeners live. A DOM node or listener count that climbs and never drops is the fastest signal there is.

### 2. Find the action that leaks

A leak is tied to a repeatable action: open and close a modal, navigate to a route and back, add and remove a widget, receive a burst of socket messages. Find it before taking snapshots.

Repeat one candidate action twenty times and watch the Performance monitor. Press the "Collect garbage" button (the bin icon in the Memory or Performance panel) between rounds. If the DOM node count or heap floor rises in steps that line up with the action, that is the action. If nothing user-driven correlates, suspect timers and subscriptions that run without interaction, and leave the page idle for ten minutes with the monitor open.

Gate: name one action and the growth per repetition before profiling.

### 3. Three snapshots

Work in a clean browser profile with extensions disabled — extension content scripts allocate in the page's heap and appear in its snapshots. Close the console or clear it, because objects logged to the console are retained by DevTools and look exactly like a leak.

1. Load the page and perform the action once or twice to warm up caches, lazy modules and pools.
2. Take heap snapshot 1 (Memory panel, Heap snapshot). Taking a snapshot forces a full garbage collection first.
3. Perform the action ten times, returning to the starting state each time. Take snapshot 2.
4. Perform the action ten more times. Take snapshot 3.
5. In snapshot 3, set the Summary view's filter to "Objects allocated between Snapshot 1 and Snapshot 2".

What remains was created during the first ten repetitions and is still alive after ten more. Anything the warm-up or one-off initialisation created is excluded by snapshot 1, and anything that is merely transient is excluded by snapshot 3. Sort by retained size, then look for counts that are multiples of ten, which is the signature of one leaked object per action.

Then type `Detached` into the class filter of the same view. Detached DOM elements are nodes no longer in the document but still referenced from JavaScript; after a close action they are almost always the leak itself or its retained payload.

### 4. Read the retainer chain

Select a leaked object and read the Retainers pane from the object towards the root. Skip entries the engine owns — `(internal)`, `(system)`, `(compiled code)`, the context of a function you did not write — and stop at the first object your code or a library you configured holds. That is the reference to break.

`references/reading-heap-snapshots.md` covers the retainer patterns and what each one means. The usual owners, in order of frequency:

- **Event listeners on long-lived targets** — `window`, `document`, a global event bus or store — added on mount and not removed on unmount. The listener's closure holds the component and its DOM.
- **Timers and animation frames** — `setInterval`, `setTimeout` chains and `requestAnimationFrame` loops not cleared on unmount.
- **Observers** — `ResizeObserver`, `IntersectionObserver` and `MutationObserver` not disconnected.
- **Subscriptions** — a store, socket or event-emitter subscription whose unsubscribe function was never called.
- **Collections that only grow** — a module-level `Map`, array or cache keyed by component, request or DOM node, with no eviction.
- **Third-party instances not destroyed** — charts, maps, editors and players that need an explicit destroy call when their container goes away.
- **Closures sharing a context** — a small callback kept alive by a long-lived owner retains every variable its enclosing function captured, including a large one used only by a sibling closure.

### 5. Fix the owner, then prove the floor is flat

Fix at the reference, not the symptom: remove the listener in the same component's cleanup, clear the timer, disconnect the observer, call the destroy method, bound the cache. Passing an `AbortController` signal to `addEventListener` lets one `abort()` in cleanup remove every listener the component added. Use a `WeakMap` for data attached to DOM nodes or objects you do not own.

Then repeat step 2: perform the action fifty times with forced collection between rounds. The heap and DOM node count must return to the same floor each time — a flat sawtooth. A floor that still rises more slowly means a second leak behind the first; return to step 3.

Add a regression check so it stays fixed; `references/automating-leak-checks.md` has a browser-test shape that repeats the action, forces collection and asserts on DOM node and heap counts.

Heap snapshots contain every string the page held, including tokens and personal data. Keep them where you would keep a production database dump, and do not attach them to a public issue.

## Anti-patterns

**Diagnosing from one snapshot.** Size is not growth. The biggest object is usually a cache that is supposed to be big.

**Leaving the console open with logging on.** DevTools retains logged objects; the leak you are chasing may be your own `console.log`.

**Calling `WeakRef` or `FinalizationRegistry` the fix.** They make the collection timing someone else's problem without removing the strong reference that caused the leak, and the registry callback is not guaranteed to run.

**Reloading the page on a timer.** It hides the leak, loses user state, and the leak returns with the next feature that holds more memory per action.

**Testing in development mode only.** Development builds retain extra data for tooling, and React Strict Mode mounts components twice. Confirm the fix in a production build.

## Output format

```markdown
## Growth
[Footprint versus JavaScript memory, DOM node and listener trend, growth per repetition of the action.]

## Action
[The repeatable action that leaks, and the count used.]

## Leaked objects
[Type, count after 10 and 20 repetitions, retained size, detached nodes.]

## Retainer chain
[From the leaked object to the first reference your code owns, with file and line.]

## Fix and proof
[The change; the floor after 50 repetitions with forced collection; the regression check added.]
```

## Reference files

- `references/reading-heap-snapshots.md` — read in step 3 and step 4: the Summary, Comparison and Containment views, shallow against retained size, distance, the retainer patterns for listeners, closures, timers and detached trees, and the noise to ignore.
- `references/automating-leak-checks.md` — read in step 5: a Playwright or Puppeteer check that repeats an action, forces collection and asserts on DOM nodes and heap size, memlab for scripted three-snapshot runs, and field monitoring with `performance.measureUserAgentSpecificMemory()`.
