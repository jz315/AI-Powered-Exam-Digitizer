from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from math_digitizer.config import get_config, save_config

# --- Models ---

class SettingsUpdateRequest(BaseModel):
    ocr_provider: Optional[str] = None
    ocr_model: Optional[str] = None
    gemini_key: Optional[str] = None
    aliyun_key: Optional[str] = None
    layout_model: Optional[str] = None
    layout_threads: Optional[int] = None
    pdf_dpi: Optional[int] = None
    deepseek_provider: Optional[str] = None
    deepseek_key: Optional[str] = None
    deepseek_base_url: Optional[str] = None
    theme: Optional[str] = None
    auto_save: Optional[bool] = None

class SettingsResponse(BaseModel):
    ocr_provider: str
    ocr_model: Optional[str]
    layout_model: str
    layout_threads: int
    pdf_dpi: int
    deepseek_provider: str
    deepseek_base_url: Optional[str]
    theme: str
    auto_save: bool
    # We do NOT return keys for security

# --- API Routes ---

def register_settings_routes(app):
    
    @app.get("/api/settings", response_model=SettingsResponse)
    async def get_settings():
        """Get current application settings."""
        config = get_config()
        
        # Map config object to response model
        # Note: We need to adapt the structure as our internal Config model 
        # might differ from the flat API response structure
        return {
            "ocr_provider": config.ocr.provider,
            "ocr_model": (config.ocr.models_by_provider or {}).get(config.ocr.provider),
            "layout_model": config.layout.model or "doclayout_yolo",
            "layout_threads": config.layout.threads or 4,
            "pdf_dpi": config.layout.dpi or 200,
            "deepseek_provider": config.deepseek.provider,
            "deepseek_base_url": config.deepseek.base_url,
            "theme": "system", # TODO: Persist in config
            "auto_save": True  # TODO: Persist in config
        }

    @app.put("/api/settings", response_model=SettingsResponse)
    async def update_settings(settings: SettingsUpdateRequest):
        """Update application settings."""
        try:
            config = get_config()
            
            if settings.ocr_provider:
                config.ocr.provider = settings.ocr_provider
            if settings.ocr_model:
                if not isinstance(config.ocr.models_by_provider, dict):
                    config.ocr.models_by_provider = {}
                config.ocr.models_by_provider[config.ocr.provider] = settings.ocr_model
            
            if settings.layout_model:
                config.layout.model = settings.layout_model
            if settings.layout_threads is not None:
                config.layout.threads = settings.layout_threads
            if settings.pdf_dpi is not None:
                config.layout.dpi = settings.pdf_dpi
                
            if settings.deepseek_provider:
                config.deepseek.provider = settings.deepseek_provider
            if settings.deepseek_base_url:
                config.deepseek.base_url = settings.deepseek_base_url
                
            # Handle Keys securely (if provided)
            # In a real app, use keyring or encrypted storage. 
            # Here we might update env vars or config file for simplicity in this demo.
            if settings.gemini_key:
                # set_api_key(SecretKey.GEMINI, settings.gemini_key)
                pass 
            
            save_config(config)
            
            return await get_settings()
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save settings: {e}")
