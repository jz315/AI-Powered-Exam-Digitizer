from __future__ import annotations

from typing import TYPE_CHECKING

from math_digitizer.ocr.base import (
    DEFAULT_LAYOUT_MODEL,
    LAYOUT_MODEL_LABELS,
    create_layout_extractor,
    layout_model_label_from_key,
    layout_model_key_from_label,
    ensure_model_exists,
    parse_page_range,
)

if TYPE_CHECKING:
    from math_digitizer.ocr.extractors import (
        DocLayoutExtractor,
        PPDocLayoutPlusExtractor,
        DeepseekOcrLayoutExtractor,
        AutoRouterLayoutExtractor,
    )

__all__ = [
    "DEFAULT_LAYOUT_MODEL",
    "LAYOUT_MODEL_LABELS",
    "create_layout_extractor",
    "layout_model_label_from_key",
    "layout_model_key_from_label",
    "ensure_model_exists",
    "parse_page_range",
    "DocLayoutExtractor",
    "PPDocLayoutPlusExtractor",
    "DeepseekOcrLayoutExtractor",
    "AutoRouterLayoutExtractor",
]

_extractor_classes = [
    "DocLayoutExtractor",
    "PPDocLayoutPlusExtractor",
    "DeepseekOcrLayoutExtractor",
    "AutoRouterLayoutExtractor",
]


def __getattr__(name: str):
    if name in _extractor_classes:
        from math_digitizer.ocr import extractors
        return getattr(extractors, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
