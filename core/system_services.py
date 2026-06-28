# core/system_services.py
#!/usr/bin/env python3
"""
System services setup module for AIALL vLLM Gateway
---------------------------------------------------
Chức năng:
- Cài đặt vLLM backend (Linux)
- Tạo systemd service tối ưu cho vLLM
- Cài đặt Nginx
- Cài đặt Certbot
- Cấp SSL cho domain (standalone mode)
- Windows: bỏ qua (dev mode)
"""

import os
import shutil
import subprocess
from pathlib import Path
import platform

from config import EMAIL


# ============================================================
#  UTILS
# ============================================================

def log(msg: str) -> None:
    print(f"[SERVICE] {msg}")


def run(cmd: list[str], check: bool = True):
    log("RUN: " + " ".join(cmd))
    return subprocess.run(cmd, check=check)


def is_linux() -> bool:
    return platform.system().lower() == "linux"


def apt_exists() -> bool:
    return shutil.which("apt") is not None


def systemctl_available() -> bool:
    return shutil.which("systemctl") is not None


def require_root() -> None:
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        raise SystemExit("Please run as root (sudo).")


def atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content)
    tmp.replace(path)


# ============================================================
#  INSTALL vLLM
# ============================================================

def install_vllm() -> None:
    """Install vLLM backend."""
    if not is_linux():
        log("Non-Linux system detected — skipping vLLM install.")
        return

    log("Installing vLLM backend...")

    if apt_exists():
        run(["apt", "update"])
        run(["apt", "install", "-y", "python3-pip"])

    # Upgrade pip + wheel
    run(["pip3", "install", "--upgrade", "pip", "wheel"], check=False)

    # Install vLLM
    run(["pip3", "install", "--upgrade", "vllm"], check=False)

    log("vLLM installed.")


# ============================================================
#  CONFIGURE vLLM SERVICE
# ============================================================

def configure_vllm_service() -> None:
    """Create and enable systemd service for vLLM."""
    if not is_linux():
        log("Non-Linux system detected — skipping vLLM service configuration.")
        return

    if not systemctl_available():
        log("systemd not available — skipping vLLM service configuration.")
        return

    require_root()

    service_file = Path("/etc/systemd/system/vllm.service")

    content = """[Unit]
Description=vLLM Server
After=network.target

[Service]
WorkingDirectory=/opt/vllm
ExecStart=/usr/bin/python3 -m vllm.entrypoints.openai.api_server --port 8000
Restart=always
RestartSec=3
User=root
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
"""

    atomic_write(service_file, content)

    run(["systemctl", "daemon-reload"])
    run(["systemctl", "enable", "vllm"])
    run(["systemctl", "restart", "vllm"])

    log("vLLM service configured and running.")


# ============================================================
#  INSTALL NGINX
# ============================================================

def install_nginx() -> None:
    if shutil.which("nginx"):
        log("Nginx already installed — skipping.")
        return

    if not is_linux() or not apt_exists():
        log("Cannot install Nginx — non-Linux or apt not available.")
        return

    log("Installing Nginx...")
    run(["apt", "install", "nginx", "-y"], check=False)
    log("Nginx installed.")


# ============================================================
#  INSTALL CERTBOT
# ============================================================

def install_certbot() -> None:
    if shutil.which("certbot"):
        log("Certbot already installed — skipping.")
        return

    if not is_linux() or not apt_exists():
        log("Cannot install Certbot — non-Linux or apt not available.")
        return

    log("Installing Certbot...")
    run(["apt", "install", "certbot", "python3-certbot-nginx", "-y"], check=False)
    log("Certbot installed.")


# ============================================================
#  ISSUE SSL (STANDALONE MODE)
# ============================================================

def issue_ssl_for_domain(domain: str) -> None:
    """Issue SSL certificate using certbot standalone mode."""
    if not is_linux():
        log("Non-Linux system detected — skipping SSL issue.")
        return

    require_root()

    if shutil.which("certbot") is None:
        log("Certbot not installed — cannot issue SSL.")
        return

    log(f"Requesting SSL for {domain} (standalone mode)...")

    run([
        "certbot", "certonly",
        "--standalone",
        "-d", domain,
        "--non-interactive",
        "--agree-tos",
        "-m", EMAIL,
    ], check=False)

    log(f"SSL obtained for {domain}.")

