# Engines, project layout, netcode, export and publishing

Read this for tier 2 and above before writing project files, and for the netcode section before agreeing to a tier 4 scope at all.

## Contents

- [Tier 1: one HTML file](#tier-1-one-html-file)
- [Tier 2: Phaser via Vite](#tier-2-phaser-via-vite)
- [Tier 3: Godot 4](#tier-3-godot-4)
- [When the user already has an engine](#when-the-user-already-has-an-engine)
- [Tier 4: netcode, by genre](#tier-4-netcode-by-genre)
- [Export and publishing](#export-and-publishing)
- [Asset licensing](#asset-licensing)

## Tier 1: one HTML file

Everything inline: a canvas, a style block, a script block. No build step, no server, playable by double-clicking. Sound comes from a tiny generated-effect function rather than audio files, so the file stays self-contained. Keep it under a thousand lines; past that it is a tier 2 project pretending.

```text
game.html          # canvas, styles, the loop, TUNING block at the top of the script
```

## Tier 2: Phaser via Vite

```bash
npm create vite@latest my-game -- --template vanilla
cd my-game && npm install phaser
```

```text
index.html
src/
  main.js          # Phaser config: fixed physics fps, scale mode FIT, the scene list
  tuning.js        # every feel number, exported as one object
  scenes/
    Boot.js        # loads assets, then starts Title
    Title.js
    Play.js        # the loop; owns the player, enemies, level
    Pause.js       # a scene launched over Play, not a flag inside it
    GameOver.js
  entities/        # Player.js, Enemy.js: extend Phaser.GameObjects with their own update
public/assets/     # sprites, audio, tilemaps, plus LICENSES.md
```

Set `scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH }` so the game keeps its aspect ratio at any window size, and fix the physics step rate in the config rather than letting it follow the display. Kaplay is a lighter alternative for jam-scale games when Phaser's scene system is more than the brief needs.

## Tier 3: Godot 4

```text
project.godot
scenes/
  main.tscn        # the state machine root: title, play, pause, game over
  player.tscn
  levels/level_01.tscn
scripts/
  player.gd
  player_tuning.gd # a Resource subclass with @export fields
resources/
  player_tuning.tres
assets/
  sprites/ audio/ fonts/ LICENSES.md
export_presets.cfg
```

Conventions that keep the project readable in a diff: one script per scene, signals up and calls down (a child emits, a parent connects), and input actions defined in project settings and referenced by name so remapping is a settings-screen feature rather than a search.

Run and export from the command line, which keeps a playtest loop scriptable:

```bash
godot --path . --headless --export-release "Web" build/web/index.html
godot --path . --headless --export-release "Linux" build/linux/game.x86_64
godot --path . scenes/main.tscn        # run a scene directly
```

The web export needs the export template installed once (Editor, Manage Export Templates) and a host that sends the cross-origin isolation headers; itch.io has a checkbox for it, and a static host needs `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp`.

## When the user already has an engine

Use it. Unity and Unreal are not routed to by default because their project files are binary or generated and their web exports are heavy, not because they are worse for the games they are built for. In Unity, keep simulation in `FixedUpdate`, rendering-side smoothing in `Update`, and every tuning number in a `ScriptableObject`. In Unreal, the equivalent is a data asset. Bevy is the choice for a user who wants Rust and an entity-component design from the first line; it has a fixed-timestep schedule built in.

## Tier 4: netcode, by genre

Decide the authority model before the first line of gameplay code, because it is a rewrite afterwards.

| Genre | Model | Why |
| --- | --- | --- |
| Shooter, action, MMO | Authoritative server, client-side prediction, server reconciliation, interpolation of remote entities | Cheating and latency hiding both need the server to own the truth |
| RTS, fighting, deterministic simulation | Lockstep with rollback: every client simulates the same inputs; rollback re-simulates on late input | Bandwidth is inputs only; determinism is the price, and floating point across platforms is where it breaks |
| Turn-based, async, card | Authoritative server, no prediction needed | Latency is invisible; correctness is everything |
| Co-op in a jam | Host-authoritative, or local only | The honest scope for a weekend |

Whatever the model: the server or host never trusts a client's reported position or result, the simulation is deterministic and seeded so a desync can be diagnosed, and the first playable is two clients on one machine before anything crosses a network. A jam entry that asks for real-time networked play should be scoped down to local multiplayer at A1, with the reason given.

## Export and publishing

| Target | Tier 1 | Tier 2 | Tier 3 |
| --- | --- | --- | --- |
| Browser, itch.io | Upload the file, mark it playable in browser | `npm run build`, zip `dist/`, upload | Web export, zip the folder, enable SharedArrayBuffer support in the itch project settings |
| Static host | Copy the file | Deploy `dist/` | Deploy the export folder with the two isolation headers above |
| Desktop | Not applicable | Electron or Tauri wrapping `dist/`, only if asked | Native export per platform |

`butler` is itch.io's command-line uploader and the right tool the moment a game is uploaded twice:

```bash
butler push build/web user-name/game-name:html5 --userversion 0.2.0
```

Add the itch.io API key as a secret rather than on the command line. Keep the version in one place and bump it per push, so a bug report can name a build.

## Asset licensing

Every third-party asset ships with a licence check, before the first upload:

| Licence | Use in a game | Attribution |
| --- | --- | --- |
| CC0 | Anything | None required; still credit the author |
| CC-BY | Anything | Required, in a credits screen or a shipped file |
| CC-BY-SA | Fine for assets; the share-alike applies to derivatives of the asset | Required |
| CC-BY-NC | Not in anything sold or with ads | Required |
| OFL (fonts) | Anything; embedding allowed | Include the licence file |
| Unclear or none | Do not ship it | |

Write `assets/LICENSES.md` listing each asset, its author, source URL and licence, and ship it with the build. Generated placeholder art and effects have no such obligation, which is one more reason the prototype is built with them.
