The Kanagawa palettes, original highlight definitions, and the snapshot in
`reference/kanagawa.nvim` come from https://github.com/rebelot/kanagawa.nvim,
Copyright (c) 2021 Tommaso Laurenzi, MIT license. The original license is
included in that directory and in the built plugin.

The IntelliJ UI reference files in `reference/intellij` come from JetBrains'
IntelliJ Community platform, build IU-262.8665.337. Their key inventory and dark
theme layout are used to cover the installed IDE's controls. These files are
licensed under Apache License 2.0; see `reference/intellij/LICENSE`.
Source: https://github.com/JetBrains/intellij-community/tree/master/platform/platform-resources/src/themes

Acknowledgment: https://github.com/frykher/jetbrains-kanagawa-theme by Fahim H.
is an earlier IntelliJ Kanagawa plugin and was a useful point of reference.
This port has its own implementation and mappings; none of that plugin's
source implementation is included.

`reference/queries/java-highlights.scm` is the Java Treesitter highlighting
query from the user's installed nvim-treesitter runtime, used to check Java
token categories. Its Apache 2.0 license is in `reference/queries/LICENSE`.
Source: https://github.com/nvim-treesitter/nvim-treesitter
