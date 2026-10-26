# APK evidence checklist

Run through before reporting on an authorized APK, AAB, or split set.

1. **Target identity** — file names, SHA-256 of every split, source of the
   files, and the package name/version code each one declares.
2. **Authorization** — owner and basis written down (own build, contract,
   authorized sample, owned-device pull).
3. **Signing** — schemes present, signer certificate SHA-256, rotation lineage,
   and whether it matches the expected publisher. Note debug or test keys.
4. **Manifest** — min/target SDK, permissions (dangerous and signature level
   called out), exported components with intent filters, `sharedUserId`,
   `debuggable`, `usesCleartextTraffic`, network security config.
5. **Code overview** — dex count, top-level package tree, third-party SDKs
   identified with the Evidence behind the identification, native libraries per
   ABI, obfuscation level.
6. **Answer path** — component → class → method → call, each hop with an
   Evidence ID. Reflection, `DexClassLoader`, JNI, or WebView bridges on the
   path are marked as unexamined or examined separately.
7. **Strings** — hosts, URLs, and intent actions quoted exactly, each tied to
   the method that references it, or marked "reference only".
8. **Observed vs inferred vs unknown** — every conclusion labelled.
9. **Out of bounds** — confirm no bypass, patch, or re-signed build was produced.
10. **Cleanup** — `close_binary` for opened native sessions; samples left in the
    lab, not copied to a daily-driver.
