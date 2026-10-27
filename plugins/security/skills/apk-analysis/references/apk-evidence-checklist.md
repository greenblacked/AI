# APK evidence checklist

Run through this before reporting on an authorised APK, AAB or split set.

1. **Target identity** — file names, the SHA-256 of every split, where the files came from,
   and the package name and version code each one declares.
2. **Authorisation** — the owner and the basis, written down: own build, contract, authorised
   sample, owned-device pull.
3. **Signing** — schemes present, signer certificate SHA-256, rotation lineage, and whether it
   matches the expected publisher. Note debug or test keys.
4. **Manifest** — min and target SDK, permissions (dangerous and signature level called out),
   exported components with intent filters, `sharedUserId`, `debuggable`,
   `usesCleartextTraffic`, and the network security config.
5. **Code overview** — dex count, top-level package tree, third-party SDKs identified with the
   evidence behind the identification, native libraries per ABI, obfuscation level.
6. **Answer path** — component, then class, then method, then call, each hop with an Evidence
   ID. Reflection, `DexClassLoader`, JNI and WebView bridges on the path are marked as
   unexamined or examined separately.
7. **Strings** — hosts, URLs and intent actions quoted exactly, each tied to the method that
   references it, or marked "reference only".
8. **Observed, inferred, unknown** — every conclusion labelled.
9. **Out of bounds** — confirm no bypass, patch or re-signed build was produced.
10. **Cleanup** — `close_binary` for any native session opened; samples left in the lab, not
    copied to a daily driver.
