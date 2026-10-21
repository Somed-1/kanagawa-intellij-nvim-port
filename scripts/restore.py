#!/usr/bin/env python3
"""Restore the previous UI/editor selection from a specific installation backup."""
import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("backup", type=Path, help="A directory under this project's backups directory")
args = parser.parse_args()
backup = args.backup.resolve()
if backup.parent != (ROOT / "backups").resolve():
    parser.error("Use a backup directory created by scripts/install.py")
manifest = json.loads((backup / "manifest.json").read_text())
for item in manifest["files"]:
    path = Path(item["path"])
    if item["existed"]:
        shutil.copy2(backup / item["backup"], path)
    elif path.exists():
        path.unlink()
print("Restored the previous theme selection. Restart IntelliJ to apply it.")
print("The plugin remains installed and can be selected again in Appearance.")
