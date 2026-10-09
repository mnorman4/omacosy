# VS Code theme integration plan

Status: all 16 current themes are generated and live switching is
implemented under `integrations/vscode/`. Installer/uninstaller
integration remains proposed.

Version 0.1.0 was packaged and installed locally on 2026-09-30. Every
theme was exercised through `theme-set`; Default and Silicon Labs
profile windows followed every transition, including both light themes
and all three legacy ANSI palettes.

## Goal

Make the selected Omacosy theme available as a coherent VS Code color
theme and apply it to every running VS Code window when `theme-set`
changes `~/.config/omarchy/current/theme`.

The integration should also bring newly opened windows into sync, work
with VS Code profiles, avoid modifying workspace-owned settings, and be
fully removable by `uninstall.sh`.

## Existing pieces

- Every theme has an Omarchy-compatible `colors.toml` containing the
  palette needed to derive an editor theme. Older packs use
  `color0`-`color15`; newer packs such as Hackerman expose named base,
  semantic, and bright colors instead. The general generator must
  normalize both schemas.
- `theme-set` atomically replaces the current-theme symlink. The bar
  and borders already treat that replacement as the theme-change
  notification.
- `omacosy-theme-import` preserves an upstream `vscode.json` when one
  exists. The current Osaka Jade file is metadata naming an external
  Marketplace extension and theme, not a complete VS Code theme.
- VS Code profiles have independent settings and extension state. On
  the author's machine, both the default profile and the Silicon Labs
  profile are in use.

## Proposed design

Ship one local VS Code extension containing:

1. A generated, static color theme for every directory under
   `themes/`.
2. A small local/UI extension host component that watches
   `~/.config/omarchy/current/` and selects the corresponding theme.

Suggested source layout:

```text
integrations/vscode/
├── package.json
├── extension.js
├── generate.py
└── themes/
    ├── tokyo-night-color-theme.json
    ├── catppuccin-color-theme.json
    └── ...
```

Generated theme JSON should be committed. Installing Omacosy should
not need to download Node packages, contact the VS Code Marketplace,
or generate files in the user's home directory.

### Theme generation

Map palette values directly where their meaning is unambiguous:

| Omacosy value | VS Code use |
| --- | --- |
| `background` | Editor and primary workbench background |
| `foreground` | Editor and primary text |
| `cursor` | Editor and terminal cursor |
| `selection_background` | Editor and terminal selections |
| `selection_foreground` | Selected text where supported |
| `accent` | Focus borders, buttons, badges, links, and active items |
| `color0`-`color15` | Terminal ANSI colors and syntax-color source |
| named semantic/bright colors | New-schema terminal and syntax-color source |

Derive secondary surfaces by blending palette colors rather than
introducing unrelated colors. These include the sidebar, activity bar,
panel, title bar, inactive tabs, hover states, inputs, and borders.

Use the normalized ANSI or named palette for a predictable initial
syntax mapping:

- comments and punctuation: muted neutral (`color8` or a derived mix)
- errors and invalid tokens: red (`color1`/`color9`)
- strings: green (`color2`/`color10`)
- numbers and constants: yellow (`color3`/`color11`)
- functions and properties: blue (`color4`/`color12`)
- keywords and types: magenta (`color5`/`color13`)
- operators, tags, and special tokens: cyan (`color6`/`color14`)

Generate workbench colors, TextMate token colors, semantic token
colors, and terminal colors. A theme may later supply a small override
file for hand-tuning without forking the common mapping logic.

Use `mode = "light"` or `mode = "dark"` when present. For older theme
packs without `mode`, infer it from the background's relative
luminance. Generation should fail on malformed or missing required
colors rather than silently producing a partial theme.

Add automated contrast checks for primary editor text, selections,
inputs, buttons, active tabs, and status-bar text. Contrast failures
should identify the theme and color pair and permit an intentional
per-theme override.

### Live switching

The extension should watch the parent directory
`~/.config/omarchy/current`, not the symlink target. `theme-set` uses
`ln -sfn`, so a watcher attached only to the old target can miss the
replacement.

On activation and after a debounced directory event, each extension
instance should:

1. Resolve the current theme symlink.
2. Take the final path component as the Omacosy theme name.
3. Confirm that the extension contributes that generated theme.
4. Update the active profile's `workbench.colorTheme` to
   `Omacosy: <display name>` if it is not already selected.

Each VS Code window has an extension host, so running windows update
themselves. An activation-time reconciliation covers windows opened
after the theme change and windows that were closed at the time.

Declare the watcher as a UI/local extension so remote SSH, container,
and similar windows observe the Mac's Omacosy state rather than looking
for it on the remote machine. Declare support for untrusted workspaces;
the extension only reads the current-theme link and updates a user
setting.

