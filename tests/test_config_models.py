from __future__ import annotations

from math_digitizer.config.settings import AppConfig


def test_ocr_models_by_provider_roundtrip():
    cfg = AppConfig()
    cfg.ocr.models_by_provider["gemini"] = "gemini-3-flash-preview"
    dumped = cfg.model_dump()
    assert dumped["ocr"]["models_by_provider"]["gemini"] == "gemini-3-flash-preview"

    cfg2 = AppConfig.model_validate(dumped)
    assert cfg2.ocr.models_by_provider["gemini"] == "gemini-3-flash-preview"
