#!/bin/bash
# Setup Frida for SSL pinning bypass

echo "=== Frida Setup for SSL Pinning Bypass ==="
echo ""

# Install frida-tools
echo "Installing frida-tools..."
pip3 install frida-tools

# Check device architecture
export PATH=/home/peter/android-sdk/platform-tools:$PATH

echo ""
echo "Checking connected device..."
if ! adb devices | grep -q "device$"; then
    echo "✗ No device connected. Start emulator first."
    exit 1
fi

echo "✓ Device connected"
echo ""

# Get device architecture
ARCH=$(adb shell getprop ro.product.cpu.abi | tr -d '\r')
echo "Device architecture: $ARCH"
echo ""

# Download frida-server
FRIDA_VERSION=$(pip3 show frida-tools | awk '/Version:/ {print $2}')
echo "Frida version: $FRIDA_VERSION"
echo ""

# Map architecture to frida-server naming
case "$ARCH" in
    "x86_64")
        FRIDA_ARCH="x86_64"
        ;;
    "x86")
        FRIDA_ARCH="x86"
        ;;
    "arm64-v8a")
        FRIDA_ARCH="arm64"
        ;;
    "armeabi-v7a")
        FRIDA_ARCH="arm"
        ;;
    *)
        echo "Unknown architecture: $ARCH"
        FRIDA_ARCH="arm64"  # Default guess
        ;;
esac

FRIDA_SERVER="frida-server-${FRIDA_VERSION}-android-${FRIDA_ARCH}"
DOWNLOAD_URL="https://github.com/frida/frida/releases/download/${FRIDA_VERSION}/${FRIDA_SERVER}.xz"

echo "Downloading: $FRIDA_SERVER"
echo "URL: $DOWNLOAD_URL"
echo ""

if [ ! -f "$FRIDA_SERVER" ]; then
    wget "$DOWNLOAD_URL" -O "${FRIDA_SERVER}.xz"

    if [ $? -ne 0 ]; then
        echo "✗ Download failed. You may need to download manually from:"
        echo "  https://github.com/frida/frida/releases/tag/${FRIDA_VERSION}"
        exit 1
    fi

    echo "Extracting..."
    unxz "${FRIDA_SERVER}.xz"
    chmod +x "$FRIDA_SERVER"
fi

echo "✓ Frida server ready: $FRIDA_SERVER"
echo ""

# Push to device
echo "Pushing frida-server to device..."
adb push "$FRIDA_SERVER" /data/local/tmp/frida-server
adb shell "chmod 755 /data/local/tmp/frida-server"

echo "✓ Frida server installed on device"
echo ""

echo "Starting frida-server on device..."
adb shell "/data/local/tmp/frida-server &"

sleep 2

# Check if running
if adb shell "ps | grep frida-server" | grep -q frida-server; then
    echo "✓ Frida server is running"
else
    echo "⚠ Frida server may not be running. Check manually with:"
    echo "  adb shell ps | grep frida"
fi

echo ""
echo "Setup complete!"
echo ""
echo "To use SSL pinning bypass:"
echo "1. Make sure mitmproxy is running: ./start_mitm.sh"
echo "2. Make sure proxy is configured: ./configure_proxy.sh"
echo "3. Find the app package name: adb shell pm list packages | grep camper"
echo "4. Run: frida -U -f com.campercontact.app -l ssl_bypass.js --no-pause"
echo "   (replace com.campercontact.app with actual package name)"
echo "5. Use the app - traffic should now be captured in mitmproxy"
