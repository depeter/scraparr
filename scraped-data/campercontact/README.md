# CamperContact API Scraper

This project captures network traffic from the CamperContact Android app to discover and document their API endpoints.

## Prerequisites

- mitmproxy (installed ✓)
- Android SDK with emulator or physical Android device
- CamperContact APK

## Setup Instructions

### Method 1: Using Android Emulator (Recommended for API Discovery)

1. **Create an Android Virtual Device (if not already created)**
   ```bash
   export PATH=/home/peter/android-sdk/cmdline-tools/latest/bin:$PATH
   export PATH=/home/peter/android-sdk/emulator:$PATH
   export PATH=/home/peter/android-sdk/platform-tools:$PATH

   # List available system images
   avdmanager list

   # Create AVD (example with Android 14)
   avdmanager create avd -n CamperTest -k "system-images;android-36;default;x86_64" -d "pixel_5"
   ```

2. **Start the emulator with writable system (needed for certificate)**
   ```bash
   export PATH=/home/peter/android-sdk/emulator:/home/peter/android-sdk/platform-tools:$PATH
   emulator -avd CamperTest -writable-system &
   ```

3. **Start mitmproxy**
   ```bash
   cd /home/peter/scraparr/campercontact
   ./start_mitm.sh
   # OR for file capture:
   ./capture_to_file.sh campercontact_capture.mitm
   ```

4. **Configure proxy in Android emulator**
   - Open Settings → Network & Internet → Wi-Fi
   - Long press on "AndroidWiFi" → Modify Network
   - Advanced Options → Proxy → Manual
   - Proxy hostname: `10.0.2.2` (this is the host machine from emulator perspective)
   - Proxy port: `8080`
   - Save

5. **Install mitmproxy certificate**
   - Open Chrome browser in emulator
   - Navigate to `http://mitm.it`
   - Tap "Android"
   - Name it "mitmproxy" and install
   - You may need to set a PIN/password for the device

6. **Install CamperContact app**
   ```bash
   # Download APK first, then:
   adb install campercontact.apk
   ```

7. **Use the app and capture traffic**
   - Open CamperContact app
   - Browse spots, search, view details, etc.
   - All API calls will be captured by mitmproxy
   - View in web interface at http://localhost:8081

### Method 2: Using Physical Android Device

1. **Enable USB Debugging on your device**
   - Go to Settings → About Phone
   - Tap "Build Number" 7 times to enable Developer Options
   - Go to Settings → Developer Options
   - Enable "USB Debugging"

2. **Connect device and verify**
   ```bash
   export PATH=/home/peter/android-sdk/platform-tools:$PATH
   adb devices
   ```

3. **Get your computer's IP address**
   ```bash
   ip addr show | awk '/inet .* wlan0/{print $2}' | cut -d/ -f1
   # OR
   hostname -I | awk '{print $1}'
   ```

4. **Start mitmproxy** (same as above)

5. **Configure proxy on Android device**
   - Settings → Network & Internet → Wi-Fi
   - Long press on your Wi-Fi network → Modify
   - Advanced → Proxy → Manual
   - Hostname: `<your-computer-ip>` (from step 3)
   - Port: `8080`

6. **Install certificate**
   - Open browser and go to `http://mitm.it`
   - Download and install Android certificate

7. **Install and use CamperContact**
   - Install the app from Play Store or sideload APK
   - Use the app normally, all traffic will be captured

## Capturing Traffic

### Interactive Web Interface
```bash
./start_mitm.sh
```
- View at http://localhost:8081
- Filter, search, and inspect requests in real-time
- Save individual requests or entire sessions

### Save to File (for later analysis)
```bash
./capture_to_file.sh campercontact_traffic.mitm
```

### Read captured file
```bash
mitmproxy -r campercontact_traffic.mitm
```

## Dealing with SSL Pinning

If the app uses SSL certificate pinning, you'll see connection errors. Solutions:

1. **Use older Android version** (easier to bypass on Android 6 or lower)
2. **Root the device/emulator and use Frida**
3. **Patch the APK** to disable SSL pinning
4. **Use Magisk + TrustMeAlready module** (requires root)

### Quick SSL Pinning Bypass with Frida (if needed)

```bash
# Install Frida
pip3 install frida-tools

# Download frida-server for Android
# Start frida-server on device
# Run universal SSL pinning bypass script
frida -U -f com.campercontact.app -l frida-ssl-bypass.js --no-pause
```

## Expected API Endpoints to Discover

Based on typical camping apps, we're looking for:

- `/api/spots` or `/api/campsites` - List of camping spots
- `/api/spots/{id}` - Spot details
- `/api/search` - Search functionality
- `/api/reviews` - User reviews
- `/api/facilities` - Spot facilities/amenities
- `/api/images` - Photos
- Authentication endpoints
- Filter/sort endpoints

## Next Steps

1. Capture all major app interactions
2. Document discovered endpoints in `api_documentation.md`
3. Extract authentication mechanism (Bearer tokens, API keys, etc.)
4. Test endpoints with curl/Postman to verify
5. Build Python scraper based on discovered API
6. Implement rate limiting and polite scraping practices

## Notes

- The app may use API keys or authentication - save all headers
- Some endpoints may require login - create a test account
- Respect robots.txt and rate limits
- This is for personal/research use only