Do not write `.vscode/settings.json`. If a workspace explicitly
overrides `workbench.colorTheme`, respect that choice and report the
window as locally overridden rather than mutating project files.

Unknown or temporarily missing theme links should leave the current VS
Code theme unchanged. A short debounce/retry handles the interval
while the symlink is being replaced.

## Profiles and installation

The extension must be enabled for all VS Code profiles. VS Code has a
supported **Apply Extension to all Profiles** operation; use that
rather than depending on the private layout of profile directories.

The initial implementation needs to determine whether this operation
can be established by a supported command-line/install mechanism. If
not, installation should:

- install the local extension;
- clearly request the one-time **Apply Extension to all Profiles**
  action; and
- remain safe when only the current profile has enabled it.

Do not directly rewrite every profile's `settings.json`. Besides being
an internal storage dependency, that would require JSONC-preserving
edits and could race VS Code's own settings writer.

Separate VS Code products, Insiders builds, and processes launched
with a custom `--user-data-dir` are separate installations. They are
out of the default scope and require explicit installation if support
is later desired.

## Imported `vscode.json`

Do not require third-party Marketplace themes for normal operation.
The locally generated theme is the deterministic fallback for every
Omacosy palette.

An imported `vscode.json` may eventually be treated as an optional
hand-tuned preference:

- use the named external theme only when the extension is already
  installed and the user opts into external-theme preference; or
- use it as provenance when creating a local override.

The first implementation should ignore it during selection. This
keeps installation offline and gives all themes identical behavior.

## Install and uninstall behavior

`install.sh` should install the packaged local extension after VS Code
availability is detected. VS Code must remain an optional integration:
absence of the `code` CLI must not fail the rest of the Omacosy install.

Before Omacosy first takes control of a profile, preserve that
profile's effective `workbench.colorTheme`. The implementation should
define a supported restoration path before enabling automatic changes.

`uninstall.sh` should remove only the Omacosy-owned extension and
restore the previous theme where it is still safe to do so. As with
other Omacosy cleanup, do not overwrite a theme choice the user made
after installation.

## Implementation phases

### 1. Generator prototype

- Parse every `themes/*/colors.toml`.
- Generate valid light/dark theme JSON with workbench, syntax,
  semantic, and terminal colors.
- Add deterministic-output and contrast tests.
- Visually inspect representative dark, light, muted, and saturated
  palettes.

Representative set: `tokyo-night`, `gruvbox`, `osaka-jade`, `lupine`,
and `white`.

### 2. Local extension

- Contribute all generated themes.
- Add activation-time reconciliation and parent-directory watching.
- Debounce link replacement and handle unknown/missing themes safely.
- Verify local, multi-window, multi-profile, and remote-workspace
  behavior.

### 3. Omacosy lifecycle integration

- Package and install the extension without network access.
- Add the all-profiles setup path.
- Record prior theme state and implement conservative restoration.
- Add uninstall cleanup and user documentation.

### 4. Importer integration

- Run theme generation validation when a theme is imported.
- Document optional per-theme VS Code overrides.
- Decide whether `vscode.json` remains metadata-only or gains a
  formally documented schema.

## Acceptance checks

- Every checked-in `colors.toml` produces a valid contributed theme.
- Light themes use VS Code's light theme type; dark themes use dark.
- Primary contrast checks pass or have a reviewed override.
- `theme-set tokyo-night` updates all eligible open VS Code windows
  without reload or restart.
- `theme-next` repeatedly follows the same behavior without extension
  host errors or settings-write loops.
- Default-profile and Silicon Labs-profile windows update together.
- A new VS Code window starts on the current Omacosy theme.
- A remote-workspace window follows the local Mac theme.
- A workspace-specific theme override is not rewritten.
- A missing or unknown current theme does not disturb VS Code.
- Omacosy installation succeeds when VS Code is absent.
- Uninstall removes Omacosy-owned artifacts and does not erase a newer
  user theme choice.

## Open decisions

1. Whether the first release should require the one-time
   **Apply Extension to all Profiles** UI action or defer VS Code
   integration when it cannot be configured automatically.
2. The exact policy for preserving and restoring prior per-profile
   themes without relying on private VS Code profile files.
3. Whether user-selected workspace theme overrides should be completely
   silent or surfaced through an informational status item/log entry.
4. Whether imported `vscode.json` metadata should remain supported once
   all palettes have deterministic local themes.

## References

- [VS Code color theme guide](https://code.visualstudio.com/api/extension-guides/color-theme)
- [VS Code profiles documentation](https://code.visualstudio.com/docs/configure/profiles)
