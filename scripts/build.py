#!/usr/bin/env python3
"""Build the IntelliJ theme offline from pinned reference data and the local SDK."""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "src/main/resources"
SLUG = "kanagawa-neovim-port"
VERSION = "1.1.2"
VARIANTS = ("wave", "dragon", "lotus")
THEME_IDS = {
    "wave": "f56a6b44-8174-45ab-9366-c821d0dd27fa",
    "dragon": "ae208ac8-5148-47cb-9c05-5173d0e6f823",
    "lotus": "2b8a9eaf-d48a-42ac-b394-229696ac9a73",
}


def configure_variant(variant):
    """Use Wave role names internally, with values from each variant's own roles."""
    global VARIANT, NAME, SOURCE, PALETTE
    if variant not in VARIANTS:
        raise ValueError(f"Unknown variant: {variant}")
    VARIANT = variant
    NAME = f"Kanagawa {variant.title()} (Neovim)"
    SOURCE = json.loads((ROOT / f"reference/neovim-{variant}.json").read_text())
    ui, syn = SOURCE["theme"]["ui"], SOURCE["theme"]["syn"]
    diag, diff, vcs = (SOURCE["theme"][key] for key in ("diag", "diff", "vcs"))
    PALETTE = {
        "sumiInk0": ui["bg_m3"], "sumiInk1": ui["bg_m2"], "sumiInk2": ui["bg_m1"],
        "sumiInk3": ui["bg"], "sumiInk4": ui["bg_p1"], "sumiInk5": ui["bg_p2"], "sumiInk6": ui["nontext"],
        "waveBlue1": ui["bg_visual"], "waveBlue2": ui["bg_search"],
        "winterGreen": diff["add"], "winterRed": diff["delete"], "winterBlue": diff["change"], "winterYellow": diff["text"],
        "autumnGreen": vcs["added"], "autumnRed": vcs["removed"], "autumnYellow": vcs["changed"],
        "samuraiRed": diag["error"], "roninYellow": diag["warning"], "waveAqua1": diag["hint"], "dragonBlue": diag["info"],
        "oldWhite": ui["fg_dim"], "fujiWhite": ui["fg"], "fujiGray": syn["comment"],
        "oniViolet": syn["keyword"], "oniViolet2": syn["parameter"], "crystalBlue": syn["fun"],
        "springViolet1": ui["special"], "springViolet2": syn["punct"], "springBlue": syn["special1"],
        "lightBlue": SOURCE["palette"]["lightBlue"] if variant == "wave" else syn["special1"],
        "waveAqua2": syn["type"], "springGreen": syn["string"],
        "boatYellow1": SOURCE["palette"]["boatYellow1"] if variant == "wave" else syn["regex"],
        "boatYellow2": syn["operator"], "carpYellow": syn["identifier"], "sakuraPink": syn["number"],
        "waveRed": syn["preproc"], "peachRed": syn["special3"], "surimiOrange": syn["constant"], "katanaGray": syn["deprecated"],
    }
    PALETTE = {k: v.upper() for k, v in PALETTE.items()}


configure_variant("wave")


def flatten(mapping, prefix=""):
    for key, value in mapping.items():
        key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            yield from flatten(value, key)
        else:
            yield key, value


def color(name):
    return PALETTE.get(name, name).lstrip("#")


def highlight(name):
    """Treesitter falls back from captures such as @function.method to @function."""
    while name:
        result = SOURCE["highlights"].get(name)
        if result:
            return result
        name = name.rsplit(".", 1)[0] if "." in name else ""
    raise ValueError("Unresolved Neovim highlight")


def attributes(name):
    h = highlight(name)
    result = {"FONT_TYPE": str(int(h.get("bold", False)) + 2 * int(h.get("italic", False)))}
    for source, target in (("fg", "FOREGROUND"), ("bg", "BACKGROUND"), ("sp", "EFFECT_COLOR")):
        if source in h:
            result[target] = color(h[source])
    if h.get("undercurl"):
        result["EFFECT_TYPE"] = "4"  # IntelliJ wave underscore
    elif h.get("strikethrough"):
        result["EFFECT_TYPE"] = "3"
    elif h.get("underline"):
        result["EFFECT_TYPE"] = "1"
    return result


