#!/bin/bash
# Download CamperContact APK using various methods

echo "=== Download CamperContact APK ==="
echo ""
echo "Options to get the APK:"
echo ""
echo "1. From a physical Android device with the app installed:"
echo "   - Install the app from Play Store"
echo "   - Connect device via USB"
echo "   - Run: adb shell pm list packages | grep camper"
echo "   - Run: adb shell pm path <package_name>"
echo "   - Run: adb pull /data/app/.../base.apk campercontact.apk"
echo ""
echo "2. From APK download sites (use with caution):"
echo "   - APKMirror: https://www.apkmirror.com/"
echo "   - APKPure: https://apkpure.com/"
echo "   - Search for 'CamperContact'"
echo ""
echo "3. Using Google Play Store on emulator:"
echo "   - Start emulator with Google APIs (already configured)"
echo "   - Sign in with Google account"
echo "   - Install from Play Store directly"
echo ""
echo "4. Extract from your own device:"
echo "   If you have the app installed on your phone/tablet"
echo ""

read -p "Do you want to try extracting from a connected device? (y/n): " answer

if [[ "$answer" == "y" ]]; then
    export PATH=/home/peter/android-sdk/platform-tools:$PATH

    echo ""
    echo "Checking for connected devices..."
    adb devices

    echo ""
    echo "Searching for CamperContact package..."
    PACKAGE=$(adb shell pm list packages | grep -i camper | head -1 | cut -d: -f2 | tr -d '\r')

    if [[ -z "$PACKAGE" ]]; then
        echo "✗ CamperContact app not found on device"
        echo "Please install it first from Play Store"
        exit 1
    fi

    echo "✓ Found package: $PACKAGE"
    echo ""

    echo "Getting APK path..."
    APK_PATH=$(adb shell pm path "$PACKAGE" | cut -d: -f2 | tr -d '\r')

    if [[ -z "$APK_PATH" ]]; then
        echo "✗ Could not find APK path"
        exit 1
    fi

    echo "✓ APK path: $APK_PATH"
    echo ""

    echo "Pulling APK..."
    adb pull "$APK_PATH" campercontact.apk

    if [[ -f "campercontact.apk" ]]; then
        echo ""
        echo "✓ APK downloaded successfully: campercontact.apk"
        echo ""
        echo "To install on emulator:"
        echo "  adb install campercontact.apk"
    else
        echo "✗ Failed to download APK"
    fi
else
    echo ""
    echo "Please download the APK manually and save it as: campercontact.apk"
fi
