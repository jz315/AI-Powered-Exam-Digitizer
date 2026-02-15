"""Math Digitizer - 智能数学试卷排版工具"""

__version__ = "0.1.0"

# Convenience imports (core only - OCR is lazy-loaded to avoid slow torch import)
from math_digitizer.core.generator import ExamGenerator
from math_digitizer.core.validator import validate_json_and_latex

__all__ = ["ExamGenerator", "validate_json_and_latex", "__version__"]


def __getattr__(name: str):
    if name == "create_layout_extractor":
        try:
            from math_digitizer.ocr.base import create_layout_extractor
            return create_layout_extractor
        except Exception:
            return None
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
