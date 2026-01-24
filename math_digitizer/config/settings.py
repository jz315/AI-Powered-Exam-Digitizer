"""Configuration settings with Pydantic validation."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

try:
    from platformdirs import user_config_dir
except ImportError:
    # Fallback if platformdirs not installed
    def user_config_dir(appname: str, appauthor: str | None = None) -> str:
        return os.path.expanduser("~")

logger = logging.getLogger(__name__)

APP_NAME = "math-digitizer"
CONFIG_FILENAME = "config.json"
LEGACY_CONFIG_FILENAME = ".latex_template_gui.json"


def get_config_path() -> Path:
    """Get the configuration file path.
    
    Returns platform-appropriate config directory:
    - Windows: %APPDATA%/math-digitizer/config.json
    - macOS: ~/Library/Application Support/math-digitizer/config.json
    - Linux: ~/.config/math-digitizer/config.json
    """
    config_dir = Path(user_config_dir(APP_NAME))
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / CONFIG_FILENAME


def _get_legacy_config_path() -> Path:
    """Get legacy config path for migration."""
    return Path.home() / LEGACY_CONFIG_FILENAME


class DeepseekConfig(BaseModel):
    """DeepSeek OCR configuration."""
    
    provider: str = Field(default="modelverse", description="API provider: modelverse, siliconflow, custom")
    base_url: str = Field(default="", description="Custom base URL (for custom provider)")
    model: str = Field(default="", description="Model name override")
    keys_by_provider: dict[str, str] = Field(
        default_factory=dict,
        exclude=True,
        description="DEPRECATED: API keys should live in keyring, not config.json",
    )
    
    def get_base_url(self) -> str:
        """Resolve base URL based on provider."""
        if self.provider == "siliconflow":
            return "https://api.siliconflow.cn/v1"
        if self.provider == "custom" and self.base_url:
            return self.base_url
        return "https://api.modelverse.cn/v1/"


class OcrConfig(BaseModel):
    """OCR provider configuration."""

    provider: str = Field(default="gemini", description="OCR provider: gemini, aliyun")
    models_by_provider: dict[str, str] = Field(
        default_factory=dict,
        description="OCR model per provider (e.g. gemini/aliyun)",
    )
    default_models: dict[str, str] = Field(
        default_factory=lambda: {"gemini": "gemini-3-flash-preview", "aliyun": "qwen3-vl-plus"},
        description="Default OCR model per provider",
    )

    def get_model(self, provider: str) -> str:
        """Get model for provider, falling back to default."""
        return self.models_by_provider.get(provider) or self.default_models.get(provider, "")


class AutoRouterConfig(BaseModel):
    """Auto router configuration."""
    
    outside_ratio: float = Field(default=0.01, ge=0.0, le=1.0)
    min_text_ratio: float = Field(default=0.0005, ge=0.0, le=1.0)
    min_component_area: int = Field(default=30, ge=0)
    gemini_probe: bool = Field(default=False)
    gemini_model: str = Field(default="gemini-2.5-flash-lite")
    router_mode: str = Field(default="second_pass", description="any, textness, second_pass, gemini")


class LayoutConfig(BaseModel):
    """Layout processing configuration."""
    
    model: str = Field(default="auto_router", description="Layout model key")
    threads: int = Field(default=1, ge=1, le=32)
    dpi: int = Field(default=200, ge=72, le=600)


class AppConfig(BaseModel):
    """Root application configuration."""
    
    deepseek: DeepseekConfig = Field(default_factory=DeepseekConfig)
    ocr: OcrConfig = Field(default_factory=OcrConfig)
    layout: LayoutConfig = Field(default_factory=LayoutConfig)
    auto_router: AutoRouterConfig = Field(default_factory=AutoRouterConfig)
    
    # Window state (optional)
    window_geometry: str = Field(default="1200x800")
    
    class Config:
        extra = "ignore"  # Ignore unknown fields during migration


def _migrate_legacy_config(legacy_data: dict) -> AppConfig:
    """Migrate from legacy config format to new format."""
    config = AppConfig()
    
    # DeepSeek
    if provider := legacy_data.get("deepseek_provider"):
        config.deepseek.provider = str(provider)
    if base_url := legacy_data.get("deepseek_base_url"):
        config.deepseek.base_url = str(base_url)
    
    # Layout
    if model := legacy_data.get("layout_model"):
        config.layout.model = str(model)
    if threads := legacy_data.get("layout_threads"):
        try:
            config.layout.threads = int(threads)
        except (ValueError, TypeError):
            pass
    
    # Auto Router
    if v := legacy_data.get("auto_outside_ratio"):
        try:
            config.auto_router.outside_ratio = float(v)
        except (ValueError, TypeError):
            pass
    if v := legacy_data.get("auto_min_text_ratio"):
        try:
            config.auto_router.min_text_ratio = float(v)
        except (ValueError, TypeError):
            pass
    if v := legacy_data.get("auto_min_component_area"):
        try:
            config.auto_router.min_component_area = int(v)
        except (ValueError, TypeError):
            pass
    if v := legacy_data.get("auto_gemini_probe"):
        config.auto_router.gemini_probe = bool(v)
    if v := legacy_data.get("auto_gemini_model"):
        config.auto_router.gemini_model = str(v)
    if v := legacy_data.get("auto_router_mode"):
        config.auto_router.router_mode = str(v)
    
    return config


def get_config() -> AppConfig:
    """Load configuration from file.
    
    Attempts to load from:
    1. New config path (platformdirs)
    2. Legacy config path (~/.latex_template_gui.json) with migration
    3. Returns defaults if neither exists
    """
    config_path = get_config_path()
    legacy_path = _get_legacy_config_path()
    
    # Try new config first
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            config = AppConfig.model_validate(data)
            # Scrub legacy plain-text keys if they exist in persisted config.
            if config.deepseek.keys_by_provider:
                config.deepseek.keys_by_provider = {}
                save_config(config)
            return config
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
    
    # Try legacy config and migrate
    if legacy_path.exists():
        try:
            with open(legacy_path, "r", encoding="utf-8") as f:
                legacy_data = json.load(f)
            config = _migrate_legacy_config(legacy_data)
            # Save to new location
            save_config(config)
            logger.info(f"Migrated config from {legacy_path} to {config_path}")
            return config
        except Exception as e:
            logger.warning(f"Failed to migrate legacy config: {e}")
    
    return AppConfig()


def save_config(config: AppConfig) -> None:
    """Save configuration to file."""
    config_path = get_config_path()
    try:
        tmp_path = config_path.with_suffix(config_path.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, config_path)
    except Exception as e:
        try:
            if "tmp_path" in locals() and tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        logger.error(f"Failed to save config to {config_path}: {e}")
        raise
