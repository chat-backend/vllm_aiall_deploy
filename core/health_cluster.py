# core//health_cluster.py

#!/usr/bin/env python3
"""
Cluster health & auto-heal module for AIALL vLLM Gateway
--------------------------------------------------------
Chức năng:
- Kiểm tra health từng backend vLLM bằng HTTP /v1/models
- Đếm số lần fail và auto-heal backend local sau N lần
- Drain/undrain backend khi heal
- Cập nhật upstream Nginx theo danh sách backend healthy (vllm_cluster)
"""

import os
import shutil
import subprocess
from pathlib import Path
from time import sleep
from typing import List

import requests

from config import UPSTREAM_FILE
from core.backends import (
    load_backends,
    load_drain_list,
    drain_backend,
    undrain_backend,
)

HEAL_STATE_DIR = Path("/var/lib/vllm-auto-heal")
HEAL_STATE_DIR.mkdir(parents=True, exist_ok=True)

MAX_FAILS_BEFORE_HEAL = 3
LOG_FILE = Path("/var/log/vllm-cluster-health.log")


# ============================================================
#  UTILS
# ============================================================

def log(msg: str) -> None:
    line = f"[HEALTH] {msg}"
    print(line)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content)
    tmp.replace(path)


def is_linux() -> bool:
    return os.name == "posix"


def systemctl_available() -> bool:
    return shutil.which("systemctl") is not None


# ============================================================
#  HEALTH CHECK (vLLM)
# ============================================================

def vllm_health(backend: str, timeout: int = 3) -> bool:
    url = f"http://{backend}/v1/models"
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code == 200
    except Exception as e:
        log(f"{backend} HTTP health failed: {e}")
        return False


# ============================================================
#  HEAL LOGIC
# ============================================================

def heal_backend(backend: str) -> bool:
    """
    Heal backend:
    - Tăng fail counter
    - Nếu vượt ngưỡng → drain + restart local vLLM
    - Nếu recover → undrain + reset counter
    """
    host, port = backend.split(":")
    state_file = HEAL_STATE_DIR / f"heal_{host}_{port}.state"

    fail_count = 0
    if state_file.exists():
        try:
            fail_count = int(state_file.read_text().strip())
        except Exception:
            fail_count = 0

    fail_count += 1
    state_file.write_text(str(fail_count))

    log(f"{backend} unhealthy (fail={fail_count})")

    if fail_count < MAX_FAILS_BEFORE_HEAL:
        log(f"Not healing yet (need {MAX_FAILS_BEFORE_HEAL})")
        return False

    log(f"Starting heal sequence for {backend}")

    # Drain backend
    drain_backend(backend)
    sleep(1)

    # Restart local vLLM only
    if host in ("127.0.0.1", "localhost") and is_linux() and systemctl_available():
        log(f"Restarting local vLLM for {backend}")
        subprocess.run(["systemctl", "restart", "vllm"], check=False)
        sleep(5)

        if vllm_health(backend):
            log(f"{backend} recovered after restart")
            undrain_backend(backend)
            state_file.write_text("0")
            return True

        log(f"{backend} still unhealthy after restart")
        return False

    log(f"{backend} is remote or systemctl unavailable — manual heal required")
    return False


# ============================================================
#  UPDATE UPSTREAM (vLLM)
# ============================================================

def update_upstream(healthy: List[str]) -> None:
    """
    Cập nhật file upstream Nginx theo danh sách backend healthy.
    Nếu không có backend healthy → giữ nguyên config cũ.
    """
    if not healthy:
        log("WARNING: No healthy backends — keeping previous upstream")
        return

    log(f"Updating upstream: {healthy}")

    lines = ["upstream vllm_cluster {", "    least_conn;"]
    for be in healthy:
        lines.append(f"    server {be} max_fails=3 fail_timeout=30s;")
    lines.append("}")

    atomic_write(UPSTREAM_FILE, "\n".join(lines) + "\n")

    if not is_linux():
        log("Non-Linux system detected — skipping nginx reload.")
        return

    if shutil.which("nginx") is None:
        log("Nginx not installed — skipping reload.")
        return

    try:
        if subprocess.run(["nginx", "-t"]).returncode == 0:
            subprocess.run(["nginx", "-s", "reload"], check=False)
            log("Nginx reloaded")
        else:
            log("ERROR: invalid nginx config")
    except Exception:
        log("ERROR: failed to reload nginx")


# ============================================================
#  ONE-SHOT HEALTH CHECK
# ============================================================

def health_check() -> None:
    """
    Một lần quét health toàn cluster:
    - Bỏ qua backend đang drain
    - Heal backend unhealthy nếu cần
    - Cập nhật upstream theo danh sách healthy
    """
    backends = load_backends()
    drains = load_drain_list()

    healthy: List[str] = []

    for backend in backends:
        if backend in drains:
            log(f"{backend} draining — skip")
            continue

        if vllm_health(backend):
            log(f"{backend} healthy")
            host, port = backend.split(":")
            state_file = HEAL_STATE_DIR / f"heal_{host}_{port}.state"
            try:
                state_file.write_text("0")
            except Exception:
                pass
            healthy.append(backend)
        else:
            log(f"{backend} UNHEALTHY")
            heal_backend(backend)

    update_upstream(healthy)


if __name__ == "__main__":
    health_check()





