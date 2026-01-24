"""Web-specific settings API - separate from Python GUI (output/web_config.json)."""

from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("web_settings")

BASE_DIR = Path(__file__).parent.parent.parent.parent
OUTPUT_DIR = BASE_DIR / "output"
WEB_CONFIG_FILE = OUTPUT_DIR / "web_config.json"
WEB_SECRETS_FILE = OUTPUT_DIR / ".web_secrets.json"


class LLMConfig(BaseModel):
    provider: str = "deepseek"
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com/v1"


class WebConfigModel(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    theme: str = "dark"
    auto_save: bool = True


class ApiKeysStatus(BaseModel):
    llm: bool = False
    llm_preview: str = ""
    gemini: bool = False
    gemini_preview: str = ""
    aliyun: bool = False
    aliyun_preview: str = ""
    deepseek_modelverse: bool = False
    deepseek_modelverse_preview: str = ""
    deepseek_siliconflow: bool = False
    deepseek_siliconflow_preview: str = ""
    deepseek_custom: bool = False
    deepseek_custom_preview: str = ""


class WebConfigResponse(BaseModel):
    llm: LLMConfig
    theme: str
    auto_save: bool
    has_api_key: bool = False
    api_key_preview: str = ""
    api_keys: ApiKeysStatus = Field(default_factory=ApiKeysStatus)


class WebConfigUpdateRequest(BaseModel):
    llm: Optional[LLMConfig] = None
    theme: Optional[str] = None
    auto_save: Optional[bool] = None


class SetKeyRequest(BaseModel):
    api_key: str
    key_type: str = "llm"


class SetKeyResponse(BaseModel):
    success: bool
    message: str
    preview: str = ""


class TestKeyRequest(BaseModel):
    api_key: Optional[str] = None


class TestKeyResponse(BaseModel):
    success: bool
    message: str


def _ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _load_config() -> WebConfigModel:
    _ensure_dirs()
    if not WEB_CONFIG_FILE.exists():
        return WebConfigModel()
    try:
        with open(WEB_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return WebConfigModel(**data)
    except Exception as e:
        logger.warning(f"Failed to load web config: {e}")
        return WebConfigModel()


def _save_config(config: WebConfigModel):
    _ensure_dirs()
    with open(WEB_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, ensure_ascii=False, indent=2)
    logger.info(f"Saved web config to {WEB_CONFIG_FILE}")


def _obfuscate(value: str) -> str:
    return base64.b64encode(value.encode()).decode()


def _deobfuscate(value: str) -> str:
    try:
        return base64.b64decode(value.encode()).decode()
    except Exception:
        return ""


def _load_api_key(key_type: str = "llm") -> Optional[str]:
    if not WEB_SECRETS_FILE.exists():
        return None
    try:
        with open(WEB_SECRETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            key_name = f"{key_type}_api_key" if key_type != "llm" else "llm_api_key"
            obfuscated = data.get(key_name, "")
            if obfuscated:
                return _deobfuscate(obfuscated)
    except Exception as e:
        logger.warning(f"Failed to load API key: {e}")
    return None


def _save_api_key(key: str, key_type: str = "llm"):
    _ensure_dirs()
    data = {}
    if WEB_SECRETS_FILE.exists():
        try:
            with open(WEB_SECRETS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    
    key_name = f"{key_type}_api_key" if key_type != "llm" else "llm_api_key"
    data[key_name] = _obfuscate(key)
    
    with open(WEB_SECRETS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {key_type} API key to secrets file")


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return key[:3] + "****" + key[-4:]


def get_web_api_key(key_type: str = "llm") -> Optional[str]:
    return _load_api_key(key_type)


def get_web_api_key_by_type(key_type: str) -> Optional[str]:
    env_map = {
        "gemini": "GEMINI_API_KEY",
        "aliyun": "DASHSCOPE_API_KEY", 
        "deepseek_modelverse": "DEEPSEEK_API_KEY",
        "deepseek_siliconflow": "DEEPSEEK_API_KEY",
        "deepseek_custom": "DEEPSEEK_API_KEY",
        "llm": None,
    }
    env_var = env_map.get(key_type)
    if env_var:
        env_key = os.environ.get(env_var, "").strip()
        if env_key:
            return env_key
    return _load_api_key(key_type)


def get_web_config() -> WebConfigModel:
    return _load_config()


def _build_api_keys_status() -> ApiKeysStatus:
    return ApiKeysStatus(
        llm=bool(_load_api_key("llm")),
        llm_preview=_mask_key(_load_api_key("llm") or ""),
        gemini=bool(_load_api_key("gemini")),
        gemini_preview=_mask_key(_load_api_key("gemini") or ""),
        aliyun=bool(_load_api_key("aliyun")),
        aliyun_preview=_mask_key(_load_api_key("aliyun") or ""),
        deepseek_modelverse=bool(_load_api_key("deepseek_modelverse")),
        deepseek_modelverse_preview=_mask_key(_load_api_key("deepseek_modelverse") or ""),
        deepseek_siliconflow=bool(_load_api_key("deepseek_siliconflow")),
        deepseek_siliconflow_preview=_mask_key(_load_api_key("deepseek_siliconflow") or ""),
        deepseek_custom=bool(_load_api_key("deepseek_custom")),
        deepseek_custom_preview=_mask_key(_load_api_key("deepseek_custom") or ""),
    )


def register_web_settings_routes(app):
    logger.info("Registering web settings routes")
    
    @app.get("/api/web-settings", response_model=WebConfigResponse)
    async def get_web_settings():
        logger.debug("GET /api/web-settings")
        config = _load_config()
        api_key = _load_api_key("llm")
        
        return WebConfigResponse(
            llm=config.llm,
            theme=config.theme,
            auto_save=config.auto_save,
            has_api_key=bool(api_key),
            api_key_preview=_mask_key(api_key) if api_key else "",
            api_keys=_build_api_keys_status()
        )
    
    @app.put("/api/web-settings", response_model=WebConfigResponse)
    async def update_web_settings(request: WebConfigUpdateRequest):
        logger.info(f"PUT /api/web-settings: {request}")
        config = _load_config()
        
        if request.llm is not None:
            config.llm = request.llm
        if request.theme is not None:
            config.theme = request.theme
        if request.auto_save is not None:
            config.auto_save = request.auto_save
        
        _save_config(config)
        
        api_key = _load_api_key("llm")
        return WebConfigResponse(
            llm=config.llm,
            theme=config.theme,
            auto_save=config.auto_save,
            has_api_key=bool(api_key),
            api_key_preview=_mask_key(api_key) if api_key else "",
            api_keys=_build_api_keys_status()
        )
    
    @app.post("/api/web-settings/set-key", response_model=SetKeyResponse)
    async def set_api_key(request: SetKeyRequest):
        logger.info(f"POST /api/web-settings/set-key type={request.key_type}")
        
        if not request.api_key or not request.api_key.strip():
            return SetKeyResponse(success=False, message="API Key 不能为空")
        
        key = request.api_key.strip()
        key_type = request.key_type if request.key_type in ["llm", "gemini", "aliyun", "deepseek"] else "llm"
        _save_api_key(key, key_type)
        
        key_names = {"llm": "LLM", "gemini": "Gemini", "aliyun": "阿里云", "deepseek": "DeepSeek"}
        return SetKeyResponse(
            success=True,
            message=f"{key_names.get(key_type, key_type)} API Key 已保存",
            preview=_mask_key(key)
        )
    
    @app.post("/api/web-settings/test-key", response_model=TestKeyResponse)
    async def test_api_key(request: TestKeyRequest):
        logger.info("POST /api/web-settings/test-key")
        
        api_key = request.api_key.strip() if request.api_key else None
        if not api_key:
            api_key = _load_api_key()
        
        if not api_key:
            return TestKeyResponse(success=False, message="未提供或未存储 API Key")
        
        config = _load_config()
        base_url = config.llm.base_url
        model = config.llm.model
        
        try:
            from openai import OpenAI
        except ImportError:
            return TestKeyResponse(success=False, message="openai 库未安装")
        
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Say 'OK' if you can read this."}],
                max_tokens=10,
                temperature=0,
            )
            
            result = response.choices[0].message.content or ""
            result = result.strip()
            logger.info(f"API test successful: {result}")
            
            return TestKeyResponse(success=True, message=f"连接成功！模型响应: {result}")
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"API test failed: {error_msg}")
            
            if "401" in error_msg or "Unauthorized" in error_msg:
                return TestKeyResponse(success=False, message="API Key 无效或已过期")
            if "404" in error_msg:
                return TestKeyResponse(success=False, message=f"模型 {model} 不存在或 API 地址错误")
            if "connection" in error_msg.lower():
                return TestKeyResponse(success=False, message="无法连接到 API 服务器")
            
            return TestKeyResponse(success=False, message=f"验证失败: {error_msg[:100]}")
