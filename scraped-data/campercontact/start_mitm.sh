#!/bin/bash
# Start mitmproxy web interface for capturing Android app traffic
# This will start on port 8080 for proxy and port 8081 for web interface

echo "Starting mitmweb..."
echo "Proxy will be available at: 0.0.0.0:8080"
echo "Web interface will be available at: http://127.0.0.1:8081"
echo ""
echo "Configure your Android device/emulator to use proxy: <your-ip>:8080"
echo "Install certificate from http://mitm.it after configuring proxy"
echo ""

mitmweb --web-host 0.0.0.0 --web-port 8081 --listen-host 0.0.0.0 --listen-port 8080 --set block_global=false
