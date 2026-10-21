#!/usr/bin/env python3
"""Capture real IDE windows in a disposable configuration and X11 display.

Requires a local IntelliJ SDK and Xvfb. Uses IDEA's free Java functionality.
Only the explicit example project is opened. Nothing from your projects is used.
"""
import argparse
import os
import shutil
import subprocess
import time
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--ide", type=Path, default=Path(os.environ.get("INTELLIJ_HOME", Path.home() / ".local/share/JetBrains/Toolbox/apps/intellij-idea")))
parser.add_argument("--xvfb", default=shutil.which("Xvfb"))
args = parser.parse_args()
if not args.xvfb:
    parser.error("Install Xvfb or pass --xvfb /path/to/Xvfb")
ide = args.ide.resolve()
work = ROOT / "build/screenshots"
config, plugins, project = (work / p for p in ("config", "plugins", "Kanagawa Showcase"))
output = ROOT / "docs/screenshots"
for path in (config / "options", plugins, project / "src", project / ".idea", output): path.mkdir(parents=True, exist_ok=True)
for name in ("complete.txt", "error.txt"):
    (output / name).unlink(missing_ok=True)
shutil.copy2(ROOT / "examples/ThemeDemo.java", project / "src/ThemeDemo.java")
(project / ".idea/modules.xml").write_text('<project version="4"><component name="ProjectModuleManager"><modules><module fileurl="file://$PROJECT_DIR$/showcase.iml" filepath="$PROJECT_DIR$/showcase.iml"/></modules></component></project>')
(project / "showcase.iml").write_text('<module type="JAVA_MODULE" version="4"><component name="NewModuleRootManager" inherit-compiler-output="true"><content url="file://$MODULE_DIR$"><sourceFolder url="file://$MODULE_DIR$/src" isTestSource="false"/></content><orderEntry type="inheritedJdk"/><orderEntry type="sourceFolder" forTests="false"/></component></module>')
(project / ".idea/misc.xml").write_text('<project version="4"><component name="ProjectRootManager" version="2" languageLevel="JDK_21" project-jdk-name="Showcase JDK" project-jdk-type="JavaSDK"/></project>')
(config / "options/jdk.table.xml").write_text(f'<application><component name="ProjectJdkTable"><jdk version="2"><name value="Showcase JDK"/><type value="JavaSDK"/><version value="java version 25"/><homePath value="{ide / "jbr"}"/><roots><classPath><root type="composite"><root url="jrt://{ide / "jbr"}!/" type="simple"/></root></classPath><sourcePath><root type="composite"/></sourcePath></roots></jdk></component></application>')
(config / "options/ide.general.xml").write_text('<application><component name="GeneralSettings"><option name="showTipsOnStartup" value="false"/><option name="confirmExit" value="false"/><option name="reopenLastProject" value="false"/></component></application>')
(config / "options/laf.xml").write_text('<application><component name="LafManager"><laf themeId="f56a6b44-8174-45ab-9366-c821d0dd27fa"/></component></application>')
# The screenshot project only needs the free Java functionality.
(config / "disabled_plugins.txt").write_text("com.intellij.modules.ultimate\n")
jar = ROOT / "dist/kanagawa-neovim-port-1.1.0.jar"
theme_dir = plugins / "kanagawa-neovim-port/lib"
theme_dir.mkdir(parents=True, exist_ok=True)
shutil.copy2(jar, theme_dir / jar.name)
classes = work / "classes"
classes.mkdir(exist_ok=True)
sdk = os.pathsep.join([f"{ide}/lib/*", *map(str, (ide / "plugins/java/lib").rglob("*.jar"))])
subprocess.run([str(ide / "jbr/bin/javac"), "--release", "21", "-cp", sdk, "-d", str(classes), str(ROOT / "tools/screenshots/CaptureActivity.java")], check=True)
helper = plugins / "kanagawa-screenshot-helper/lib/helper.jar"
helper.parent.mkdir(parents=True, exist_ok=True)
with ZipFile(helper, "w") as z:
    z.writestr("META-INF/plugin.xml", '<idea-plugin><id>local.kanagawa.screenshot.helper</id><name>Kanagawa Screenshot Helper</name><version>1</version><vendor>Development only</vendor><depends>com.intellij.modules.platform</depends><depends>com.intellij.java</depends><extensions defaultExtensionNs="com.intellij"><postStartupActivity implementation="local.kanagawa.capture.CaptureActivity"/></extensions></idea-plugin>')
    for file in classes.rglob("*.class"): z.write(file, str(file.relative_to(classes)))
properties = work / "idea.properties"
properties.write_text("\n".join(f"idea.{key}.path={path}" for key, path in {"config":config,"system":work/"system","plugins":plugins,"log":work/"log"}.items()) + "\n")
options = work / "idea.vmoptions"
options.write_text((ide / "bin/idea64.vmoptions").read_text() + f'\n-Xmx2048m\n-Dkanagawa.screenshot.dir={output}\n-Didea.trust.all.projects=true\n-Dide.show.tips.on.startup.default.value=false\n-Didea.initially.ask.config=never\n-Didea.suppress.statistics.report=true\n')
env = {**os.environ, "DISPLAY":":98", "WAYLAND_DISPLAY":"", "XDG_SESSION_TYPE":"x11", "IDEA_PROPERTIES":str(properties), "IDEA_VM_OPTIONS":str(options)}
with (work / "display.log").open("w") as display_log, (work / "launcher.log").open("w") as ide_log:
    display = subprocess.Popen([args.xvfb, ":98", "-screen", "0", "1600x1000x24", "-nolisten", "tcp"], stdout=display_log, stderr=subprocess.STDOUT)
    app = None
    try:
        time.sleep(1)
        if display.poll() is not None: raise RuntimeError("Xvfb did not start; see build/screenshots/display.log")
        app = subprocess.Popen([str(ide / "bin/idea"), str(project)], env=env, stdout=ide_log, stderr=subprocess.STDOUT)
        print("Started isolated IntelliJ screenshot instance", flush=True)
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            if (output / "error.txt").exists(): raise RuntimeError((output / "error.txt").read_text())
            if (output / "complete.txt").exists():
                print("Captured Wave, Dragon and Lotus in docs/screenshots/", flush=True)
                (output / "complete.txt").unlink()
                break
            if app.poll() is not None: raise RuntimeError("IDE exited before capture; see build/screenshots/launcher.log")
            time.sleep(1)
        else: raise RuntimeError("Screenshot capture timed out; inspect the isolated display and launcher log")
    finally:
        if app and app.poll() is None: app.terminate()
        display.terminate()
