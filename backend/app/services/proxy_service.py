"""
Service for managing mitmproxy capture process
"""
import asyncio
import subprocess
import socket
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ProxyService:
    """Manage mitmproxy process for traffic capture"""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.capture_dir = Path("/home/peter/scraparr/campercontact")
        self.capture_file = self.capture_dir / "campercontact_traffic.mitm"
        self.port = 8080
        self.web_port = 8081

    def get_server_ip(self) -> str:
        """Get the server's local IP address"""
        try:
            # Try to get from environment variable first (for Docker)
            import os
            host_ip = os.environ.get('HOST_IP')
            if host_ip:
                return host_ip

            # Get primary IP by creating a socket connection
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()

            # If we got a Docker internal IP (172.x or 10.x), try to get host IP
            if ip.startswith('172.') or ip.startswith('10.'):
                # Read from /etc/hosts or return a default
                return "192.168.1.6"  # Fallback to known host IP

            return ip
        except Exception as e:
            logger.error(f"Failed to get server IP: {e}")
            return "192.168.1.6"  # Fallback to known host IP

    def is_running(self) -> bool:
        """Check if mitmproxy is currently running"""
        if self.process is None:
            return False
        return self.process.poll() is None

    def start(self, web_interface: bool = True) -> dict:
        """
        Start mitmproxy

        Args:
            web_interface: If True, start mitmweb, else start mitmdump

        Returns:
            Status dict with success/error info
        """
        if self.is_running():
            return {
                "success": False,
                "error": "Proxy is already running",
                "status": "running"
            }

        try:
            # Ensure capture directory exists
            self.capture_dir.mkdir(parents=True, exist_ok=True)

            if web_interface:
                # Start mitmweb with web interface
                cmd = [
                    "mitmweb",
                    "--web-host", "0.0.0.0",
                    "--web-port", str(self.web_port),
                    "--listen-host", "0.0.0.0",
                    "--listen-port", str(self.port),
                    "--set", "block_global=false",
                    "--set", "web_open_browser=false",
                    "-w", str(self.capture_file)
                ]
            else:
                # Start mitmdump (no web interface)
                cmd = [
                    "mitmdump",
                    "--listen-host", "0.0.0.0",
                    "--listen-port", str(self.port),
                    "--set", "block_global=false",
                    "-w", str(self.capture_file)
                ]

            logger.info(f"Starting mitmproxy: {' '.join(cmd)}")

            # Start process in background
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.capture_dir)
            )

            # Give it a moment to start
            import time
            time.sleep(2)

            # Check if it started successfully
            if self.process.poll() is not None:
                # Process died
                stderr = self.process.stderr.read().decode() if self.process.stderr else "Unknown error"
                logger.error(f"mitmproxy failed to start: {stderr}")
                return {
                    "success": False,
                    "error": f"Failed to start: {stderr}",
                    "status": "stopped"
                }

            server_ip = self.get_server_ip()
            logger.info(f"mitmproxy started successfully on {server_ip}:{self.port}")

            return {
                "success": True,
                "status": "running",
                "server_ip": server_ip,
                "proxy_port": self.port,
                "web_port": self.web_port if web_interface else None,
                "capture_file": str(self.capture_file)
            }

        except Exception as e:
            logger.error(f"Failed to start mitmproxy: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "stopped"
            }

    def stop(self) -> dict:
        """Stop mitmproxy"""
        if not self.is_running():
            return {
                "success": False,
                "error": "Proxy is not running",
                "status": "stopped"
            }

        try:
            logger.info("Stopping mitmproxy...")
            self.process.terminate()

            # Wait up to 5 seconds for graceful shutdown
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("mitmproxy didn't stop gracefully, killing...")
                self.process.kill()
                self.process.wait()

            self.process = None
            logger.info("mitmproxy stopped")

            return {
                "success": True,
                "status": "stopped",
                "message": "Proxy stopped successfully"
            }

        except Exception as e:
            logger.error(f"Failed to stop mitmproxy: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "unknown"
            }

    def get_status(self) -> dict:
        """Get current proxy status"""
        running = self.is_running()
        server_ip = self.get_server_ip() if running else None

        status = {
            "running": running,
            "status": "running" if running else "stopped",
            "server_ip": server_ip,
            "proxy_port": self.port if running else None,
            "web_port": self.web_port if running else None,
            "capture_file": str(self.capture_file) if running else None,
            "capture_exists": self.capture_file.exists(),
            "capture_size": self.capture_file.stat().st_size if self.capture_file.exists() else 0
        }

        return status

    def get_instructions(self) -> dict:
        """Get setup instructions for Android device"""
        server_ip = self.get_server_ip()

        return {
            "server_ip": server_ip,
            "proxy_port": self.port,
            "web_interface_url": f"http://{server_ip}:{self.web_port}",
            "certificate_url": "http://mitm.it",
            "steps": [
                {
                    "step": 1,
                    "title": "Configure WiFi Proxy",
                    "instructions": [
                        "Open Settings → Network & Internet → Wi-Fi",
                        "Long press your WiFi network → Modify",
                        "Advanced Options → Proxy → Manual",
                        f"Proxy hostname: {server_ip}",
                        f"Proxy port: {self.port}",
                        "Save"
                    ]
                },
                {
                    "step": 2,
                    "title": "Install mitmproxy Certificate",
                    "instructions": [
                        "Open Chrome browser on your phone",
                        "Navigate to: http://mitm.it",
                        "Tap 'Android'",
                        "Download and install the certificate",
                        "You may need to set a screen lock PIN first"
                    ]
                },
                {
                    "step": 3,
                    "title": "Install CamperContact App",
                    "instructions": [
                        "Open Play Store",
                        "Search for 'CamperContact'",
                        "Install the app"
                    ]
                },
                {
                    "step": 4,
                    "title": "Use the App",
                    "instructions": [
                        "Open CamperContact",
                        "Browse spots, search, view details",
                        "All traffic will be captured automatically",
                        f"View live traffic at: http://{server_ip}:{self.web_port}"
                    ]
                },
                {
                    "step": 5,
                    "title": "When Done",
                    "instructions": [
                        "Stop the proxy capture",
                        "WiFi Settings → Modify → Proxy → None",
                        "Analyze captured traffic"
                    ]
                }
            ],
            "troubleshooting": {
                "ssl_pinning": {
                    "title": "If you see SSL/Connection errors",
                    "description": "The app likely uses SSL certificate pinning. Modern Android apps (especially on Android 7+) don't trust user certificates by default.",
                    "solutions": [
                        "Try an older Android device (Android 6 or lower)",
                        "Use Frida to bypass SSL pinning (advanced)",
                        "Root your device and use Magisk + TrustMeAlready module"
                    ]
                },
                "no_traffic": {
                    "title": "No traffic appearing",
                    "description": "If you don't see any requests in the capture",
                    "solutions": [
                        "Test with Chrome browser first (visit any website)",
                        "Check firewall allows port 8080",
                        "Verify proxy settings on phone",
                        "Make sure phone and server are on same network"
                    ]
                }
            }
        }


# Global instance
proxy_service = ProxyService()
