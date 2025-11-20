#!/bin/bash
# Setup Android emulator for traffic capture

export PATH=/home/peter/android-sdk/cmdline-tools/latest/bin:$PATH
export PATH=/home/peter/android-sdk/emulator:$PATH
export PATH=/home/peter/android-sdk/platform-tools:$PATH

AVD_NAME="CamperTest"

echo "=== Android Emulator Setup for CamperContact Traffic Capture ==="
echo ""

# Check if AVD already exists
if avdmanager list avd | grep -q "Name: $AVD_NAME"; then
    echo "✓ AVD '$AVD_NAME' already exists"
    echo ""
    echo "Would you like to:"
    echo "1) Start the existing emulator"
    echo "2) Delete and recreate it"
    echo "3) Exit"
    read -p "Choice (1-3): " choice

    case $choice in
        1)
            echo "Starting emulator..."
            emulator -avd $AVD_NAME -writable-system &
            echo ""
            echo "✓ Emulator starting in background"
            echo "Wait for boot to complete, then run: ./configure_proxy.sh"
            ;;
        2)
            echo "Deleting existing AVD..."
            avdmanager delete avd -n $AVD_NAME
            ;;
        3)
            exit 0
            ;;
    esac
fi

# Create new AVD if doesn't exist
if ! avdmanager list avd | grep -q "Name: $AVD_NAME"; then
    echo "Creating new AVD: $AVD_NAME"
    echo ""

    # Check available system images
    echo "Available system images:"
    avdmanager list target

    echo ""
    echo "Creating AVD with system-images;android-36;google_apis;x86_64"

    # Create AVD
    echo "no" | avdmanager create avd \
        -n $AVD_NAME \
        -k "system-images;android-36;google_apis;x86_64" \
        -d "pixel_5" \
        --force

    if [ $? -eq 0 ]; then
        echo ""
        echo "✓ AVD created successfully"
        echo ""
        echo "Starting emulator..."
        emulator -avd $AVD_NAME -writable-system &
        echo ""
        echo "✓ Emulator starting in background"
        echo ""
        echo "Next steps:"
        echo "1. Wait for emulator to fully boot (~1-2 minutes)"
        echo "2. Run: ./configure_proxy.sh"
        echo "3. Install CamperContact APK"
        echo "4. Start capturing traffic with ./start_mitm.sh"
    else
        echo "✗ Failed to create AVD"
        echo ""
        echo "Try checking available system images with:"
        echo "  avdmanager list"
        exit 1
    fi
fi
