# Headless Server Setup Guide

Since this is a headless server, you'll capture traffic remotely. Here are your options:

## Option 1: Physical Android Device (Recommended)

Use your actual phone/tablet and point it to the server's mitmproxy.

### Steps:

1. **Get server's IP address**
   ```bash
   # On server
   hostname -I | awk '{print $1}'
   # Or
   ip addr show | grep "inet " | grep -v 127.0.0.1
   ```

2. **Start mitmproxy on server (allow remote connections)**
   ```bash
   cd /home/peter/scraparr/campercontact

   # Option A: Web interface (view on your computer)
   mitmweb --web-host 0.0.0.0 --web-port 8081 --listen-host 0.0.0.0 --listen-port 8080 --set block_global=false

   # Option B: Save to file
   mitmdump --listen-host 0.0.0.0 --listen-port 8080 -w campercontact_traffic.mitm --set block_global=false
   ```

3. **Configure WiFi proxy on your Android device**
   - Settings → Network & Internet → Wi-Fi
   - Long press your WiFi network → Modify
   - Advanced Options → Proxy → Manual
   - Proxy hostname: `<SERVER_IP>` (from step 1)
   - Proxy port: `8080`
   - Save

4. **Install mitmproxy certificate**
   - Open Chrome on your Android device
   - Navigate to: `http://mitm.it`
   - Download and install Android certificate
   - Settings → Security → Install from storage

5. **Install CamperContact from Play Store**
   - Open Play Store
   - Search "CamperContact"
   - Install

6. **Use the app**
   - All traffic goes through the server's mitmproxy
   - View in browser: `http://<SERVER_IP>:8081`

7. **When done, disable proxy**
   - WiFi settings → Modify → Proxy → None

## Option 2: Run Emulator on Local Machine, Proxy to Server

Run the Android emulator on your local computer, but route traffic through the server.

### Steps:

1. **On server: Start mitmproxy**
   ```bash
   cd /home/peter/scraparr/campercontact
   mitmdump --listen-host 0.0.0.0 --listen-port 8080 -w campercontact_traffic.mitm
   ```

2. **On local machine: Install Android SDK**
   - Download Android Studio or SDK Command-line tools
   - Create an AVD (Android Virtual Device)
   ```bash
   avdmanager create avd -n CamperTest -k "system-images;android-33;google_apis;x86_64"
   emulator -avd CamperTest
   ```

3. **Configure proxy on emulator**
   - Settings → Network → Wi-Fi
   - AndroidWiFi → Modify → Proxy
   - Hostname: `<SERVER_IP>`
   - Port: `8080`

4. **Install certificate and app (same as Option 1)**

5. **Analyze on server**
   ```bash
   python3 analyze_traffic.py campercontact_traffic.mitm
   ```

## Option 3: ADB over Network

Connect your physical Android device over network (no USB needed).

### Steps:

1. **On Android device**
   - Enable Developer Options (tap Build Number 7 times)
   - Enable "USB Debugging"
   - Enable "Wireless Debugging" (Android 11+)

2. **Connect via ADB**
   ```bash
   # On server (if device is on same network)
   export PATH=/home/peter/android-sdk/platform-tools:$PATH

   # Get device IP from Android WiFi settings
   adb connect <DEVICE_IP>:5555

   # Verify
   adb devices
   ```

3. **Configure proxy remotely**
   ```bash
   # Get server IP
   SERVER_IP=$(hostname -I | awk '{print $1}')

   # Set proxy
   adb shell settings put global http_proxy ${SERVER_IP}:8080
   ```

4. **Install certificate and use app**

## Option 4: Headless Emulator with Remote Display

Run emulator headless on server, view remotely with scrcpy.

### Setup:

1. **On server: Install scrcpy dependencies**
   ```bash
   sudo apt-get install -y scrcpy
   ```

2. **Start headless emulator**
   ```bash
   export PATH=/home/peter/android-sdk/emulator:$PATH
   emulator -avd CamperTest -no-window -no-audio &
   ```

3. **On local machine: Connect via SSH with port forwarding**
   ```bash
   ssh -L 5037:localhost:5037 peter@<SERVER_IP>
   ```

4. **On local machine: Run scrcpy**
   ```bash
   scrcpy
   ```

This is complex and may not work well over network.

## Recommended Approach

**Use Option 1** (Physical Android Device):
- ✅ Simplest setup
- ✅ Real device behavior
- ✅ No emulator overhead
- ✅ Can test actual app from Play Store

## Firewall Configuration

If you can't connect, you may need to open port 8080:

```bash
# Check if firewall is running
sudo ufw status

# If active, allow port 8080
sudo ufw allow 8080/tcp

# Or for specific IP only
sudo ufw allow from <YOUR_PHONE_IP> to any port 8080
```

## Testing Connection

Before using the app, test if proxy works:

1. **Configure proxy on Android device**
2. **Open Chrome**
3. **Visit any website**
4. **Check mitmproxy - you should see the request**

If you see traffic from Chrome, you're good to go!

## Quick Start (Physical Device)

```bash
# 1. Get server IP
hostname -I | awk '{print $1}'

# 2. Start mitmproxy
cd /home/peter/scraparr/campercontact
./start_mitm_remote.sh  # New script (will create below)

# 3. On Android: WiFi → Modify → Proxy → Manual
#    Host: <server-ip>
#    Port: 8080

# 4. On Android: Chrome → http://mitm.it → Install cert

# 5. On Android: Install CamperContact from Play Store

# 6. Use the app!

# 7. View captures:
#    Browser: http://<server-ip>:8081
#    Or analyze file: python3 analyze_traffic.py campercontact_traffic.mitm
```
