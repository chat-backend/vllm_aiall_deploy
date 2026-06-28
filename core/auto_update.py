# core//auto_update.py
#!/usr/bin/env python3
"""
Auto-update module for AIALL vLLM Gateway
-----------------------------------------
Chức năng:
- Update hệ thống (Linux)
- Update vLLM backend (pip3)
- Restart vLLM service
- Reload Nginx
- Restart Node Exporter
- Restart Fail2ban
- Windows: safe-skip mode
"""

import os
import shutil
import subprocess
from time import sleep


# ============================================================
#  UTILS
# ============================================================

def log(msg: str) -> None:
    print(f"[AUTO-UPDATE] {msg}")


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    log(f"RUN: {' '.join(cmd)}")
    try:
        return subprocess.run(cmd, check=check)
    except Exception as e:
        log(f"❌ Command failed: {e}")
        if check:
            raise
        return subprocess.CompletedProcess(cmd, 1)


def is_linux() -> bool:
    return os.name == "posix"


def is_linux_root() -> bool:
    if hasattr(os, "geteuid"):
        return os.geteuid() == 0
    return False


def require_root() -> None:
    if is_linux() and not is_linux_root():
        raise SystemExit("Please run as root (sudo).")


def check_internet() -> None:
    log("Checking internet connectivity...")

    ping_cmd = ["ping", "-n", "1", "8.8.8.8"] if os.name == "nt" else ["ping", "-c", "1", "8.8.8.8"]

    result = subprocess.run(
        ping_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if result.returncode != 0:
        log("❌ No internet connection — aborting update.")
        raise SystemExit(1)

    log("✅ Internet OK.")


# ============================================================
#  SYSTEM UPDATE
# ============================================================

def update_system() -> None:
    if not is_linux():
        log("Windows detected — skipping system update.")
        return

    apt = shutil.which("apt")
    if not apt:
        log("apt not found — skipping system update.")
        return

    log("Updating system packages...")

    run(["rm", "-f", "/var/lib/dpkg/lock-frontend"], check=False)
    run(["rm", "-f", "/var/lib/dpkg/lock"], check=False)

    run([apt, "update", "-y"])
    run([apt, "upgrade", "-y"])
    run([apt, "autoremove", "-y"])

    log("✅ System packages updated.")


# ============================================================
#  UPDATE vLLM
# ============================================================

def update_vllm() -> None:
    if not is_linux():
        log("Windows detected — skipping vLLM update.")
        return

    pip3 = shutil.which("pip3")
    if not pip3:
        log("pip3 not found — cannot update vLLM.")
        return

    log("Updating vLLM backend...")

    run([pip3, "install", "--upgrade", "pip", "wheel"], check=False)
    run([pip3, "install", "--upgrade", "vllm"], check=False)

    systemctl = shutil.which("systemctl")
    if systemctl:
        run([systemctl, "restart", "vllm"], check=False)
        log("vLLM service restarted.")
    else:
        log("systemctl not found — please restart vLLM manually.")

    sleep(2)
    log("✅ vLLM updated.")


# ============================================================
#  UPDATE NGINX
# ============================================================

def update_nginx() -> None:
    nginx_bin = shutil.which("nginx")
    if not nginx_bin:
        log("Nginx not installed — skipping.")
        return

    log("Reloading Nginx...")

    test_result = run([nginx_bin, "-t"], check=False)
    if test_result.returncode == 0:
        run([nginx_bin, "-s", "reload"], check=False)
        log("✅ Nginx reloaded.")
    else:
        log("❌ Nginx config invalid — NOT reloading.")


# ============================================================
#  UPDATE NODE EXPORTER
# ============================================================

def update_node_exporter() -> None:
    node_exporter = shutil.which("node_exporter")
    if not node_exporter:
        log("Node Exporter not installed — skipping.")
        return

    log("Restarting Node Exporter...")

    systemctl = shutil.which("systemctl")
    if systemctl:
        run([systemctl, "restart", "node_exporter"], check=False)
        log("✅ Node Exporter restarted.")
    else:
        log("systemctl not found — please restart node_exporter manually.")


# ============================================================
#  UPDATE FAIL2BAN
# ============================================================

def update_fail2ban() -> None:
    fail2ban = shutil.which("fail2ban-client")
    if not fail2ban:
        log("Fail2ban not installed — skipping.")
        return

    log("Reloading Fail2ban...")

    systemctl = shutil.which("systemctl")
    if systemctl:
        run([systemctl, "reload", "fail2ban"], check=False)
        run([systemctl, "restart", "fail2ban"], check=False)
        log("✅ Fail2ban reloaded & restarted.")
    else:
        log("systemctl not found — please manage Fail2ban manually.")


# ============================================================
#  AUTO UPDATE MODE (FULL)
# ============================================================

def auto_update_mode() -> None:
    log("🚀 Starting AUTO-UPDATE mode...")

    require_root()
    check_internet()

    update_system()
    update_vllm()
    update_nginx()
    update_node_exporter()
    update_fail2ban()

    log("✅ AUTO-UPDATE completed successfully.")


