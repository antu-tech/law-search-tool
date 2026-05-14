#!/bin/bash
set -e

# Build Antu Legal Search macOS .app and .dmg
# Usage: cd build && ./build-dmg.sh

cd "$(dirname "$0")/.."
BUILD_DIR="$(pwd)/build"
DIST_DIR="$BUILD_DIR/dist"
APP_NAME="Antu Legal Search"
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"
DMG_NAME="Antu-Legal-Search-macOS.dmg"
VOL_NAME="Antu Legal Search"

rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

echo "=== Step 1: Bundle Python GUI with PyInstaller ==="
python3 -m PyInstaller \
  --name "$APP_NAME" \
  --windowed \
  --onedir \
  --distpath "$DIST_DIR" \
  --workpath "$BUILD_DIR/work" \
  --specpath "$BUILD_DIR" \
  --noconfirm \
  --clean \
  "$BUILD_DIR/mac-gui/gui.py"

echo "=== Step 2: Verify bundle ==="
if [ ! -d "$APP_BUNDLE" ]; then
  echo "ERROR: .app bundle not found at $APP_BUNDLE"
  exit 1
fi

echo "=== Step 3: Create .dmg ==="
# Create a temporary directory for dmg contents
TMP_DMG="$BUILD_DIR/dmg-contents"
rm -rf "$TMP_DMG"
mkdir -p "$TMP_DMG"

# Copy app
cp -R "$APP_BUNDLE" "$TMP_DMG/"

# Create Applications symlink
ln -s /Applications "$TMP_DMG/Applications"

# Create README shortcut
cat > "$TMP_DMG/README.txt" <<'EOF'
Antu Legal Search
==================

1. 將「Antu Legal Search」拖曳到 Applications 資料夾
2. 開啟「Antu Legal Search」
3. 點選「啟動服務」
4. 點選「開啟瀏覽器」

首次使用須先安裝 Docker Desktop：
https://www.docker.com/products/docker-desktop
EOF

# Build the dmg
hdiutil create \
  -volname "$VOL_NAME" \
  -srcfolder "$TMP_DMG" \
  -ov \
  -format UDZO \
  "$DIST_DIR/$DMG_NAME"

echo ""
echo "=== Done ==="
echo "  .app: $APP_BUNDLE"
echo "  .dmg: $DIST_DIR/$DMG_NAME"
echo ""
