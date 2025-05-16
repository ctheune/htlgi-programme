#! /usr/bin/env nix-shell
#! nix-shell -i bash -p bash -p uv

uv run update.py
cp result.html ~/public_html/htlgi/index.html