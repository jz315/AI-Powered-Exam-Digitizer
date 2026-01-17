from __future__ import annotations

import os
import threading

import customtkinter as ctk

from math_digitizer.utils.paths import get_resource_path
from math_digitizer.gui.services.deps import ExamGenerator, validate_json_and_latex
from math_digitizer.gui.components import UiMixin, PdfOcrMixin, EditorMixin, LogMixin, GenerationMixin, StatusMixin
from math_digitizer.gui.theme import Theme

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class PremiumExamApp(ctk.CTk, UiMixin, PdfOcrMixin, EditorMixin, LogMixin, GenerationMixin, StatusMixin):
    def __init__(self):
        super().__init__()
        Theme.init_fonts(self, base_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

        # 1. 窗口基础设置
        self.title("Math Digitizer Pro - 数学试卷数字化工具")
        self.geometry("1200x800")
        self.configure(fg_color=Theme.COLOR_BG_MAIN)
        
        # 网格布局配置
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Header
        self.grid_rowconfigure(1, weight=1) # Main Content

        # 初始化业务逻辑
        self.generator = ExamGenerator(template_file=str(get_resource_path("resources/exam_template.txt")))
        self.prompt_file = str(get_resource_path("resources/prompt.md"))
        self._image_tool = None
        self._pdf_path = ""
        self._pdf_ocr_last_text = ""
        self._pdf_ocr_last_dir = ""
        self._pdf_ocr_preview = None
        self._log_lock = threading.Lock()
        self._log_path = self._init_log_file()
        self._layout_extractors = {}

        # === 界面初始化 ===
        self.setup_header()       # 顶部标题栏
        self.setup_main_tabs()    # 核心：选项卡布局

        # 校验线程逻辑
        self._validation_after_id = None
        self._last_issues = []
        self._validation_seq = 0
        self._validation_lock = threading.Lock()
        self._validation_pending_seq = 0
        self._validation_pending_text = ""
        self._validation_request_event = threading.Event()
        self._validation_stop_event = threading.Event()
        self._validation_worker: threading.Thread | None = None

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._ensure_validation_worker()

    def _on_close(self):
        try:
            if self._image_tool is not None and self._image_tool.winfo_exists():
                self._image_tool.destroy()
            self._validation_stop_event.set()
            self._validation_request_event.set()
            self._save_pdf_ocr_config()
        except Exception:
            pass
        self.destroy()

    def _ensure_validation_worker(self):
        if self._validation_worker is not None and self._validation_worker.is_alive():
            return
        self._validation_worker = threading.Thread(target=self._validation_worker_loop, daemon=True)
        self._validation_worker.start()

    def _validation_worker_loop(self):
        while not self._validation_stop_event.is_set():
            self._validation_request_event.wait()
            self._validation_request_event.clear()
            if self._validation_stop_event.is_set(): break

            with self._validation_lock:
                seq = self._validation_pending_seq
                json_str = self._validation_pending_text

            data, issues = validate_json_and_latex(json_str)

            def apply_result():
                if self._validation_stop_event.is_set(): return
                if seq != self._validation_seq: return
                self._set_issues_panel(issues)
                if data and isinstance(data, dict):
                    try:
                        new_t = data.get("meta", {}).get("title")
                        if new_t and not self.entry_filename.get().strip():
                            self.entry_filename.delete(0, "end")
                            self.entry_filename.insert(0, str(new_t))
                    except Exception: pass

            try: self.after(0, apply_result)
            except Exception: pass
