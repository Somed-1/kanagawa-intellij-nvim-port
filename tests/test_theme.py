import importlib.util
import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("builder", ROOT / "scripts/build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class WaveTests(unittest.TestCase):
    variant = "wave"

    def setUp(self):
        builder.configure_variant(self.variant)
        stem = f"Kanagawa{self.variant.title()}Neovim"
        self.theme = json.loads((ROOT / f"src/main/resources/themes/{stem}.theme.json").read_text())
        self.scheme = ET.parse(ROOT / f"src/main/resources/themes/{stem}.xml").getroot()
        self.colors = {e.get("name"): e.get("value").upper() for e in self.scheme.findall("colors/option")}
        self.attrs = {e.get("name"): {o.get("name"): o.get("value") for o in e.findall("value/option")}
                      for e in self.scheme.findall("attributes/option")}
        self.roles = json.loads((ROOT / "reference/editor-mapping.json").read_text())

    def test_syntax_colors_and_styles_match_exported_neovim(self):
        for key, source in self.roles.items():
            with self.subTest(key=key, source=source):
                # Source comparisons are independent of the builder's conversion.
                capture = source
                while not builder.SOURCE["highlights"].get(capture):
                    capture = capture.rsplit(".", 1)[0]
                expected = builder.SOURCE["highlights"][capture]
                actual = self.attrs[key]
                self.assertEqual(actual["FONT_TYPE"], str(bool(expected.get("bold")) + 2 * bool(expected.get("italic"))))
                for src, dst in (("fg", "FOREGROUND"), ("bg", "BACKGROUND")):
                    self.assertEqual(actual.get(dst, "").upper(), expected.get(src, "").lstrip("#").upper())

    def test_editor_features_match_neovim(self):
        h = builder.SOURCE["highlights"]
        pairs = {"CARET_ROW_COLOR": ("CursorLine", "bg"), "GUTTER_BACKGROUND": ("LineNr", "bg"),
                 "LINE_NUMBERS_COLOR": ("LineNr", "fg"), "LINE_NUMBER_ON_CARET_ROW_COLOR": ("CursorLineNr", "fg"),
                 "SELECTION_BACKGROUND": ("Visual", "bg"), "DOCUMENTATION_COLOR": ("NormalFloat", "bg")}
        for key, (group, part) in pairs.items():
            self.assertEqual(self.colors[key], h[group][part].lstrip("#").upper())
        self.assertEqual(self.attrs["SEARCH_RESULT_ATTRIBUTES"]["BACKGROUND"], h["Search"]["bg"].lstrip("#").upper())
        for key, source in (("ERRORS_ATTRIBUTES", "DiagnosticError"), ("WARNING_ATTRIBUTES", "DiagnosticWarn")):
            self.assertEqual(self.attrs[key]["EFFECT_COLOR"], h[source]["fg"].lstrip("#").upper())

    def test_idle_ui_surfaces_are_darker_than_editor(self):
        for key in ("Panel.background", "Tree.background", "List.background", "Table.background",
                    "MainToolbar.background", "StatusBar.background", "EditorTabs.background",
                    "Popup.background", "ToolTip.background", "SearchEverywhere.Header.background"):
            value = builder.PALETTE[self.theme["ui"][key]]
            ui = builder.SOURCE["theme"]["ui"]
            self.assertIn(value, (ui["bg_m3"].upper(), ui["bg_m2"].upper()), key)
            self.assertTrue(all(int(value[i:i+2], 16) < int(ui["bg"][i:i+2], 16) for i in (1, 3, 5)), key)

    def test_ui_uses_only_exact_source_palette_colors(self):
        allowed = set(builder.PALETTE.values())
        for key, value in self.theme["ui"].items():
            if value in builder.PALETTE:
                continue
            matches = re.findall(r"#[0-9A-F]{6}(?:[0-9A-F]{2})?", value)
            self.assertTrue(matches, (key, value))
            for match in matches:
                self.assertIn(match[:7], allowed, (key, value))

    def test_terminal_palette_matches_all_sixteen_original_colors(self):
        names = "BLACK RED GREEN YELLOW BLUE MAGENTA CYAN WHITE BLACK_BRIGHT RED_BRIGHT GREEN_BRIGHT YELLOW_BRIGHT BLUE_BRIGHT MAGENTA_BRIGHT CYAN_BRIGHT WHITE_BRIGHT".split()
        for name, expected in zip(names, builder.SOURCE["theme"]["term"][:16]):
            self.assertEqual(self.attrs["BLOCK_TERMINAL_" + name]["FOREGROUND"].upper(), expected.lstrip("#").upper())

    def test_plugin_resources_and_identity(self):
        with ZipFile(ROOT / f"dist/{builder.SLUG}-{builder.VERSION}.jar") as jar:
            plugin = ET.fromstring(jar.read("META-INF/plugin.xml"))
            providers = plugin.findall("extensions/themeProvider")
            self.assertEqual(len(providers), 3)
            self.assertEqual(len({p.get("id") for p in providers}), 3)
            provider = next(p for p in providers if p.get("id") == builder.THEME_IDS[self.variant])
            self.assertEqual(plugin.findtext("id"), "io.github.somed1.kanagawa.nvim")
            self.assertNotIn("intellij", plugin.findtext("id").lower())
            theme = json.loads(jar.read(provider.get("path").lstrip("/")))
            bundled = next(p for p in plugin.findall("extensions/bundledColorScheme") if p.get("id") == theme["editorScheme"])
            self.assertEqual(bundled.get("id"), theme["editorScheme"])
            scheme = ET.fromstring(jar.read(bundled.get("path")))
            self.assertEqual(scheme.get("name"), theme["name"])
            self.assertIn("META-INF/KANAGAWA-LICENSE", jar.namelist())
            self.assertEqual([name for name in jar.namelist() if name.endswith(".class")],
                             ["local/kanagawa/JavaKanagawaAnnotator.class"])
            self.assertIn("META-INF/kanagawa-java.xml", jar.namelist())

    def test_does_not_override_user_fonts_or_sizes(self):
        self.assertFalse(self.scheme.findall("option"))
        for key in self.theme["ui"]:
            self.assertNotIn("font", key.lower())

    def test_light_and_dark_parent_schemes(self):
        light = self.variant == "lotus"
        self.assertEqual(self.theme["dark"], not light)
        self.assertEqual(self.theme["parentTheme"], "ExperimentalLight" if light else "ExperimentalDark")
        self.assertEqual(self.scheme.get("parent_scheme"), "Default" if light else "Darcula")
        self.assertEqual(self.attrs["TEXT"]["BACKGROUND"], builder.SOURCE["highlights"]["Normal"]["bg"].lstrip("#").upper())

    def test_toolbar_text_contrast(self):
        def luminance(value):
            channels = [int(value[i:i+2], 16) / 255 for i in (1, 3, 5)]
            linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
            return sum(a * b for a, b in zip(linear, (0.2126, 0.7152, 0.0722)))
        bg = luminance(builder.PALETTE[self.theme["ui"]["MainToolbar.background"]])
        for key in ("MainToolbar.foreground", "MainToolbar.Dropdown.foreground"):
            fg = luminance(builder.PALETTE[self.theme["ui"][key]])
            ratio = (max(fg, bg) + 0.05) / (min(fg, bg) + 0.05)
            self.assertGreaterEqual(ratio, 4.5, key)


class DragonTests(WaveTests):
    variant = "dragon"


class LotusTests(WaveTests):
    variant = "lotus"


if __name__ == "__main__":
    unittest.main()
