# Known WebKit-only causes

Contents: the main list from step 3 with symptoms, checks and fixes, then the less
common causes worth checking when the main list comes up empty.

## Main list, in checking order

| Symptom | Cause | Check | Fix |
| --- | --- | --- | --- |
| Bottom of a full-height section hidden behind the toolbar; layout jumps as toolbars retract | `100vh` is the large viewport on iOS | Compare `window.innerHeight` with the element's height in Web Inspector | `height: 100vh; height: 100dvh;` (or `svh` to fit the smallest viewport) |
| Fixed bottom bar under the home indicator | Safe area not applied | Is `viewport-fit=cover` set, and is the bar padded? | `padding-bottom: env(safe-area-inset-bottom)` with `viewport-fit=cover` in the viewport meta tag |
| Fixed bar jumps or hides when the keyboard opens | The keyboard shrinks the visual viewport, not the layout viewport | Log `visualViewport.height` on `resize` while typing | Position from `visualViewport` events, or let the bar scroll with content while an input has focus |
| Page zooms in when a field is tapped | Input font size under 16px | Computed `font-size` of the focused field | 16px or more on inputs, selects and text areas |
| Sticky header scrolls away | An ancestor's `overflow` makes it the scroll container | Walk up from the sticky element checking computed `overflow` | Remove the overflow, or move the sticky element out of that ancestor |
| Rounded card does not clip an animated or transformed child | WebKit compositing with `overflow: hidden` and `border-radius` | Remove the child's transform and see if clipping returns | `isolation: isolate` on the clipping element |
| `Invalid Date`, or dates off by the time zone | Non-ISO date strings parsed differently | Evaluate the exact string in the Safari console | ISO 8601 with `T` and an offset, or a parsing library |
| Date field shows a format the code does not expect | Native picker display differs from `value` | Read `input.value`, not the displayed text | Always read and write `yyyy-mm-dd` in `value` |
| Logged out after about a week, only on iOS and Safari | ITP deletes script-writable storage after seven days of Safari use without interaction, and caps `document.cookie` cookies at seven days | Where does the session live: local storage, IndexedDB, a JavaScript-set cookie? | Server-set `HttpOnly` cookie from your own domain |
| Offline data or drafts vanish | IndexedDB evicted under pressure or by the cap above; Private Browsing storage ends with the session | Reproduce after a week idle or under low disk; check Private Browsing | Treat it as a cache, sync to the server, request persistence and check the result |
| `undefined is not a function` on a modern API | The API is newer than the user's Safari | Compatibility data for the user's exact version | Feature-detect and provide a fallback or polyfill |

Home Screen web apps are not subject to the seven-day cap in the same way as Safari tabs,
because their counter is based on use of the app itself; a bug reported only from Safari
tabs, not from the installed app, points at ITP.

## Less common causes

| Symptom | Cause | Fix |
| --- | --- | --- |
| A tap on a `div` does nothing on iOS, but works on desktop | iOS may not dispatch click events to elements it does not consider clickable, notably with delegation on `body` | Use a real `button` or link; this is also the accessible fix |
| Hover style stays on after a tap | Touch devices emulate hover on tap | Wrap hover styles in `@media (hover: hover)` |
| Video will not autoplay or jumps to fullscreen | Inline autoplay needs specific attributes on iOS | `muted` and `playsinline` on the `video` element |
| Login inside an embedded iframe fails | Safari blocks third-party cookies by default | Move login to a top-level page, or use the Storage Access API (`document.requestStorageAccess()`) |
| Frosted-glass effect missing on older Safari | Older versions need the prefixed property | Declare `-webkit-backdrop-filter` beside `backdrop-filter` |
| Layout breaks only on an old iPad | A layout feature newer than its iOS version, such as flexbox `gap` | Check compatibility for that version; use `@supports` and a fallback |
| Fails only inside an app's in-app browser | A web view with different storage, permissions and features | Reproduce in that app; offer to open in Safari for flows that need full storage |
| Fails only with Lockdown Mode on | Lockdown Mode disables some web technologies | Confirm with the user; degrade gracefully rather than requiring the feature |

When nothing here matches, reduce the page: delete half the markup, styles or script,
recheck in the same environment, and repeat until the smallest page that still fails is
left. That page is both the diagnosis and the bug report.
