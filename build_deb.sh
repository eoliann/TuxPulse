#!/usr/bin/env bash
set -e

APP_NAME="tuxpulse"
VERSION="1.0"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PKG_DIR="$ROOT_DIR/packaging/deb"
DIST_DIR="$ROOT_DIR/dist"
TARGET="$PKG_DIR/usr/share/tuxpulse"

rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"
rm -rf "$TARGET"
mkdir -p "$TARGET"

cp -r "$ROOT_DIR/app" "$TARGET/"

mkdir -p "$PKG_DIR/usr/share/icons/hicolor/256x256/apps"
if [ -f "$ROOT_DIR/assets/tuxpulse.png" ]; then
    cp "$ROOT_DIR/assets/tuxpulse.png" "$PKG_DIR/usr/share/icons/hicolor/256x256/apps/tuxpulse.png"
fi

chmod 755 "$PKG_DIR/usr/bin/tuxpulse"

dpkg-deb --build "$PKG_DIR" "$DIST_DIR/${APP_NAME}_${VERSION}.deb"
echo "Built: $DIST_DIR/${APP_NAME}_${VERSION}.deb"
