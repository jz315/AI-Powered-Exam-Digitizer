from __future__ import annotations

import json
import customtkinter as ctk

try:
    from math_digitizer.core.generator import ExamGenerator
    from math_digitizer.core.validator import ValidationIssue, extract_first_latex_error, validate_json_and_latex
    from math_digitizer.tools.image_preprocess import ImagePreprocessTool
except ImportError:
    class ExamGenerator:
        def __init__(self, template_file): pass
        def process_data(self, d): return d
        def render(self, d, output_tex): return True
        def compile_pdf(self, path): return True
    
    class ValidationIssue:
        def __init__(self, severity, line, col, message, context, path=""):
            self.severity = severity
            self.line = line
            self.col = col
            self.message = message
            self.context = context
            self.path = path
            
    def extract_first_latex_error(*args): return None
    def validate_json_and_latex(text): return json.loads(text) if text else {}, []
    
    class ImagePreprocessTool(ctk.CTkToplevel):
        def __init__(self, parent, theme, on_close): super().__init__(parent); self.on_close=on_close
