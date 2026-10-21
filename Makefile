.PHONY: build test install export
build:
	python3 scripts/build.py
test: build
	python3 -m unittest discover -s tests -v
export:
	nvim --headless -u NONE -i NONE -l scripts/export_neovim.lua
install: test
	python3 scripts/install.py
