# Platform technical requirements, expanded

Read this before scheduling the step 5 test pass. Each platform's real checklist — Sony's TRC, Microsoft's XR requirements, Nintendo's lotcheck guidelines, Apple's and Google's review guidelines — is behind that platform's developer portal, and the console ones are under NDA. This file is the category list with the test each category implies, so the pass can be planned and staffed before anyone has read the document.

## Contents

- [How to run the pass](#how-to-run-the-pass)
- [Lifecycle: suspend, resume and termination](#lifecycle-suspend-resume-and-termination)
- [Accounts, sign-out and user switching](#accounts-sign-out-and-user-switching)
- [Input and controllers](#input-and-controllers)
- [Storage, save data and quota](#storage-save-data-and-quota)
- [Network loss and recovery](#network-loss-and-recovery)
- [Achievements, trophies and platform features](#achievements-trophies-and-platform-features)
- [Boot, load and responsiveness](#boot-load-and-responsiveness)
- [Nomenclature and localisation](#nomenclature-and-localisation)
- [Display, hardware modes and accessibility](#display-hardware-modes-and-accessibility)
- [The hardware and configuration matrix](#the-hardware-and-configuration-matrix)

## How to run the pass

Treat it as a scripted pass with a recorded result per row, not as exploratory testing. Each row below is a scenario with a pass condition; a tester who has not been given the pass condition will report "it seemed fine".

Run it on retail-configuration hardware. Dev kits have more memory, faster or differently behaved storage, and a network path that does not resemble a player's. Suspend timing, storage-full handling and boot time are all cases where the dev kit passes and the retail unit does not.

Run it twice: once at content lock, and once on the exact build being submitted. The second run exists because the fix for a requirement failure is the most common cause of the next one.

## Lifecycle: suspend, resume and termination

- Suspend during gameplay, during a loading screen, during a cutscene, during a save, and while a network request is in flight. Resume each. The game returns to the same state, audio resumes, and no input is lost or stuck.
- Suspend for a long period — hours — and resume. Anything the game derived from wall-clock time, a session token, or a timer has to survive or be re-established rather than producing a negative duration or an expired-session crash.
- Be terminated while suspended, which the platform may do at any time, and relaunch. The game reaches a playable state with the last save intact.
- Resume with the network gone, the controller changed, and the account signed out. Each is a separate case and each is tested.

## Accounts, sign-out and user switching

- Sign out the active user mid-session. The game returns to a screen appropriate to having no user, does not continue play under a vanished profile, and writes nothing to that profile afterwards.
- Switch to a different user. Save data, settings, achievements and entitlements follow the new user; nothing leaks from the previous one.
- Start with no user signed in at all, where the platform allows it.
- Lose an entitlement mid-session — a shared or family licence revoked while playing. The expected behaviour is platform-specific and it is tested.

## Input and controllers

- Disconnect the active controller during play. The game pauses by itself and shows a reconnect prompt naming the correct device in the platform's own terms.
- Reconnect it, and separately connect a different one. Input rebinds to the right pad and does not silently follow the wrong one.
- Connect more controllers than the game supports, and fewer than a mode requires.
- Every controller type the platform requires, including handheld modes, detached pads and any accessibility controller. Rumble, gyro and touch behaviour where mandated.
- Every action reachable by controller alone, with no keyboard or touch dependency, on a console.

## Storage, save data and quota

- Fill the storage device and attempt a save. A clear message, a retry path, and no lost data or crash.
- Exceed the title's own save quota, which is smaller than the device and is the case that actually happens. Count slots, autosaves and backups against it — `game-save-system` sizes that.
- Remove external storage mid-session where the platform supports removable media.
- Corrupt or absent save data at launch. The game starts, says what happened, and does not delete anything it cannot replace.
- Save data messaging: the platform's required indicator is visible while writing, the warning against powering off appears where mandated, and no write starts inside a restricted window such as during suspend.

## Network loss and recovery

- Disconnect the network during a download, a login, a purchase, a leaderboard write and an in-game session. Each produces a stated outcome and a route forward, never an indefinite spinner.
- Reconnect. Anything queued resolves or is discarded with a message; nothing is silently lost.
- Run on a slow and lossy link rather than only a disconnected one — the partial case is where soft locks live, and `game-netcode` owns the in-play behaviour.
- Fail a purchase or a restore, and repeat a purchase, since double-charge and lost-entitlement paths are both checked.

## Achievements, trophies and platform features

- Metadata complete, localised into every required language, and consistent with the game's own names for things.
- Each unlock fires once, at the moment the requirement is met, and not again on a reload.
- Unlocks queue and deliver correctly when earned offline.
- Any platform overlay, share, capture, rich presence or activity feature the platform requires behaves as specified, including being invoked at awkward moments.

## Boot, load and responsiveness

- Time from launch to a responsive screen, on retail hardware from cold. Several platforms cap it.
- The first frame shows something the platform permits; an extended black screen is a failure on some platforms even when the game is working.
- The game responds to the platform's system menu, guide button or home gesture at every stage of boot and load, not only once play has started.

## Nomenclature and localisation

- Buttons, accounts, storage, online services and the hardware itself carry that platform's official names. Another platform's term, or a generic one where the platform specifies its own, is a straightforward rejection and is trivially found by a text search.
- Legal, safety and system-facing strings are localised into every language the storefront lists for the territory, even when the game's content is not.
- Health and epilepsy warnings, and any mandated legal screen, appear where and as specified.
- Text fits its box in every language. Expansion breaks layouts that were built against English.

## Display, hardware modes and accessibility

- Every supported resolution and display mode, including handheld and docked where applicable, HDR on and off, and the platform's performance and quality modes if the game offers them.
- Safe area respected, so nothing required sits under an overscan boundary.
- Any accessibility feature the platform mandates, and any platform-level setting the game must honour rather than override.
- Multiple monitors, alt-tab and window resize on PC storefronts, including while loading.

## The hardware and configuration matrix

Build the matrix explicitly rather than testing on whatever is on the desk:

| Axis | Values that must appear |
| --- | --- |
| Hardware | Every model and revision the platform requires, at retail configuration, including the lowest one |
| Storage | Internal, external, and the platform's slowest supported medium |
| Account state | Signed in, signed out, secondary user, child account, offline account |
| Network | Full, slow, lossy, absent, and lost mid-operation |
| Storage state | Empty, nearly full, quota exceeded, corrupt save present |
| Language | Every language the territory requires, at least for system-facing text |
| Install state | Fresh install, update over a previous version, and play-while-downloading where the platform supports it |

The rows that get skipped are the last three, and they are where late rejections come from.
