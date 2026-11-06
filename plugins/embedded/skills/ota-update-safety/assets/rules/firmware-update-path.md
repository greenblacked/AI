---
paths:
  - "**/ota/**/*.c"
  - "**/bootloader/**/*.c"
  - "**/*ota*.c"
---

# Firmware update path

- Write flash only to the inactive slot, because the running slot is the only image that boots if the update fails.
- Write the boot-select flag last, as one record with a sequence number and CRC, so a power cut leaves either the old selection or the new one.
- Confirm the new image only after the application health check passes, not at `main()`, so a hang rolls back.
- Raise the anti-rollback counter after confirmation, never before.
- Name the proof in the change: the filled-in power-cut sweep record for this release.
