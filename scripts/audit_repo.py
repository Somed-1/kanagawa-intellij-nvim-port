#!/usr/bin/env python3
"""Check the tracked publication set for local artifacts, secrets and broken links."""
import re
import subprocess
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
files = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
files = [name for name in files if name]
if not files:
    raise SystemExit("No tracked files: stage the intended publication set first")
problems = []
private = re.compile(rb"-----BEGIN (?:OPENSSH|RSA|EC|DSA|ENCRYPTED) PRIVATE KEY-----")
tokens = re.compile(rb"(?:github_pat_[A-Za-z0-9_]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|perm:[A-Za-z0-9_-]{30,})")
for name in files:
    path = ROOT / name
    if path.parts and path.relative_to(ROOT).parts[0] in {"build", "dist", "backups", ".ssh", ".idea"}:
        problems.append(f"Local-only directory is tracked: {name}")
    if path.suffix in {".class", ".jar", ".zip", ".key", ".pem", ".log", ".db", ".pyc"}:
        problems.append(f"Build, credential or local-state artifact is tracked: {name}")
    content = path.read_bytes()
    if private.search(content) or tokens.search(content):
        problems.append(f"Possible credential material: {name}")
    if str(Path.home()).encode() + b"/" in content:
        problems.append(f"Personal absolute path: {name}")
    if path.suffix == ".md":
        for target in re.findall(r"\]\(([^)]+)\)", content.decode()):
            if target.startswith(("https://", "http://", "#")):
                continue
            if not (path.parent / target.split("#", 1)[0]).exists():
                problems.append(f"Broken local link in {name}: {target}")
for jar in (ROOT / "dist").glob("kanagawa-neovim-port-*.jar"):
    with ZipFile(jar) as archive:
        for name in archive.namelist():
            if "screenshot" in name.lower() or name.endswith((".key", ".pem", ".log")):
                problems.append(f"Development/private file in plugin: {name}")
if problems:
    raise SystemExit("\n".join(problems))
print(f"Publication audit passed: {len(files)} tracked files; no local artifacts, credential patterns or broken Markdown links")
