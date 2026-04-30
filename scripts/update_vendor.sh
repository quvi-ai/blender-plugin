#!/usr/bin/env bash
# Usage: bash scripts/update_vendor.sh [path-to-python-sdk]
#
# Copies the QUVIAI Python SDK source into quviai_blender/vendor/quviai/
# so it is bundled with the add-on without requiring pip.
#
# Run this script whenever the SDK is updated, then commit the vendor/ changes.

set -euo pipefail

SDK_PATH="${1:-../quviai-python-sdk}"
SRC="${SDK_PATH}/src/quviai"
DEST="$(dirname "$0")/../quviai_blender/vendor/quviai"

if [ ! -d "$SRC" ]; then
  echo "ERROR: SDK source not found at '$SRC'"
  echo "Usage: bash scripts/update_vendor.sh <path-to-python-sdk>"
  exit 1
fi

echo "Copying SDK from '$SRC' → '$DEST' ..."
rm -rf "$DEST"
cp -r "$SRC" "$DEST"

# Write a version marker
SDK_VERSION=$(cd "$SDK_PATH" && git describe --tags --always 2>/dev/null || echo "unknown")
echo "$SDK_VERSION" > "$(dirname "$0")/../quviai_blender/vendor/VENDOR_VERSION"

echo "Done. SDK version: $SDK_VERSION"
echo "Remember to commit the vendor/ changes."
