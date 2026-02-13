#!/bin/bash
# Teen Zen - Icon Installer for Capacitor (iOS + Android)
# Run from your project root: /Users/admin/Documents/hello_world/teen.zen

set -e

PROJECT="/Users/admin/Documents/hello_world/teen.zen/chatbot-rag/frontend"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Teen Zen Icon Installer ==="
echo ""

# --- iOS ---
IOS_DEST="$PROJECT/ios/App/App/Assets.xcassets/AppIcon.appiconset"
if [ -d "$IOS_DEST" ]; then
    cp "$SCRIPT_DIR/ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png" "$IOS_DEST/AppIcon-1024.png"
    echo "✅ iOS icon copied"
else
    echo "⚠️  iOS directory not found: $IOS_DEST"
fi

# --- Android ---
ANDROID_RES="$PROJECT/android/app/src/main/res"
if [ -d "$ANDROID_RES" ]; then
    for density in mipmap-mdpi mipmap-hdpi mipmap-xhdpi mipmap-xxhdpi mipmap-xxxhdpi; do
        src="$SCRIPT_DIR/android/app/src/main/res/$density"
        dest="$ANDROID_RES/$density"
        if [ -d "$dest" ]; then
            cp "$src/ic_launcher.png" "$dest/ic_launcher.png"
            cp "$src/ic_launcher_round.png" "$dest/ic_launcher_round.png"
            cp "$src/ic_launcher_foreground.png" "$dest/ic_launcher_foreground.png"
            echo "✅ Android $density copied"
        else
            mkdir -p "$dest"
            cp "$src/"* "$dest/"
            echo "✅ Android $density created and copied"
        fi
    done

    # Adaptive icon XML (Android 8+)
    ANYDPI="$ANDROID_RES/mipmap-anydpi-v26"
    mkdir -p "$ANYDPI"
    cp "$SCRIPT_DIR/android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml" "$ANYDPI/"
    cp "$SCRIPT_DIR/android/app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml" "$ANYDPI/"
    echo "✅ Android adaptive icon XMLs copied"

    # Background color
    VALUES="$ANDROID_RES/values"
    mkdir -p "$VALUES"
    cp "$SCRIPT_DIR/android/app/src/main/res/values/ic_launcher_background.xml" "$VALUES/"
    echo "✅ Android background color set to #1E1B4B"
else
    echo "⚠️  Android res directory not found: $ANDROID_RES"
fi

# --- Web / PWA ---
PUBLIC="$PROJECT/public"
if [ -d "$PUBLIC" ]; then
    cp "$SCRIPT_DIR/public/icon-512.png" "$PUBLIC/icon-512.png"
    cp "$SCRIPT_DIR/public/icon-192.png" "$PUBLIC/icon-192.png"
    echo "✅ Web icons copied"
else
    echo "⚠️  Public directory not found: $PUBLIC"
fi

echo ""
echo "=== All icons installed! ==="
echo ""
echo "Now rebuild:"
echo "  cd $PROJECT"
echo "  npm run build:app"
echo "  npx cap sync ios"
echo "  npx cap sync android"
echo ""
echo "Then rerun in Xcode (Cmd+R) and Android Studio."
