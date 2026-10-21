# JetBrains Marketplace submission

Publication is intentionally left to the maintainer. No Marketplace listing
or approval is claimed by this repository.

1. Sign in at https://plugins.jetbrains.com and create a vendor profile if
   needed. Accept the Marketplace Developer Agreement yourself.
2. Choose **Upload plugin** and upload `dist/kanagawa-neovim-port-1.1.0.zip`.
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
