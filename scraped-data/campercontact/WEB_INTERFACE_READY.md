# ✅ Proxy Capture Web Interface - Ready!

## 🎉 What's Been Added

I've integrated the CamperContact API traffic capture directly into your Scraparr web interface!

### New Features:

1. **📱 Proxy Capture Page** - Access at `/proxy` in your Scraparr UI
2. **🎛️ Control Panel** - Start/stop mitmproxy from the web interface
3. **📋 Android Setup Instructions** - Step-by-step guide displayed in the UI
4. **🔴 Live Status** - Real-time proxy status with automatic updates
5. **⚠️ SSL Pinning Warnings** - Built-in troubleshooting for modern Android
6. **🔗 Quick Links** - Direct links to certificate download and live traffic viewer

## 🚀 How to Use

### Step 1: Access the Proxy Page

Open your browser and navigate to:
- **http://192.168.1.6:3001/proxy**

You'll see a new "Proxy Capture" option in the left sidebar menu.

### Step 2: Start Capture

1. Click the **"Start Capture"** button in the web interface
2. The interface will show:
   - Server IP: `192.168.1.6`
   - Proxy Port: `8080`
   - Web Interface URL for live traffic viewing

### Step 3: Configure Your Android Phone

The web interface displays step-by-step instructions:

1. **WiFi Settings** → Long press network → Modify
2. **Proxy:** Manual
3. **Hostname:** `192.168.1.6`
4. **Port:** `8080`
5. Save

### Step 4: Install Certificate

1. Open Chrome on your phone
2. Go to: **http://mitm.it**
3. Download and install Android certificate

### Step 5: Install & Use CamperContact

1. Install from Play Store
2. Use the app normally
3. All traffic is automatically captured!

### Step 6: View Live Traffic

Click the **"Open Web Interface"** link in the Proxy Capture page to see requests in real-time.

### Step 7: Stop & Analyze

1. Click **"Stop Capture"** when done
2. Analyze the captured traffic:
   ```bash
   cd /home/peter/scraparr/campercontact
   python3 analyze_traffic.py campercontact_traffic.mitm
   ```

## 📍 API Endpoints

The following endpoints have been added to the Scraparr API:

- `GET /api/proxy/status` - Get current proxy status
- `POST /api/proxy/start` - Start mitmproxy
- `POST /api/proxy/stop` - Stop mitmproxy
- `GET /api/proxy/instructions` - Get setup instructions
- `GET /api/proxy/certificate-url` - Get certificate download URL

## ⚠️ Important Notes

### Latest Android (7+)

Your phone has the latest Android, which **doesn't trust user certificates by default**. If you see SSL errors:

1. **The app likely uses SSL certificate pinning**
2. **Solutions:**
   - Try Frida SSL bypass (see troubleshooting in web UI)
   - Use an older Android device (Android 6 or lower)
   - Root your device (advanced)

The web interface shows warnings and solutions for this!

### Firewall

If you can't connect from your phone, you may need to allow port 8080:

```bash
sudo ufw allow 8080/tcp
sudo ufw allow 8081/tcp
```

## 📂 Files Created

### Backend:
- `/home/peter/work/scraparr/backend/app/api/proxy.py` - Proxy API endpoints
- `/home/peter/work/scraparr/backend/app/services/proxy_service.py` - Proxy management service

### Frontend:
- `/home/peter/work/scraparr/frontend/src/pages/ProxyCapturePage.tsx` - Proxy control UI

### Capture Tools (previously created):
- `/home/peter/scraparr/campercontact/` - All capture scripts and tools

## 🎨 Screenshots

The interface includes:
- ✅ Status indicator (Running/Stopped)
- 🎚️ Start/Stop buttons
- 📊 Capture file size display
- 📱 5-step Android setup guide
- 🔗 Quick links to certificate and live viewer
- ⚠️ Android SSL pinning warning
- 🛠️ Expandable troubleshooting section

## 🧪 Testing

API is verified working:
```bash
$ curl http://192.168.1.6:8000/api/proxy/status
{"running":false,"status":"stopped","server_ip":null,...}
```

## 💡 Next Steps

1. **Try it now!** Go to http://192.168.1.6:3001/proxy
2. **Start the proxy** and follow on-screen instructions
3. **If you hit SSL pinning issues:**
   - Check the troubleshooting accordion in the web UI
   - Consider using Frida (scripts are ready at `/home/peter/scraparr/campercontact/`)
4. **After capture:** Analyze with `python3 analyze_traffic.py`
5. **Build scraper:** Update `scraper.py` with discovered endpoints

## 🎯 What This Enables

Once you capture the traffic and discover the API:
- Build a CamperContact scraper for Scraparr
- Schedule automatic data collection
- Integrate camping spot data into your Scraparr database
- No more manual web scraping!

## 🆘 Troubleshooting

### Web UI not loading?
- Check frontend is running: `ps aux | grep "react-scripts"`
- Frontend should be on port 3001

### API endpoints 404?
- Backend should auto-reload, but if not: `docker compose restart backend`
- Wait 10 seconds for full startup

### Proxy won't start?
- Check mitmproxy is installed: `which mitmproxy`
- Check logs in web UI or: `docker logs scraparr-backend`

---

**Ready to discover CamperContact's API!** 🚀📱

Go to: **http://192.168.1.6:3001/proxy**
