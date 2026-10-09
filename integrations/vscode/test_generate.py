#!/usr/bin/env python3

import json
import unittest

import generate


class ThemeGenerationTests(unittest.TestCase):
    def test_every_palette_generates_one_theme(self):
        files, contributions = generate.generated()
        sources = list(generate.THEMES_DIR.glob("*/colors.toml"))
        self.assertEqual(len(files), len(sources))
        self.assertEqual(len(contributions), len(sources))
        self.assertEqual(len({item["label"] for item in contributions}), len(sources))

    def test_generated_json_has_readable_primary_text(self):
        files, _ = generate.generated()
        for path, rendered in files.items():
            with self.subTest(theme=path.name):
                theme = json.loads(rendered)
                colors = theme["colors"]
                self.assertGreaterEqual(
                    generate.contrast(colors["editor.foreground"], colors["editor.background"]),
                    4.5,
                )
                self.assertGreaterEqual(
                    generate.contrast(colors["button.foreground"], colors["button.background"]),
                    4.5,
                )

    def test_manifest_type_matches_generated_type(self):
        files, contributions = generate.generated()
        by_path = {item["path"].removeprefix("./themes/"): item for item in contributions}
        for path, rendered in files.items():
            with self.subTest(theme=path.name):
                theme = json.loads(rendered)
                expected = "vs" if theme["type"] == "light" else "vs-dark"
                self.assertEqual(by_path[path.name]["uiTheme"], expected)


if __name__ == "__main__":
    unittest.main()
