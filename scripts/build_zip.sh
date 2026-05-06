#!/usr/bin/env bash
# Builds two ZIP files:
#   quviai_blender.zip           — legacy add-on format (GitHub release, Blender < 4.2)
#   quviai_blender_extension.zip — Extensions Platform format (extensions.blender.org)
# Usage: bash scripts/build_zip.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEGACY="$REPO_ROOT/quviai_blender.zip"
EXTENSION="$REPO_ROOT/quviai_blender_extension.zip"

EXCLUDE_ARGS=(
  --exclude "*.pyc"
  --exclude "*/__pycache__/*"
)

# --- Legacy format: quviai_blender/ folder at ZIP root ---
cd "$REPO_ROOT"
rm -f "$LEGACY"
zip -r "$LEGACY" quviai_blender/ "${EXCLUDE_ARGS[@]}"
echo "Built (legacy):    $LEGACY"

# --- Extension format: files at ZIP root, manifest required ---
rm -f "$EXTENSION"
cd "$REPO_ROOT/quviai_blender"
zip -r "$EXTENSION" . "${EXCLUDE_ARGS[@]}"
cd "$REPO_ROOT"
echo "Built (extension): $EXTENSION"

echo ""
echo "Legacy    → Install in Blender: Edit → Preferences → Add-ons → Install…"
echo "Extension → Upload to:          https://extensions.blender.org/submit/"
