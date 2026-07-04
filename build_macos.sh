#!/usr/bin/env bash
set -euo pipefail

# Build AutoScope for macOS
# Produces build/macos/AutoScope.app

echo "Building AutoScope for macOS..."

flet build macos --project autoscope --product "AutoScope"

echo "Build complete. App bundle: build/macos/AutoScope.app"

# Optional: create a .dmg if create-dmg is installed
if command -v create-dmg &>/dev/null; then
    APP="build/macos/AutoScope.app"
    DMG="build/macos/AutoScope.dmg"
    echo "Creating DMG..."
    rm -f "$DMG"
    create-dmg \
        --volname "AutoScope" \
        --window-pos 200 120 \
        --window-size 800 400 \
        --icon-size 100 \
        --app-drop-link 600 185 \
        "$DMG" \
        "$APP" || echo "create-dmg failed; app bundle is still available at $APP"
else
    echo "create-dmg not installed. Skipping DMG creation."
    echo "Install with: brew install create-dmg"
fi
