# Firmware region notes

Working notes for an authorized image. Keep one table per image digest.

## Region table

| Offset | Size | Type (detected) | Entropy | Evidence ID | Notes |
| --- | --- | --- | --- | --- | --- |
| 0x0 | | bootloader / vendor header | | | |
| | | partition table (MBR, GUID partition table, MTD, vendor) | | | |
| | | kernel (uImage, FIT, zImage, Android boot) | | | |
| | | root filesystem (SquashFS, UBI/UBIFS, ext4, JFFS2, EROFS) | | | |
| | | configuration / NVRAM | | | |
| | | signature / certificate / hash tree (vbmeta, dm-verity) | | | |
| | | unidentified / padding | | | |

## Common containers

- **Android images**: sparse images (`simg2img` first), `super.img` dynamic
  partitions, `payload.bin` OTA packages, `vbmeta` describing verified boot.
- **Embedded Linux**: uImage/FIT with SquashFS root; UBI volumes need the
  erase-block and page sizes recorded.
- **Raw NAND dumps**: may include OOB/spare bytes and bad-block markers; strip
  them with the documented geometry before carving.

## Extraction log fields

Region, tool and version, command flags, output directory, output digest,
result (complete / partial / failed), and the error text if any.

## Do not claim without Evidence

- Encryption from entropy alone.
- Boot-time execution from an init reference alone.
- Version from a path or filename alone.
- Image equivalence beyond the regions actually compared.
- That a signature check is absent because you did not find it.
