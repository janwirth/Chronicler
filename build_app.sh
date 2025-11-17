#!/bin/bash
# Build Chronicler.app bundle for macOS

set -e

APP_NAME="Chronicler"
BUNDLE_DIR="dist/${APP_NAME}.app"
CONTENTS_DIR="${BUNDLE_DIR}/Contents"
MACOS_DIR="${CONTENTS_DIR}/MacOS"
RESOURCES_DIR="${CONTENTS_DIR}/Resources"

echo "Building ${APP_NAME}.app..."

# Clean previous build
rm -rf dist
mkdir -p "${MACOS_DIR}"
mkdir -p "${RESOURCES_DIR}"

# Copy Python script
echo "Copying application files..."
cp chronicler.py "${MACOS_DIR}/"
cp viewer.py "${MACOS_DIR}/"

# Copy virtual environment
echo "Copying Python dependencies..."
cp -r venv "${RESOURCES_DIR}/"

# Convert PNG to ICNS (macOS icon format)
echo "Converting icon..."
mkdir -p icon.iconset
sips -z 16 16     icon.png --out icon.iconset/icon_16x16.png
sips -z 32 32     icon.png --out icon.iconset/icon_16x16@2x.png
sips -z 32 32     icon.png --out icon.iconset/icon_32x32.png
sips -z 64 64     icon.png --out icon.iconset/icon_32x32@2x.png
sips -z 128 128   icon.png --out icon.iconset/icon_128x128.png
sips -z 256 256   icon.png --out icon.iconset/icon_128x128@2x.png
sips -z 256 256   icon.png --out icon.iconset/icon_256x256.png
sips -z 512 512   icon.png --out icon.iconset/icon_256x256@2x.png
sips -z 512 512   icon.png --out icon.iconset/icon_512x512.png
sips -z 1024 1024 icon.png --out icon.iconset/icon_512x512@2x.png
iconutil -c icns icon.iconset -o "${RESOURCES_DIR}/${APP_NAME}.icns"
rm -rf icon.iconset

# Create launcher script
echo "Creating launcher..."
cat > "${MACOS_DIR}/${APP_NAME}" << 'EOF'
#!/bin/bash
# Chronicler launcher script

# Get the directory where the app is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RESOURCES_DIR="${DIR}/../Resources"

# Use the bundled Python virtual environment
export PATH="${RESOURCES_DIR}/venv/bin:$PATH"

# Run the chronicler
cd "${DIR}"
exec python3 chronicler.py
EOF

chmod +x "${MACOS_DIR}/${APP_NAME}"

# Create Info.plist
echo "Creating Info.plist..."
cat > "${CONTENTS_DIR}/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIconFile</key>
    <string>${APP_NAME}.icns</string>
    <key>CFBundleIdentifier</key>
    <string>com.chronicles.logger</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.14</string>
    <key>LSUIElement</key>
    <false/>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSAppleEventsUsageDescription</key>
    <string>Chronicler needs to monitor keyboard input to log your activity.</string>
    <key>NSSystemAdministrationUsageDescription</key>
    <string>Chronicler needs accessibility access to monitor keyboard input across all applications.</string>
</dict>
</plist>
EOF

# Create PkgInfo
echo -n "APPL????" > "${CONTENTS_DIR}/PkgInfo"

# Ad-hoc code signing (self-signed) for stable identity
echo "Signing app bundle..."
codesign --force --deep --sign - "${BUNDLE_DIR}" 2>/dev/null || echo "Warning: Could not sign app (this is OK for testing)"

# Set extended attributes to mark as safe
xattr -cr "${BUNDLE_DIR}"

echo ""
echo "✓ Build complete: ${BUNDLE_DIR}"
echo ""
echo "IMPORTANT: To fix permission prompts:"
echo "1. Go to System Settings → Privacy & Security"
echo "2. Remove any existing 'Chronicler' entries from:"
echo "   - Accessibility"
echo "   - Screen Recording"
echo "3. Launch the app: open ${BUNDLE_DIR}"
echo "4. Grant permissions when prompted (ONE TIME only)"
echo ""
echo "To add to Login Items:"
echo "  System Settings → General → Login Items → Click '+' → Add Chronicler.app"
