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
  --icon "$BUILD_DIR/../assets/AntuLegalSearch.icns" \
  --noconfirm \
  --clean \
  "$BUILD_DIR/mac-gui/gui.py"

echo "=== Step 2: Verify bundle ==="
if [ ! -d "$APP_BUNDLE" ]; then
  echo "ERROR: .app bundle not found at $APP_BUNDLE"
  exit 1
fi

# Force Finder to recognize the custom icon
touch "$APP_BUNDLE"
if command -v SetFile &> /dev/null; then
  SetFile -a C "$APP_BUNDLE" 2>/dev/null || true
fi
# Register with LaunchServices so icon cache is warm
if [ -x "/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister" ]; then
  /System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister -f "$APP_BUNDLE" 2>/dev/null || true
fi

echo "=== Step 3: Create .dmg ==="
TMP_DMG="$BUILD_DIR/dmg-contents"
rm -rf "$TMP_DMG"
mkdir -p "$TMP_DMG"

# Copy app (use ditto to preserve all macOS metadata)
ditto "$APP_BUNDLE" "$TMP_DMG/$APP_NAME.app"
touch "$TMP_DMG/$APP_NAME.app"

# Create Applications symlink
ln -s /Applications "$TMP_DMG/Applications"

# Create README
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

# Build the compressed dmg
hdiutil create \
  -volname "$VOL_NAME" \
  -srcfolder "$TMP_DMG" \
  -ov \
  -format UDZO \
  "$DIST_DIR/$DMG_NAME"

echo "=== Step 4: Set DMG layout ==="
# Mount, set icon positions, unmount
osascript <<EOF
try
    set dmgPath to POSIX file "$DIST_DIR/$DMG_NAME" as alias
    tell application "Finder"
        set mountedDisk to mount volume dmgPath as URL
        tell disk "$VOL_NAME"
            open
            set current view of container window to icon view
            set toolbar visible of container window to false
            set statusbar visible of container window to false
            set bounds of container window to {100, 100, 540, 380}
            set icon size of icon view options of container window to 96
            set arrangement of icon view options of container window to not arranged
            try
                set position of item "$APP_NAME.app" of container window to {120, 140}
            end try
            try
                set position of item "Applications" of container window to {320, 140}
            end try
            update registering applications
        end tell
        delay 1
        eject disk "$VOL_NAME"
    end tell
end try
EOF

echo ""
echo "=== Done ==="
echo "  .app: $APP_BUNDLE"
echo "  .dmg: $DIST_DIR/$DMG_NAME"
echo ""
