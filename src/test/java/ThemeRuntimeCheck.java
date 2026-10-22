import com.intellij.ide.ui.UITheme;
import com.intellij.ide.ui.UIThemeBean;
import com.intellij.ide.ui.UIThemeBeanKt;
import com.intellij.ide.ui.ColorMapKt;
import com.intellij.openapi.editor.colors.ColorKey;
import com.intellij.openapi.editor.colors.TextAttributesKey;
import com.intellij.openapi.editor.colors.impl.DefaultColorsScheme;
import com.intellij.openapi.editor.colors.impl.EditorColorsSchemeImpl;
import com.intellij.openapi.util.JDOMUtil;
import kotlin.Unit;
import kotlin.jvm.functions.Function2;
import tools.jackson.core.ObjectReadContext;
import tools.jackson.core.json.JsonFactory;

import javax.swing.UIDefaults;
import java.awt.Color;
import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/** Uses the installed IDE's actual parsers and applies its real UIDefaults. */
public class ThemeRuntimeCheck {
    private static final List<String> warnings = new ArrayList<>();
    private static final Function2<String, Throwable, Unit> warn = (message, error) -> {
        warnings.add(message + (error == null ? "" : ": " + error));
        return Unit.INSTANCE;
    };

    private static UIThemeBean read(Path path) throws Exception {
        try (var parser = new JsonFactory().createParser(ObjectReadContext.empty(), Files.readAllBytes(path))) {
            return UIThemeBeanKt.readTheme(parser, warn);
        }
    }

    private static void color(Color actual, String expected, String label) {
        if (actual == null || !String.format("%06X", actual.getRGB() & 0xFFFFFF).equals(expected)) {
            throw new AssertionError(label + ": " + actual + " != #" + expected);
        }
    }

