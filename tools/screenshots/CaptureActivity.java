package local.kanagawa.capture;

import com.intellij.codeInsight.daemon.DaemonCodeAnalyzer;
import com.intellij.ide.ui.LafManager;
import com.intellij.ide.ui.laf.UIThemeLookAndFeelInfo;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.editor.colors.EditorColorsManager;
import com.intellij.openapi.fileEditor.FileEditorManager;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.project.DumbService;
import com.intellij.openapi.projectRoots.JavaSdk;
import com.intellij.openapi.projectRoots.ProjectJdkTable;
import com.intellij.openapi.roots.ProjectRootManager;
import com.intellij.openapi.startup.StartupActivity;
import com.intellij.openapi.vfs.LocalFileSystem;
import com.intellij.openapi.wm.ToolWindowManager;
import com.intellij.openapi.wm.WindowManager;
import com.intellij.util.concurrency.AppExecutorUtil;

import javax.imageio.ImageIO;
import java.awt.Rectangle;
import java.awt.Robot;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.TimeUnit;

/** Development-only helper loaded into an isolated IDE, never the release plugin. */
public final class CaptureActivity implements StartupActivity.DumbAware {
    private static final String[] VARIANTS = {"Wave", "Dragon", "Lotus"};
    private static final String[] IDS = {
        "f56a6b44-8174-45ab-9366-c821d0dd27fa",
        "ae208ac8-5148-47cb-9c05-5173d0e6f823",
        "2b8a9eaf-d48a-42ac-b394-229696ac9a73"};

    @Override
    public void runActivity(Project project) {
        later(() -> {
            try {
                ApplicationManager.getApplication().runWriteAction(() -> {
                    var table = ProjectJdkTable.getInstance();
                    var existing = table.findJdk("Showcase JDK");
                    if (existing != null) table.removeJdk(existing);
                    var sdk = JavaSdk.getInstance().createJdk("Showcase JDK", System.getProperty("java.home"), false);
                    table.addJdk(sdk);
                    ProjectRootManager.getInstance(project).setProjectSdk(sdk);
                });
                var file = LocalFileSystem.getInstance().refreshAndFindFileByPath(project.getBasePath() + "/src/ThemeDemo.java");
                if (file == null) throw new IllegalStateException("Missing sample source");
                FileEditorManager.getInstance(project).openFile(file, true);
                var frame = WindowManager.getInstance().getFrame(project);
                frame.setBounds(0, 0, 1600, 1000);
                frame.toFront();
                var tree = ToolWindowManager.getInstance(project).getToolWindow("Project");
                if (tree != null) tree.show();
                later(() -> DumbService.getInstance(project).runWhenSmart(() -> captureVariant(project, 0)), 8);
            } catch (Throwable error) { fail(error); }
        }, 20);
    }

    private static void later(Runnable action, int seconds) {
        AppExecutorUtil.getAppScheduledExecutorService().schedule(
            () -> ApplicationManager.getApplication().invokeLater(action), seconds, TimeUnit.SECONDS);
    }

    private static void captureVariant(Project project, int index) {
        try {
            var laf = LafManager.getInstance();
            UIThemeLookAndFeelInfo selected = null;
            var themes = laf.getInstalledThemes().iterator();
            while (themes.hasNext()) {
                var theme = themes.next();
                if (IDS[index].equals(theme.getId())) selected = theme;
            }
            if (selected == null) throw new IllegalStateException("Theme not registered: " + VARIANTS[index]);
            laf.setCurrentUIThemeLookAndFeel(selected);
            laf.updateUI();
            var manager = EditorColorsManager.getInstance();
            var source = manager.getScheme("Kanagawa " + VARIANTS[index] + " (Neovim)");
            if (source == null) throw new IllegalStateException("Scheme not registered: " + VARIANTS[index]);
            var scheme = (com.intellij.openapi.editor.colors.EditorColorsScheme) source.clone();
            scheme.setEditorFontName("JetBrains Mono");
            scheme.setEditorFontSize(17);
            manager.setGlobalScheme(scheme);
            var editor = FileEditorManager.getInstance(project).getSelectedTextEditor();
            if (editor != null) {
                editor.getCaretModel().moveToOffset(0);
                editor.getSettings().setLineNumbersShown(true);
                editor.getSettings().setFoldingOutlineShown(false);
            }
            DaemonCodeAnalyzer.getInstance(project).restart();
            new Robot().mouseMove(1, 999);
            later(() -> {
                try {
                    Path output = Path.of(System.getProperty("kanagawa.screenshot.dir"));
                    Files.createDirectories(output);
                    var frame = WindowManager.getInstance().getFrame(project);
                    frame.toFront();
                    var image = new Robot().createScreenCapture(new Rectangle(frame.getLocationOnScreen(), frame.getSize()));
                    ImageIO.write(image, "png", output.resolve(VARIANTS[index].toLowerCase() + ".png").toFile());
                    if (index + 1 < VARIANTS.length) captureVariant(project, index + 1);
                    else {
                        Files.writeString(output.resolve("complete.txt"), "Captured three real IntelliJ windows\n");
                        ApplicationManager.getApplication().exit(true, true, false);
                    }
                } catch (Throwable error) { fail(error); }
            }, 8);
        } catch (Throwable error) { fail(error); }
    }

    private static void fail(Throwable error) {
        error.printStackTrace();
        try {
            Files.writeString(Path.of(System.getProperty("kanagawa.screenshot.dir"), "error.txt"), error.toString());
        } catch (Exception ignored) { }
    }
}
