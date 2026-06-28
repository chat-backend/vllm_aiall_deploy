# config.py
#!/usr/bin/env python3
"""
vLLM PRO+ Gateway – System Configuration (V4-PRODUCTION-CROSSPLATFORM)
----------------------------------------------------------------------
- API chuẩn OpenAI (vLLM)
- Không prefix
- Backend normalize
- Path normalize
- Health check /v1/models
- Hỗ trợ multi-backend
- Chạy được trên Windows + Linux
"""

from pathlib import Path
from dataclasses import dataclass
from typing import List
import os
import platform

print("[CONFIG] Loaded vLLM PRO+ Gateway configuration (V4-PRODUCTION-CROSSPLATFORM)")

# ============================================================
#  DOMAIN & EMAIL CONFIG
# ============================================================

DOMAINS: List[str] = ["api.aiallplatform.com"]
EMAIL: str = "openaimanage@gmail.com"

# ============================================================
#  BASE DIRECTORIES (CROSS-PLATFORM)
# ============================================================

if platform.system().lower().startswith("win"):
    CONFIG_DIR = Path("vllm_config")  # local folder for Windows dev
else:
    CONFIG_DIR = Path("/etc/vllm")    # production path for Linux

CONFIG_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_CONFIG_FILE = CONFIG_DIR / "project.conf"
API_KEY_FILE = CONFIG_DIR / "api_key"
BACKENDS_CONFIG = CONFIG_DIR / "backends.conf"
DRAIN_CONFIG = CONFIG_DIR / "backends.drain"

DEFAULT_BACKENDS = ["http://127.0.0.1:8000"]

# ============================================================
#  NGINX CONFIG PATHS (Linux only)
# ============================================================

if platform.system().lower().startswith("win"):
    UPSTREAM_FILE = Path("nginx_upstream.conf")
    LOG_FILE = Path("vllm_deploy.log")
else:
    UPSTREAM_FILE = Path("/etc/nginx/conf.d/vllm-upstream.conf")
    LOG_FILE = Path("/var/log/vllm-deploy.log")

# ============================================================
#  PROJECT CONFIG STRUCTURE
# ============================================================

@dataclass
class ProjectConfig:
    config_version: str = "1.0"

    base_url: str = os.getenv("VLLM_BASE_URL", "https://api.aiallplatform.com")

    api_chat: str = "/v1/chat/completions"
    api_completion: str = "/v1/completions"
    api_models: str = "/v1/models"

    api_key: str = ""
    token_secret: str = ""

    default_max_tokens: int = 1024
    default_min_tokens: int = 1
    default_temperature: float = 0.7
    default_top_p: float = 0.9

    def normalize(self, path: str) -> str:
        return path if path.startswith("/") else f"/{path}"

    def full(self, path: str) -> str:
        return f"{self.base_url}{self.normalize(path)}"

    @property
    def url_chat(self) -> str:
        return self.full(self.api_chat)

    @property
    def url_completion(self) -> str:
        return self.full(self.api_completion)

    @property
    def url_models(self) -> str:
        return self.full(self.api_models)

    def backend_url(self, backend: str, path: str) -> str:
        backend = backend if backend.startswith("http") else f"http://{backend}"
        return f"{backend}{self.normalize(path)}"

    def backend_health_url(self, backend: str) -> str:
        return self.backend_url(backend, self.api_models)

    @staticmethod
    def from_dict(data: dict) -> "ProjectConfig":
        return ProjectConfig(
            config_version=data.get("CONFIG_VERSION", "1.0"),
            base_url=data.get("BASE_URL", os.getenv("VLLM_BASE_URL", "https://api.aiallplatform.com")),

            api_chat=data.get("API_CHAT", "/v1/chat/completions"),
            api_completion=data.get("API_COMPLETION", "/v1/completions"),
            api_models=data.get("API_MODELS", "/v1/models"),

            api_key=data.get("API_KEY", ""),
            token_secret=data.get("TOKEN_SECRET", ""),

            default_max_tokens=int(data.get("DEFAULT_MAX_TOKENS", 1024)),
            default_min_tokens=int(data.get("DEFAULT_MIN_TOKENS", 1)),
            default_temperature=float(data.get("DEFAULT_TEMPERATURE", 0.7)),
            default_top_p=float(data.get("DEFAULT_TOP_P", 0.9)),
        )

__all__ = [
    "DOMAINS",
    "EMAIL",
    "CONFIG_DIR",
    "PROJECT_CONFIG_FILE",
    "API_KEY_FILE",
    "BACKENDS_CONFIG",
    "DRAIN_CONFIG",
    "DEFAULT_BACKENDS",
    "UPSTREAM_FILE",
    "LOG_FILE",
    "ProjectConfig",
]

