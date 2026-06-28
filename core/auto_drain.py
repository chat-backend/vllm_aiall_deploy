# core/auto_drain.py
#!/usr/bin/env python3
"""
Auto-drain module for AIALL vLLM Gateway Cluster
------------------------------------------------
Chức năng:
- Đọc danh sách backend hiện tại
- Health-check backend qua HTTP /v1/models
- Đọc CPU metrics từ Node Exporter
- Tự động drain/undrain backend theo CPU
- Không auto-scale (vLLM không hỗ trợ local multi-instance)
"""

import subprocess
from pathlib import Path
from typing import Optional, Tuple, List
import requests

from core.backends import (
    load_backends,
    load_drain_list,
    drain_backend,
    undrain_backend,
)
from core.health_cluster import health_check


# ============================================================
#  PATHS & STATE
# ============================================================

LOG_FILE = Path("/var/log/vllm-auto-drain.log")
STATE_DIR = Path("/var/lib/vllm-auto-drain")

CPU_DRAIN_THRESHOLD = 85
CPU_UNDRAIN_THRESHOLD = 60


def ensure_state_dirs() -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


# ============================================================
#  LOGGING
# ============================================================

def log(msg: str) -> None:
    line = f"[AUTO-DRAIN] {msg}"
    print(line)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ============================================================
#  HEALTH CHECK (vLLM)
# ============================================================

def vllm_health(backend: str, timeout: int = 3) -> bool:
    url = f"http://{backend}/v1/models"
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


# ============================================================
#  METRICS / CPU PARSING
# ============================================================

def curl_metrics(url: str) -> Optional[str]:
    try:
        out = subprocess.check_output(
            ["curl", "-fsS", "--max-time", "2", url],
            stderr=subprocess.DEVNULL,
        )
        return out.decode()
    except Exception:
        return None


def parse_cpu(metrics: str) -> Tuple[float, float]:
    idle = 0.0
    busy = 0.0
    for line in metrics.splitlines():
        if "node_cpu_seconds_total" not in line:
            continue
        if 'mode="idle"' in line:
            idle += float(line.split()[-1])
        elif 'mode="' in line:
            busy += float(line.split()[-1])
    return idle, busy


def load_cpu_state(host: str) -> Optional[Tuple[float, float]]:
    state_file = STATE_DIR / f"cpu_{host}.state"
    if not state_file.exists():
        return None
    try:
        return tuple(map(float, state_file.read_text().split()))
    except Exception:
        return None


def save_cpu_state(host: str, idle: float, busy: float) -> None:
    state_file = STATE_DIR / f"cpu_{host}.state"
    try:
        state_file.write_text(f"{idle} {busy}")
    except Exception:
        pass


def compute_cpu_percent(host: str, idle: float, busy: float) -> Optional[int]:
    prev = load_cpu_state(host)
    save_cpu_state(host, idle, busy)

    if prev is None:
        log(f"Init CPU state for {host}")
        return None

    prev_idle, prev_busy = prev
    delta_idle = idle - prev_idle
    delta_busy = busy - prev_busy
    delta_total = delta_idle + delta_busy

    if delta_total <= 0:
        return None

    return int((delta_busy / delta_total) * 100)


# ============================================================
#  AUTO-DRAIN LOGIC
# ============================================================

def process_backend(backend: str, drains: List[str]) -> None:
    host, port = backend.split(":")

    # 1) HEALTH CHECK
    if not vllm_health(backend):
        log(f"{backend} unhealthy → draining")
        drain_backend(backend)
        return

    # 2) CPU METRICS
    metrics = curl_metrics(f"http://{host}:9100/metrics")
    if not metrics:
        log(f"Node Exporter unreachable for {backend} → draining")
        drain_backend(backend)
        return

    idle, busy = parse_cpu(metrics)
    cpu_percent = compute_cpu_percent(host, idle, busy)
    if cpu_percent is None:
        return

    log(f"{backend} CPU≈{cpu_percent}%")

    # 3) AUTO-DRAIN
    if cpu_percent >= CPU_DRAIN_THRESHOLD:
        if backend not in drains:
            log(f"High load → draining {backend}")
            drain_backend(backend)

    # 4) AUTO-UNDRAIN
    elif cpu_percent <= CPU_UNDRAIN_THRESHOLD:
        if backend in drains:
            log(f"CPU normal → undraining {backend}")
            undrain_backend(backend)


# ============================================================
#  MAIN ENTRY
# ============================================================

def auto_drain() -> None:
    ensure_state_dirs()

    backends = load_backends()
    drains = load_drain_list()

    if len(backends) == 1:
        log("Single-backend mode — skip auto-drain")
        return

    for backend in backends:
        process_backend(backend, drains)

    # Sync upstream after all changes
    health_check()


if __name__ == "__main__":
    auto_drain()
