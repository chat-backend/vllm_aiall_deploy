# core/firewall.py

#!/usr/bin/env python3
"""
Firewall setup module for AIALL vLLM Gateway
--------------------------------------------
Chức năng:
- Kiểm tra và cài đặt UFW (Ubuntu/Debian)
- Thêm rule cho các port quan trọng:
    22   SSH
    80   HTTP
    443  HTTPS
    8000 vLLM backend
    6001 Gateway API
    9100 Node Exporter
- Không phá SSH
- Safe khi chạy nhiều lần
- Windows: bỏ qua
"""

import os
import shutil
import subprocess


# ============================================================
#  LOGGING
# ============================================================

def log(msg: str) -> None:
    print(f"[FIREWALL] {msg}")


# ============================================================
#  SAFE RUN
# ============================================================

def run(cmd: list[str], check: bool = True):
    log("RUN: " + " ".join(cmd))
    return subprocess.run(cmd, check=check)


# ============================================================
#  HELPERS
# ============================================================

def is_linux() -> bool:
    return os.name == "posix"


def apt_exists() -> bool:
    return shutil.which("apt") is not None


def ufw_exists() -> bool:
    return shutil.which("ufw") is not None


def systemctl_available() -> bool:
    return shutil.which("systemctl") is not None


def require_root() -> None:
    """Yêu cầu root trên Linux, Windows thì bỏ qua."""
    if hasattr(os, "geteuid"):
        if os.geteuid() != 0:
            raise SystemExit("Please run as root (sudo).")


def ufw_is_enabled() -> bool:
    try:
        result = subprocess.run(
            ["ufw", "status"],
            capture_output=True,
            text=True,
            check=False,
        )
        return "Status: active" in result.stdout
    except Exception:
        return False


def allow_port(port: str) -> None:
    """Add UFW rule only if not already present."""
    try:
        result = subprocess.run(
            ["ufw", "status"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        log("Failed to read UFW status — cannot add port rule.")
        return

    for line in result.stdout.splitlines():
        # Match exact port (avoid matching 22 vs 2222)
        if line.strip().startswith(port + " "):
            log(f"Port {port} already allowed.")
            return

    run(["ufw", "allow", port])


# ============================================================
#  MAIN ENTRY
# ============================================================

def setup_firewall() -> None:
    """
    Setup firewall rules:
    - Safe for multiple runs
    - Does not break SSH
    - Adds rules for:
        22   SSH
        80   HTTP
        443  HTTPS
        8000 vLLM backend
        6001 Gateway API
        9100 Node Exporter
    """
    if not is_linux():
        log("Non-Linux system detected — skipping firewall setup.")
        return

    require_root()

    log("Configuring UFW firewall...")

    # 1) Install UFW if missing
    if not ufw_exists():
        if not apt_exists():
            log("UFW not installed and apt not available — skipping UFW install.")
            return
        log("UFW not installed — installing via apt...")
        run(["apt", "install", "ufw", "-y"])
    else:
        log("UFW already installed.")

    # 2) Allow essential ports
    allow_port("22")     # SSH
    allow_port("80")     # HTTP
    allow_port("443")    # HTTPS
    allow_port("8000")   # vLLM backend
    allow_port("6001")   # Gateway API
    allow_port("9100")   # Node Exporter

    # Optional monitoring ports (Prometheus/Grafana)
    allow_port("9090")   # Prometheus (optional)
    allow_port("3000")   # Grafana (optional)

    # 3) Enable UFW if not active
    if not ufw_is_enabled():
        log("Enabling UFW...")
        run(["ufw", "--force", "enable"])
    else:
        log("UFW already active.")

    log("Firewall configured successfully.")


