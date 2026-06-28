# main.py — FastAPI version (final)

#!/usr/bin/env python3
"""
AIALL vLLM Gateway – System Service (FastAPI, FULL INTEGRATION, CROSS-PLATFORM SAFE)
------------------------------------------------------------------------------------
- Không xử lý API AI chính (đã đi qua Nginx → vLLM backend)
- Hiển thị thông tin cấu hình runtime
- Quản lý backend (add/remove/drain/undrain)
- Health-check cluster
- Auto-update, auto-drain, rolling-restart (Linux-only)
- Tích hợp trực tiếp deploy_main.py nhưng an toàn trên Windows
"""

from fastapi import FastAPI
import uvicorn
import platform

# ===== Runtime Config =====
from config_loader import load_runtime_config
cfg = load_runtime_config()

# ===== Import deploy_main logic =====
from deploy_main import (
    full_deploy,
    auto_update_mode,
    health_check,
    auto_drain,
    rolling_restart,
    handle_backend_command,
)

# ===== Backend manager =====
import core.backends as be


IS_LINUX = platform.system().lower().startswith("linux")

# ============================================================
#  FASTAPI APP
# ============================================================

app = FastAPI(
    title="AIALL vLLM Gateway – System Service",
    version="2.0.0",
)


# ============================================================
#  ROOT ENDPOINT
# ============================================================

@app.get("/")
def index():
    return {
        "service": "AIALL vLLM Gateway – System Service",
        "status": "running",
        "note": "API chính chạy qua Nginx → vLLM backend (OpenAI-compatible)",
        "base_url": cfg.base_url,
        "api_chat": cfg.url_chat,
        "api_completion": cfg.url_completion,
        "api_models": cfg.url_models,
        "default_params": {
            "max_tokens": cfg.default_max_tokens,
            "min_tokens": cfg.default_min_tokens,
            "temperature": cfg.default_temperature,
            "top_p": cfg.default_top_p,
        },
        "backends": be.load_backends(),
        "env": {
            "is_linux": IS_LINUX,
        },
    }


# ============================================================
#  SYSTEM HEALTH
# ============================================================

@app.get("/system/health")
def system_health():
    return {"status": "ok"}


# ============================================================
#  CLUSTER HEALTH
# ============================================================

@app.get("/cluster/health")
def cluster_health():
    if not IS_LINUX:
        return {"cluster": "unknown", "error": "cluster health is Linux-only"}
    try:
        health_check()
        return {"cluster": "healthy"}
    except Exception as e:
        return {"cluster": "unhealthy", "error": str(e)}


# ============================================================
#  FULL DEPLOY (manual trigger)
# ============================================================

@app.post("/cluster/deploy")
def cluster_deploy():
    if not IS_LINUX:
        return {"deploy": "unsupported", "error": "deploy is Linux-only"}
    try:
        full_deploy()
        return {"deploy": "completed"}
    except Exception as e:
        return {"deploy": "failed", "error": str(e)}


# ============================================================
#  AUTO UPDATE
# ============================================================

@app.post("/cluster/update")
def cluster_update():
    if not IS_LINUX:
        return {"update": "unsupported", "error": "update is Linux-only"}
    try:
        auto_update_mode()
        return {"update": "started"}
    except Exception as e:
        return {"update": "failed", "error": str(e)}


# ============================================================
#  AUTO DRAIN
# ============================================================

@app.post("/cluster/auto-drain")
def cluster_auto_drain():
    if not IS_LINUX:
        return {"auto_drain": "unsupported", "error": "auto-drain is Linux-only"}
    try:
        auto_drain()
        return {"auto_drain": "started"}
    except Exception as e:
        return {"auto_drain": "failed", "error": str(e)}


# ============================================================
#  ROLLING RESTART
# ============================================================

@app.post("/cluster/rolling-restart")
def cluster_rolling_restart():
    if not IS_LINUX:
        return {"rolling_restart": "unsupported", "error": "rolling-restart is Linux-only"}
    try:
        rolling_restart()
        return {"rolling_restart": "started"}
    except Exception as e:
        return {"rolling_restart": "failed", "error": str(e)}


# ============================================================
#  BACKEND MANAGEMENT
# ============================================================

@app.post("/backend/add")
def add_backend(backend: str):
    try:
        handle_backend_command("add-backend", backend)
        return {"backend": backend, "status": "added"}
    except Exception as e:
        return {"backend": backend, "status": "failed", "error": str(e)}


@app.post("/backend/remove")
def remove_backend(backend: str):
    try:
        handle_backend_command("remove-backend", backend)
        return {"backend": backend, "status": "removed"}
    except Exception as e:
        return {"backend": backend, "status": "failed", "error": str(e)}


@app.post("/backend/drain")
def drain_backend(backend: str):
    try:
        handle_backend_command("drain-backend", backend)
        return {"backend": backend, "status": "drained"}
    except Exception as e:
        return {"backend": backend, "status": "failed", "error": str(e)}


@app.post("/backend/undrain")
def undrain_backend(backend: str):
    try:
        handle_backend_command("undrain-backend", backend)
        return {"backend": backend, "status": "undrained"}
    except Exception as e:
        return {"backend": backend, "status": "failed", "error": str(e)}


# ============================================================
#  UVICORN ENTRY POINT
# ============================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=6001,
        reload=False
    )

