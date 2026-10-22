#!/usr/bin/env python3
"""Install the built plugin locally and select its UI/editor scheme for next start."""
import argparse
import datetime
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
NAME = "Kanagawa Wave (Neovim)"
THEME_ID = "f56a6b44-8174-45ab-9366-c821d0dd27fa"
PLUGIN_ID = "io.github.somed1.kanagawa.nvim"
LEGACY_PLUGIN_ID = "local.kanagawa.intellij.neovim"
SLUG = "kanagawa-neovim-port"
VERSION = "1.1.2"


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".kanagawa-new")
    temporary.write_bytes(data)
    temporary.replace(path)


def select(path, component_name, tag, attributes):
    root = ET.parse(path).getroot() if path.exists() else ET.Element("application")
    component = next((e for e in root.findall("component") if e.get("name") == component_name), None)
    if component is None:
        component = ET.SubElement(root, "component", name=component_name)
    element = component.find(tag)
    if element is None:
        element = ET.SubElement(component, tag)
    element.attrib.clear()
    element.attrib.update(attributes)
    ET.indent(root, space="  ")
    atomic_write(path, ET.tostring(root, encoding="utf-8") + b"\n")


def install():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path.home() / ".config/JetBrains/IntelliJIdea2026.2")
    parser.add_argument("--plugins", type=Path, default=Path.home() / ".local/share/JetBrains/IntelliJIdea2026.2")
    args = parser.parse_args()
    if not args.config.is_dir() or not args.plugins.is_dir():
        parser.error("The specified IntelliJ configuration and plugin directories must already exist")
    jar = ROOT / f"dist/{SLUG}-{VERSION}.jar"
    with ZipFile(jar) as archive:
        descriptor = ET.fromstring(archive.read("META-INF/plugin.xml"))
        if descriptor.findtext("id") != PLUGIN_ID:
            raise RuntimeError("Unexpected plugin identity")
    backup = ROOT / "backups" / datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup.mkdir(parents=True)
    changed = []
    for name in ("laf.xml", "colors.scheme.xml"):
        path = args.config / "options" / name
        if path.exists():
            shutil.copy2(path, backup / name)
        changed.append({"path": str(path), "backup": name, "existed": path.exists()})
    dest = args.plugins / SLUG
    if dest.exists():
        shutil.copytree(dest, backup / SLUG)
    legacy = args.plugins / "kanagawa-wave-neovim"
    if legacy.exists():
        for previous in (legacy / "lib").glob("*.jar"):
            with ZipFile(previous) as archive:
                if ET.fromstring(archive.read("META-INF/plugin.xml")).findtext("id") not in (PLUGIN_ID, LEGACY_PLUGIN_ID):
                    raise RuntimeError("Unexpected plugin in legacy installation; refusing to replace it")
        shutil.copytree(legacy, backup / legacy.name)
    atomic_write(dest / "lib" / jar.name, jar.read_bytes())
    for previous in (dest / "lib").glob("*.jar"):
        if previous.name != jar.name:
            previous.unlink()
    if legacy.exists():
        shutil.rmtree(legacy)
    select(args.config / "options/laf.xml", "LafManager", "laf", {"themeId": THEME_ID})
    select(args.config / "options/colors.scheme.xml", "EditorColorsManagerImpl", "global_color_scheme", {"name": NAME})
    manifest = {"plugin": str(dest), "files": changed, "themeName": NAME, "themeId": THEME_ID,
                "sha256": hashlib.sha256(jar.read_bytes()).hexdigest()}
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    assert (dest / "lib" / jar.name).read_bytes() == jar.read_bytes()
    print(f"Installed: {dest / 'lib' / jar.name}")
    print(f"Selected for next start: {NAME}")
    print(f"Backup: {backup}")
    print("Restart IntelliJ to load the plugin. If the running IDE rewrites its settings on exit,")
    print("select Kanagawa Wave (Neovim) in Appearance and Editor > Color Scheme after restarting.")


if __name__ == "__main__":
    install()