def ui_theme():
    light = VARIANT == "lotus"
    baseline = json.loads((ROOT / f"reference/intellij/expUI_{'light' if light else 'dark'}.theme.json").read_text())
    ramps = {
        "Gray": "sumiInk0 sumiInk1 sumiInk2 sumiInk4 sumiInk5 sumiInk6 fujiGray katanaGray oldWhite oldWhite fujiWhite fujiWhite fujiWhite fujiWhite",
        "Blue": "waveBlue1 waveBlue2 waveBlue2 dragonBlue crystalBlue crystalBlue crystalBlue crystalBlue springBlue springBlue springBlue springViolet2 lightBlue",
        "Green": "winterGreen winterGreen winterGreen autumnGreen autumnGreen autumnGreen springGreen springGreen springGreen springGreen springGreen springGreen",
        "Yellow": "winterYellow winterYellow boatYellow1 boatYellow2 boatYellow2 carpYellow carpYellow carpYellow carpYellow carpYellow carpYellow",
        "Red": "winterRed winterRed winterRed autumnRed autumnRed waveRed waveRed peachRed sakuraPink sakuraPink sakuraPink sakuraPink",
        "Orange": "winterYellow winterYellow boatYellow1 boatYellow2 surimiOrange surimiOrange surimiOrange surimiOrange surimiOrange surimiOrange surimiOrange",
        "Purple": "winterBlue winterBlue sumiInk4 springViolet1 oniViolet oniViolet oniViolet oniViolet oniViolet2 oniViolet2 oniViolet2 oniViolet2",
        "Teal": "waveBlue1 waveBlue1 waveBlue2 waveAqua1 waveAqua1 waveAqua1 waveAqua2 waveAqua2 waveAqua2 waveAqua2 lightBlue lightBlue",
    }
    translation = {f"{family}{i}": name for family, ramp in ramps.items()
                   for i, name in enumerate(ramp.split(), 1)}
    if light:
        # JetBrains' light ramps run from dark foregrounds to pale backgrounds.
        for family in ramps:
            keys = sorted((k for k in baseline["colors"] if re.fullmatch(family + r"\d+", k)), key=lambda k: int(k[len(family):]))
            original = [translation[k] for k in keys]
            for key, name in zip(keys, reversed(original)):
                translation[key] = name
        gray = "fujiWhite fujiWhite oldWhite oldWhite fujiGray fujiGray sumiInk6 sumiInk6 sumiInk5 sumiInk4 sumiInk2 sumiInk1 sumiInk1 sumiInk0".split()
        translation.update({f"Gray{i}": name for i, name in enumerate(gray, 1)})
        translation["windowsPopupBorder"] = "sumiInk6"
    original_hex = {v.upper(): PALETTE[translation[k]] for k, v in baseline["colors"].items()}

    def recolor(value):
        if value in translation:
            return translation[value]
        if not isinstance(value, str):
            return value

        def replace(match):
            original = match[0].upper()
            rgb, alpha = original[:7], original[7:]
            if rgb in original_hex:
                return original_hex[rgb] + alpha
            if rgb == "#FFFFFF":
                return PALETTE["fujiWhite"] + alpha
            if rgb == "#000000":
                return PALETTE["sumiInk0"] + alpha
            # Rare platform-specific accent colors have no Neovim component.
            # Quantize them to the exact Wave palette, retaining opacity.
            def distance(candidate):
                return sum((int(rgb[i:i+2], 16) - int(candidate[i:i+2], 16)) ** 2
                           for i in (1, 3, 5))
            return min(PALETTE.values(), key=distance) + alpha

        return re.sub(r"#[0-9a-fA-F]{8}(?![0-9a-fA-F])|#[0-9a-fA-F]{6}(?![0-9a-fA-F])", replace, value)

    # Override every bundled Dark color entry, including less visible dialogs.
    # Keep platform metrics and widget classes inherited from Dark.
    ui = {key: recolor(value) for key, value in flatten(baseline["ui"])
          if isinstance(value, str) and (value in translation or "#" in value)}

    def put(value, *keys):
        for key in keys:
            ui[key] = value

    put("sumiInk1", "*.background", "*.disabledBackground", "*.inactiveBackground",
        "Panel.background", "SidePanel.background", "Tree.background", "List.background",
        "Table.background", "Viewport.background", "ScrollPane.background", "ToolWindow.background",
        "ToolWindow.Header.background", "ToolWindow.Header.inactiveBackground", "DialogWrapper.background",
        "OptionPane.background", "Plugins.background", "Settings.background", "WelcomeScreen.background")
    put("sumiInk0", "MenuBar.background", "Menu.background", "MenuItem.background", "PopupMenu.background",
        "Popup.background", "Popup.Header.activeBackground", "Popup.Header.inactiveBackground",
        "Popup.Advertiser.background", "CompletionPopup.Advertiser.background", "ComplexPopup.Header.background",
        "ToolTip.background", "Balloon.background", "Notification.background", "ParameterInfo.background",
        "SearchEverywhere.background", "SearchEverywhere.Header.background", "SearchEverywhere.SearchField.background",
        "SearchEverywhere.List.background", "SearchEverywhere.List.settingsBackground",
        "SearchEverywhere.Advertiser.background", "SearchEverywhere.SearchField.borderColor",
        "MainToolbar.background", "MainToolbar.inactiveBackground", "MainToolbar.Icon.background", "MainToolbar.Dropdown.background",
        "TitlePane.background", "TitlePane.inactiveBackground", "ToolBar.background", "StatusBar.background",
        "ToolWindow.Stripe.background", "ToolWindow.Button.background", "ToolWindow.HeaderTab.background",
        "EditorTabs.background", "EditorTabs.inactiveMaskColor", "MainWindow.Tab.background",
        "MainWindow.Tab.selectedBackground", "WelcomeScreen.Details.background")
    put("sumiInk2", "TextField.background", "TextArea.background", "TextPane.background",
        "FormattedTextField.background", "PasswordField.background", "ComboBox.background",
        "ComboBox.nonEditableBackground", "ComboBox.ArrowButton.background", "ComboBox.ArrowButton.nonEditableBackground",
        "Spinner.background", "Editor.SearchField.background", "Plugins.SearchField.background")
    put("sumiInk3", "Editor.background", "EditorPane.background", "EditorPane.inactiveBackground",
        "EditorTabs.underlinedTabBackground", "EditorTabs.selectedBackground", "TabbedPane.selectedBackground")
    put("sumiInk1", "EditorTabs.underlinedTabInactiveBackground", "EditorTabs.selectedInactiveBackground",
        "TabbedPane.background", "TabbedPane.contentAreaColor", "Table.stripeColor")
    put("sumiInk4", "*.hoverBackground", "ActionButton.hoverBackground", "ActionButton.pressedBackground",
        "MainToolbar.Icon.hoverBackground", "MainToolbar.Icon.pressedBackground", "MainToolbar.Dropdown.hoverBackground",
        "MainToolbar.Dropdown.pressedBackground", "MainToolbar.Dropdown.transparentHoverBackground",
        "TitlePane.Button.hoverBackground", "EditorTabs.hoverBackground", "EditorTabs.hoverInactiveBackground",
        "ToolWindow.HeaderTab.hoverBackground", "ToolWindow.HeaderTab.hoverInactiveBackground",
        "ToolWindow.Button.hoverBackground", "Plugins.hoverBackground", "List.hoverBackground",
        "Button.startBackground", "Button.endBackground", "TabbedPane.hoverColor")
    put("fujiWhite", "*.foreground", "*.selectionForeground", "*.selectionInactiveForeground",
        "Tree.foreground", "List.foreground", "Table.foreground", "TextField.foreground",
        "EditorTabs.selectedForeground", "MainToolbar.foreground", "MainToolbar.Dropdown.foreground",
        "MainToolbar.Dropdown.hoverForeground", "CompletionPopup.foreground",
        "SearchEverywhere.Tab.selectedForeground", "MenuItem.selectionForeground", "Menu.selectionForeground")
    put("oldWhite", "*.infoForeground", "*.shortcutForeground", "*.acceleratorForeground",
        "EditorTabs.foreground", "StatusBar.Widget.foreground", "StatusBar.Breadcrumbs.foreground",
        "TitlePane.infoForeground", "TitlePane.inactiveInfoForeground", "ToolWindow.Button.foreground",
        "ToolWindow.Button.selectedForeground", "ParameterInfo.foreground", "ToolTip.foreground")
    put("fujiGray", "*.disabledForeground", "*.inactiveForeground", "*.disabledText",
        "Label.disabledForeground", "Popup.Advertiser.foreground", "SearchEverywhere.Advertiser.foreground")
    put("waveBlue1", "*.selectionBackground", "*.selectionInactiveBackground", "*.lightSelectionBackground",
        "Tree.selectionBackground", "List.selectionBackground", "Table.selectionBackground",
        "Tree.selectionInactiveBackground", "List.selectionInactiveBackground", "Table.selectionInactiveBackground",
        "ToolWindow.Button.selectedBackground", "Menu.selectionBackground", "MenuItem.selectionBackground")
    put("waveBlue2", "CompletionPopup.selectionBackground", "SearchEverywhere.Tab.selectedBackground",
        "SearchEverywhere.List.selectionBackground", "TextField.selectionBackground", "TextArea.selectionBackground")
    put("waveBlue1", "CompletionPopup.background")
    put("sumiInk4", "*.borderColor", "*.separatorColor", "Component.borderColor", "Popup.borderColor",
        "Popup.inactiveBorderColor", "Separator.foreground", "Borders.color", "Borders.ContrastBorderColor",
        "ToolWindow.Stripe.separatorColor", "EditorTabs.underTabsBorderColor", "MainToolbar.separatorColor")
    put("sumiInk3", "Button.default.foreground")
    put("crystalBlue", "Button.default.startBackground", "Button.default.endBackground")
    put("crystalBlue", "*.focusColor", "Component.focusColor", "Button.focusedBorderColor",
        "EditorTabs.underlineColor", "DefaultTabs.underlineColor", "TabbedPane.underlineColor",
        "CompletionPopup.matchForeground", "Link.activeForeground", "Link.hoverForeground")
    put("sumiInk6", "EditorTabs.inactiveUnderlineColor", "DefaultTabs.inactiveUnderlineColor",
        "ScrollBar.thumbColor", "ScrollBar.hoverThumbColor")
    put("sumiInk0", "ScrollBar.trackColor", "ScrollBar.background")
    put("roninYellow", "ParameterInfo.currentParameterForeground", "Component.warningFocusColor")
    put("samuraiRed", "Component.errorFocusColor", "*.errorForeground", "SpeedSearch.errorForeground")
    put("springGreen", "Label.successForeground", "ProgressBar.passedColor")
    put("waveAqua2", "ProgressBar.progressColor", "ProgressBar.indeterminateStartColor", "ProgressBar.indeterminateEndColor")
    # Colorful project header gradients must not brighten the surrounding chrome.
    for i in range(1, 10):
        ui[f"RecentProject.Color{i}.MainToolbarGradientStart"] = "sumiInk0"
        ui[f"RecentProject.Color{i}.MainToolbarGradientEnd"] = "sumiInk0"
    for key in list(ui):
        if "Selection" in key or "selection" in key:
            continue
        if key.startswith("Notification.ToolWindow.") and key.endswith("Background"):
            ui[key] = "sumiInk0"
    icon_roles = {
        "Actions.Red": "waveRed", "Actions.Yellow": "carpYellow", "Actions.Green": "springGreen",
        "Actions.Blue": "crystalBlue", "Actions.Grey": "fujiGray", "Actions.GreyInline": "fujiWhite",
        "Objects.Grey": "fujiGray", "Objects.Blue": "crystalBlue", "Objects.Green": "springGreen",
        "Objects.Yellow": "carpYellow", "Objects.YellowDark": "boatYellow2", "Objects.Purple": "oniViolet",
        "Objects.Pink": "sakuraPink", "Objects.Red": "waveRed", "Objects.RedStatus": "samuraiRed",
        "Objects.GreenAndroid": "springGreen", "Objects.BlackText": "fujiWhite"}
    icons = {"ColorPalette": {key: PALETTE[role] for key, role in icon_roles.items()}}
    return {"name": NAME, "dark": not light, "author": "Somed-1; original palette by Tommaso Laurenzi",
            "parentTheme": "ExperimentalLight" if light else "ExperimentalDark", "editorScheme": NAME,
            "colors": dict(sorted({**{key: PALETTE[name] for key, name in translation.items()}, **PALETTE}.items())),
            "ui": dict(sorted(ui.items())), "icons": icons}


