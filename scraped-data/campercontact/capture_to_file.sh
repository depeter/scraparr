#!/bin/bash
# Start mitmproxy in dump mode to capture traffic to a file
# Usage: ./capture_to_file.sh [output_file]

OUTPUT_FILE="${1:-campercontact_traffic.mitm}"

echo "Starting mitmdump..."
echo "Proxy available at: 0.0.0.0:8080"
echo "Capturing traffic to: $OUTPUT_FILE"
echo ""
echo "Configure your Android device/emulator to use proxy: <your-ip>:8080"
echo "Install certificate from http://mitm.it after configuring proxy"
echo "Press Ctrl+C to stop capturing"
echo ""

mitmdump --listen-host 0.0.0.0 --listen-port 8080 -w "$OUTPUT_FILE" --set block_global=false
