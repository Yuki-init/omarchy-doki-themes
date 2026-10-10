#!/bin/bash
# Install the Doki themes into Omarchy.
#
# usage: ./install.sh [--link] [theme...]
#   --link   symlink themes instead of copying, so edits in this repo show up live
#   theme    only install these (e.g. doki-aqua); default is all of them

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEMES_DIR="$HOME/.config/omarchy/themes"
LINK=false

if [[ ${1:-} == --link ]]; then
  LINK=true
  shift
fi

mkdir -p "$THEMES_DIR"

if (($#)); then
  themes=("$@")
else
  themes=()
  for dir in "$REPO_DIR"/themes/doki-*/; do
    themes+=("$(basename "$dir")")
  done
fi

for theme in "${themes[@]}"; do
  src="$REPO_DIR/themes/$theme"
  dest="$THEMES_DIR/$theme"

  if [[ ! -d $src ]]; then
    echo "Unknown theme: $theme" >&2
    exit 1
  fi

  rm -rf "$dest"
  if $LINK; then
    ln -s "$src" "$dest"
  else
    cp -a "$src" "$dest"
  fi
done

echo "Installed ${#themes[@]} Doki theme(s) into $THEMES_DIR"
