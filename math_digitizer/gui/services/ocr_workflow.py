from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from math_digitizer.config import get_config
from math_digitizer.ocr import (
    DEFAULT_LAYOUT_MODEL,
    layout_model_key_from_label,
    layout_model_label_from_key,
)
from math_digitizer.gui.services.ocr_service import LayoutJob, OcrJob, OcrService


@dataclass
class LayoutContext:
    model_key: str
    model_label: str
    deepseek_provider: str
    deepseek_key: str
    deepseek_base_url: str | None
    auto_router_config: dict | None


class OcrWorkflow:
    def __init__(self, ocr_service: OcrService, config_provider: Callable[[], object] = get_config) -> None:
        self._ocr_service = ocr_service
        self._get_config = config_provider

    def build_auto_router_config(
        self,
        *,
        enabled: bool,
        outside_ratio: str,
        min_text_ratio: str,
        min_component_area: str,
        use_gemini_probe: bool,
        gemini_api_key: str,
        gemini_model: str,
        router_mode: str,
    ) -> dict | None:
        if not enabled:
            return None
        config = self._get_config()
        defaults = config.auto_router
        return {
            "text_outside_ratio": _parse_float(outside_ratio, defaults.outside_ratio),
            "min_text_ratio": _parse_float(min_text_ratio, defaults.min_text_ratio),
            "min_component_area": _parse_int(min_component_area, defaults.min_component_area),
            "use_gemini_probe": bool(use_gemini_probe),
            "gemini_api_key": gemini_api_key,
            "gemini_model": gemini_model or defaults.gemini_model,
            "router_mode": router_mode or defaults.router_mode,
        }

    def resolve_layout_context(
        self,
        *,
        layout_model_label: str,
        deepseek_provider: str,
        deepseek_key: str,
        deepseek_base_url: str | None,
        auto_router_config: dict | None,
    ) -> LayoutContext:
        model_key = layout_model_key_from_label(layout_model_label) or DEFAULT_LAYOUT_MODEL
        model_label = layout_model_label_from_key(model_key)

        if model_key in ("deepseek_ocr", "auto_router") and not deepseek_key:
            raise RuntimeError("请先填写 DeepSeek API Key")
        if deepseek_provider == "custom" and not deepseek_base_url:
            raise RuntimeError("自定义提供商需要填写 Base URL")

        return LayoutContext(
            model_key=model_key,
            model_label=model_label,
            deepseek_provider=deepseek_provider,
            deepseek_key=deepseek_key,
            deepseek_base_url=deepseek_base_url,
            auto_router_config=auto_router_config,
        )

    def build_layout_job(
        self,
        *,
        pdf_path: str,
        dpi: int,
        page_range: str,
        layout_threads: int,
        output_root: Path,
        ctx: LayoutContext,
    ) -> LayoutJob:
        return LayoutJob(
            pdf_path=pdf_path,
            layout_model_key=ctx.model_key,
            deepseek_provider=ctx.deepseek_provider,
            deepseek_key=ctx.deepseek_key,
            deepseek_base_url=ctx.deepseek_base_url,
            auto_router_config=ctx.auto_router_config,
            dpi=dpi,
            page_range=page_range,
            layout_threads=layout_threads,
            output_root=output_root,
        )

    def build_ocr_job(
        self,
        *,
        pdf_path: str,
        dpi: int,
        page_range: str,
        layout_threads: int,
        output_root: Path,
        ocr_provider: str,
        ocr_api_key: str,
        ocr_model: str,
        prompt: str,
        ctx: LayoutContext,
    ) -> OcrJob:
        return OcrJob(
            pdf_path=pdf_path,
            layout_model_key=ctx.model_key,
            deepseek_provider=ctx.deepseek_provider,
            deepseek_key=ctx.deepseek_key,
            deepseek_base_url=ctx.deepseek_base_url,
            auto_router_config=ctx.auto_router_config,
            dpi=dpi,
            page_range=page_range,
            layout_threads=layout_threads,
            ocr_provider=ocr_provider,
            ocr_api_key=ocr_api_key,
            ocr_model=ocr_model,
            prompt=prompt,
            output_root=output_root,
        )

    @property
    def ocr_service(self) -> OcrService:
        return self._ocr_service


def _parse_float(raw: str, fallback: float) -> float:
    try:
        return float(str(raw).strip() or str(fallback))
    except Exception:
        return fallback


def _parse_int(raw: str, fallback: int) -> int:
    try:
        return int(float(str(raw).strip() or str(fallback)))
    except Exception:
        return fallback