def editor_scheme():
    roles = {}

    def role(group, keys):
        for key in keys.split():
            roles[key] = group

    role("Normal", "TEXT DEFAULT_TEXT")
    role("@variable", "DEFAULT_IDENTIFIER DEFAULT_LOCAL_VARIABLE DEFAULT_REASSIGNED_LOCAL_VARIABLE IDENTIFIER LOCAL_VARIABLE_ATTRIBUTES REASSIGNED_LOCAL_VARIABLE_ATTRIBUTES KOTLIN_LOCAL_VARIABLE KOTLIN_MUTABLE_VARIABLE KOTLIN_WRAPPED_INTO_REF PY.LOCAL_VARIABLE JS.LOCAL_VARIABLE")
    role("Comment", "DEFAULT_LINE_COMMENT DEFAULT_BLOCK_COMMENT DEFAULT_DOC_COMMENT LINE_COMMENT JAVA_LINE_COMMENT BLOCK_COMMENT JAVA_BLOCK_COMMENT DOC_COMMENT JAVA_DOC_COMMENT KOTLIN_LINE_COMMENT KOTLIN_BLOCK_COMMENT KOTLIN_DOC_COMMENT PY.LINE_COMMENT PY.DOC_COMMENT CSS.COMMENT YAML_COMMENT XML_COMMENT HTML_COMMENT")
    role("Keyword", "DEFAULT_KEYWORD KEYWORD JAVA_KEYWORD KOTLIN_KEYWORD KOTLIN_KEYWORD_VAL KOTLIN_KEYWORD_VAR PY.KEYWORD JS.KEYWORD CSS.KEYWORD SQL_KEYWORD YAML_KEYWORD")
    role("String", "DEFAULT_STRING STRING JAVA_STRING KOTLIN_STRING PY.STRING PY.UNICODE_STRING JS.STRING CSS.STRING YAML_STRING YAML_SCALAR_STRING YAML_SCALAR_DSTRING XML_ATTRIBUTE_VALUE HTML_ATTRIBUTE_VALUE PROPERTIES.VALUE CUSTOM_STRING_ATTRIBUTES")
    role("Number", "DEFAULT_NUMBER NUMBER JAVA_NUMBER KOTLIN_NUMBER PY.NUMBER JS.NUMBER CSS.NUMBER YAML_NUMBER")
    role("Operator", "DEFAULT_OPERATION_SIGN OPERATION_SIGN JAVA_OPERATION_SIGN KOTLIN_OPERATION_SIGN KOTLIN_AMPERSAND KOTLIN_ARROW KOTLIN_SAFE_ACCESS KOTLIN_QUEST KOTLIN_EXCLEXCL PY.OPERATION_SIGN JS.OPERATION_SIGN CSS.OPERATION_SIGN PROPERTIES.KEY_VALUE_SEPARATOR")
    role("Delimiter", "DEFAULT_BRACES DEFAULT_BRACKETS DEFAULT_PARENTHS DEFAULT_COMMA DEFAULT_SEMICOLON DEFAULT_DOT BRACES BRACKETS PARENTHS PARENTHESES COMMA DOT JAVA_PARENTH JAVA_BRACES JAVA_BRACKETS JAVA_COMMA JAVA_DOT JAVA_SEMICOLON KOTLIN_PARENTHESIS KOTLIN_BRACES KOTLIN_BRACKETS KOTLIN_COMMA KOTLIN_SEMICOLON KOTLIN_COLON KOTLIN_DOUBLE_COLON KOTLIN_DOT KOTLIN_FUNCTION_LITERAL_BRACES_AND_ARROW PY.PARENTHS PY.BRACKETS PY.BRACES PY.COMMA PY.DOT JS.BRACES JS.BRACKETS JS.PARENTHS JS.COMMA JS.DOT JS.SEMICOLON YAML_SIGN XML_TAG HTML_TAG")
    role("@string.escape", "DEFAULT_VALID_STRING_ESCAPE VALID_STRING_ESCAPE JAVA_VALID_STRING_ESCAPE KOTLIN_STRING_ESCAPE PY.VALID_STRING_ESCAPE JS.VALID_STRING_ESCAPE PROPERTIES.VALID_STRING_ESCAPE CUSTOM_VALID_STRING_ESCAPE_ATTRIBUTES")
    role("Error", "DEFAULT_INVALID_STRING_ESCAPE INVALID_STRING_ESCAPE JAVA_INVALID_STRING_ESCAPE KOTLIN_INVALID_STRING_ESCAPE PY.INVALID_STRING_ESCAPE PROPERTIES.INVALID_STRING_ESCAPE")
    role("Type", "DEFAULT_CLASS_NAME DEFAULT_CLASS_REFERENCE DEFAULT_INTERFACE_NAME CLASS_NAME_ATTRIBUTES ANONYMOUS_CLASS_NAME_ATTRIBUTES ABSTRACT_CLASS_NAME_ATTRIBUTES INTERFACE_NAME_ATTRIBUTES ENUM_NAME_ATTRIBUTES RECORD_NAME_ATTRIBUTES TYPE_PARAMETER_NAME_ATTRIBUTES KOTLIN_CLASS KOTLIN_ABSTRACT_CLASS KOTLIN_TRAIT KOTLIN_OBJECT KOTLIN_ENUM KOTLIN_TYPE_ALIAS KOTLIN_TYPE_PARAMETER KOTLIN_DATA_CLASS KOTLIN_DATA_OBJECT PY.CLASS_DEFINITION JS.CLASS JS.INTERFACE JS.TYPE_PARAMETER JS.MODULE_NAME")
    role("@variable.parameter", "DEFAULT_PARAMETER DEFAULT_REASSIGNED_PARAMETER PARAMETER_ATTRIBUTES LAMBDA_PARAMETER_ATTRIBUTES REASSIGNED_PARAMETER_ATTRIBUTES IMPLICIT_ANONYMOUS_CLASS_PARAMETER_ATTRIBUTES KOTLIN_PARAMETER KOTLIN_CLOSURE_DEFAULT_PARAMETER KOTLIN_NAMED_ARGUMENT PY.PARAMETER JS.PARAMETER")
    role("@variable.member", "DEFAULT_INSTANCE_FIELD DEFAULT_STATIC_FIELD INSTANCE_FIELD_ATTRIBUTES INSTANCE_FINAL_FIELD_ATTRIBUTES STATIC_FIELD_ATTRIBUTES STATIC_FIELD_IMPORTED_ATTRIBUTES RECORD_COMPONENT_ATTRIBUTES ANNOTATION_ATTRIBUTE_NAME_ATTRIBUTES KOTLIN_INSTANCE_PROPERTY KOTLIN_PACKAGE_PROPERTY KOTLIN_BACKING_FIELD_VARIABLE KOTLIN_EXTENSION_PROPERTY KOTLIN_SYNTHETIC_EXTENSION_PROPERTY KOTLIN_DYNAMIC_PROPERTY_CALL KOTLIN_ANDROID_EXTENSIONS_PROPERTY_CALL KOTLIN_INSTANCE_PROPERTY_CUSTOM_PROPERTY_DECLARATION KOTLIN_PACKAGE_PROPERTY_CUSTOM_PROPERTY_DECLARATION PY.INSTANCE_FIELD PY.CLASS_VARIABLE JS.INSTANCE_MEMBER_VARIABLE JS.STATIC_MEMBER_VARIABLE JS.GLOBAL_VARIABLE CSS.IDENT CSS.CLASS_NAME CSS.IDENTIFIER PROPERTIES.KEY YAML_SCALAR_KEY JSON.PROPERTY_KEY")
    role("Constant", "DEFAULT_CONSTANT DEFAULT_GLOBAL_VARIABLE STATIC_FINAL_FIELD_ATTRIBUTES STATIC_FINAL_FIELD_IMPORTED_ATTRIBUTES KOTLIN_ENUM_ENTRY KOTLIN_SMART_CONSTANT PY.PREDEFINED_DEFINITION JS.CONSTANT")
    role("Function", "DEFAULT_FUNCTION_CALL DEFAULT_FUNCTION_DECLARATION DEFAULT_INSTANCE_METHOD DEFAULT_STATIC_METHOD METHOD_CALL_ATTRIBUTES METHOD_DECLARATION_ATTRIBUTES STATIC_METHOD_ATTRIBUTES STATIC_METHOD_IMPORTED_ATTRIBUTES STATIC_METHOD_CALL_IMPORTED_ATTRIBUTES ABSTRACT_METHOD_ATTRIBUTES INHERITED_METHOD_ATTRIBUTES KOTLIN_FUNCTION_DECLARATION KOTLIN_FUNCTION_CALL KOTLIN_PACKAGE_FUNCTION_CALL KOTLIN_EXTENSION_FUNCTION_CALL KOTLIN_DYNAMIC_FUNCTION_CALL PY.FUNCTION_DEFINITION PY.METHOD_CALL JS.FUNCTION_DECLARATION JS.FUNCTION_CALL JS.GLOBAL_FUNCTION JS.INSTANCE_MEMBER_FUNCTION JS.STATIC_MEMBER_FUNCTION")
    role("@constructor", "CONSTRUCTOR_CALL_ATTRIBUTES CONSTRUCTOR_DECLARATION_ATTRIBUTES KOTLIN_CONSTRUCTOR")
    role("@variable.builtin", "PY.SELF_PARAMETER JS.THIS_SUPER")
    role("@type.builtin", "DEFAULT_PREDEFINED_SYMBOL PY.BUILTIN_NAME")
    role("PreProc", "DEFAULT_METADATA CSS.IMPORTANT JSP_DIRECTIVE_NAME")
    role("@attribute", "ANNOTATION_NAME_ATTRIBUTES KOTLIN_ANNOTATION KOTLIN_BUILTIN_ANNOTATION PY.DECORATOR PY.DECORATOR_NAME")
    role("@tag", "DEFAULT_TAG HTML_TAG_NAME HTML_CUSTOM_TAG_NAME XML_TAG_NAME XML_PROLOGUE")
    role("@tag.attribute", "DEFAULT_ATTRIBUTE HTML_ATTRIBUTE_NAME XML_ATTRIBUTE_NAME")
    role("Special", "DEFAULT_ENTITY HTML_ENTITY_REFERENCE XML_ENTITY_REFERENCE DEFAULT_DOC_COMMENT_TAG DEFAULT_DOC_MARKUP DOC_COMMENT_TAG DOC_COMMENT_MARKUP JAVA_DOC_TAG JAVA_DOC_MARKUP KDOC_TAG_NAME KDOC_LINK DEFAULT_DOC_COMMENT_TAG_VALUE DOC_COMMENT_TAG_VALUE CSS.URL")
    role("Identifier", "DEFAULT_LABEL KOTLIN_LABEL")
    role("@boolean", "YAML_BOOLEAN JS.BOOLEAN")
    role("@string.regexp", "JS.REGEXP REGEXP.BRACES REGEXP.BRACKETS REGEXP.PARENTHS REGEXP.CHAR_CLASS REGEXP.META REGEXP.QUOTE_CHARACTER REGEXP.ESC_CHARACTER")
    role("Todo", "TODO_DEFAULT_ATTRIBUTES")
    role("MatchParen", "MATCHED_BRACE_ATTRIBUTES")
    role("Normal", "INJECTED_LANGUAGE_FRAGMENT DEFAULT_TEMPLATE_LANGUAGE_COLOR XML_TAG_DATA HTML_TAG_DATA")
    for suffix, capture in {
        "RETURN": "@keyword.return", "EXCEPTION": "@keyword.exception", "IMPORT": "@keyword.import",
        "PRIMITIVE": "@type.builtin", "BOOLEAN": "@boolean", "NULL": "@constant.builtin",
        "SELF": "@variable.builtin", "SUPER": "Function", "KEYWORD_OPERATOR": "@keyword.operator", "CONDITIONAL": "@keyword",
    }.items():
        role(capture, "KANAGAWA_JAVA_" + suffix)

    mapped = {key: attributes(group) for key, group in roles.items()}
    colors = {
        "CARET_COLOR": "oldWhite", "CARET_ROW_COLOR": "sumiInk5", "GUTTER_BACKGROUND": "sumiInk4",
        "LINE_NUMBERS_COLOR": "sumiInk6", "LINE_NUMBER_ON_CARET_ROW_COLOR": "roninYellow",
        "SELECTION_BACKGROUND": "waveBlue1", "SELECTION_BACKGROUND_INACTIVE": "waveBlue1", "SELECTION_FOREGROUND": "fujiWhite",
        "WHITESPACES": "sumiInk6", "TABS": "sumiInk6", "INDENT_GUIDE": "sumiInk4", "VISUAL_INDENT_GUIDE": "sumiInk4",
        "SELECTED_INDENT_GUIDE": "sumiInk6", "MATCHED_BRACES_INDENT_GUIDE_COLOR": "roninYellow",
        "RIGHT_MARGIN_COLOR": "sumiInk4", "SOFT_WRAP_SIGN_COLOR": "sumiInk6", "METHOD_SEPARATORS_COLOR": "sumiInk0",
        "TEARLINE_COLOR": "sumiInk0", "SELECTED_TEARLINE_COLOR": "sumiInk6", "BREADCRUMBS_BORDER_COLOR": "sumiInk0",
        "STICKY_LINES_BACKGROUND": "sumiInk3", "STICKY_LINES_HOVERED_COLOR": "sumiInk4", "STICKY_LINES_BORDER_COLOR": "sumiInk0",
        "DOCUMENTATION_COLOR": "sumiInk0", "DOC_COMMENT_GUIDE": "sumiInk4", "DOC_COMMENT_LINK": "springBlue",
        "LOOKUP_COLOR": "waveBlue1", "INFORMATION_HINT": "sumiInk0", "QUESTION_HINT": "sumiInk0", "ERROR_HINT": "sumiInk0",
        "NOTIFICATION_BACKGROUND": "sumiInk0", "PROMOTION_PANE": "sumiInk0", "PREVIEW_BACKGROUND": "sumiInk0",
        "PREVIEW_BORDER_COLOR": "sumiInk6", "CONSOLE_BACKGROUND_KEY": "sumiInk3", "READONLY_BACKGROUND": "sumiInk3",
        "READONLY_FRAGMENT_BACKGROUND": "sumiInk3", "RECENT_LOCATIONS_SELECTION": "waveBlue1",
        "ADDED_LINES_COLOR": "autumnGreen", "MODIFIED_LINES_COLOR": "autumnYellow", "DELETED_LINES_COLOR": "autumnRed",
        "WHITESPACES_MODIFIED_LINES_COLOR": "autumnYellow", "BORDER_LINES_COLOR": "sumiInk6",
        "IGNORED_ADDED_LINES_BORDER_COLOR": "autumnGreen", "IGNORED_DELETED_LINES_BORDER_COLOR": "autumnRed",
        "IGNORED_MODIFIED_LINES_BORDER_COLOR": "autumnYellow", "DIFF_SEPARATORS_BACKGROUND": "sumiInk0",
        "ANNOTATIONS_COLOR": "fujiGray", "ANNOTATIONS_LAST_COMMIT_COLOR": "oldWhite",
        "TAB_SELECTED": "sumiInk3", "TAB_SELECTED_INACTIVE": "sumiInk1", "TAB_UNDERLINE": "crystalBlue",
        "TAB_UNDERLINE_INACTIVE": "sumiInk6", "MODIFIED_TAB_ICON": "autumnYellow",
        "ScrollBar.thumbColor": "sumiInk6", "ScrollBar.hoverThumbColor": "springViolet1",
        "ScrollBar.Mac.thumbColor": "sumiInk6", "ScrollBar.Mac.hoverThumbColor": "springViolet1",
        "ScrollBar.trackColor": "sumiInk3", "SCROLLBAR_THUMB_COLOR": "sumiInk6",
    }
    for key in ("FILESTATUS_ADDED FILESTATUS_COPIED FILESTATUS_addedOutside").split(): colors[key] = "autumnGreen"
    for key in ("FILESTATUS_MODIFIED FILESTATUS_RENAMED FILESTATUS_NOT_CHANGED_IMMEDIATE FILESTATUS_NOT_CHANGED_RECURSIVE FILESTATUS_modifiedOutside").split(): colors[key] = "autumnYellow"
    for key in ("FILESTATUS_DELETED FILESTATUS_IDEA_FILESTATUS_DELETED_FROM_FILE_SYSTEM FILESTATUS_OBSOLETE").split(): colors[key] = "autumnRed"
    for key in ("FILESTATUS_IDEA_FILESTATUS_MERGED_WITH_BOTH_CONFLICTS FILESTATUS_IDEA_FILESTATUS_MERGED_WITH_CONFLICTS FILESTATUS_IDEA_FILESTATUS_MERGED_WITH_PROPERTY_CONFLICTS FILESTATUS_changelistConflict").split(): colors[key] = "samuraiRed"
    colors.update({"FILESTATUS_MERGED": "oniViolet", "FILESTATUS_UNKNOWN": "dragonBlue", "FILESTATUS_IDEA_FILESTATUS_IGNORED": "katanaGray", "FILESTATUS_HIJACKED": "waveRed", "FILESTATUS_SWITCHED": "springBlue"})
    for i, c in enumerate(("sumiInk0", "sumiInk1", "sumiInk2", "sumiInk3", "sumiInk4"), 1): colors[f"VCS_ANNOTATIONS_COLOR_{i}"] = c

    custom = {
        "ERRORS_ATTRIBUTES": {"EFFECT_COLOR": color("samuraiRed"), "EFFECT_TYPE": "4"},
        "WRONG_REFERENCES_ATTRIBUTES": {"FOREGROUND": color("samuraiRed"), "EFFECT_COLOR": color("samuraiRed"), "EFFECT_TYPE": "4"},
        "WARNING_ATTRIBUTES": {"EFFECT_COLOR": color("roninYellow"), "EFFECT_TYPE": "4"},
        "INFO_ATTRIBUTES": {"EFFECT_COLOR": color("dragonBlue"), "EFFECT_TYPE": "4"},
        "WEAK_WARNING_ATTRIBUTES": {"EFFECT_COLOR": color("waveAqua1"), "EFFECT_TYPE": "4"},
        "TYPO": {"EFFECT_COLOR": color("samuraiRed"), "EFFECT_TYPE": "4"},
        "DEPRECATED_ATTRIBUTES": {"FOREGROUND": color("katanaGray"), "EFFECT_TYPE": "3", "EFFECT_COLOR": color("katanaGray")},
        "MARKED_FOR_REMOVAL_ATTRIBUTES": {"EFFECT_TYPE": "3", "EFFECT_COLOR": color("peachRed")},
        "NOT_USED_ELEMENT_ATTRIBUTES": {"FOREGROUND": color("fujiGray")},
        "BAD_CHARACTER": {"EFFECT_COLOR": color("samuraiRed"), "EFFECT_TYPE": "4"},
        "SEARCH_RESULT_ATTRIBUTES": attributes("Search"), "TEXT_SEARCH_RESULT_ATTRIBUTES": attributes("Search"),
        "WRITE_SEARCH_RESULT_ATTRIBUTES": attributes("Search"), "IDENTIFIER_UNDER_CARET_ATTRIBUTES": {"BACKGROUND": color("winterYellow")},
        "WRITE_IDENTIFIER_UNDER_CARET_ATTRIBUTES": {"BACKGROUND": color("winterYellow"), "EFFECT_COLOR": color("oldWhite"), "EFFECT_TYPE": "1"},
        "FOLDED_TEXT_ATTRIBUTES": attributes("Folded"),
        "EXECUTIONPOINT_ATTRIBUTES": {"BACKGROUND": color("winterRed")}, "BREAKPOINT_ATTRIBUTES": {"BACKGROUND": color("winterRed")},
        "NOT_TOP_FRAME_ATTRIBUTES": {"BACKGROUND": color("winterBlue")},
        "DIFF_INSERTED": {"BACKGROUND": color("winterGreen"), "ERROR_STRIPE_COLOR": color("autumnGreen")},
        "DIFF_DELETED": {"BACKGROUND": color("winterRed"), "ERROR_STRIPE_COLOR": color("autumnRed")},
        "DIFF_MODIFIED": {"BACKGROUND": color("winterBlue"), "ERROR_STRIPE_COLOR": color("autumnYellow")},
        "DIFF_CONFLICT": {"BACKGROUND": color("winterYellow"), "ERROR_STRIPE_COLOR": color("roninYellow")},
    }
    for key in ("INLINE_PARAMETER_HINT INLINE_PARAMETER_HINT_HIGHLIGHTED INLINE_PARAMETER_HINT_CURRENT INLAY_DEFAULT INLAY_TEXT_WITHOUT_BACKGROUND INLINE_SUGGESTION DEBUGGER_INLINED_VALUES").split():
        custom[key] = {"FOREGROUND": color("sumiInk6"), "FONT_TYPE": "0"}
    for key in ("BREADCRUMBS_DEFAULT BREADCRUMBS_HOVERED BREADCRUMBS_CURRENT BREADCRUMBS_INACTIVE").split():
        custom[key] = {"FOREGROUND": color("oldWhite"), "BACKGROUND": color("sumiInk0"), "FONT_TYPE": "0"}
    for key in ("HYPERLINK_ATTRIBUTES FOLLOWED_HYPERLINK_ATTRIBUTES INACTIVE_HYPERLINK_ATTRIBUTES CTRL_CLICKABLE").split():
        custom[key] = attributes("Underlined")
    terminal = SOURCE["theme"]["term"][:16]
    ansi = ("BLACK RED GREEN YELLOW BLUE MAGENTA CYAN GRAY DARKGRAY RED_BRIGHT GREEN_BRIGHT YELLOW_BRIGHT BLUE_BRIGHT MAGENTA_BRIGHT CYAN_BRIGHT WHITE").split()
    block = ("BLACK RED GREEN YELLOW BLUE MAGENTA CYAN WHITE BLACK_BRIGHT RED_BRIGHT GREEN_BRIGHT YELLOW_BRIGHT BLUE_BRIGHT MAGENTA_BRIGHT CYAN_BRIGHT WHITE_BRIGHT").split()
    for names, prefix, suffix in ((ansi, "CONSOLE_", "_OUTPUT"), (block, "BLOCK_TERMINAL_", "")):
        for key, c in zip(names, terminal): custom[prefix + key + suffix] = {"FOREGROUND": color(c), "FONT_TYPE": "0"}
    for key, group in {"CONSOLE_NORMAL_OUTPUT": "Normal", "CONSOLE_USER_INPUT": "Normal", "CONSOLE_OUTPUT": "Normal", "CONSOLE_ERROR_OUTPUT": "DiagnosticError", "CONSOLE_SYSTEM_OUTPUT": "Comment", "LOG_ERROR_OUTPUT": "DiagnosticError", "LOG_WARNING_OUTPUT": "DiagnosticWarn", "LOG_INFO_OUTPUT": "DiagnosticInfo", "LOG_DEBUG_OUTPUT": "Comment", "LOG_VERBOSE_OUTPUT": "Comment"}.items():
        custom[key] = attributes(group)
        custom[key].pop("BACKGROUND", None)
    mapped.update(custom)
    root = ET.Element("scheme", name=NAME, version="142", parent_scheme="Default" if VARIANT == "lotus" else "Darcula")
    meta = ET.SubElement(root, "metaInfo")
    ET.SubElement(meta, "property", name="originalScheme").text = NAME
    ET.SubElement(meta, "property", name="kanagawaSourceCommit").text = json.loads((ROOT / "reference/source.json").read_text())["commit"]
    # Explicitly disable IntelliJ rainbow identifiers so semantic colors remain exact.
    ET.SubElement(meta, "property", name="rainbow Default language").text = "false"
    cs = ET.SubElement(root, "colors")
    for key, value in sorted(colors.items()): ET.SubElement(cs, "option", name=key, value=color(value))
    at = ET.SubElement(root, "attributes")
    for key, values in sorted(mapped.items()):
        value = ET.SubElement(ET.SubElement(at, "option", name=key), "value")
        for name, v in sorted(values.items()): ET.SubElement(value, "option", name=name, value=v)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode") + "\n", roles


