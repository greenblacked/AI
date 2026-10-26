# Firmware image anatomy

Read this after `file` and the first `xxd` read, when the outer container is not obvious.
The table is a shortlist of magics, not an exhaustive catalogue: the authoritative move is
always to read the bytes at an offset and check them against the format they claim.

## Contents

- [Outer containers, by the first bytes](#outer-containers-by-the-first-bytes)
- [Region inventory](#region-inventory)
- [Extraction log](#extraction-log)
- [Entropy is a lead, not a finding](#entropy-is-a-lead-not-a-finding)
- [Reading a filesystem without changing it](#reading-a-filesystem-without-changing-it)
- [Update verification: what to look for](#update-verification-what-to-look-for)
- [What the image cannot prove](#what-the-image-cannot-prove)
- [Safety defaults](#safety-defaults)

## Outer containers, by the first bytes

| Bytes at the offset | Format | What it usually means |
| --- | --- | --- |
| `hsqs` or `sqsh` | squashfs (little or big endian) | A read-only root filesystem, often the whole vendor partition |
| `UBI#` | UBI volume header | Raw NAND with wear levelling; the volumes inside are separate containers |
| `85 19` pairs | JFFS2 node | Older NAND root filesystem, often cleanly extractable |
| `45 3d cd 28` | cramfs | Small read-only image, common on cameras and older routers |
| `d0 0d fe ed` | device tree blob (FIT or DTB) | Boot configuration; a FIT can carry the kernel and initramfs |
| `27 05 19 56` | legacy U-Boot uImage | One boot component, not necessarily the filesystem |
| `HDR0` | TRX (a router firmware container) | A container at a vendor offset with several partitions inside |
| `1f 8b`, `fd 37 7a 58 5a 00`, `42 5a 68`, `28 b5 2f fd` | gzip, xz, bzip2, zstd | One compressed region, possibly the whole image or one member |
| `53 ef` | ext2/3/4 superblock at offset 0x438 | A writable filesystem, unusual in an update but common in a dump |
| `ANDROID!` | Mobile-platform boot image | Kernel plus ramdisk; the extraction is separate from the system image |
| `ustar` at offset 257 | tar | Often the container for a vendor's set of partition images |

Most images are nested: a header, then one or more of these at offsets the header declares.
A region that starts with a plausible magic but whose declared length runs past the file is a
signature collision, not a format; check the boundary against the file size before trusting
it.

## Region inventory

Keep one table per image digest, filled from the scan before anything is extracted. A region
whose type is a guess says so.

| Offset | Size | Type (detected) | Entropy | Evidence ID | Notes |
| --- | --- | --- | --- | --- | --- |
| 0x0 | | bootloader or vendor header | | | |
| | | partition table (MBR, GUID partition table, MTD, vendor) | | | |
| | | kernel (`uImage`, FIT, `zImage`, mobile-platform boot) | | | |
| | | root filesystem (SquashFS, UBI/UBIFS, ext4, JFFS2, EROFS) | | | |
| | | configuration or NVRAM | | | |
| | | signature, certificate or hash tree (`vbmeta`, `dm-verity`) | | | |
| | | unidentified or padding | | | |

Nested containers worth recognising: a mobile-platform image is often sparse and needs `simg2img`
before its partitions appear, with `super.img` holding dynamic partitions, `payload.bin` as
an OTA container and `vbmeta` describing verified boot. A UBI volume needs its erase-block
and page sizes recorded before it can be read. A raw NAND dump may carry OOB or spare bytes
and bad-block markers; strip them with the documented geometry before carving, or the
filesystem offsets will be wrong.

## Extraction log

Record, per region: the region, the tool and its version, the flags, the output directory,
the output digest, the result (complete, partial or failed) and the error text if any. A
"partial" that is written down is a finding; the same gap rounded up to "extracted" is a
wrong answer.

## Entropy is a lead, not a finding

A high-entropy region is compressed or encrypted; it is not evidence of which. `gzip -t` on
a gzip-shaped member answers compression cheaply, and an extractor's failure on a member
that looks compressed is an unknown, not proof of encryption. Do not report "the filesystem
is encrypted" without a format that says so or code that decrypts it.

## Reading a filesystem without changing it

Extract into a scratch directory and treat the result as read-only. When a mount is
unavoidable, use `mount -o loop,ro` inside an isolated VM, and record the mount options in
the notes. A writable mount of a vendor filesystem can rewrite journals and lose the state
that showed what the device shipped with.

## Update verification: what to look for

The question "does this update verify its signature" is answered in the image, not in the
release notes. Read, in this order:

1. The update client or rc script that handles the package — what it invokes, and with which
   arguments.
2. The verifier it calls (a signature check, a hash comparison, a manifest), and the public
   key or hash it compares against, with the path and offset.
3. What happens on failure — abort, warn and continue, or ignore — because a check that
   warns is not enforcement.
4. Whether a bootloader or secure-boot fuse enforces the same thing independently, and
   whether the image shows that state at all.

A signature format present in the package proves nothing about whether it is checked. Say
which of the four you observed, and leave the rest unresolved.

## What the image cannot prove

The image is what ships, not what runs. A device may have the vendor's post-install scripts
rewrite configuration on first boot, a bootloader may reject an unsigned image regardless of
the filesystem's contents, and a service may accept the package only from a signed channel.
Each of those is a separate claim with its own evidence.

Do not claim, without evidence that says so directly:

- that a region is encrypted, when high entropy may be compression;
- that a service runs at boot, from an init or rc reference alone;
- a component's version from a path or filename alone;
- that two images are identical beyond the regions actually compared;
- that a signature check is absent, because none was found.

## Safety defaults

- Keep the original image and its digest; analyse a copy.
- Extract in a scratch directory inside a VM with no credentials and no route to the
  corporate network.
- Never run, chroot into, or emulate extracted binaries as part of the analysis, and never
  flash the image to a live device to "see if it works".
- Do not copy embedded keys or passwords into a report; cite the path and say the material is
  there.
