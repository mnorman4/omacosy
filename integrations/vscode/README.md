# Omacosy Theme for VS Code

This extension contributes a generated color theme for every Omacosy
palette and follows `~/.config/omarchy/current/theme` while VS Code is
running.

The generator normalizes both supported palette formats: legacy
`color0`-`color15` themes and newer named-color themes.

Regenerate the checked-in themes and manifest after changing a palette
or the common mapping:

```sh
python3 integrations/vscode/generate.py
python3 integrations/vscode/generate.py --check
```

The extension deliberately preserves a workspace or workspace-folder
`workbench.colorTheme` override. Diagnostics are available in the
**Omacosy Theme** output channel.
