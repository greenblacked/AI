# Durable writes, checksums, backups and the corruption test rig

Read this at step 4 while the write path is being built, and at step 5 when deciding what the loader does with a file it cannot trust. The single idea underneath all of it: a save is several operations, and the player's machine can stop between any two of them.

## Contents

- [The atomic write sequence](#the-atomic-write-sequence)
- [Why each step is there](#why-each-step-is-there)
- [Platform differences](#platform-differences)
- [Checksums](#checksums)
- [The load path, in order](#the-load-path-in-order)
- [Backup rotation](#backup-rotation)
- [Save cadence](#save-cadence)
- [The interruption test rig](#the-interruption-test-rig)

## The atomic write sequence

```python
def write_save(path: Path, payload: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())  # the bytes are durable only after this
    os.replace(tmp, path)  # atomic: a reader sees old or new, never both
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)  # the rename itself is now durable
    finally:
        os.close(directory)
```

Serialise fully before any of this runs. A serialisation exception that happens after the destination has been touched has already cost the player their save.

## Why each step is there

| Step | The failure it prevents |
| --- | --- |
| Serialise into memory first | A partially serialised object graph is written over a good save, and the exception arrives after the damage |
| Temporary file in the same directory | A rename across filesystems is a copy and a delete, which is not atomic |
| `flush` then `fsync` | The rename is recorded before the data, and the power loss leaves a correctly named file of zero or stale length |
| `os.replace` / `rename` | Truncate-then-write leaves a file that is half old and half new and parses part of the way through |
| `fsync` the directory | The rename is in the page cache and does not survive; the save reverts to the previous one with no error anywhere |

The fourth row is the common corruption in shipped games. It has no crash attached to it, because there was no crash — the process was simply not running when the machine stopped.

## Platform differences

- **Windows.** `ReplaceFile` or `MoveFileEx` with `MOVEFILE_REPLACE_EXISTING` gives the atomic replace. `FlushFileBuffers` is the fsync. There is no directory fsync; the file flush covers it.
- **macOS.** `fsync` does not force the drive to flush its own cache; `fcntl(F_FULLFSYNC)` does. For save data the difference matters only on a hard power loss, which is exactly the case being defended against.
- **Consoles.** Saves go through a platform save-data API rather than raw file writes. It supplies atomicity, the quota accounting and the mount lifecycle. The platform also requires a visible saving indicator and constrains writes around suspend and sign-out; those are certification requirements and belong to `game-certification`.
- **Browser.** IndexedDB transactions are atomic and are the durable store. `localStorage` is not a save system: it is synchronous, small, and cleared by storage-pressure heuristics without asking.
- **Mobile.** The process is killed by the OS without warning when backgrounded. Save on the pause or background callback, and complete it inside the short window the platform allows rather than starting a long write there.

## Checksums

- **Pick for speed, not strength.** CRC32C, xxHash or BLAKE3 all detect the damage that actually happens: truncation, a zeroed block, a flipped byte, a half-copied sync. A cryptographic hash costs more and detects no additional accidents.
- **Cover the payload and exclude the checksum field**, or the value depends on itself.
- **Store it in the header**, so it can be read and checked before the payload is parsed or decompressed. Checking after decompression turns a damaged file into a library exception in a crash report.
- **Checksums are not tamper-proofing.** The value is recomputed by anyone editing the file. An HMAC whose key ships in the client is recovered soon after release, and the only real defence for anything competitive is a server-authoritative copy.

## The load path, in order

1. Read the header. Wrong magic means this is not a save file; say that, and do not touch the backups.
2. Version above the current one means a save from a newer build; refuse with that message rather than attempting a parse.
3. Checksum mismatch means damage. Move to the fallback chain.
4. Parse. A parse failure is damage the checksum did not catch, which usually means the file was written by a build with a defect; treat it the same way.
5. Migrate, after taking a backup tagged with the source version.
6. Validate semantics: ids that still exist, values inside their ranges, no duplicate unique keys. Clamp and drop rather than crash, and log every clamp with the field name, because a rising rate there is a migration bug reporting itself.

The fallback chain is: most recent backup, then the next, then the last known-good, then refuse. Every step that succeeds tells the player what was recovered and what they lost — a silent fallback to an hour-old save is reported as the game deleting progress.

Never delete a file that failed to load. Rename it, keep it, and name the path in the message. It is the only evidence of the defect and the only route back for that player.

## Backup rotation

- Three previous saves per slot covers the realistic sequence, which is one bad write followed by the player immediately saving again.
- Hold the last save that loaded and validated cleanly outside the rotation, so a run of corrupt writes cannot push the only good file off the end.
- Write the pre-migration backup with the source version in its name, and keep it until the player has saved successfully on the new version.
- Count the whole set against the platform's save quota: slots, autosaves, backups and the pre-migration copy. The quota is per title and small on consoles, and exceeding it fails as a write error in front of the player.

## Save cadence

- Autosave on boundaries the player can name — area change, checkpoint, end of an encounter — plus a bounded timer for long stretches without one.
- Coalesce triggers that fire together. Three systems each requesting a save on the same frame should produce one write.
- Do not save during a frame the player is judging. A save that takes 30 ms during combat reads as a stutter, and `game-performance` owns that measurement.
- Save on quit, on suspend and on background, since those are the moments the process is about to stop existing.

## The interruption test rig

Truncation, in a shell, against a copy:

```bash
size=$(wc -c < save.dat)
for offset in $(seq 1024 1024 "$size"); do
  head -c "$offset" save.dat > "truncated-$offset.dat"
done
```

Then load each one and assert the game refuses cleanly and falls back. Add a zeroed file, a file of the right length filled with random bytes, an empty file, and a file with one byte flipped in the middle of the payload.

For the write path, run the save in a loop in a child process and kill it at a random point each iteration, then assert that the resulting directory state loads as either the old save or the new one — never as anything else. A few hundred iterations finds a missing fsync or a non-atomic replace; reasoning about the code does not.

Run both against every platform's real storage path, not against a desktop temporary directory. The cases this catches are platform behaviour.
