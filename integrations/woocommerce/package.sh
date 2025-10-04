#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")" && pwd)
ARTIFACT_DIR="$ROOT_DIR/dist"
PACKAGE_NAME="state-tax-wizard-woocommerce"
VERSION="0.1.0"

rm -rf "$ARTIFACT_DIR"
mkdir -p "$ARTIFACT_DIR"

zip -r "$ARTIFACT_DIR/${PACKAGE_NAME}-${VERSION}.zip" \
  state-tax-wizard.php \
  includes \
  admin \
  assets \
  tests \
  README.md \
  composer.json 2>/dev/null || true

echo "Created package at $ARTIFACT_DIR/${PACKAGE_NAME}-${VERSION}.zip"
