# Measurement commands

How to produce each number the skill uses and how to read it. Run measurements on a
release configuration; a debug build's size says nothing about what ships.

## Contents

- iOS: App Thinning size report
- iOS: link map attribution
- Android: bundletool sizes
- Android: inside one APK
- A per-PR gate, in outline

## iOS: App Thinning size report

Export an archive for a non-store distribution method with thinning for all variants. The
store export does not produce the report, because the store does the thinning itself.

```bash
xcodebuild -exportArchive \
  -archivePath build/App.xcarchive \
  -exportPath build/export \
  -exportOptionsPlist ExportOptions.plist
```

```xml
<!-- ExportOptions.plist, the keys that matter here -->
<key>method</key>
<string>release-testing</string>   <!-- "ad-hoc" in older Xcode versions -->
<key>thinning</key>
<string>&lt;thin-for-all-variants&gt;</string>
```

`build/export/App Thinning Size Report.txt` lists each device variant with its compressed
and uncompressed size. Compressed approximates download size and uncompressed approximates
install size. It is an estimate: the store encrypts the executable, which then compresses
less well, so the store's figure for a binary-heavy app is higher. Use the report for
attribution and per-change deltas, and App Store Connect for the number you publish.

## iOS: link map attribution

Set `LD_GENERATE_MAP_FILE = YES` on the app target for a release build. The linker writes
a link map (its path is set by `LD_MAP_FILE_PATH`) with an object-file table and a symbol
table carrying each symbol's size and the index of the file it came from. Summing sizes per
file, then per library, attributes the executable to modules and SDKs.

```python
# linkmap_sizes.py LINKMAP  -> bytes per library, largest first
import collections, re, sys

files, sizes, section = {}, collections.Counter(), None
for line in open(sys.argv[1], errors="replace"):
    if line.startswith("# Object files:"):
        section = "files"
        continue
    if line.startswith("# Sections:") or line.startswith("# Dead Stripped Symbols:"):
        section = None
        continue
    if line.startswith("# Symbols:"):
        section = "symbols"
        continue
    if section == "files":
        m = re.match(r"\[\s*(\d+)\]\s+(.*)", line)
        if m:
            files[int(m.group(1))] = m.group(2).strip()
    elif section == "symbols":
        m = re.match(r"0x[0-9A-Fa-f]+\s+0x([0-9A-Fa-f]+)\s+\[\s*(\d+)\]", line)
        if m:
            path = files.get(int(m.group(2)), "?")
            library = path.split("(")[0].rsplit("/", 1)[-1]
            sizes[library] += int(m.group(1), 16)

for library, size in sizes.most_common(30):
    print(f"{size:>12,}  {library}")
```

Run it with `python3 -I linkmap_sizes.py <link map>`. Resources, asset catalogues and
embedded frameworks are outside the executable; take their sizes from the thinning report
and the `.app` bundle's contents.

## Android: bundletool sizes

`bundletool` is usually run as `java -jar bundletool-all-<version>.jar`; the commands below
assume an alias.

```bash
bundletool build-apks --bundle=app-release.aab --output=app.apks
bundletool get-size total --apks=app.apks
bundletool get-size total --apks=app.apks --dimensions=ABI,SCREEN_DENSITY,LANGUAGE,SDK
bundletool get-device-spec --output=reference-device.json      # from a connected device
bundletool get-size total --apks=app.apks --device-spec=reference-device.json
bundletool extract-apks --apks=app.apks --device-spec=reference-device.json --output-dir=apks/
```

`get-size total` prints minimum and maximum download size in bytes, per dimension when
asked. The spread between them is the per-device variation Play Console shows. The
extracted APKs are what that device would install, and are the input for `apkanalyzer`.

## Android: inside one APK

```bash
apkanalyzer -h apk download-size apks/base-master.apk
apkanalyzer -h apk file-size apks/base-master.apk
apkanalyzer dex packages --defined-only apks/base-master.apk
unzip -lv apks/base-master.apk | sort -k3 -n -r | head -30     # largest entries, compressed
./gradlew :app:dependencies --configuration releaseRuntimeClasspath
```

The dex package listing attributes code size to packages, which maps to libraries; the
dependency tree shows which direct dependency pulled each transitive one in. Android
Studio's APK Analyzer shows the same breakdown interactively and can diff two APKs.

## A per-PR gate, in outline

1. Build the release configuration of the pull request's head and of its merge base, or
   fetch the merge base's stored measurement from the main branch's last build.
2. Measure the same thing both times: `bundletool get-size total` with the reference
   device spec; the thinning report's compressed size for the reference iOS variant.
3. Post the delta and the top component deltas (link map, dex packages, largest files) on
   the pull request.
4. Fail above the agreed threshold unless an override is recorded with a name and reason.
5. On merge to main, store the new measurement as the next baseline.

Keep the reference device and variant fixed; changing them changes the number without any
change to the app.
