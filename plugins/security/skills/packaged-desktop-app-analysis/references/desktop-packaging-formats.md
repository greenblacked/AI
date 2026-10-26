# Desktop packaging formats

Read this once the outer artifact is identified and before extracting, so the right reader is
chosen for the packaging that is actually there. Each section says what the marker is, what
the extraction yields, and what it still cannot prove.

## Electron

An Electron app is a native framework binary plus one ASAR archive of application code.

- macOS: `Example.app/Contents/Frameworks/Electron Framework.framework`, application code at
  `Example.app/Contents/Resources/app.asar`, with `app.asar.unpacked` beside it for native
  modules that cannot live inside the archive.
- Windows and Linux: the application sits under `resources/` next to the executable.

An ASAR is not a zip: it begins with a small binary header that carries a JSON index of every
member, then the concatenated file bytes. `unzip -l` on it fails and that failure is not
evidence of corruption. Extract with an ASAR-aware reader, through REA's
`analyze_javascript_application` or an equivalent, and keep the index: it preserves the
original paths, which the zip reading loses.

The runtime switches live in the Electron binary as a fuse wire, not in the ASAR:

| Fuse | What it decides |
| --- | --- |
| `RunAsNode` | Whether `ELECTRON_RUN_AS_NODE=1` turns the app into a Node process |
| `EnableNodeCliInspectArguments` | Whether `--inspect` and `--inspect-brk` are honoured at all |
| `EnableNodeOptionsEnvironmentVariable` | Whether `NODE_OPTIONS` is read |
| `EnableEmbeddedAsarIntegrityValidation` | Whether the app checks an embedded hash of `app.asar` |
| `OnlyLoadAppFromAsar` | Whether code outside the ASAR can be loaded |
| `GrantFileProtocolExtraPrivileges` | Whether `file://` keeps the privileges it once had |

Read them with `inspect_electron_fuses` through REA before attaching anything. A disabled
`EnableNodeCliInspectArguments` explains an empty target list without a tooling problem, and
an enabled `RunAsNode` is itself a finding about the shipped attack surface.

## Node single executable (SEA)

A Node SEA is the `node` binary with a blob appended; the application is inside that blob, not
in a separate archive. Detect it by the appended blob's marker and the absence of a Node
installation in the package, then treat extraction as best-effort: the blob is a serialized
asset, and what comes out is the bundled code, not the project layout. Confirm the Node
version from the binary's own strings before reconstructing anything, because the blob's
format follows the runtime that built it.

## PyInstaller

A PyInstaller executable is a bootloader with an appended CArchive. One-file builds unpack
themselves into a temporary directory at run time; one-directory builds ship the CArchive as
a separate `.pkg`-like file beside the executable. The CArchive begins with the `MEI` cookie
magic followed by the archive version and offsets.

REA's `inspect_artifact` inventories the CArchive without launching it, and `extract_artifact`
publishes accepted members. Bytecode decompilation is outside that capability: a recovered
`.pyc` is derived bytes whose 16-byte header was reconstructed, and its source is a
decompiler's inference. Say that in the report, and never present it as the vendor's source.

## Bundled JVM and .NET

- A JVM desktop app ships a runtime directory with `libjvm` and jars or modules. Treat each jar
  as a zip and read classes with `javap`; `managed-bytecode` under `reverse-engineering` has
  the reading procedure.
- A .NET single-file bundle is the host executable plus a bundle marker and compressed
  assemblies. Use a managed-artifact reader rather than a native disassembler; the bundle is
  not the IL that matters, and `dotnet-assembly-analysis` reads what comes out.

## Installers and images

| Wrapper | Where the app is | Read with |
| --- | --- | --- |
| DMG | A disk image containing the `.app` | A read-only mount in a VM, or an image reader |
| MSI | A CAB inside the MSI database | An MSI extractor, never `msiexec /i` on the host |
| DEB, RPM | `data.tar.*` or a cpio payload | The package tool's list mode, then extract |
| AppImage | squashfs appended to a runtime | The extractor the image declares, into a scratch directory |
| Snap | squashfs with a `meta/snap.yaml` | The same, after reading the manifest |

Extract, do not install. An installer run on the analysis host can register services, add
certificates and write to the user profile before you have read anything.

## What none of these prove

The packaging tells you what ships. Whether the app requires a valid signature at launch,
what it fetches after startup, and what the server does with its data are separate claims.
Report packaging facts as packaging facts, and leave the rest as unknowns until they are
observed.
