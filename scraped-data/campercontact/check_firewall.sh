#!/bin/bash
# Check firewall and network configuration

echo "=== Network Configuration Check ==="
echo ""

# Get server IP
echo "Server IP addresses:"
hostname -I
echo ""

# Check if ufw is installed and active
if command -v ufw &> /dev/null; then
    echo "UFW Firewall status:"
    sudo ufw status
    echo ""

    # Check if port 8080 is allowed
    if sudo ufw status | grep -q "8080"; then
        echo "✓ Port 8080 is configured in firewall"
    else
        echo "⚠ Port 8080 not found in firewall rules"
        echo ""
        read -p "Allow port 8080? (y/n): " answer
        if [[ "$answer" == "y" ]]; then
            sudo ufw allow 8080/tcp
            echo "✓ Port 8080 allowed"
        fi
    fi
else
    echo "UFW not installed or not in use"
fi

echo ""
echo "Checking listening ports:"
sudo netstat -tlnp | grep -E ":(8080|8081)" || echo "No services on 8080/8081 (start mitmproxy first)"

echo ""
echo "To test connectivity from Android device:"
echo "  1. Install 'Network Tools' app from Play Store"
echo "  2. Use 'Ping' or 'Port Scanner' to test connection to:"
echo "     $(hostname -I | awk '{print $1}'):8080"
echo ""
echo "Or from another machine:"
echo "  curl -x http://$(hostname -I | awk '{print $1}'):8080 http://example.com"
