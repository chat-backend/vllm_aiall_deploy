# config_loader.py
#!/usr/bin/env python3
"""
Runtime Config Loader for AIALL vLLM Gateway (V4-FULL-SYNC)
-----------------------------------------------------------
- Đọc cấu hình runtime từ project.conf + api_key
- Validate đầy đủ
- Chuẩn hóa URL cho API vLLM / OpenAI
"""

from pathlib import Path
from typing import Dict
from config import PROJECT_CONFIG_FILE, API_KEY_FILE, ProjectConfig


# ============================================================
#  LOAD project.conf
# ============================================================

def load_project_conf() -> Dict[str, str]:
    """Đọc file project.conf và trả về dict."""
    if not PROJECT_CONFIG_FILE.exists():
        raise FileNotFoundError(f"Missing project config: {PROJECT_CONFIG_FILE}")

    data = {}
    for line in PROJECT_CONFIG_FILE.read_text().splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip()

    if not data:
        raise ValueError("project.conf is empty or invalid")

    required = [
        "BASE_URL",
        "API_CHAT",
        "API_COMPLETION",
        "API_MODELS",
        "TOKEN_SECRET",
    ]

    for key in required:
        if key not in data or not data[key]:
            raise ValueError(f"Missing required config key: {key}")

    return data


# ============================================================
#  LOAD api_key
# ============================================================

def load_api_key() -> str:
    """Đọc file api_key và trả về API_KEY thật."""
    if not API_KEY_FILE.exists():
        raise FileNotFoundError(f"Missing API key file: {API_KEY_FILE}")

    content = API_KEY_FILE.read_text().strip()

    if "=" in content:
        name, key = content.split("=", 1)
        name = name.strip()
        key = key.strip()

        if name != "AIALL_API_KEY":
            raise ValueError(f"Unexpected key name in api_key file: {name}")

        return key

    return content


# ============================================================
#  LOAD FULL RUNTIME CONFIG
# ============================================================

def load_runtime_config() -> ProjectConfig:
    """
    Trả về ProjectConfig hoàn chỉnh:
    - BASE_URL
    - URL_CHAT
    - URL_COMPLETION
    - URL_MODELS
    - DEFAULT_MAX_TOKENS
    - DEFAULT_TEMPERATURE
    - API_KEY
    - TOKEN_SECRET
    """

    data = load_project_conf()
    api_key = load_api_key()

    # Ghi đè API_KEY từ file api_key
    data["API_KEY"] = api_key

    # Chuẩn hóa URL
    base = data["BASE_URL"].rstrip("/")

    data["URL_CHAT"] = base + data["API_CHAT"]
    data["URL_COMPLETION"] = base + data["API_COMPLETION"]
    data["URL_MODELS"] = base + data["API_MODELS"]

    return ProjectConfig.from_dict(data)


