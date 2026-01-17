"""Configuration management for Math Digitizer.

Provides unified config handling with:
- Pydantic models for validation
- Keyring integration for secure API key storage
- Cross-platform config paths via platformdirs
"""

from math_digitizer.config.settings import (
    AppConfig,
    DeepseekConfig,
    GeminiConfig,
    OcrConfig,
    LayoutConfig,
    AutoRouterConfig,
    get_config,
    save_config,
    get_config_path,
)
from math_digitizer.config.secrets import (
    get_api_key,
    set_api_key,
    delete_api_key,
    list_api_keys,
    is_keyring_available,
    SecretKey,
)

__all__ = [
    # Settings
    "AppConfig",
    "DeepseekConfig",
    "GeminiConfig",
    "OcrConfig",
    "LayoutConfig",
    "AutoRouterConfig",
    "get_config",
    "save_config",
    "get_config_path",
    # Secrets
    "get_api_key",
    "set_api_key",
    "delete_api_key",
    "list_api_keys",
    "is_keyring_available",
    "SecretKey",
]
