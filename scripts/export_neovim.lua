-- Run from the project root with nvim --headless -u NONE -i NONE -l ...
vim.opt.rtp:prepend(vim.fn.getcwd() .. "/reference/kanagawa.nvim")
local kanagawa = require("kanagawa")
kanagawa.setup({})
for _, variant in ipairs({ "wave", "dragon", "lotus" }) do
  vim.o.background = variant == "lotus" and "light" or "dark"
  kanagawa.load(variant)
  local colors = require("kanagawa.colors").setup({ theme = variant })
  local names = vim.fn.getcompletion("", "highlight")
  local highlights = {}
  for _, name in ipairs(names) do
    local value = vim.api.nvim_get_hl(0, { name = name, link = false })
    for _, key in ipairs({ "fg", "bg", "sp" }) do
      if value[key] then value[key] = string.format("#%06X", value[key]) end
    end
    highlights[name] = value
  end
  local result = { palette = colors.palette, theme = colors.theme, highlights = highlights }
  vim.fn.writefile({ vim.json.encode(result) }, "reference/neovim-" .. variant .. ".json")
  print("Exported " .. variant .. " colors and resolved Neovim highlight groups")
end
