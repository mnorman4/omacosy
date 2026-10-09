#!/usr/bin/env python3
"""Generate VS Code themes from every Omacosy palette."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
THEMES_DIR = ROOT / "themes"
EXTENSION_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = EXTENSION_DIR / "themes"
PACKAGE = EXTENSION_DIR / "package.json"
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")

BASE_REQUIRED = ("accent", "background", "foreground")
NAMED_REQUIRED = (
    "selection", "muted", "dark_background", "darker_background",
    "lighter_background", "dark_foreground", "light_foreground",
    "bright_foreground", "red", "yellow", "green", "cyan", "blue",
    "magenta", "bright_red", "bright_yellow", "bright_green",
    "bright_cyan", "bright_blue", "bright_magenta",
)
ANSI_REQUIRED = tuple(f"color{i}" for i in range(16)) + (
    "cursor", "selection_foreground", "selection_background",
)


def rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def hex_color(red: int, green: int, blue: int) -> str:
    return f"#{red:02x}{green:02x}{blue:02x}"


def blend(first: str, second: str, second_weight: float) -> str:
    a, b = rgb(first), rgb(second)
    return hex_color(*(round(x * (1 - second_weight) + y * second_weight) for x, y in zip(a, b)))


def relative_luminance(color: str) -> float:
    values = []
    for channel in rgb(color):
        value = channel / 255
        values.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2]


def contrast(first: str, second: str) -> float:
    high, low = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def highest_contrast(background: str, *candidates: str) -> str:
    return max(candidates, key=lambda candidate: contrast(background, candidate))


def display_name(slug: str) -> str:
    return " ".join(word.capitalize() for word in slug.split("-"))


def load_source(path: Path) -> dict[str, str]:
    with path.open("rb") as handle:
        source = tomllib.load(handle)
    missing = [key for key in BASE_REQUIRED if key not in source]
    if missing:
        raise ValueError(f"{path}: missing required colors: {', '.join(missing)}")

    schema = "ansi" if "color0" in source else "named"
    required = ANSI_REQUIRED if schema == "ansi" else NAMED_REQUIRED
    missing = [key for key in required if key not in source]
    if missing:
        raise ValueError(f"{path}: missing {schema} colors: {', '.join(missing)}")

    invalid = [key for key in (*BASE_REQUIRED, *required) if not HEX_COLOR.fullmatch(source[key])]
    if invalid:
        raise ValueError(f"{path}: invalid #RRGGBB colors: {', '.join(invalid)}")
    if "mode" in source and source["mode"] not in ("dark", "light"):
        raise ValueError(f"{path}: mode must be dark or light")
    return source


def normalize(path: Path) -> dict[str, str]:
    source = load_source(path)
    if "color0" not in source:
        return {
            "mode": source.get("mode", "dark"),
            "accent": source["accent"],
            "cursor": source.get("cursor", source["accent"]),
            "selection": source["selection"],
            "selection_foreground": source.get("selection_foreground", source["bright_foreground"]),
            "muted": source["muted"],
            "background": source["background"],
            "dark_background": source["dark_background"],
            "darker_background": source["darker_background"],
            "lighter_background": source["lighter_background"],
            "foreground": source["foreground"],
            "dark_foreground": source["dark_foreground"],
            "light_foreground": source["light_foreground"],
            "bright_foreground": source["bright_foreground"],
            "red": source["red"],
            "yellow": source["yellow"],
            "orange": source.get("orange", source["yellow"]),
            "green": source["green"],
            "cyan": source["cyan"],
            "blue": source["blue"],
            "magenta": source["magenta"],
            "bright_red": source["bright_red"],
            "bright_yellow": source["bright_yellow"],
            "bright_green": source["bright_green"],
            "bright_cyan": source["bright_cyan"],
            "bright_blue": source["bright_blue"],
            "bright_magenta": source["bright_magenta"],
        }

    background = source["background"]
    mode = source.get("mode", "light" if relative_luminance(background) > 0.5 else "dark")
    return {
        "mode": mode,
        "accent": source["accent"],
        "cursor": source["cursor"],
        "selection": source["selection_background"],
        "selection_foreground": source["selection_foreground"],
        "muted": source["color8"],
        "background": background,
        "dark_background": blend(background, "#000000", 0.18 if mode == "dark" else 0.04),
        "darker_background": blend(background, "#000000", 0.32 if mode == "dark" else 0.09),
        "lighter_background": blend(background, source["foreground"], 0.08 if mode == "dark" else 0.03),
        "foreground": source["foreground"],
        "dark_foreground": source["color8"],
        "light_foreground": source["color7"],
        "bright_foreground": source["color15"],
        "red": source["color1"],
        "yellow": source["color3"],
        "orange": source["color3"],
        "green": source["color2"],
        "cyan": source["color6"],
        "blue": source["color4"],
        "magenta": source["color5"],
        "bright_red": source["color9"],
        "bright_yellow": source["color11"],
        "bright_green": source["color10"],
        "bright_cyan": source["color14"],
        "bright_blue": source["color12"],
        "bright_magenta": source["color13"],
    }


def token(scopes: str | list[str], foreground: str, font_style: str | None = None) -> dict:
    settings = {"foreground": foreground}
    if font_style is not None:
        settings["fontStyle"] = font_style
    return {"scope": scopes, "settings": settings}


def build_theme(slug: str, p: dict[str, str]) -> dict:
    button_text = highest_contrast(
        p["accent"], p["darker_background"], p["bright_foreground"], "#000000", "#ffffff"
    )
    selection_text = highest_contrast(
        p["selection"], p["selection_foreground"], p["foreground"], "#000000", "#ffffff"
    )
    comment = highest_contrast(p["background"], p["dark_foreground"], p["muted"])
    colors = {
        "foreground": p["foreground"],
        "descriptionForeground": p["light_foreground"],
        "disabledForeground": p["dark_foreground"] + "A0",
        "focusBorder": p["accent"],
        "contrastBorder": p["muted"],
        "selection.background": p["selection"],
        "textLink.foreground": p["accent"],
        "textLink.activeForeground": p["bright_green"],
        "textBlockQuote.background": p["dark_background"],
        "textBlockQuote.border": p["accent"],
        "textCodeBlock.background": p["darker_background"],
        "button.background": p["accent"],
        "button.foreground": button_text,
        "button.hoverBackground": p["bright_green"],
        "button.secondaryBackground": p["muted"],
        "button.secondaryForeground": highest_contrast(p["muted"], p["foreground"], "#000000", "#ffffff"),
        "button.secondaryHoverBackground": p["lighter_background"],
        "badge.background": p["accent"],
        "badge.foreground": button_text,
        "input.background": p["dark_background"],
        "input.foreground": p["foreground"],
        "input.border": p["muted"],
        "input.placeholderForeground": p["dark_foreground"],
        "dropdown.background": p["dark_background"],
        "dropdown.foreground": p["foreground"],
        "dropdown.border": p["muted"],
        "list.activeSelectionBackground": p["selection"],
        "list.activeSelectionForeground": selection_text,
        "list.inactiveSelectionBackground": p["selection"] + "A0",
        "list.inactiveSelectionForeground": p["foreground"],
        "list.hoverBackground": p["lighter_background"],
        "list.focusOutline": p["accent"],
        "activityBar.background": p["darker_background"],
        "activityBar.foreground": p["accent"],
        "activityBar.inactiveForeground": p["dark_foreground"],
        "activityBar.border": p["muted"],
        "activityBarBadge.background": p["accent"],
        "activityBarBadge.foreground": button_text,
        "sideBar.background": p["dark_background"],
        "sideBar.foreground": p["light_foreground"],
        "sideBar.border": p["muted"],
        "sideBarTitle.foreground": p["bright_foreground"],
        "sideBarSectionHeader.background": p["lighter_background"],
        "sideBarSectionHeader.foreground": p["accent"],
        "editorGroupHeader.tabsBackground": p["darker_background"],
        "editorGroup.border": p["muted"],
        "tab.activeBackground": p["background"],
        "tab.activeForeground": p["bright_foreground"],
        "tab.activeBorderTop": p["accent"],
        "tab.inactiveBackground": p["dark_background"],
        "tab.inactiveForeground": p["dark_foreground"],
        "tab.border": p["muted"],
        "titleBar.activeBackground": p["darker_background"],
        "titleBar.activeForeground": p["bright_foreground"],
        "titleBar.inactiveBackground": p["darker_background"],
        "titleBar.inactiveForeground": p["dark_foreground"],
        "titleBar.border": p["muted"],
        "statusBar.background": p["darker_background"],
        "statusBar.foreground": p["light_foreground"],
        "statusBar.border": p["muted"],
        "statusBar.debuggingBackground": p["muted"],
        "statusBar.noFolderBackground": p["darker_background"],
        "panel.background": p["dark_background"],
        "panel.border": p["muted"],
        "panelTitle.activeForeground": p["accent"],
        "panelTitle.inactiveForeground": p["dark_foreground"],
        "panelTitle.activeBorder": p["accent"],
        "editor.background": p["background"],
        "editor.foreground": p["foreground"],
        "editorCursor.foreground": p["cursor"],
        "editor.selectionBackground": p["selection"],
        "editor.selectionForeground": selection_text,
        "editor.inactiveSelectionBackground": p["selection"] + "80",
        "editor.selectionHighlightBackground": p["muted"] + "70",
        "editor.wordHighlightBackground": p["blue"] + "35",
        "editor.wordHighlightStrongBackground": p["cyan"] + "35",
        "editor.lineHighlightBackground": p["lighter_background"] + "80",
        "editorLineNumber.foreground": p["dark_foreground"],
        "editorLineNumber.activeForeground": p["accent"],
        "editorWhitespace.foreground": p["muted"],
        "editorIndentGuide.background1": p["muted"] + "70",
        "editorIndentGuide.activeBackground1": p["accent"] + "A0",
        "editorBracketMatch.background": p["selection"],
        "editorBracketMatch.border": p["accent"],
        "editor.findMatchBackground": p["accent"] + "45",
        "editor.findMatchBorder": p["accent"],
        "editor.findMatchHighlightBackground": p["cyan"] + "30",
        "editorGutter.background": p["background"],
        "editorWidget.background": p["dark_background"],
        "editorWidget.foreground": p["foreground"],
        "editorWidget.border": p["muted"],
        "editorHoverWidget.background": p["dark_background"],
        "editorHoverWidget.foreground": p["foreground"],
        "editorHoverWidget.border": p["muted"],
        "peekView.border": p["accent"],
        "peekViewEditor.background": p["dark_background"],
        "peekViewResult.background": p["darker_background"],
        "peekViewTitle.background": p["lighter_background"],
        "terminal.background": p["background"],
        "terminal.foreground": p["foreground"],
        "terminalCursor.foreground": p["cursor"],
        "terminal.selectionBackground": p["selection"],
        "terminal.ansiBlack": p["darker_background"],
        "terminal.ansiRed": p["red"],
        "terminal.ansiGreen": p["green"],
        "terminal.ansiYellow": p["yellow"],
        "terminal.ansiBlue": p["blue"],
        "terminal.ansiMagenta": p["magenta"],
        "terminal.ansiCyan": p["cyan"],
        "terminal.ansiWhite": p["light_foreground"],
        "terminal.ansiBrightBlack": p["dark_foreground"],
        "terminal.ansiBrightRed": p["bright_red"],
        "terminal.ansiBrightGreen": p["bright_green"],
        "terminal.ansiBrightYellow": p["bright_yellow"],
        "terminal.ansiBrightBlue": p["bright_blue"],
        "terminal.ansiBrightMagenta": p["bright_magenta"],
        "terminal.ansiBrightCyan": p["bright_cyan"],
        "terminal.ansiBrightWhite": p["bright_foreground"],
        "gitDecoration.addedResourceForeground": p["green"],
        "gitDecoration.modifiedResourceForeground": p["cyan"],
        "gitDecoration.deletedResourceForeground": p["red"],
        "gitDecoration.untrackedResourceForeground": p["bright_green"],
        "gitDecoration.ignoredResourceForeground": p["dark_foreground"],
    }

    tokens = [
        token(["comment", "punctuation.definition.comment"], comment, "italic"),
        token(["string", "constant.other.symbol"], p["green"]),
        token(["constant.numeric", "constant.language", "support.constant"], p["bright_yellow"]),
        token(["keyword", "storage", "storage.type"], p["bright_green"], "bold"),
        token(["entity.name.function", "support.function", "variable.function"], p["cyan"]),
        token(["entity.name.type", "entity.name.class", "support.type", "support.class"], p["magenta"]),
        token(["variable", "meta.definition.variable.name"], p["foreground"]),
        token(["variable.parameter", "meta.function-call.arguments"], p["light_foreground"]),
        token(["entity.name.tag", "support.class.component"], p["accent"]),
        token(["entity.other.attribute-name", "support.type.property-name"], p["bright_cyan"]),
        token(["keyword.operator", "punctuation.separator", "punctuation.accessor"], p["blue"]),
        token(["markup.heading", "entity.name.section"], p["accent"], "bold"),
        token("markup.bold", p["bright_foreground"], "bold"),
        token("markup.italic", p["light_foreground"], "italic"),
        token(["markup.inline.raw", "markup.fenced_code.block"], p["bright_cyan"]),
        token(["invalid", "invalid.illegal"], p["bright_red"], "bold underline"),
    ]

    return {
        "$schema": "vscode://schemas/color-theme",
        "name": f"Omacosy: {display_name(slug)}",
        "type": p["mode"],
        "semanticHighlighting": True,
        "colors": colors,
        "tokenColors": tokens,
        "semanticTokenColors": {
            "comment": {"foreground": comment, "italic": True},
            "string": p["green"],
            "number": p["bright_yellow"],
            "keyword": {"foreground": p["bright_green"], "bold": True},
            "function": p["cyan"],
            "method": p["cyan"],
            "type": p["magenta"],
            "class": p["magenta"],
            "property": p["bright_cyan"],
            "variable.readonly": p["bright_yellow"],
            "parameter": p["light_foreground"],
        },
    }


def generated() -> tuple[dict[Path, str], list[dict[str, str]]]:
    files: dict[Path, str] = {}
    contributions = []
    for source_path in sorted(THEMES_DIR.glob("*/colors.toml")):
        slug = source_path.parent.name
        palette = normalize(source_path)
        output = OUTPUT_DIR / f"{slug}-color-theme.json"
        files[output] = json.dumps(build_theme(slug, palette), indent=2) + "\n"
        contributions.append({
            "label": f"Omacosy: {display_name(slug)}",
            "uiTheme": "vs" if palette["mode"] == "light" else "vs-dark",
            "path": f"./themes/{slug}-color-theme.json",
        })
    return files, contributions


def rendered_package(contributions: list[dict[str, str]]) -> str:
    package = json.loads(PACKAGE.read_text())
    package["contributes"]["themes"] = contributions
    return json.dumps(package, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated files are stale")
    args = parser.parse_args()
    files, contributions = generated()
    files[PACKAGE] = rendered_package(contributions)

    expected_outputs = {path.name for path in files if path.parent == OUTPUT_DIR}
    stale = [path for path, rendered in files.items() if not path.exists() or path.read_text() != rendered]
    extra = sorted(path for path in OUTPUT_DIR.glob("*-color-theme.json") if path.name not in expected_outputs)
    if args.check:
        if stale or extra:
            for path in stale:
                print(f"stale: {path}", file=sys.stderr)
            for path in extra:
                print(f"unexpected: {path}", file=sys.stderr)
            return 1
        return 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path, rendered in files.items():
        path.write_text(rendered)
        print(path)
    for path in extra:
        path.unlink()
        print(f"removed {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
