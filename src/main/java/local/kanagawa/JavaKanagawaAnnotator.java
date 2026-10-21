package local.kanagawa;

import com.intellij.lang.annotation.AnnotationHolder;
import com.intellij.lang.annotation.Annotator;
import com.intellij.lang.annotation.HighlightSeverity;
import com.intellij.openapi.editor.colors.EditorColorsManager;
import com.intellij.openapi.editor.colors.EditorColorsScheme;
import com.intellij.openapi.editor.colors.TextAttributesKey;
import com.intellij.openapi.project.DumbAware;
import com.intellij.psi.JavaTokenType;
import com.intellij.psi.PsiConditionalExpression;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiJavaToken;
import com.intellij.psi.PsiKeyword;
import com.intellij.psi.PsiTypeElement;
import org.jetbrains.annotations.NotNull;

/** Restores Kanagawa captures which IntelliJ's single Java KEYWORD key cannot express. */
public final class JavaKanagawaAnnotator implements Annotator, DumbAware {
    public static String keyForKeyword(String text) {
        return switch (text) {
            case "return", "yield" -> "KANAGAWA_JAVA_RETURN";
            case "throw", "throws", "try", "catch", "finally" -> "KANAGAWA_JAVA_EXCEPTION";
            case "import", "package", "exports", "module", "opens", "provides", "requires", "uses" -> "KANAGAWA_JAVA_IMPORT";
            case "boolean", "byte", "short", "int", "long", "char", "float", "double", "void", "var" -> "KANAGAWA_JAVA_PRIMITIVE";
            case "true", "false" -> "KANAGAWA_JAVA_BOOLEAN";
            case "null" -> "KANAGAWA_JAVA_NULL";
            case "this" -> "KANAGAWA_JAVA_SELF";
            case "super" -> "KANAGAWA_JAVA_SUPER";
            case "new" -> "KANAGAWA_JAVA_KEYWORD_OPERATOR";
            default -> null;
        };
    }

    public static boolean usesKanagawa(EditorColorsScheme scheme) {
        if (scheme.getMetaProperties().getProperty("kanagawaSourceCommit") != null) return true;
        // IntelliJ drops custom metadata when it makes an editable scheme copy.
        String name = scheme.getName();
        if (name == null) return false;
        if (name.startsWith("_@user_")) name = name.substring("_@user_".length());
        return name.equals("Kanagawa Wave (Neovim)") || name.equals("Kanagawa Dragon (Neovim)")
                || name.equals("Kanagawa Lotus (Neovim)");
    }

    @Override
    public void annotate(@NotNull PsiElement element, @NotNull AnnotationHolder holder) {
        if (!(element instanceof PsiJavaToken token)) return;
        String key = null;
        if (element instanceof PsiKeyword || token.getTokenType() == JavaTokenType.TRUE_KEYWORD
                || token.getTokenType() == JavaTokenType.FALSE_KEYWORD || token.getTokenType() == JavaTokenType.NULL_KEYWORD) {
            key = keyForKeyword(token.getText());
        } else if (token.getTokenType() == JavaTokenType.IDENTIFIER
                && element.getParent() instanceof PsiTypeElement && "var".equals(token.getText())) {
            key = "KANAGAWA_JAVA_PRIMITIVE";
        } else if ((token.getTokenType() == JavaTokenType.QUEST || token.getTokenType() == JavaTokenType.COLON)
                && element.getParent() instanceof PsiConditionalExpression) {
            key = "KANAGAWA_JAVA_CONDITIONAL";
        }
        if (key == null) return;
        EditorColorsScheme scheme = EditorColorsManager.getInstance().getGlobalScheme();
        if (!usesKanagawa(scheme)) return;
        var attributes = scheme.getAttributes(TextAttributesKey.createTextAttributesKey(key));
        if (attributes != null) {
            // Boolean bold must not retain the base keyword's italic font style.
            holder.newSilentAnnotation(HighlightSeverity.INFORMATION).range(element)
                    .enforcedTextAttributes(attributes).create();
        }
    }
}
