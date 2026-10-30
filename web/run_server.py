#!/usr/bin/env python3
"""
Mobile API Server Runner (web/run_server.py)
Detects host LAN IP, generates terminal ASCII QR code, and starts Uvicorn server.

Author: MouhammedBoure
Role: Backend Architecture & Processing Bridge (agy11)
Branch: backend/agy11-mobile-api-server
"""

from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path
from typing import Optional

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import qrcode
import uvicorn


def detect_lan_ip(preferred_fallback: str = "192.168.1.7") -> str:
    """
    Detect the host machine's primary local area network (LAN) IPv4 address.
    Uses UDP socket probe with fallback to hostname resolution and preferred IP.
    """
    # 1. UDP probe to broadcast address
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except Exception:
        pass

    # 2. Hostname resolution
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    # 3. Fallback
    return preferred_fallback


def print_server_banner(lan_ip: str, port: int) -> None:
    """Print high-visibility terminal banner with QR code and access URLs."""
    mobile_url = f"http://{lan_ip}:{port}"
    local_url = f"http://127.0.0.1:{port}"

    print("\n" + "=" * 76)
    print("      🏛️  ALGERIAN REAL ESTATE MOBILE VIDEO STUDIO & API SERVER  🏛️")
    print("          Backend Architecture & Processing Bridge (agy11)")
    print("=" * 76)
    print("\n📲 Scan this QR code with your smartphone camera to connect instantly:\n")

    try:
        qr = qrcode.QRCode(border=1)
        qr.add_data(mobile_url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except Exception as exc:
        print(f"   [Notice: QR Code generation skipped: {exc}]")

    print("\n" + "-" * 76)
    print(f"  👉 Mobile Web Access:  \033[1;32m{mobile_url}\033[0m")
    print(f"  👉 Localhost Access:   \033[1;36m{local_url}\033[0m")
    print("-" * 76)
    print("  Available REST Endpoints:")
    print("    • POST /api/upload-and-process  Upload mobile video & generate marketing cut")
    print("    • GET  /api/presets             Retrieve Algerian real estate presets")
    print("    • GET  /api/health              Service health and telemetry check")
    print("    • GET  /api/status/{job_id}     Query job status and execution summary")
    print("    • GET  /outputs/*               Static media serving (cuts & keyframes)")
    print("    • GET  /                        Mobile web studio interface")
    print("=" * 76 + "\n")


def main() -> None:
    """CLI launcher entrypoint."""
    parser = argparse.ArgumentParser(
        prog="python -m web.run_server",
        description="Launch Algerian Real Estate Mobile Studio API Server (agy11).",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Binding host interface (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default 8000)")
    parser.add_argument("--lan-ip", default=None, help="Explicit LAN IP override for QR code generation")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for local development")
    args = parser.parse_args()

    lan_ip = args.lan_ip or detect_lan_ip()
    print_server_banner(lan_ip=lan_ip, port=args.port)

    # Start Uvicorn Server
    uvicorn.run(
        "web.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