def archive(files):
    output = io.BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as z:
        for name, data in sorted(files.items()):
            info = ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data)
    return output.getvalue()


def build():
    themes = RES / "themes"
    themes.mkdir(parents=True, exist_ok=True)
    reports = {}
    for variant in VARIANTS:
        configure_variant(variant)
        theme = ui_theme()
        scheme, roles = editor_scheme()
        stem = f"Kanagawa{variant.title()}Neovim"
        (themes / f"{stem}.theme.json").write_text(json.dumps(theme, indent=2) + "\n")
        (themes / f"{stem}.xml").write_text(scheme)
        reports[variant] = {"uiColorEntries": len(theme["ui"]), "mappedSyntaxAttributes": len(roles),
                            "editorAttributes": len(ET.fromstring(scheme).findall("attributes/option")),
                            "editorColors": len(ET.fromstring(scheme).findall("colors/option"))}
    (ROOT / "reference/editor-mapping.json").write_text(json.dumps(dict(sorted(roles.items())), indent=2) + "\n")
    files = {str(p.relative_to(RES)): p.read_bytes() for p in RES.rglob("*") if p.is_file()}
    ide = Path(os.environ.get("INTELLIJ_HOME", Path.home() / ".local/share/JetBrains/Toolbox/apps/intellij-idea"))
    classes = ROOT / "build/classes"
    if classes.exists():
        shutil.rmtree(classes)
    classes.mkdir(parents=True, exist_ok=True)
    sdk = f"{ide}/lib/*:{ide}/plugins/java/lib/*"
    subprocess.run([str(ide / "jbr/bin/javac"), "--release", "21", "-cp", sdk, "-d", str(classes),
                    *map(str, (ROOT / "src/main/java").rglob("*.java"))], check=True)
    files.update({str(p.relative_to(classes)): p.read_bytes() for p in classes.rglob("*.class")})
    files["META-INF/LICENSE"] = (ROOT / "LICENSE").read_bytes()
    files["META-INF/KANAGAWA-LICENSE"] = (ROOT / "reference/kanagawa.nvim/LICENSE").read_bytes()
    files["META-INF/INTELLIJ-APACHE-LICENSE"] = (ROOT / "reference/intellij/LICENSE").read_bytes()
    files["META-INF/THIRD_PARTY_NOTICES.md"] = (ROOT / "THIRD_PARTY_NOTICES.md").read_bytes()
    data = archive(files)
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    jar = dist / f"{SLUG}-{VERSION}.jar"
    jar.write_bytes(data)
    (dist / f"{SLUG}-{VERSION}.zip").write_bytes(archive({f"{SLUG}/lib/{jar.name}": data}))
    for variant in VARIANTS:
        stem = f"Kanagawa{variant.title()}Neovim"
        shutil.copyfile(themes / f"{stem}.xml", dist / f"{stem}.icls")
    (dist / "coverage.json").write_text(json.dumps(reports, indent=2) + "\n")
    print(f"Built {jar.name}: {reports}")


if __name__ == "__main__":
    build()
