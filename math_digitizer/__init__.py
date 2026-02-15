"""Math Digitizer - 智能数学试卷排版工具"""

__version__ = "0.1.0"

# Convenience imports
from math_digitizer.core.generator import ExamGenerator
from math_digitizer.core.validator import validate_json_and_latex
try:
    from math_digitizer.ocr.base import create_layout_extractor
except Exception:  # Optional OCR deps may be missing in minimal installs
    create_layout_extractor = None
