# JetBrains Marketplace submission

Version **1.1.1** was submitted on **2026-10-22** under the **Somed-1** vendor:
https://plugins.jetbrains.com/plugin/35388-kanagawa-neovim-port

The upload was accepted and is awaiting JetBrains review. The listing includes
the Wave, Dragon and Lotus screenshots, MIT license, source link, original
project credits, AI disclosure and installation instructions. Upload acceptance
does not mean the plugin has been approved or is publicly installable yet.

Marketplace plugin ID: `io.github.somed1.kanagawa.nvim`. The GitHub-only 1.1.0
release used a local ID containing the reserved word `intellij`; Marketplace
rejected that ID, so 1.1.1 uses the new identity. Remove 1.1.0 before upgrading
manually; `scripts/install.py` replaces the local installation directly.

For future submissions:

1. Sign in at https://plugins.jetbrains.com and create a vendor profile if
   needed. The existing profile is Somed-1.
2. Choose **Upload plugin** and upload `dist/kanagawa-neovim-port-1.1.1.zip`.
3. Use **Kanagawa Neovim Port** as the name, **Themes** as the category, and the
   repository README as the basis for the description.
4. Set the source and issue tracker URLs to this GitHub repository, choose MIT
   as the license, and add the screenshots from `docs/screenshots/`.
5. Retain the upstream credits and AI disclosure. Submit for JetBrains review.

The ZIP includes all three variants, a plugin icon, the MIT license and
third-party notices. IntelliJ Platform build 262 (2026.2) is the minimum
declared version; do not advertise earlier versions without testing them.

Official instructions:
https://plugins.jetbrains.com/docs/marketplace/uploading-a-new-plugin.html

After the initial listing is created, future uploads can use the Marketplace
API with a maintainer-provided token stored as a secret, never in source:
https://plugins.jetbrains.com/docs/marketplace/plugin-upload.html
