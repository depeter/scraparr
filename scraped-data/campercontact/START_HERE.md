# 📱 CamperContact API Discovery - Headless Server Edition

## TL;DR - Use Your Phone

Since this is a headless server, you'll use your **physical Android device** and route traffic through this server.

## Quick Start (5 minutes)

### 1️⃣ Start mitmproxy on server
```bash
cd /home/peter/scraparr/campercontact
./start_mitm_remote.sh
```

This will display the server IP and instructions. Keep this running.

### 2️⃣ Configure your Android phone

**WiFi Settings:**
- Open Settings → Network & Internet → Wi-Fi
- Long press your WiFi network
- Select "Modify network" or tap the gear icon
- Scroll down → Advanced options
- Proxy: **Manual**
- Proxy hostname: **[Server IP from step 1]**
- Proxy port: **8080**
- Save

### 3️⃣ Install mitmproxy certificate

**On your phone:**
- Open Chrome browser
- Navigate to: **http://mitm.it**
- Tap "Android"
- Download the certificate
- Give it a name (e.g., "mitmproxy")
- Install it

**Note:** You may need to set a screen lock PIN/password first.

### 4️⃣ Install CamperContact

- Open Play Store
- Search "CamperContact"
- Install the app

### 5️⃣ Use the app

- Open CamperContact
- Browse camping spots
- Search locations
- View spot details
- Check reviews
- Use all features you want to scrape

**All traffic is being captured!**

### 6️⃣ View captured traffic

**Option A:** Web interface (from your computer/phone)
- Open browser: `http://[SERVER_IP]:8081`

**Option B:** Analyze the capture file
```bash
# Stop mitmproxy (Ctrl+C)
python3 analyze_traffic.py campercontact_traffic.mitm
```

### 7️⃣ Don't forget to disable proxy!

When done:
- WiFi Settings → Modify → Proxy → **None**

## Troubleshooting

### Can't connect to server

```bash
# On server - check firewall
./check_firewall.sh

# Allow port 8080 if needed
sudo ufw allow 8080/tcp
sudo ufw allow 8081/tcp  # For web interface
```

### Certificate won't install

1. Set screen lock first: Settings → Security → Screen Lock → PIN
2. Try Settings → Security → Install from storage
3. Select "VPN and apps" when asked

### App shows "Connection failed" or "SSL error"

The app uses **SSL pinning**. You have two options:

**Option A:** Try on older Android device (Android 6 or lower is easier)

**Option B:** Use Frida to bypass (advanced)
```bash
# On server
./setup_frida.sh

# Find app package name
adb shell pm list packages | grep camper

# Run with bypass
frida -U -f com.campercontact.app -l ssl_bypass.js --no-pause
```

### No traffic appearing in mitmproxy

1. **Test with Chrome first:**
   - With proxy configured, open Chrome
   - Visit any website (e.g., http://example.com)
   - You should see it in mitmproxy

2. **If Chrome works but app doesn't:**
   - App likely uses SSL pinning (see above)

3. **If nothing works:**
   - Check firewall (see above)
   - Verify proxy settings on phone
   - Make sure you're on the same network as the server
   - Try pinging the server from your phone

## Alternative: Save to File Instead of Web Interface

If you don't need real-time viewing:

```bash
# Use this instead of start_mitm_remote.sh
./capture_remote.sh campercontact_capture.mitm
```

Press Ctrl+C when done, then analyze:

```bash
python3 analyze_traffic.py campercontact_capture.mitm
```

## Next Steps After Capture

1. **Analyze the traffic:**
   ```bash
   python3 analyze_traffic.py campercontact_traffic.mitm
   ```

2. **Review the findings:**
   - Check console output for API endpoints
   - Open `campercontact_traffic_analysis.json` for details

3. **Update the scraper:**
   - Edit `scraper.py` with discovered endpoints
   - Add authentication if needed
   - Test individual endpoints

4. **Run the scraper:**
   ```bash
   python3 scraper.py --query "Netherlands"
   ```

## What to Capture

Make sure to perform these actions in the app:
- ✅ Browse featured/popular spots
- ✅ Search by location name
- ✅ Search by current GPS location
- ✅ View spot details
- ✅ View photos/gallery
- ✅ Read reviews
- ✅ Apply filters (facilities, price, etc.)
- ✅ View map
- ✅ Login (if app requires it)

The more you use, the more API endpoints you'll discover!

## Files Overview

- `start_mitm_remote.sh` - Start capture with web interface
- `capture_remote.sh` - Capture to file only
- `check_firewall.sh` - Check network/firewall config
- `analyze_traffic.py` - Analyze captured traffic
- `scraper.py` - The scraper (update after analysis)
- `HEADLESS_SETUP.md` - Detailed setup options

## Getting Help

- Full documentation: `README.md`
- Headless setup options: `HEADLESS_SETUP.md`
- Quick reference: `QUICKSTART.md` (for local emulator - not applicable here)

---

**Ready to start?** Run: `./start_mitm_remote.sh`
