#! /usr/bin/env nix-shell
#! nix-shell -i bash -p bash -p uv
set -euxo pipefail
cd "$(dirname "$0")"
uv run update.py --output ~/public_html/htlgi
