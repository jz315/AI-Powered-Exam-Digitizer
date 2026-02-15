from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from math_digitizer.ocr.extractors.yolo import DocLayoutExtractor
    from math_digitizer.ocr.extractors.paddle import PPDocLayoutPlusExtractor
    from math_digitizer.ocr.extractors.deepseek import DeepseekOcrLayoutExtractor
    from math_digitizer.ocr.extractors.auto_router import AutoRouterLayoutExtractor

__all__ = [
    "DocLayoutExtractor",
    "PPDocLayoutPlusExtractor",
    "DeepseekOcrLayoutExtractor",
    "AutoRouterLayoutExtractor",
]

_lazy_imports = {
    "DocLayoutExtractor": "math_digitizer.ocr.extractors.yolo",
    "PPDocLayoutPlusExtractor": "math_digitizer.ocr.extractors.paddle",
    "DeepseekOcrLayoutExtractor": "math_digitizer.ocr.extractors.deepseek",
    "AutoRouterLayoutExtractor": "math_digitizer.ocr.extractors.auto_router",
}


def __getattr__(name: str):
    if name in _lazy_imports:
        import importlib
        module = importlib.import_module(_lazy_imports[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