    public static void main(String[] args) throws Exception {
        Path root = Path.of(args[0]);
        String variant = args.length > 1 ? args[1] : "wave";
        String stem = "Kanagawa" + Character.toUpperCase(variant.charAt(0)) + variant.substring(1) + "Neovim";
        String displayName = "Kanagawa " + Character.toUpperCase(variant.charAt(0)) + variant.substring(1) + " (Neovim)";
        var jar = root.resolve("dist/kanagawa-neovim-port-1.1.2.jar");
        try (var loader = new URLClassLoader(new java.net.URL[]{jar.toUri().toURL()}, ThemeRuntimeCheck.class.getClassLoader())) {
            var bean = read(root.resolve("src/main/resources/themes/" + stem + ".theme.json"));
            var parent = read(root.resolve("reference/intellij/expUI_" + (variant.equals("lotus") ? "light" : "dark") + ".theme.json"));
            UIThemeBeanKt.importFromParentTheme(bean, parent);
            ColorMapKt.initializeNamedColors(bean, warn);
            // Icon patcher creation needs a running IDE application; the real
            // UI parser, parent merge and named-color resolver work headlessly.
            var theme = new UITheme("f56a6b44-8174-45ab-9366-c821d0dd27fa",
                    bean, null, null, null, loader);
            UIDefaults defaults = new UIDefaults();
            // Seed some ordinary Swing keys so wildcard substitution is exercised.
            for (String key : List.of("Panel.background", "Label.foreground", "Tree.background", "Tree.selectionBackground")) {
                defaults.put(key, Color.WHITE);
            }
            theme.applyTheme(defaults);
            for (String key : List.of("Panel.background", "Tree.background", "List.background", "Table.background")) {
                color(defaults.getColor(key), String.format("%06X", bean.colorMap.map.get("sumiInk1").getRGB() & 0xFFFFFF), key);
            }
            for (String key : List.of("MainToolbar.background", "StatusBar.background", "EditorTabs.background",
                    "SearchEverywhere.Header.background", "ToolTip.background", "Popup.background")) {
                color(defaults.getColor(key), String.format("%06X", bean.colorMap.map.get("sumiInk0").getRGB() & 0xFFFFFF), key);
            }
            color(defaults.getColor("Editor.background"), String.format("%06X", bean.colorMap.map.get("sumiInk3").getRGB() & 0xFFFFFF), "Editor.background");
            color(defaults.getColor("Label.foreground"), String.format("%06X", bean.colorMap.map.get("fujiWhite").getRGB() & 0xFFFFFF), "Wildcard foreground");
            color(defaults.getColor("MainToolbar.Dropdown.foreground"), String.format("%06X", bean.colorMap.map.get("fujiWhite").getRGB() & 0xFFFFFF), "Toolbar dropdown foreground");
            color(defaults.getColor("Tree.selectionBackground"), String.format("%06X", bean.colorMap.map.get("waveBlue1").getRGB() & 0xFFFFFF), "Tree selection");
            if (!displayName.equals(bean.editorScheme)
                    || loader.getResource("themes/" + stem + ".xml") == null) {
                throw new AssertionError("Editor scheme cannot be loaded from the plugin JAR");
            }
            var scheme = new EditorColorsSchemeImpl(new DefaultColorsScheme());
            scheme.setName("Unrelated theme");
            var xml = JDOMUtil.load(root.resolve("src/main/resources/themes/" + stem + ".xml"));
            // Parse the actual colors/attributes with the same methods readExternal
            // uses. Resolving registered scheme parents needs a running IDE.
            scheme.readColors(xml.getChild("colors"));
            scheme.readAttributes(xml.getChild("attributes"));
            color(scheme.getDefaultBackground(), String.format("%06X", bean.colorMap.map.get("sumiInk3").getRGB() & 0xFFFFFF), "Editor scheme background");
            color(scheme.getDefaultForeground(), String.format("%06X", bean.colorMap.map.get("fujiWhite").getRGB() & 0xFFFFFF), "Editor scheme foreground");
            color(scheme.getColor(ColorKey.createColorKey("LINE_NUMBER_ON_CARET_ROW_COLOR")), String.format("%06X", bean.colorMap.map.get("roninYellow").getRGB() & 0xFFFFFF), "Current line number");
            var keyword = scheme.getAttributes(TextAttributesKey.createTextAttributesKey("DEFAULT_KEYWORD"));
            color(keyword.getForegroundColor(), String.format("%06X", bean.colorMap.map.get("oniViolet").getRGB() & 0xFFFFFF), "Keyword");
            if (keyword.getFontType() != 2) throw new AssertionError("Lost italic keyword style");
            color(scheme.getAttributes(TextAttributesKey.createTextAttributesKey("PARAMETER_ATTRIBUTES")).getForegroundColor(), String.format("%06X", bean.colorMap.map.get("oniViolet2").getRGB() & 0xFFFFFF), "Java parameter");
            color(scheme.getAttributes(TextAttributesKey.createTextAttributesKey("STATIC_FINAL_FIELD_ATTRIBUTES")).getForegroundColor(), String.format("%06X", bean.colorMap.map.get("surimiOrange").getRGB() & 0xFFFFFF), "Java constant");
            if (local.kanagawa.JavaKanagawaAnnotator.usesKanagawa(scheme)) throw new AssertionError("Enabled outside Kanagawa");
            scheme.getMetaProperties().setProperty("kanagawaSourceCommit", "test");
            if (!local.kanagawa.JavaKanagawaAnnotator.usesKanagawa(scheme)) throw new AssertionError("Not enabled for Kanagawa");
            // Editable copies lose custom metadata in a running IDE. Exercise
            // their resulting names here without requiring application services.
            scheme.getMetaProperties().remove("kanagawaSourceCommit");
            scheme.setName(displayName);
            if (!local.kanagawa.JavaKanagawaAnnotator.usesKanagawa(scheme)) throw new AssertionError("Lost highlighting without metadata");
            scheme.setName("_@user_" + displayName);
            if (!local.kanagawa.JavaKanagawaAnnotator.usesKanagawa(scheme)) throw new AssertionError("Lost highlighting in editable copy");
            scheme.setName("Unrelated theme");
            if (local.kanagawa.JavaKanagawaAnnotator.usesKanagawa(scheme)) throw new AssertionError("Enabled for unrelated theme");
            for (String word : List.of("return", "yield", "throw", "catch", "int", "var", "true", "false", "null", "this", "new", "package", "import")) {
                String key = local.kanagawa.JavaKanagawaAnnotator.keyForKeyword(word);
                if (key == null || scheme.getDirectlyDefinedAttributes(TextAttributesKey.createTextAttributesKey(key)) == null) {
                    throw new AssertionError("Missing Java capture: " + word);
                }
            }
            color(scheme.getAttributes(TextAttributesKey.createTextAttributesKey("KANAGAWA_JAVA_RETURN")).getForegroundColor(), String.format("%06X", bean.colorMap.map.get("peachRed").getRGB() & 0xFFFFFF), "Return keyword");
            color(scheme.getAttributes(TextAttributesKey.createTextAttributesKey("KANAGAWA_JAVA_PRIMITIVE")).getForegroundColor(), String.format("%06X", bean.colorMap.map.get("springBlue").getRGB() & 0xFFFFFF), "Primitive type");
            var bool = scheme.getAttributes(TextAttributesKey.createTextAttributesKey("KANAGAWA_JAVA_BOOLEAN"));
            color(bool.getForegroundColor(), String.format("%06X", bean.colorMap.map.get("surimiOrange").getRGB() & 0xFFFFFF), "Boolean");
            if (bool.getFontType() != 1) throw new AssertionError("Boolean must be bold without italics");
            if (!warnings.isEmpty()) throw new AssertionError("Theme parser warnings: " + warnings);
            System.out.println("PASS " + variant + ": IntelliJ UITheme parser, resolved UI defaults, JAR resources and EditorColorsScheme parser");
            System.out.println("Resolved UI defaults: " + defaults.size());
        }
    }
}
