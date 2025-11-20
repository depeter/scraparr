#!/bin/bash
# Capture traffic to file from remote Android device

SERVER_IP=$(hostname -I | awk '{print $1}')
OUTPUT_FILE="${1:-campercontact_traffic.mitm}"

if [[ -z "$SERVER_IP" ]]; then
    echo "Error: Could not determine server IP"
    exit 1
fi

echo "=== Remote Traffic Capture to File ==="
echo ""
echo "Server IP: $SERVER_IP"
echo "Proxy: $SERVER_IP:8080"
echo "Output: $OUTPUT_FILE"
echo ""
echo "Configure your Android device:"
echo "  Settings → WiFi → Modify Network"
echo "  Proxy: Manual"
echo "  Hostname: $SERVER_IP"
echo "  Port: 8080"
echo ""
echo "Install certificate: http://mitm.it"
echo ""
echo "Press Ctrl+C to stop capturing"
echo ""

# Start mitmdump for file capture
mitmdump \
    --listen-host 0.0.0.0 \
    --listen-port 8080 \
    --set block_global=false \
    -w "$OUTPUT_FILE"
