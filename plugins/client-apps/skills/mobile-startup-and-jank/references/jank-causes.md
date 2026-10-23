# Jank causes

The common causes of dropped frames in native apps, how each shows in a trace, and the
fix. Read this at step 6 with a Perfetto or Instruments trace open.

## Contents

- [Reading a slow frame](#reading-a-slow-frame)
- [Causes on both platforms](#causes-on-both-platforms)
- [Android-specific](#android-specific)
- [iOS-specific](#ios-specific)
- [Cross-platform frameworks](#cross-platform-frameworks)

## Reading a slow frame

Find a frame over budget in the trace, then ask which thread ran long:

- **Main or UI thread long:** your code, layout, binding or decoding is on it. Most jank
  is here.
- **Render thread or GPU long:** too much to draw — overdraw, large bitmaps uploaded as
  textures, blur, shadows, offscreen passes.
- **Neither long, frame still late:** the main thread waited — on a lock, I/O, a binder
  call — or the CPU was busy elsewhere or throttled. Check thread states and CPU
  frequency in the trace.

Judge the result on the same scripted scroll before and after, by p95 frame time or hitch
ratio.

## Causes on both platforms

| Cause | How it shows | Fix |
| --- | --- | --- |
| Work in item binding or cell configuration | Long bind or configure slices on the main thread, worst when a new item type appears | Precompute display models off the main thread; bind only assigns |
| Image decoding on the main thread, or at full size | Decode slices on the main thread; large texture uploads | Decode off the main thread at display size; cache decoded bitmaps sized to the view |
| Deep or nested layout | Long measure and layout passes, repeated for nested weights or intrinsic sizing | Flatten; avoid measuring children twice |
| Allocation churn | Frequent garbage collection, or allocation slices inside each frame | Reuse objects in the scroll path; avoid formatting strings per frame |
| Synchronous I/O or database reads during scroll | Main thread waiting, not running | Page data in ahead of the scroll on a background thread |
| Text measurement for many long strings | Text layout slices per item | Precompute text layout off the main thread where the platform allows |

## Android-specific

| Cause | How it shows | Fix |
| --- | --- | --- |
| No Baseline Profile | JIT and verification slices during the first scrolls after install | Generate and ship one covering the scroll journey |
| `RecyclerView` full rebinds | `notifyDataSetChanged` followed by binding every visible row | `ListAdapter` with `DiffUtil`, stable IDs |
| Compose recomposing too much | Recomposition counts high for items whose data did not change | Stable parameters, `key` in lazy lists, `remember` derived values, read fast-changing state as late as possible |
| Overdraw | GPU overdraw debug overlay shows red areas | Remove backgrounds hidden under other backgrounds |
| Nested scrolling containers | Measure passes repeated per child | One lazy list with multiple item types |

## iOS-specific

| Cause | How it shows | Fix |
| --- | --- | --- |
| Shadows without a shadow path, masks, corner radius with clipping | Offscreen render passes in the Animation Hitches or Core Animation instruments | Set `shadowPath`; pre-render rounded images; avoid masks in scrolling cells |
| Auto Layout cost in self-sizing cells | Long layout passes per cell | Simpler constraint sets; cache heights where content is fixed |
| SwiftUI view bodies recomputed broadly | Many body evaluations per scroll in the SwiftUI instrument | Narrow the observed state per view; split large views |
| Commit hitches | Hitches attributed to the app's commit phase | Less work between the touch and the commit: layout, decoding, view creation |
| Render hitches | Hitches attributed to the render server | Fewer layers, less blending and offscreen work |

## Cross-platform frameworks

- **Flutter:** profile in profile mode, never debug; the performance overlay separates UI
  and raster thread time. Shader compilation jank on first use of an effect is a known
  class; check the current Flutter guidance for the rendering engine your version uses.
- **React Native:** separate JavaScript thread time from UI thread time; long JavaScript
  tasks during scroll delay updates, and lists need virtualisation with stable keys.
