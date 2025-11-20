# Quick Start Guide - CamperContact API Discovery

## TL;DR

```bash
# 1. Start mitmproxy
./start_mitm.sh

# 2. Setup Android emulator (in another terminal)
./setup_emulator.sh

# 3. Configure proxy (wait for emulator to boot)
./configure_proxy.sh

# 4. In emulator browser, go to http://mitm.it and install certificate

# 5. Install CamperContact
# Either download APK or install from Play Store in emulator

# 6. Use the app - all traffic is captured

# 7. Analyze captured traffic
python3 analyze_traffic.py campercontact_traffic.mitm

# 8. Build scraper based on findings
# Edit scraper.py with discovered endpoints
python3 scraper.py --query "Amsterdam"
```

## Detailed Workflow

### Phase 1: Setup (One-time)

1. **Install dependencies**
   ```bash
   pip3 install -r requirements.txt
   ```

2. **Create Android emulator**
   ```bash
   ./setup_emulator.sh
   ```
   This will create and start an AVD named "CamperTest"

3. **Wait for emulator to boot** (~1-2 minutes)
   Watch the emulator window until you see the home screen

### Phase 2: Capture Traffic

1. **Start mitmproxy** (Terminal 1)
   ```bash
   ./start_mitm.sh
   ```
   - Web interface: http://localhost:8081
   - Proxy: localhost:8080

2. **Configure proxy on emulator** (Terminal 2)
   ```bash
   ./configure_proxy.sh
   ```

3. **Install mitmproxy certificate**
   - Open Chrome in emulator
   - Go to: `http://mitm.it`
   - Tap "Android"
   - Give it a name and install
   - May need to set device PIN

4. **Get CamperContact APK**

   Option A: From physical device
   ```bash
   ./download_apk.sh
   ```

   Option B: From Play Store
   - Open Play Store in emulator
   - Sign in with Google account
   - Search and install CamperContact

   Option C: Download from APKMirror/APKPure
   - Visit https://www.apkmirror.com/
   - Search for CamperContact
   - Download and transfer to project folder

5. **Install APK** (if not using Play Store)
   ```bash
   export PATH=/home/peter/android-sdk/platform-tools:$PATH
   adb install campercontact.apk
   ```

6. **Use the app**
   - Open CamperContact
   - Search for spots
   - View details
   - Check reviews
   - Use filters
   - View maps
   - Login if needed
   - Perform ALL actions you want to scrape later

7. **Monitor traffic**
   - Watch http://localhost:8081 in your browser
   - Look for API calls (usually contain /api/, /rest/, /graphql/, etc.)
   - Filter by domain to focus on CamperContact's servers

### Phase 3: Analysis

1. **Stop capturing**
   - Ctrl+C in the mitmproxy terminal
   - Traffic is saved automatically

2. **Analyze captured traffic**
   ```bash
   python3 analyze_traffic.py campercontact_traffic.mitm
   ```

   This will:
   - List all domains contacted
   - Identify potential API endpoints
   - Show HTTP methods and status codes
   - Extract authentication headers
   - Save detailed analysis to JSON

3. **Review the analysis**
   - Check console output for API endpoints
   - Open `campercontact_traffic_analysis.json` for details
   - Look for patterns in URLs
   - Identify authentication mechanism
   - Note required headers

4. **Document findings**
   Create `api_documentation.md` with:
   - Base URL
   - Authentication method
   - Endpoints discovered
   - Request/response examples
   - Rate limits observed

### Phase 4: Build Scraper

1. **Update scraper.py**
   - Set correct `BASE_URL`
   - Update headers with real User-Agent
   - Implement authentication if needed
   - Update endpoint methods with real paths
   - Adjust parameters based on actual API

2. **Test individual endpoints**
   ```bash
   # Test with curl first
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        -H "User-Agent: CamperContact-App/X.X.X" \
        "https://api.campercontact.com/api/spots?lat=52.3676&lon=4.9041"
   ```

3. **Run scraper**
   ```bash
   # Search by query
   python3 scraper.py --query "Amsterdam"

   # Search by location
   python3 scraper.py --lat 52.3676 --lon 4.9041 --radius 50

   # With API key if needed
   python3 scraper.py --api-key "YOUR_KEY" --query "France"
   ```

4. **Verify output**
   - Check `data/` directory for JSON files
   - Verify data completeness
   - Check for errors in logs

## Troubleshooting

### "Certificate verification failed" in app

The app likely uses SSL pinning. Solutions:

1. **Try older Android version** (Android 6 or lower in emulator)
2. **Root emulator and use Frida**
   ```bash
   pip3 install frida-tools
   # Download frida-server for your architecture
   # Push to device and run
   adb push frida-server /data/local/tmp/
   adb shell "chmod 755 /data/local/tmp/frida-server"
   adb shell "/data/local/tmp/frida-server &"

   # Run SSL pinning bypass
   frida -U -f com.campercontact.app -l ssl-bypass.js --no-pause
   ```

3. **Patch APK** with tools like apktool, remove pinning, re-sign

### "No traffic appearing in mitmproxy"

1. Check proxy is set: `adb shell settings get global http_proxy`
2. Verify mitmproxy is running on port 8080
3. Test with Chrome browser first (visit any website)
4. Make sure certificate is installed

### "Cannot install certificate"

1. Need to set screen lock first (Settings → Security → Screen Lock)
2. Install as "VPN and apps" certificate
3. On newer Android, may need root to install system certificate

### Emulator won't start

1. Check KVM is enabled: `lsmod | grep kvm`
2. Try without hardware acceleration: `emulator -avd CamperTest -writable-system -no-accel`
3. Check available disk space
4. Review emulator logs: `~/.android/avd/CamperTest.avd/*.log`

## Tips for Success

1. **Be thorough**: Use every feature in the app before analyzing
2. **Take notes**: Document what you were doing when each request was made
3. **Check auth**: Look for tokens, API keys, or session cookies
4. **Test endpoints**: Verify each discovered endpoint with curl before scraping
5. **Be polite**: Implement rate limiting, use reasonable delays
6. **Respect ToS**: Only scrape what you need, for personal/research use
7. **Cache data**: Don't re-scrape the same data repeatedly

## Project Structure

```
campercontact/
├── README.md                      # Detailed documentation
├── QUICKSTART.md                  # This file
├── requirements.txt               # Python dependencies
├── start_mitm.sh                  # Start mitmproxy web interface
├── capture_to_file.sh             # Capture to file
├── setup_emulator.sh              # Create/start emulator
├── configure_proxy.sh             # Configure emulator proxy
├── download_apk.sh                # Helper to get APK
├── analyze_traffic.py             # Analyze captured traffic
├── scraper.py                     # The scraper (template)
├── campercontact_traffic.mitm     # Captured traffic (after capture)
├── campercontact_traffic_analysis.json  # Analysis results
├── api_documentation.md           # Your API docs (to be created)
└── data/                          # Scraped data output
    └── spots_*.json
```

## Next Steps After First Capture

1. Create detailed API documentation
2. Test authentication and session management
3. Implement pagination if needed
4. Add error handling and retries
5. Implement caching to avoid re-scraping
6. Add progress bars for long scrapes
7. Consider database storage for large datasets
8. Build data export/transformation pipeline for Scraparr

## Resources

- mitmproxy docs: https://docs.mitmproxy.org/
- Android emulator docs: https://developer.android.com/studio/run/emulator
- Frida (SSL pinning bypass): https://frida.re/
- APK tools: https://ibotpeaches.github.io/Apktool/
