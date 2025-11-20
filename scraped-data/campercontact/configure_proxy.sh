#!/bin/bash
# Configure Android emulator proxy settings

export PATH=/home/peter/android-sdk/platform-tools:$PATH

echo "=== Configure Android Proxy for mitmproxy ==="
echo ""

# Check if device is connected
if ! adb devices | grep -q "device$"; then
    echo "✗ No Android device/emulator detected"
    echo "Please start the emulator first with: ./setup_emulator.sh"
    exit 1
fi

echo "✓ Android device detected"
echo ""

# Wait for device to be fully booted
echo "Waiting for device to be fully booted..."
adb wait-for-device
adb shell 'while [[ -z $(getprop sys.boot_completed) ]]; do sleep 1; done'
echo "✓ Device fully booted"
echo ""

# Set up proxy (for emulator, use 10.0.2.2)
echo "Setting up proxy via ADB..."
adb shell settings put global http_proxy 10.0.2.2:8080

echo "✓ Proxy configured"
echo ""
echo "Next steps:"
echo "1. Make sure mitmproxy is running: ./start_mitm.sh"
echo "2. Open Chrome browser on the emulator"
echo "3. Navigate to: http://mitm.it"
echo "4. Download and install the Android certificate"
echo "5. Install CamperContact app and start using it"
echo ""
echo "To check if proxy is working, open Chrome and navigate to any website"
echo "You should see the traffic in mitmproxy web interface at http://localhost:8081"
echo ""
echo "To remove proxy later:"
echo "  adb shell settings put global http_proxy :0"
