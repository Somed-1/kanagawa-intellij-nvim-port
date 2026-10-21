# Development

The plugin contains three UI themes and their three editor schemes, plus one
optional Java annotator. Its plugin ID stays stable across upgrades.

## Sources

`reference/kanagawa.nvim` is a pinned, MIT-licensed snapshot of the upstream Lua
theme implementation. `reference/source.json` records its commit. The three
`reference/neovim-*.json` files contain the palette, semantic roles and resolved
Neovim highlight styles exported from that snapshot.

`scripts/build.py` uses the semantic roles of each variant rather than applying
a color filter to Wave. Wave and Dragon inherit IntelliJ's dark controls;
Lotus inherits light controls. Editor backgrounds, syntax styles, diagnostics,
selection and terminal colors follow the corresponding Neovim export. UI
surfaces use that variant's dimmed background roles.

The generator uses internal Wave role names as aliases for all three variants.
For example, `sumiInk3` in a generated Lotus theme resolves to Lotus's own
editor background, not Wave's background. These aliases keep the control map
shared while all values come from the selected variant.

## Build and validation

Python 3 and IntelliJ IDEA 2026.2+ with its bundled JDK are required. No Gradle
or Python dependencies are needed. Set `INTELLIJ_HOME` to the SDK directory.

```sh
make build
make test
python3 scripts/check_runtime.py --ide "$INTELLIJ_HOME"
```

`make export` additionally requires Neovim and re-exports all three source
variants. Building does not load the user's Neovim configuration.

The tests compare every mapped syntax style, editor feature and all 16 terminal
colors to the source exports. The runtime check uses the installed IDE's theme
parser, parent merge, named colors, UI defaults and editor color/attribute
parsers. The Java extension applies to marked Kanagawa schemes and the named
editable copies IntelliJ makes when custom metadata is dropped. UI and language engines differ, so arbitrary third-party
controls and token categories may require additional mappings.

## Screenshots

The README images are real IntelliJ windows, captured using only
`examples/ThemeDemo.java` in a disposable project and isolated X11 display.
The screenshot helper is development tooling and is excluded from the plugin.

```sh
python3 scripts/capture_screenshots.py --ide "$INTELLIJ_HOME" --xvfb /path/to/Xvfb
```

The isolated instance uses IDEA's free Java functionality. Its configurations,
system caches, logs and helper plugins stay under ignored `build/`.
Screenshots alone are written into `docs/screenshots/`.

## Local installation

For the original Linux development setup, `make install` updates the user plugin
directory, migrates the older Wave-only installation, and selects Wave for the
next launch. Use `scripts/install.py --config ... --plugins ...` for other paths.
Settings and the previous plugin are backed up under ignored `backups/`.

For distribution, use the plugin ZIP and the IDE's Install Plugin from Disk
command as described in the README. The `.icls` files are editor-only exports;
they do not include UI themes or the Java extension.
