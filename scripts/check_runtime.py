#!/usr/bin/env python3
"""Validate with the installed IDE's own JDK and platform, without starting it."""
import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--ide", type=Path, default=Path.home() / ".local/share/JetBrains/Toolbox/apps/intellij-idea")
args = parser.parse_args()
ide = args.ide.resolve()
output = ROOT / "build/runtime-check"
output.mkdir(parents=True, exist_ok=True)
classpath = f"{ide}/lib/*:{ide}/plugins/java/lib/*:{ROOT}/dist/kanagawa-neovim-port-1.1.0.jar"
subprocess.run([str(ide / "jbr/bin/javac"), "-cp", classpath, "-d", str(output),
                str(ROOT / "src/test/java/ThemeRuntimeCheck.java")], check=True)
for variant in ("wave", "dragon", "lotus"):
    subprocess.run([str(ide / "jbr/bin/java"), "-Djava.awt.headless=true",
                "--add-opens=java.desktop/sun.font=ALL-UNNAMED",
                "--add-opens=java.desktop/sun.awt=ALL-UNNAMED",
                "-cp", classpath + ":" + str(output), "ThemeRuntimeCheck", str(ROOT), variant], check=True)
