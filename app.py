#!/usr/bin/env python3
"""
Root Platform Runner & 1-Command Entrypoint (app.py)
Autonomous Video Production, Gemini Vision Inference, and Mobile Studio Server.

Author: MohammedBoure
Role: Backend Architecture & Processing Bridge (agy11)
Branch: backend/agy11-auto-vision-script-and-app-runner
"""

from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path
from typing import Optional

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Load environment configuration (.env)
def _ensure_env_loaded() -> None:
    """Ensure GEMINI_API_KEY is loaded from .env into os.environ."""
    import os
    if os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEYS"):
        return
    for env_path in [REPO_ROOT / ".env", REPO_ROOT / "tts" / ".env"]:
        if env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("\"'")
                            if k not in os.environ:
                                os.environ[k] = v
            except OSError:
                pass

_ensure_env_loaded()

import qrcode
import uvicorn


def detect_lan_ip(preferred_fallback: str = "192.168.1.7") -> str:
    """
    Detect the host machine's primary local area network (LAN) IPv4 address.
    Uses UDP probe to broadcast IP with fallback to hostname resolution.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except Exception:
        pass

    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    return preferred_fallback


def print_banner(lan_ip: str, port: int = 8000) -> None:
    """Print high-visibility terminal banner with ASCII QR code and network URLs."""
    local_url = f"http://localhost:{port}"
    network_url = f"http://{lan_ip}:{port}"

    print("\n" + "=" * 78)
    print("      🏛️  ALGERIAN REAL ESTATE AI VIDEO STUDIO & AUTONOMOUS ENGINE  🏛️")
    print("          Backend Architecture & Processing Bridge (agy11)")
    print("=" * 78)
    print("\n📲 Scan with your smartphone camera to launch the mobile recording studio:\n")

    try:
        qr = qrcode.QRCode(border=1)
        qr.add_data(network_url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except Exception as exc:
        print(f"   [QR Code generator: {exc}]")

    print("\n" + "-" * 78)
    print(f"  👉 Local:   \033[1;36m{local_url}\033[0m")
    print(f"  👉 Network: \033[1;32m{network_url}\033[0m")
    print("-" * 78)
    print("  AI Features Active:")
    print("    🧠 Multimodal Vision : Autonomous architectural script & mood inference")
    print("    🎙️ Expressive TTS     : Gemini 3.8 Flash TTS with emotional tone steering")
    print("    🎵 Smart Ducking     : Sidechain compression over curated Algerian music")
    print("    ⚡ 1-Click Workflow  : Real-time progress tracking & instant mobile cuts")
    print("=" * 78 + "\n")


def main() -> None:
    """CLI launcher entrypoint with graceful shutdown handling."""
    parser = argparse.ArgumentParser(
        prog="python app.py",
        description="Run Algerian Real Estate AI Video Studio & Backend Server (agy11).",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Binding host interface (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default 8000)")
    parser.add_argument("--lan-ip", default=None, help="Explicit LAN IP override for QR code generation")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    lan_ip = args.lan_ip or detect_lan_ip()
    print_banner(lan_ip=lan_ip, port=args.port)

    try:
        uvicorn.run(
            "web.server:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\n[Server] Shutdown signal received. Exiting gracefully...")
        sys.exit(0)


if __name__ == "__main__":
    main()
