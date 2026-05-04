#!/usr/bin/env bash
# Builds quviai_blender.zip ready to install in Blender.
# Usage: bash scripts/build_zip.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$REPO_ROOT/quviai_blender.zip"

cd "$REPO_ROOT"
rm -f "$OUT"
zip -r "$OUT" quviai_blender/ \
  --exclude "*.pyc" \
  --exclude "*/__pycache__/*"

echo "Built: $OUT"
echo "Install in Blender: Edit → Preferences → Add-ons → Install…"
