#!/bin/bash
# Start mitmproxy for remote/headless capture (physical Android device)

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

if [[ -z "$SERVER_IP" ]]; then
    echo "Error: Could not determine server IP"
    echo "Please check network configuration"
    exit 1
fi

echo "=== Starting mitmproxy for Remote Capture ==="
echo ""
echo "Server IP: $SERVER_IP"
echo "Proxy available at: $SERVER_IP:8080"
echo "Web interface at: http://$SERVER_IP:8081"
echo ""
echo "Configure your Android device:"
echo "  1. WiFi Settings → Long press network → Modify"
echo "  2. Advanced → Proxy → Manual"
echo "  3. Proxy hostname: $SERVER_IP"
echo "  4. Proxy port: 8080"
echo "  5. Save"
echo ""
echo "Then install certificate:"
echo "  1. Open Chrome browser"
echo "  2. Navigate to: http://mitm.it"
echo "  3. Download and install Android certificate"
echo ""
echo "View captures in browser: http://$SERVER_IP:8081"
echo ""
echo "Starting mitmweb..."
echo ""

# Start mitmweb with remote access enabled
mitmweb \
    --web-host 0.0.0.0 \
    --web-port 8081 \
    --listen-host 0.0.0.0 \
    --listen-port 8080 \
    --set block_global=false \
    --set web_open_browser=false
