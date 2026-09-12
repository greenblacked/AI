# Texture compression, per platform

Read this before setting any per-platform override. The formats are not interchangeable, the wrong choice does not error, and the cost of getting it wrong is measured in whole multiples of texture memory rather than percentages.

## Contents

- [Why this is the biggest lever](#why-this-is-the-biggest-lever)
- [Desktop and current consoles: the BC family](#desktop-and-current-consoles-the-bc-family)
- [Mobile: ASTC and ETC2](#mobile-astc-and-etc2)
- [Console families](#console-families)
- [Web: transcode at load](#web-transcode-at-load)
- [Choosing by what the texture contains](#choosing-by-what-the-texture-contains)
- [The silent fallbacks](#the-silent-fallbacks)
- [Setting it per engine](#setting-it-per-engine)
- [Sizes worth memorising](#sizes-worth-memorising)

## Why this is the biggest lever

A GPU samples block-compressed textures directly from their compressed form, so compression is a permanent reduction in memory and in the bandwidth spent reading it, not a decode step at load. An uncompressed RGBA8 texture is 4 bytes per pixel. Block compression takes that to 1 byte per pixel for the high-quality formats and 0.5 for the cheap ones, and on mobile ASTC goes lower still. Nothing else in the pipeline offers an eight-times reduction for a setting change.

The PNG in the project is an intermediate. It is decoded at import, compressed to the target format, and never read at runtime; its file size tells you nothing about what ships. Two textures that are both 3 MB as PNG can differ by a factor of eight in the build.

## Desktop and current consoles: the BC family

BC (block compression, also called S3TC or DXT for the older members) is what every desktop GPU and every current console GPU supports. All of it is 4x4 blocks.

| Format | Also called | Bits/pixel | Use for |
| --- | --- | --- | --- |
| BC1 | DXT1 | 4 | Opaque colour. The default for any albedo without alpha. 1-bit alpha available at no cost, with visible fringing. |
| BC2 | DXT3 | 8 | Explicit 4-bit alpha. Effectively obsolete; BC3 is better at the same size. |
| BC3 | DXT5 | 8 | Colour with smooth alpha. Also the historical home of packed two-channel normals. |
| BC4 | ATI1, RGTC1 | 4 | One channel. Roughness, metalness, height, any grayscale mask. |
| BC5 | ATI2, RGTC2, 3Dc | 8 | Two channels. The correct format for tangent-space normal maps: store X and Y, reconstruct Z in the shader. |
| BC6H | BPTC float | 8 | HDR colour, signed or unsigned. Cubemaps, lightmaps, skies. |
| BC7 | BPTC | 8 | High-quality colour with or without alpha. The default when quality matters and the size is affordable. |

The practical rule for desktop: BC1 for opaque colour, BC7 for colour that shows compression artefacts or needs alpha, BC5 for normals, BC4 for single-channel masks, BC6H for anything HDR. BC7 encoding is slow, which is an import-time cost, not a runtime one.

Encoding quality varies more than people expect between encoders. A rate-distortion-optimised BC encoder produces output that compresses substantially better in the package archive on top of the fixed GPU size, which is worth knowing when the download rather than the memory is the binding constraint.

## Mobile: ASTC and ETC2

**ASTC** is the modern answer on both Android and iOS. It is supported by every Vulkan-capable Android device and by Apple hardware from the A8 onward, which covers everything a game released now would target. Its distinguishing feature is a selectable block size, which makes the quality-to-size trade continuous rather than a choice between two formats:

| Block size | Bits/pixel | Roughly equivalent to |
| --- | --- | --- |
| 4x4 | 8.00 | BC7 quality |
| 5x5 | 5.12 | — |
| 6x6 | 3.56 | Between BC1 and BC7 |
| 8x8 | 2.00 | Below BC1, still usable for large surfaces |
| 12x12 | 0.89 | Backgrounds and detail maps only |

ASTC handles one to four channels in the same format, so there is no separate normal-map or single-channel variant to pick — the encoder is told what the channels mean, not which format to use. A reasonable default set is 6x6 for albedo, 5x5 or 4x4 for normals and anything the player inspects closely, and 8x8 for large distant surfaces.

**ETC2 and EAC** are the fallback, and they are mandatory in OpenGL ES 3.0, so they are the floor on any device that lacks ASTC. ETC2 RGB8 is 4 bits per pixel, ETC2 RGBA8 (colour plus EAC alpha) is 8, EAC R11 and RG11 give one and two channels at 4 and 8. ETC2 has no HDR member, and its normal-map quality is noticeably worse than BC5 or ASTC. **ETC1** is the OpenGL ES 2.0-era format: 4 bits per pixel, RGB only, no alpha at all, which is why projects targeting it historically shipped a second texture for the alpha channel. Neither is worth targeting unless a device floor forces it.

**PVRTC** is PowerVR's format and appears only in older iOS work. It is 4 and 2 bits per pixel, it requires square power-of-two textures, and Apple's guidance has been ASTC for years. Treat a project still set to PVRTC as a finding.

Android's practical complication is that the App Bundle format supports texture-compression targeting, so a single upload can carry an ASTC set and an ETC2 set and deliver only the one the device can use. Without it, supporting an ETC2 floor means every device downloads the worse textures.

## Console families

- **PlayStation 5 and Xbox Series X|S** use AMD RDNA GPUs and therefore the full BC family, same as desktop. The differences that matter are elsewhere: both have hardware decompression for the package archive, so the choice of BC encoder interacts with how well the archive compresses, and both platforms have strict certification limits on install size.
- **Nintendo Switch and Switch 2** use NVIDIA hardware, which supports ASTC as well as the BC and ETC families. ASTC is the usual choice because the memory budget is much closer to a mobile device than to a console, and the selectable block size is how a title fits.
- Platform-specific formats and the exact toolchain live behind each platform's NDA. When a console is in scope, the platform's own texture tooling documentation overrides anything here.

## Web: transcode at load

The web is the one target where the format cannot be chosen at build time, because the build does not know what GPU will run it. WebGL 2 exposes compressed formats as extensions and the set differs by device: desktop browsers generally offer S3TC and BPTC, mobile browsers offer ETC2 and usually ASTC. WebGPU exposes the same three families as optional features, and a given adapter will have BC or the ETC2 and ASTC pair, not all of them.

Shipping one format therefore means either shipping uncompressed textures or excluding half of the devices. The answer is a supercompressed container that is transcoded on load to whatever the device supports: Basis Universal inside a KTX2 file, which is what the glTF `KHR_texture_basisu` extension carries. It has two modes — ETC1S, which is small in the download and lower quality, and UASTC, which is larger in the download and transcodes to BC7 or ASTC at high quality. Both transcode in milliseconds, and both give the GPU a compressed texture at the end, which plain PNG or JPEG delivery does not.

If the web build is a secondary target and the audience is on desktop, shipping BC and accepting the loss is a defensible shortcut. Say that it is a shortcut.

## Choosing by what the texture contains

Format follows content, not the folder it came from.

| Content | Desktop | Mobile |
| --- | --- | --- |
| Opaque albedo | BC1, or BC7 where banding shows | ASTC 6x6 |
| Albedo with smooth alpha | BC7 | ASTC 6x6 or 5x5 |
| Cutout alpha only | BC1 with 1-bit alpha | ASTC 6x6 |
| Tangent-space normal | BC5 | ASTC 5x5, encoded as a normal map |
| Single-channel mask | BC4 | ASTC with one channel, or EAC R11 |
| Packed masks (roughness, metal, AO) | BC7, or BC1 if the artefacts are invisible | ASTC 6x6 |
| HDR, lightmaps, skies | BC6H | Engine's HDR fallback, often RGBM or RGBA half |
| UI and text | BC7, or uncompressed where crispness matters | ASTC 4x4 or uncompressed |
| Anything the shader compares against a threshold | Uncompressed or BC4 | Uncompressed or EAC R11 |

Three things resist compression and are worth knowing before an artist reports a bug. Sharp colour transitions band under BC1. Normal maps compressed as ordinary colour produce visibly faceted lighting, which is the entire reason BC5 exists. And any texture whose values are read as data rather than as colour — a lookup table, a flow map, a mask with a hard threshold in the shader — should not be block compressed at all, because the error is small in perceptual terms and catastrophic in numeric terms.

Colour space is a separate axis and an equally common defect: albedo and UI are sRGB, normals, masks and data are linear. A normal map flagged sRGB is wrong in a way that looks like a lighting bug.

## The silent fallbacks

Each of these produces a working build with several times the intended texture memory and no warning:

- **A texture left at the default with no platform override.** Some importers default to uncompressed for formats they cannot encode automatically.
- **Dimensions that are not a multiple of the block size.** Block formats work on 4x4 blocks and up. A 1023-pixel texture cannot be tiled by them, so the importer either pads or falls back to uncompressed. Powers of two avoid the question entirely.
- **A format the target does not support.** Requesting BC on an Android build gives an uncompressed texture on any device without desktop-format support, which is nearly all of them.
- **An unnecessary alpha channel.** A fully opaque alpha channel is invisible in the editor and forces the 8-bit-per-pixel variant across the whole texture.
- **A render target or a texture created in code.** These bypass the import settings entirely and are commonly full-rate RGBA, sometimes at screen resolution, sometimes several of them.
- **Read/Write or CPU access enabled.** Keeping a texture readable from the CPU keeps a second full copy in system memory. It is off by default and gets switched on to solve one problem, then left on.

When the measured texture memory is roughly double or quadruple what the format table predicts, one of these is the cause. Check them before changing artwork.

## Setting it per engine

- **Unity.** The Texture Importer's Default tab holds max size, compression quality and whether mipmaps are generated; the per-platform tabs override format and max size per build target, and the per-platform override is the setting that matters — the default alone does not control what mobile ships. `Texture Type` is the shorthand that sets several things at once: Normal Map selects the two-channel path, Sprite disables mipmaps, Single Channel selects the one-channel format.
- **Unreal.** The Texture editor's `Compression Settings` enumerates the choice by intent rather than by format name: Default gives BC1 or BC3 depending on alpha, Normalmap gives BC5, Masks disables sRGB and keeps the channels independent, Grayscale gives a single channel, HDR gives BC6H, and BC7 forces the high-quality path. `Maximum Texture Size` and the texture group set per-platform limits, and the texture groups in the device profiles are where a platform-wide downscale belongs.
- **Godot 4.** The Import dock's `Compress > Mode` chooses between Lossless, Lossy, VRAM Compressed, VRAM Uncompressed and Basis Universal. VRAM Compressed is the one that produces a GPU format, and which family it produces is decided by the project settings `rendering/textures/vram_compression/import_s3tc_bptc` and `import_etc2_astc`, at least one of which must be enabled for the platforms being exported. `Normal Map` mode and `High Quality` (which selects BPTC or ASTC over the cheaper family) are the two other settings that change the format.

## Sizes worth memorising

A 2048 by 2048 texture, without mipmaps:

| Format | Size |
| --- | --- |
| RGBA8 uncompressed | 16 MiB |
| BC7, BC3, ASTC 4x4 | 4 MiB |
| BC1, BC4, ETC2 RGB | 2 MiB |
| ASTC 6x6 | 1.8 MiB |
| ASTC 8x8 | 1 MiB |

Mipmaps add one third. Halving the resolution quarters the size, which is usually a larger and safer win than changing format. A hundred 2048 albedo textures at BC1 with mipmaps is 266 MiB, which is the entire memory budget of a mid-range phone spent on one channel of one material property — which is why the resolution cap and the streaming system matter as much as the format.
