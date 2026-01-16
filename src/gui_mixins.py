from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pyperclip

from gui_deps import ImagePreprocessTool, extract_first_latex_error, validate_json_and_latex
from gui_ocr import call_gemini_ocr
from gui_theme import Theme
from layout_engine import (
    DEFAULT_LAYOUT_MODEL,
    LAYOUT_MODEL_LABELS,
    create_layout_extractor,
    layout_model_key_from_label,
    layout_model_label_from_key,
)


class CollapsibleFrame(ctk.CTkFrame):
    """可折叠面板组件 - 用于隐藏高级设置"""

    def __init__(
        self,
        parent,
        title: str = "高级设置",
        expanded: bool = False,
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._expanded = expanded

        self._header = ctk.CTkFrame(self, fg_color="transparent", cursor="hand2")
        self._header.pack(fill="x")

        self._arrow = ctk.CTkLabel(
            self._header,
            text="▶" if not expanded else "▼",
            width=20,
            font=(Theme.FONT_FAMILY[0], 12),
            text_color=Theme.COLOR_TEXT_SECONDARY,
        )
        self._arrow.pack(side="left", padx=(0, 5))

        self._title_label = ctk.CTkLabel(
            self._header,
            text=title,
            font=(Theme.FONT_FAMILY[0], 13),
            text_color=Theme.COLOR_TEXT_SECONDARY,
        )
        self._title_label.pack(side="left")

        self._content = ctk.CTkFrame(self, fg_color="transparent")
        if expanded:
            self._content.pack(fill="x", pady=(8, 0))

        self._header.bind("<Button-1>", self._toggle)
        self._arrow.bind("<Button-1>", self._toggle)
        self._title_label.bind("<Button-1>", self._toggle)

    @property
    def content(self) -> ctk.CTkFrame:
        """返回内容区域供外部添加控件"""
        return self._content

    def _toggle(self, event=None):
        self._expanded = not self._expanded
        if self._expanded:
            self._arrow.configure(text="▼")
            self._content.pack(fill="x", pady=(8, 0))
        else:
            self._arrow.configure(text="▶")
            self._content.pack_forget()

    def expand(self):
        if not self._expanded:
            self._toggle()

    def collapse(self):
        if self._expanded:
            self._toggle()


class UiMixin:
    def setup_header(self):
        """顶部状态栏"""
        header_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew", padx=Theme.PAD_OUTER, pady=(15, 5))
        
        # 标题
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="📐 数学试卷数字化工具", font=(Theme.FONT_FAMILY_BOLD[0], 20), text_color=Theme.COLOR_TEXT_PRIMARY).pack(side="left")
        ctk.CTkLabel(title_box, text=" v2.0", font=(Theme.FONT_FAMILY[0], 12), text_color=Theme.COLOR_TEXT_SECONDARY).pack(side="left", pady=(8,0))

        # GPU/CPU 指示器
        gpu_available, gpu_info = self._detect_gpu()
        gpu_text = f"🚀 {gpu_info}" if gpu_available else "💻 CPU"
        gpu_color = "#22c55e" if gpu_available else Theme.COLOR_TEXT_SECONDARY
        self.gpu_label = ctk.CTkLabel(
            header_frame, text=gpu_text,
            font=(Theme.FONT_FAMILY[0], 12),
            text_color=gpu_color
        )
        self.gpu_label.pack(side="right", padx=(10, 0))

        # 状态指示器
        self.status_label = ctk.CTkLabel(header_frame, text="Ready", font=(Theme.FONT_FAMILY[0], 13), text_color=Theme.COLOR_TEXT_SECONDARY)
        self.status_label.pack(side="right")

    def _detect_gpu(self):
        try:
            import torch
            if torch.cuda.is_available():
                name = torch.cuda.get_device_name(0)
                name = name.strip() if isinstance(name, str) else "GPU"
                return True, f"GPU {name}"
        except Exception:
            pass
        return False, "CPU"

    def setup_main_tabs(self):
        """主要的三段式工作流布局"""
        self.tabview = ctk.CTkTabview(self, corner_radius=Theme.CORNER_RADIUS_L)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=Theme.PAD_OUTER, pady=(0, Theme.PAD_OUTER))
        
        # 创建三个主要选项卡
        self.tab_ocr = self.tabview.add(" 1. 智能提取 (OCR) ")
        self.tab_edit = self.tabview.add(" 2. 数据编辑 (Editor) ")
        self.tab_export = self.tabview.add(" 3. 导出与工具 (Export) ")

        # 配置 Tab 内部布局
        self.tab_ocr.grid_columnconfigure(0, weight=1)
        self.tab_edit.grid_columnconfigure(0, weight=1)
        self.tab_edit.grid_rowconfigure(1, weight=1) # 编辑器占满
        self.tab_export.grid_columnconfigure(0, weight=1)
        self.tab_export.grid_columnconfigure(1, weight=1)

        # 填充内容
        self._init_ocr_tab_ui()
        self._init_editor_tab_ui()
        self._init_export_tab_ui()

    def _init_ocr_tab_ui(self):
        container = ctk.CTkFrame(self.tab_ocr, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        container.grid_columnconfigure(0, weight=2)
        container.grid_columnconfigure(1, weight=3)
        container.grid_rowconfigure(0, weight=1)

        left_panel = ctk.CTkFrame(container, fg_color=Theme.COLOR_BG_PANEL, corner_radius=Theme.CORNER_RADIUS_L)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        scroll_frame = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(scroll_frame, text="🛠️ 基础配置", font=(Theme.FONT_FAMILY_BOLD[0], 16)).pack(anchor="w", padx=15, pady=(15, 10))
        
        key_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        key_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(key_frame, text="Gemini Key:", width=90, anchor="w").pack(side="left")
        env_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.entry_gemini_key = ctk.CTkEntry(key_frame, placeholder_text="粘贴 API Key...", show="•")
        self.entry_gemini_key.pack(side="left", fill="x", expand=True)
        if env_key:
            self.entry_gemini_key.insert(0, env_key)
        self.entry_gemini_key.bind("<FocusOut>", lambda _e: self._save_pdf_ocr_config())

        layout_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        layout_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(layout_frame, text="Layout:", width=90, anchor="w").pack(side="left")
        self.layout_model_var = tk.StringVar(value=layout_model_label_from_key(DEFAULT_LAYOUT_MODEL))
        layout_labels = list(LAYOUT_MODEL_LABELS.values())
        self.layout_model_menu = ctk.CTkOptionMenu(
            layout_frame,
            values=layout_labels,
            variable=self.layout_model_var,
            command=lambda _val: self._save_pdf_ocr_config(),
        )
        self.layout_model_menu.pack(side="left", fill="x", expand=True)

        threads_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        threads_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(threads_frame, text="Layout Threads:", width=90, anchor="w").pack(side="left")
        self.entry_layout_threads = ctk.CTkEntry(threads_frame, width=70, placeholder_text="1")
        self.entry_layout_threads.insert(0, "1")
        self.entry_layout_threads.pack(side="left")
        self.entry_layout_threads.bind("<FocusOut>", lambda _e: self._save_pdf_ocr_config())

        opts_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        opts_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(opts_frame, text="Model:", width=90, anchor="w").pack(side="left")
        self.entry_gemini_model = ctk.CTkEntry(opts_frame, placeholder_text="Model", width=140)
        self.entry_gemini_model.insert(0, "gemini-2.5-flash")
        self.entry_gemini_model.pack(side="left", padx=(0, 10))
        self.entry_pdf_dpi = ctk.CTkEntry(opts_frame, placeholder_text="DPI", width=60)
        self.entry_pdf_dpi.insert(0, "200")
        self.entry_pdf_dpi.pack(side="left")
        ctk.CTkLabel(opts_frame, text="DPI").pack(side="left", padx=5)

        page_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        page_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(page_frame, text="Pages:", width=90, anchor="w").pack(side="left")
        self.entry_page_range = ctk.CTkEntry(page_frame, placeholder_text="1-3,5,8 (留空=全部)")
        self.entry_page_range.pack(side="left", fill="x", expand=True)

        self._advanced_section = CollapsibleFrame(scroll_frame, title="▸ 高级设置 (DeepSeek / Auto Router)", expanded=False)
        self._advanced_section.pack(fill="x", padx=20, pady=(15, 5))
        adv = self._advanced_section.content

        provider_frame = ctk.CTkFrame(adv, fg_color="transparent")
        provider_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(provider_frame, text="DS Provider:", width=90, anchor="w").pack(side="left")
        self.deepseek_provider_var = tk.StringVar(value="modelverse")
        self.deepseek_provider_menu = ctk.CTkOptionMenu(
            provider_frame,
            values=["modelverse", "siliconflow", "custom"],
            variable=self.deepseek_provider_var,
            command=self._on_deepseek_provider_change,
        )
        self.deepseek_provider_menu.pack(side="left", fill="x", expand=True)

        ds_key_frame = ctk.CTkFrame(adv, fg_color="transparent")
        ds_key_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(ds_key_frame, text="DeepSeek Key:", width=90, anchor="w").pack(side="left")
        env_ds_key = (
            os.environ.get("MODELVERSE_API_KEY", "").strip()
            or os.environ.get("SILICONFLOW_API_KEY", "").strip()
            or os.environ.get("DEEPSEEK_API_KEY", "").strip()
        )
        self.entry_deepseek_key = ctk.CTkEntry(ds_key_frame, placeholder_text="Paste API Key...", show="*")
        self.entry_deepseek_key.pack(side="left", fill="x", expand=True)
        if env_ds_key:
            self.entry_deepseek_key.insert(0, env_ds_key)
        self.entry_deepseek_key.bind("<FocusOut>", lambda _e: self._save_pdf_ocr_config())

        ds_url_frame = ctk.CTkFrame(adv, fg_color="transparent")
        ds_url_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(ds_url_frame, text="Base URL:", width=90, anchor="w").pack(side="left")
        self.entry_deepseek_base_url = ctk.CTkEntry(ds_url_frame, placeholder_text="https://api.siliconflow.cn/v1")
        self.entry_deepseek_base_url.pack(side="left", fill="x", expand=True)
        self.entry_deepseek_base_url.bind("<FocusOut>", lambda _e: self._save_pdf_ocr_config())

        auto_frame = ctk.CTkFrame(adv, fg_color="transparent")
        auto_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(auto_frame, text="Auto Router:", width=90, anchor="w").pack(side="left")
        self.entry_auto_outside_ratio = ctk.CTkEntry(auto_frame, width=65, placeholder_text="out%")
        self.entry_auto_outside_ratio.insert(0, "0.01")
        self.entry_auto_outside_ratio.pack(side="left", padx=(0, 4))
        self.entry_auto_min_text_ratio = ctk.CTkEntry(auto_frame, width=65, placeholder_text="min%")
        self.entry_auto_min_text_ratio.insert(0, "0.0005")
        self.entry_auto_min_text_ratio.pack(side="left", padx=(0, 4))
        self.entry_auto_min_component_area = ctk.CTkEntry(auto_frame, width=50, placeholder_text="area")
        self.entry_auto_min_component_area.insert(0, "30")
        self.entry_auto_min_component_area.pack(side="left")
        self.entry_auto_outside_ratio.bind("<FocusOut>", lambda _e: self._save_pdf_ocr_config())
        self.entry_auto_min_text_ratio.bind("<FocusOut>", lambda _e: self._save_pdf_ocr_config())
        self.entry_auto_min_component_area.bind("<FocusOut>", lambda _e: self._save_pdf_ocr_config())

        auto2_frame = ctk.CTkFrame(adv, fg_color="transparent")
        auto2_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(auto2_frame, text="Router Mode:", width=90, anchor="w").pack(side="left")
        self.router_mode_var = tk.StringVar(value="any")
        self.router_mode_menu = ctk.CTkOptionMenu(
            auto2_frame,
            values=["any", "textness", "second_pass", "gemini"],
            variable=self.router_mode_var,
            command=lambda _val: self._save_pdf_ocr_config(),
            width=120,
        )
        self.router_mode_menu.pack(side="left")

        auto3_frame = ctk.CTkFrame(adv, fg_color="transparent")
        auto3_frame.pack(fill="x", pady=5)
        self.var_auto_gemini_probe = tk.BooleanVar(value=False)
        self.chk_auto_gemini_probe = ctk.CTkCheckBox(
            auto3_frame,
            text="Gemini Probe",
            variable=self.var_auto_gemini_probe,
            command=self._save_pdf_ocr_config,
        )
        self.chk_auto_gemini_probe.pack(side="left", padx=(0, 8))
        self.entry_auto_gemini_model = ctk.CTkEntry(auto3_frame, width=150, placeholder_text="gemini model")
        self.entry_auto_gemini_model.insert(0, "gemini-2.5-flash-lite")
        self.entry_auto_gemini_model.pack(side="left", fill="x", expand=True)
        self.entry_auto_gemini_model.bind("<FocusOut>", lambda _e: self._save_pdf_ocr_config())

        ctk.CTkFrame(scroll_frame, height=2, fg_color=Theme.COLOR_BORDER).pack(fill="x", padx=15, pady=15)

        ctk.CTkLabel(scroll_frame, text="📄 PDF 处理", font=(Theme.FONT_FAMILY_BOLD[0], 16)).pack(anchor="w", padx=15, pady=(0, 10))
        
        self.btn_select_pdf = ctk.CTkButton(scroll_frame, text="选择 PDF 文件...", command=self.select_pdf_file, fg_color=Theme.COLOR_BLUE_BTN, hover_color=Theme.COLOR_BLUE_HOVER)
        self.btn_select_pdf.pack(fill="x", padx=15, pady=5)
        
        self.pdf_path_label = ctk.CTkLabel(scroll_frame, text="未选择文件", text_color=Theme.COLOR_TEXT_SECONDARY, wraplength=250)
        self.pdf_path_label.pack(pady=(0, 10))

        self.btn_run_layout = ctk.CTkButton(scroll_frame, text="🧭 仅版面识别", command=self.start_pdf_layout_thread, height=36, font=(Theme.FONT_FAMILY_BOLD[0], 14), fg_color=Theme.COLOR_BLUE_BTN, hover_color=Theme.COLOR_BLUE_HOVER)
        self.btn_run_layout.pack(fill="x", padx=15, pady=(5, 5))

        self.btn_run_pdf_ocr = ctk.CTkButton(scroll_frame, text="🚀 开始切题与识别", command=self.start_pdf_ocr_thread, height=42, font=(Theme.FONT_FAMILY_BOLD[0], 15), fg_color=Theme.COLOR_GREEN_BTN, hover_color=Theme.COLOR_GREEN_HOVER)
        self.btn_run_pdf_ocr.pack(fill="x", padx=15, pady=(0, 15))

        self.pdf_ocr_progress = ctk.CTkProgressBar(scroll_frame)
        self.pdf_ocr_progress.pack(fill="x", padx=15, pady=(0, 10))
        self.pdf_ocr_progress.set(0)

        right_panel = ctk.CTkFrame(container, fg_color=Theme.COLOR_BG_PANEL, corner_radius=Theme.CORNER_RADIUS_L)
        right_panel.grid(row=0, column=1, sticky="nsew")
        
        ctk.CTkLabel(right_panel, text="识别状态 📜", font=(Theme.FONT_FAMILY_BOLD[0], 16)).pack(anchor="w", padx=20, pady=(20, 10))
        
        self.pdf_ocr_status_label = ctk.CTkLabel(right_panel, text="等待开始...", anchor="w", justify="left")
        self.pdf_ocr_status_label.pack(fill="x", padx=20, pady=(0, 10))

        res_frame = ctk.CTkFrame(right_panel, fg_color=("gray95", "#252525"))
        res_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        ctk.CTkLabel(res_frame, text="识别完成后，结果将自动复制到剪贴板。\n您也可以手动操作：", text_color=Theme.COLOR_TEXT_SECONDARY, justify="center").pack(pady=30)
        
        btn_box = ctk.CTkFrame(res_frame, fg_color="transparent")
        btn_box.pack()
        self.btn_copy_pdf_ocr = ctk.CTkButton(btn_box, text="📋 复制完整文本", command=self.copy_pdf_ocr_result, state="disabled", width=140)
        self.btn_copy_pdf_ocr.pack(side="left", padx=5)
        self.btn_open_pdf_ocr_dir = ctk.CTkButton(btn_box, text="📂 打开输出目录", command=self.open_pdf_ocr_output_dir, state="disabled", width=140)
        self.btn_open_pdf_ocr_dir.pack(side="left", padx=5)

        self._load_pdf_ocr_config()
        self._apply_deepseek_provider(save=False)

    def _init_editor_tab_ui(self):
        """Tab 2: 纯净的编辑器界面"""
        # 顶部提示
        top_bar = ctk.CTkFrame(self.tab_edit, fg_color="transparent", height=30)
        top_bar.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        ctk.CTkLabel(top_bar, text="JSON 编辑器", font=(Theme.FONT_FAMILY_BOLD[0], 14)).pack(side="left")
        ctk.CTkLabel(top_bar, text=" (请将 OCR 得到的 JSON 粘贴至此处)", text_color=Theme.COLOR_TEXT_SECONDARY).pack(side="left")

        self.btn_copy = ctk.CTkButton(top_bar, text="Copy OCR Prompt", command=self.copy_prompt, fg_color=Theme.COLOR_BLUE_BTN, width=150)
        self.btn_copy.pack(side="right")

        # 分割布局：上部是编辑器（权重高），下部是校验信息（权重低）
        paned = ctk.CTkFrame(self.tab_edit, fg_color="transparent")
        paned.grid(row=1, column=0, sticky="nsew")
        paned.grid_rowconfigure(0, weight=10) # Editor gets 70% space
        paned.grid_rowconfigure(1, weight=3)  # Issues get 30% space
        paned.grid_columnconfigure(0, weight=1)

        # 1. 编辑器区域
        editor_frame = ctk.CTkFrame(paned, fg_color=("gray95", "#1E1E1E"), corner_radius=Theme.CORNER_RADIUS_S)
        editor_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 5))
        editor_frame.grid_rowconfigure(0, weight=1)
        editor_frame.grid_columnconfigure(1, weight=1)

        self.line_numbers = tk.Canvas(editor_frame, width=40, highlightthickness=0, bd=0)
        self.line_numbers.grid(row=0, column=0, sticky="ns")

        self.json_textbox = ctk.CTkTextbox(editor_frame, font=(Theme.FONT_CODE[0], 14), corner_radius=0, fg_color=("gray95", "#1E1E1E"), border_width=0, activate_scrollbars=True, undo=True)
        self.json_textbox.grid(row=0, column=1, sticky="nsew", padx=(2, 0))
        self.json_textbox.bind("<KeyRelease>", self.on_json_change)
        
        self._text_widget = self.json_textbox._textbox
        self._bind_editor_events()
        self._configure_editor_tags()

        # 2. 校验反馈区域
        issues_frame = ctk.CTkFrame(paned, fg_color=Theme.COLOR_BG_PANEL, corner_radius=Theme.CORNER_RADIUS_S, border_width=1, border_color=Theme.COLOR_BORDER)
        issues_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        issues_frame.grid_rowconfigure(1, weight=1)
        issues_frame.grid_columnconfigure(0, weight=1)

        self.issues_header_label = ctk.CTkLabel(issues_frame, text="✓ 校验通过", font=(Theme.FONT_FAMILY_BOLD[0], 13), text_color=Theme.COLOR_GREEN_BTN)
        self.issues_header_label.grid(row=0, column=0, sticky="w", padx=10, pady=(5, 0))

        self.issues_textbox = ctk.CTkTextbox(issues_frame, font=(Theme.FONT_CODE[0], 12), fg_color="transparent", height=80, activate_scrollbars=True)
        self.issues_textbox.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self._set_issues_panel([], header="未检测到问题")

    def _init_export_tab_ui(self):
        """Tab 3: 工具与生成"""
        self.tab_export.grid_columnconfigure(0, weight=1)
        self.tab_export.grid_columnconfigure(1, weight=1)
        
        # 左列：辅助工具
        left_col = ctk.CTkFrame(self.tab_export, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)
        
        # Card 2: 图片工具
        card_img = self.create_card(left_col, "🧼 图片处理", "二值化与去噪工具")
        ctk.CTkButton(card_img, text="🖼️ 打开图片预处理工具", command=self.open_image_tool, fg_color=Theme.COLOR_BLUE_BTN).pack(fill="x", padx=15, pady=15)
        
        # 右列：生成设置与日志
        right_col = ctk.CTkFrame(self.tab_export, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=10)

        # Card 3: 生成配置
        card_gen = self.create_card(right_col, "⚙️ 导出设置", "设置文件名并生成")
        self.entry_filename = ctk.CTkEntry(card_gen, placeholder_text="文件名 (留空则自动读取JSON标题)")
        self.entry_filename.pack(fill="x", padx=15, pady=(15, 10))
        
        self.btn_generate = ctk.CTkButton(card_gen, text="✨ 生成 PDF 文件", command=self.start_generation_thread, height=50, font=(Theme.FONT_FAMILY_BOLD[0], 16), fg_color=Theme.COLOR_GREEN_BTN, hover_color=Theme.COLOR_GREEN_HOVER)
        self.btn_generate.pack(fill="x", padx=15, pady=(5, 15))

        # Card 4: 系统日志
        card_log = self.create_card(right_col, "🪵 系统日志", "运行记录")
        card_log.pack(fill="both", expand=True)
        
        log_toolbar = ctk.CTkFrame(card_log, fg_color="transparent")
        log_toolbar.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(log_toolbar, text="过滤:", font=(Theme.FONT_FAMILY[0], 11)).pack(side="left", padx=(0, 5))
        self._log_filter_var = tk.StringVar(value="all")
        filter_menu = ctk.CTkOptionMenu(
            log_toolbar,
            values=["all", "info", "warn", "error", "debug"],
            variable=self._log_filter_var,
            command=lambda v: self._set_log_filter(v),
            width=80,
            height=24,
        )
        filter_menu.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            log_toolbar,
            text="📂 打开日志",
            command=self._open_log_file,
            width=80,
            height=24,
            font=(Theme.FONT_FAMILY[0], 11),
            fg_color="gray",
        ).pack(side="right", padx=(5, 0))

        ctk.CTkButton(
            log_toolbar,
            text="清空",
            command=self._clear_log,
            width=50,
            height=24,
            font=(Theme.FONT_FAMILY[0], 11),
            fg_color="gray",
        ).pack(side="right")
        
        self.log_textbox = ctk.CTkTextbox(card_log, font=(Theme.FONT_CODE[0], 11), activate_scrollbars=True)
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_textbox.configure(state="disabled")
        self._configure_log_tags()

    def create_card(self, parent, title, subtitle=""):
        frame = ctk.CTkFrame(parent, fg_color=Theme.COLOR_BG_PANEL, corner_radius=Theme.CORNER_RADIUS_L)
        frame.pack(fill="x", pady=(0, 20))
        
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 5))
        ctk.CTkLabel(header, text=title, font=(Theme.FONT_FAMILY_BOLD[0], 15)).pack(side="left")
        if subtitle:
            ctk.CTkLabel(header, text=subtitle, font=(Theme.FONT_FAMILY[0], 12), text_color=Theme.COLOR_TEXT_SECONDARY).pack(side="right")
        
        return frame

    # ---------------- 业务逻辑保持不变，UI 辅助函数 ----------------

    def copy_prompt(self):
        try:
            if os.path.exists(self.prompt_file):
                with open(self.prompt_file, 'r', encoding='utf-8') as f: pyperclip.copy(f.read())
                self.flash_status("✅ 提示词已成功复制！")
            else:
                self.flash_status(f"❌ 错误：找不到文件 {self.prompt_file}")
        except Exception as e:
            self.flash_status(f"❌ 复制出错: {e}")

    def open_image_tool(self):
        if self._image_tool is None or not self._image_tool.winfo_exists():
            try:
                self._image_tool = ImagePreprocessTool(self, theme=Theme, on_close=self._on_image_tool_close)
            except Exception:
                messagebox.showerror("错误", "无法加载 ImagePreprocessTool，请确保 image_preprocess.py 存在。")
        else:
            self._image_tool.focus()
            self._image_tool.lift()

    def _on_image_tool_close(self):
        self._image_tool = None

class PdfOcrMixin:
    """PDF OCR 逻辑部分，已与 UI 分离，仅保留绑定逻辑"""
    def select_pdf_file(self):
        path = filedialog.askopenfilename(title="选择 PDF", filetypes=[("PDF Files", "*.pdf")])
        if not path: return
        self._pdf_path = path
        self.pdf_path_label.configure(text=os.path.basename(path))
        self.pdf_ocr_status_label.configure(text="已就绪，请点击开始。")
        self.pdf_ocr_progress.set(0)

    def _set_pdf_ocr_status(self, text: str):
        self.after(0, lambda: self.pdf_ocr_status_label.configure(text=text))
        self._append_log(text)

    def _set_pdf_ocr_progress(self, value: float):
        v = max(0.0, min(1.0, float(value)))
        self.after(0, lambda: self.pdf_ocr_progress.set(v))

    def _set_pdf_ocr_controls_enabled(self, enabled: bool):
        def apply():
            st = "normal" if enabled else "disabled"
            self.btn_select_pdf.configure(state=st)
            self.deepseek_provider_menu.configure(state=st)
            self.entry_deepseek_key.configure(state=st)
            self.entry_deepseek_base_url.configure(state=st)
            self.entry_layout_threads.configure(state=st)
            self.btn_run_layout.configure(state=st)
            self.btn_run_pdf_ocr.configure(state=st)
            self.entry_gemini_key.configure(state=st)
            self.entry_gemini_model.configure(state=st)
            self.layout_model_menu.configure(state=st)
            self.entry_auto_outside_ratio.configure(state=st)
            self.entry_auto_min_text_ratio.configure(state=st)
            self.entry_auto_min_component_area.configure(state=st)
            self.router_mode_menu.configure(state=st)
            self.chk_auto_gemini_probe.configure(state=st)
            self.entry_auto_gemini_model.configure(state=st)
            self.entry_page_range.configure(state=st)
        self.after(0, apply)

    def _ensure_deepseek_keys(self):
        if not hasattr(self, "_deepseek_keys") or not isinstance(self._deepseek_keys, dict):
            self._deepseek_keys = {}

    def _get_deepseek_provider(self) -> str:
        return (self.deepseek_provider_var.get() or "modelverse").strip().lower()

    def _get_layout_threads(self) -> int:
        try:
            v = int(self.entry_layout_threads.get().strip() or "1")
        except Exception:
            v = 1
        if v < 1:
            v = 1
        if v > 32:
            v = 32
        return v

    def _remember_current_deepseek_key(self):
        self._ensure_deepseek_keys()
        provider = self._get_deepseek_provider()
        key = (self.entry_deepseek_key.get() or "").strip()
        if key:
            self._deepseek_keys[provider] = key

    def _env_deepseek_key(self, provider: str) -> str:
        if provider == "siliconflow":
            return os.environ.get("SILICONFLOW_API_KEY", "").strip()
        if provider == "modelverse":
            return (
                os.environ.get("MODELVERSE_API_KEY", "").strip()
                or os.environ.get("DEEPSEEK_API_KEY", "").strip()
            )
        return (
            os.environ.get("DEEPSEEK_API_KEY", "").strip()
            or os.environ.get("MODELVERSE_API_KEY", "").strip()
            or os.environ.get("SILICONFLOW_API_KEY", "").strip()
        )

    def _apply_deepseek_provider(self, provider: str | None = None, save: bool = True):
        self._ensure_deepseek_keys()
        new_provider = (provider or self._get_deepseek_provider()).strip().lower()
        old_provider = getattr(self, "_deepseek_provider_current", None)
        if old_provider:
            current_key = (self.entry_deepseek_key.get() or "").strip()
            if current_key:
                self._deepseek_keys[old_provider] = current_key

        new_key = self._deepseek_keys.get(new_provider) or self._env_deepseek_key(new_provider)
        self.entry_deepseek_key.delete(0, "end")
        if new_key:
            self.entry_deepseek_key.insert(0, new_key)
        self._deepseek_provider_current = new_provider
        if save:
            self._save_pdf_ocr_config()

    def _on_deepseek_provider_change(self, _val=None):
        self._apply_deepseek_provider(_val, save=True)

    def _get_deepseek_api_key(self, provider: str) -> str:
        entry_key = (self.entry_deepseek_key.get() or "").strip()
        if entry_key:
            return entry_key
        self._ensure_deepseek_keys()
        cached = self._deepseek_keys.get(provider)
        if cached:
            return cached
        if provider == "siliconflow":
            return os.environ.get("SILICONFLOW_API_KEY", "").strip()
        if provider == "custom":
            return (
                os.environ.get("DEEPSEEK_API_KEY", "").strip()
                or os.environ.get("MODELVERSE_API_KEY", "").strip()
                or os.environ.get("SILICONFLOW_API_KEY", "").strip()
            )
        return (
            os.environ.get("MODELVERSE_API_KEY", "").strip()
            or os.environ.get("DEEPSEEK_API_KEY", "").strip()
        )

    def _resolve_deepseek_base_url(self, provider: str) -> str | None:
        if provider == "siliconflow":
            return "https://api.siliconflow.cn/v1"
        if provider == "custom":
            url = (self.entry_deepseek_base_url.get() or "").strip()
            return url or None
        return None

    def start_pdf_layout_thread(self):
        if not self._pdf_path or not os.path.exists(self._pdf_path):
            messagebox.showwarning("提示", "请先选择一个 PDF 文件。")
            return

        model_label = (self.layout_model_var.get() or "").strip()
        model_key = layout_model_key_from_label(model_label) or DEFAULT_LAYOUT_MODEL

        provider = self._get_deepseek_provider()
        ds_key = self._get_deepseek_api_key(provider)
        if model_key in ("deepseek_ocr", "auto_router") and not ds_key:
            messagebox.showwarning("提示", "请先填写 DeepSeek API Key。")
            return
        if provider == "custom":
            base_url = self._resolve_deepseek_base_url(provider)
            if not base_url:
                messagebox.showwarning("提示", "自定义提供商需要填写 Base URL。")
                return

        api_key = (self.entry_gemini_key.get() or os.environ.get("GEMINI_API_KEY", "")).strip()
        if model_key == "auto_router" and self.var_auto_gemini_probe.get() and not api_key:
            messagebox.showwarning("提示", "启用 Gemini Probe 时需要 Gemini API Key。")
            return

        try:
            dpi = int(self.entry_pdf_dpi.get() or "200")
        except Exception:
            dpi = 200

        self._pdf_ocr_last_text = ""
        self._pdf_ocr_last_dir = ""
        self.btn_copy_pdf_ocr.configure(state="disabled")
        self.btn_open_pdf_ocr_dir.configure(state="disabled")

        self._set_pdf_ocr_controls_enabled(False)
        self._set_pdf_ocr_progress(0)
        self._set_pdf_ocr_status("正在初始化版面识别...")
        self.flash_status("📄 开始版面识别...")

        page_range = (self.entry_page_range.get() or "").strip()

        threading.Thread(
            target=self._run_pdf_layout,
            args=(self._pdf_path, dpi, page_range, api_key),
            daemon=True,
        ).start()

    def start_pdf_ocr_thread(self):
        if not self._pdf_path or not os.path.exists(self._pdf_path):
            messagebox.showwarning("提示", "请先选择一个 PDF 文件。")
            return

        api_key = (self.entry_gemini_key.get() or os.environ.get("GEMINI_API_KEY", "")).strip()
        if not api_key:
            messagebox.showwarning("提示", "请填写 Gemini API Key。")
            return

        model = (self.entry_gemini_model.get() or "gemini-1.5-flash").strip()
        try: dpi = int(self.entry_pdf_dpi.get() or "200")
        except: dpi = 200
        
        self._pdf_ocr_last_text = ""
        self._pdf_ocr_last_dir = ""
        self.btn_copy_pdf_ocr.configure(state="disabled")
        self.btn_open_pdf_ocr_dir.configure(state="disabled")

        self._set_pdf_ocr_controls_enabled(False)
        self._set_pdf_ocr_progress(0)
        self._set_pdf_ocr_status("正在初始化...")
        self.flash_status("📄 开始处理...")

        page_range = (self.entry_page_range.get() or "").strip()

        threading.Thread(
            target=self._run_pdf_ocr,
            args=(self._pdf_path, api_key, model, dpi, page_range),
            daemon=True,
        ).start()

    def _run_pdf_layout(self, pdf_path: str, dpi: int, page_range: str, api_key: str):
        try:
            pdf_path_obj = Path(pdf_path)
            output_root = Path("output") / "pdf_ocr"
            output_dir = output_root / pdf_path_obj.stem
            self._append_log(f"[cfg] pdf={pdf_path_obj}")
            self._append_log(f"[cfg] output_dir={output_dir}")
            self._append_log(f"[cfg] dpi={dpi}, page_range={page_range or 'ALL'}")

            model_label = (self.layout_model_var.get() or "").strip()
            model_key = layout_model_key_from_label(model_label) or DEFAULT_LAYOUT_MODEL
            model_label = layout_model_label_from_key(model_key)
            self._append_log(f"[cfg] layout_model={model_key} ({model_label})")

            self._set_pdf_ocr_status(f"正在加载布局模型: {model_label} ...")
            if model_key not in self._layout_extractors:
                try:
                    provider = self._get_deepseek_provider()
                    mv_key = self._get_deepseek_api_key(provider)
                    base_url = self._resolve_deepseek_base_url(provider)
                    self._append_log(f"[cfg] deepseek_provider={provider} base_url={base_url or 'default'}")
                    if model_key in ("deepseek_ocr", "auto_router") and not mv_key:
                        raise RuntimeError("请先填写 DeepSeek API Key")
                    if provider == "custom" and not base_url:
                        raise RuntimeError("自定义提供商需要填写 Base URL")
                    auto_cfg = None
                    if model_key == "auto_router":
                        try:
                            outside_ratio = float(self.entry_auto_outside_ratio.get().strip() or "0.01")
                        except Exception:
                            outside_ratio = 0.01
                        try:
                            min_text_ratio = float(self.entry_auto_min_text_ratio.get().strip() or "0.0005")
                        except Exception:
                            min_text_ratio = 0.0005
                        try:
                            min_area = int(float(self.entry_auto_min_component_area.get().strip() or "30"))
                        except Exception:
                            min_area = 30
                        auto_cfg = {
                            "text_outside_ratio": outside_ratio,
                            "min_text_ratio": min_text_ratio,
                            "min_component_area": min_area,
                            "use_gemini_probe": bool(self.var_auto_gemini_probe.get()),
                            "gemini_api_key": api_key,
                            "gemini_model": (self.entry_auto_gemini_model.get().strip() or "gemini-2.5-flash-lite"),
                            "router_mode": (self.router_mode_var.get().strip() or "any"),
                        }
                        self._append_log(
                            f"[cfg] auto_router outside_ratio={outside_ratio}, min_text_ratio={min_text_ratio}, "
                            f"min_component_area={min_area}, gemini_probe={auto_cfg['use_gemini_probe']}, "
                            f"gemini_model={auto_cfg['gemini_model']}, router_mode={auto_cfg['router_mode']}"
                        )
                    self._layout_extractors[model_key] = create_layout_extractor(
                        model_key,
                        deepseek_api_key=mv_key or None,
                        deepseek_base_url=base_url or None,
                        auto_router_config=auto_cfg,
                    )
                except Exception as e:
                    raise RuntimeError(f"模型初始化失败: {e}")

            extractor = self._layout_extractors[model_key]

            def _layout_log(**info):
                event = info.get("event")
                page = info.get("page")
                total = info.get("total")
                model = info.get("model")
                if event == "page_start":
                    self._append_log(f"[layout] page {page}/{total} start ({model})")
                elif event == "page_detected":
                    self._append_log(f"[layout] page {page}/{total} detected items={info.get('items')} ({model})")
                elif event == "page_saved":
                    self._append_log(f"[layout] page {page}/{total} saved items={info.get('items')} ({model})")
                elif event == "router_textness":
                    self._append_log(
                        f"[router] page {page}/{total} text_ratio={info.get('text_ratio', 0):.6f} "
                        f"outside_ratio={info.get('outside_ratio', 0):.6f} use_deepseek={info.get('use_deepseek')}"
                    )
                elif event == "router_gemini_probe":
                    self._append_log(
                        f"[router] page {page}/{total} gemini_probe={info.get('gemini_has_text')} use_deepseek={info.get('use_deepseek')}"
                    )
                elif event == "router_decision":
                    self._append_log(
                        f"[router] page {page}/{total} choose={info.get('chosen')} items={info.get('items')}"
                    )
                elif event == "router_second_pass":
                    self._append_log(
                        f"[router] page {page}/{total} second_pass items={info.get('second_items')}"
                    )
                else:
                    self._append_log(f"[layout] page {page}/{total} event={event} info={info}")

            if hasattr(extractor, "progress_cb"):
                extractor.progress_cb = _layout_log

            range_note = f" (Pages: {page_range})" if page_range else ""
            self._set_pdf_ocr_status(f"正在分析 PDF: {pdf_path_obj.name}{range_note} ...")

            ignored = ["abandon"] if model_key == "doclayout_yolo" else None
            self._append_log(f"[cfg] ignored_labels={ignored}")
            layout_threads = self._get_layout_threads()
            layout_kwargs = {}
            if model_key == "deepseek_ocr":
                layout_kwargs["num_workers"] = layout_threads
                self._append_log(f"[cfg] layout_threads={layout_threads}")

            items = extractor.process_pdf(
                pdf_path=pdf_path_obj, output_dir=output_root, dpi=dpi, conf=0.25,
                ignored_labels=ignored, page_range=page_range or None, return_items=True, **layout_kwargs
            )

            if not items:
                raise RuntimeError("No layout items detected")
            self._append_log(f"[layout] detected_items={len(items)}")
            page_counts = {}
            for it in items:
                p = it.get("page")
                if not p:
                    continue
                page_counts[p] = page_counts.get(p, 0) + 1
            if page_counts:
                pages = ",".join(str(p) for p in sorted(page_counts))
                self._append_log(f"[layout] pages={pages}")
                for p in sorted(page_counts):
                    self._append_log(f"[layout] page {p} items={page_counts[p]}")

            self._pdf_ocr_last_dir = str(output_dir)
            self._set_pdf_ocr_progress(1.0)
            self._set_pdf_ocr_status("版面识别完成。")
            self.flash_status("✅ 版面识别完成")
            self.after(0, lambda: self.btn_open_pdf_ocr_dir.configure(state="normal"))
            self.after(0, lambda: messagebox.showinfo("成功", "版面识别完成！"))

        except Exception as e:
            self._set_pdf_ocr_status(f"错误: {e}")
            self.flash_status(f"❌ 失败: {e}")
            err_text = str(e)
            self.after(0, lambda msg=err_text: messagebox.showerror("出错", msg))
        finally:
            self._set_pdf_ocr_controls_enabled(True)

    def _run_pdf_ocr(self, pdf_path: str, api_key: str, model_name: str, dpi: int, page_range: str):
        try:
            pdf_path_obj = Path(pdf_path)
            output_root = Path("output") / "pdf_ocr"
            output_dir = output_root / pdf_path_obj.stem
            self._append_log(f"[cfg] pdf={pdf_path_obj}")
            self._append_log(f"[cfg] output_dir={output_dir}")
            self._append_log(f"[cfg] dpi={dpi}, page_range={page_range or 'ALL'}")
            self._append_log(f"[cfg] gemini_model={model_name}")
            
            model_label = (self.layout_model_var.get() or "").strip()
            model_key = layout_model_key_from_label(model_label) or DEFAULT_LAYOUT_MODEL
            model_label = layout_model_label_from_key(model_key)
            self._append_log(f"[cfg] layout_model={model_key} ({model_label})")

            self._set_pdf_ocr_status(f"正在加载布局模型: {model_label} ...")
            if model_key not in self._layout_extractors:
                try:
                    provider = self._get_deepseek_provider()
                    mv_key = self._get_deepseek_api_key(provider)
                    base_url = self._resolve_deepseek_base_url(provider)
                    self._append_log(f"[cfg] deepseek_provider={provider} base_url={base_url or 'default'}")
                    if model_key in ("deepseek_ocr", "auto_router") and not mv_key:
                        raise RuntimeError("请先填写 DeepSeek API Key")
                    if provider == "custom" and not base_url:
                        raise RuntimeError("自定义提供商需要填写 Base URL")
                    auto_cfg = None
                    if model_key == "auto_router":
                        try:
                            outside_ratio = float(self.entry_auto_outside_ratio.get().strip() or "0.01")
                        except Exception:
                            outside_ratio = 0.01
                        try:
                            min_text_ratio = float(self.entry_auto_min_text_ratio.get().strip() or "0.0005")
                        except Exception:
                            min_text_ratio = 0.0005
                        try:
                            min_area = int(float(self.entry_auto_min_component_area.get().strip() or "30"))
                        except Exception:
                            min_area = 30
                        auto_cfg = {
                            "text_outside_ratio": outside_ratio,
                            "min_text_ratio": min_text_ratio,
                            "min_component_area": min_area,
                            "use_gemini_probe": bool(self.var_auto_gemini_probe.get()),
                            "gemini_api_key": api_key,
                            "gemini_model": (self.entry_auto_gemini_model.get().strip() or "gemini-2.5-flash-lite"),
                            "router_mode": (self.router_mode_var.get().strip() or "any"),
                        }
                        self._append_log(
                            f"[cfg] auto_router outside_ratio={outside_ratio}, min_text_ratio={min_text_ratio}, "
                            f"min_component_area={min_area}, gemini_probe={auto_cfg['use_gemini_probe']}, "
                            f"gemini_model={auto_cfg['gemini_model']}, router_mode={auto_cfg['router_mode']}"
                        )
                    self._layout_extractors[model_key] = create_layout_extractor(
                        model_key,
                        deepseek_api_key=mv_key or None,
                        deepseek_base_url=base_url or None,
                        auto_router_config=auto_cfg,
                    )
                except Exception as e:
                    raise RuntimeError(f"模型初始化失败: {e}")

            extractor = self._layout_extractors[model_key]

            def _layout_log(**info):
                event = info.get("event")
                page = info.get("page")
                total = info.get("total")
                model = info.get("model")
                if event == "page_start":
                    self._append_log(f"[layout] page {page}/{total} start ({model})")
                elif event == "page_detected":
                    self._append_log(f"[layout] page {page}/{total} detected items={info.get('items')} ({model})")
                elif event == "page_saved":
                    self._append_log(f"[layout] page {page}/{total} saved items={info.get('items')} ({model})")
                elif event == "router_textness":
                    self._append_log(
                        f"[router] page {page}/{total} text_ratio={info.get('text_ratio', 0):.6f} "
                        f"outside_ratio={info.get('outside_ratio', 0):.6f} use_deepseek={info.get('use_deepseek')}"
                    )
                elif event == "router_gemini_probe":
                    self._append_log(
                        f"[router] page {page}/{total} gemini_probe={info.get('gemini_has_text')} use_deepseek={info.get('use_deepseek')}"
                    )
                elif event == "router_decision":
                    self._append_log(
                        f"[router] page {page}/{total} choose={info.get('chosen')} items={info.get('items')}"
                    )
                elif event == "router_second_pass":
                    self._append_log(
                        f"[router] page {page}/{total} second_pass items={info.get('second_items')}"
                    )
                else:
                    self._append_log(f"[layout] page {page}/{total} event={event} info={info}")

            if hasattr(extractor, "progress_cb"):
                extractor.progress_cb = _layout_log

            range_note = f" (Pages: {page_range})" if page_range else ""
            self._set_pdf_ocr_status(f"正在分析 PDF: {pdf_path_obj.name}{range_note} ...")
            
            ignored = ["abandon"] if model_key == "doclayout_yolo" else None
            self._append_log(f"[cfg] ignored_labels={ignored}")
            layout_threads = self._get_layout_threads()
            layout_kwargs = {}
            if model_key == "deepseek_ocr":
                layout_kwargs["num_workers"] = layout_threads
                self._append_log(f"[cfg] layout_threads={layout_threads}")

            items = extractor.process_pdf(
                pdf_path=pdf_path_obj, output_dir=output_root, dpi=dpi, conf=0.25,
                ignored_labels=ignored, page_range=page_range or None, return_items=True, **layout_kwargs
            )

            if not items: raise RuntimeError("No OCR items detected")
            self._append_log(f"[layout] detected_items={len(items)}")
            page_counts = {}
            for it in items:
                p = it.get("page")
                if not p:
                    continue
                page_counts[p] = page_counts.get(p, 0) + 1
            if page_counts:
                pages = ",".join(str(p) for p in sorted(page_counts))
                self._append_log(f"[layout] pages={pages}")
                for p in sorted(page_counts):
                    self._append_log(f"[layout] page {p} items={page_counts[p]}")

            figure_labels = getattr(extractor, "figure_labels", {"figure"})
            full_text_list = []
            total_items = len(items)
            prompt = "转文字。与题目无关内容（草稿，手写字）请忽略。特别注意补集符号。不确定的内容不要瞎猜而是插入'【不确定】'到文本里。不要输出解释性话语。"
            results: list[str | None] = [None] * total_items
            ocr_indices: list[int] = []

            for idx, item in enumerate(items):
                label = item.get("label")
                if label in figure_labels:
                    path_str = item.get("path", "")
                    if path_str:
                        try:
                            rel = os.path.relpath(path_str, output_dir)
                        except Exception:
                            rel = path_str
                        rel = rel.replace("\\", "/")
                        rel = quote(rel, safe="/-._~")
                    else:
                        rel = ""
                    results[idx] = f"![img]({rel})"
                else:
                    ocr_indices.append(idx)

            self._set_pdf_ocr_progress(0.3)
            self._set_pdf_ocr_status(
                f"正在识别（共 {total_items} 项，OCR {len(ocr_indices)} 项 / 图像 {total_items - len(ocr_indices)} 项）Gemini 处理中..."
            )
            self._append_log(f"[ocr] queue={len(ocr_indices)}")

            max_workers = 8
            completed = 0

            def _ocr_one(seq: int, idx: int):
                self._set_pdf_ocr_status(f"正在识别 ({seq}/{len(ocr_indices)})...")
                item = items[idx]
                item_name = os.path.basename(item.get("path", ""))
                t0 = time.time()
                self._append_log(f"[ocr] start {seq}/{len(ocr_indices)} file={item_name}")
                res = call_gemini_ocr(api_key, model_name, item["path"], prompt)
                dt = time.time() - t0
                self._append_log(f"[ocr] done {seq}/{len(ocr_indices)} file={item_name} len={len(res)} time={dt:.2f}s")
                return idx, res

            if ocr_indices:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [executor.submit(_ocr_one, seq + 1, idx) for seq, idx in enumerate(ocr_indices)]
                    for future in as_completed(futures):
                        idx, txt = future.result()
                        results[idx] = txt
                        completed += 1
                        self._set_pdf_ocr_progress(0.3 + (0.6 * completed / len(ocr_indices)))
            else:
                self._set_pdf_ocr_progress(0.9)

            for txt in results:
                if txt: full_text_list.append(f"{txt}")

            merged_text = "\n".join(full_text_list)
            with open(output_dir / "merged.txt", "w", encoding="utf-8") as f: f.write(merged_text)

            self._pdf_ocr_last_text = merged_text
            self._pdf_ocr_last_dir = str(output_dir)
            try: pyperclip.copy(merged_text)
            except: pass

            self._set_pdf_ocr_progress(1.0)
            self._set_pdf_ocr_status("完成！结果已复制。")
            self.flash_status("✅ OCR 完成")

            self.after(0, lambda: self.btn_copy_pdf_ocr.configure(state="normal"))
            self.after(0, lambda: self.btn_open_pdf_ocr_dir.configure(state="normal"))
            self.after(0, lambda: messagebox.showinfo("成功", f"处理完成！\n文本已复制。"))

        except Exception as e:
            self._set_pdf_ocr_status(f"错误: {e}")
            self.flash_status(f"❌ 失败: {e}")
            err_text = str(e)
            self.after(0, lambda msg=err_text: messagebox.showerror("出错", msg))
        finally:
            self._set_pdf_ocr_controls_enabled(True)

    def copy_pdf_ocr_result(self):
        if self._pdf_ocr_last_text:
            pyperclip.copy(self._pdf_ocr_last_text)
            self.flash_status("✅ 已复制")

    def open_pdf_ocr_output_dir(self):
        path = self._pdf_ocr_last_dir
        if path and os.path.exists(path):
            if os.name == "nt": os.startfile(path)
            else: subprocess.call(["open" if sys.platform == "darwin" else "xdg-open", path])

    def _load_pdf_ocr_config(self):
        try:
            if not os.path.exists(self._config_path): return
            with open(self._config_path, "r") as f: data = json.load(f)
            self._deepseek_keys = {}
            if isinstance(data.get("deepseek_keys"), dict):
                self._deepseek_keys.update(data.get("deepseek_keys", {}))
            if k := data.get("gemini_key"): 
                self.entry_gemini_key.delete(0, "end"); self.entry_gemini_key.insert(0, k)
            mvk = data.get("deepseek_key") or data.get("modelverse_key")
            if mvk:
                provider = (data.get("deepseek_provider") or "modelverse").strip().lower()
                self._deepseek_keys[provider] = mvk
            if v := data.get("deepseek_provider"):
                if str(v) in ["modelverse", "siliconflow", "custom"]:
                    self.deepseek_provider_var.set(str(v))
            if v := data.get("deepseek_base_url"):
                self.entry_deepseek_base_url.delete(0, "end"); self.entry_deepseek_base_url.insert(0, str(v))
            if v := data.get("layout_threads"):
                self.entry_layout_threads.delete(0, "end"); self.entry_layout_threads.insert(0, str(v))
            if v := data.get("auto_outside_ratio"):
                self.entry_auto_outside_ratio.delete(0, "end"); self.entry_auto_outside_ratio.insert(0, str(v))
            if v := data.get("auto_min_text_ratio"):
                self.entry_auto_min_text_ratio.delete(0, "end"); self.entry_auto_min_text_ratio.insert(0, str(v))
            if v := data.get("auto_min_component_area"):
                self.entry_auto_min_component_area.delete(0, "end"); self.entry_auto_min_component_area.insert(0, str(v))
            if v := data.get("auto_gemini_probe"):
                self.var_auto_gemini_probe.set(bool(v))
            if v := data.get("auto_gemini_model"):
                self.entry_auto_gemini_model.delete(0, "end"); self.entry_auto_gemini_model.insert(0, str(v))
            if v := data.get("auto_router_mode"):
                if str(v) in ["any", "textness", "second_pass", "gemini"]:
                    self.router_mode_var.set(str(v))
            if model_key := data.get("layout_model"):
                label = layout_model_label_from_key(model_key)
                if label in LAYOUT_MODEL_LABELS.values():
                    self.layout_model_var.set(label)
            self._apply_deepseek_provider(save=False)
        except: pass

    def _save_pdf_ocr_config(self):
        try:
            model_label = (self.layout_model_var.get() or "").strip()
            model_key = layout_model_key_from_label(model_label) or DEFAULT_LAYOUT_MODEL
            self._remember_current_deepseek_key()
            with open(self._config_path, "w") as f:
                json.dump({
                    "gemini_key": self.entry_gemini_key.get().strip(),
                    "deepseek_key": self.entry_deepseek_key.get().strip(),
                    "modelverse_key": self.entry_deepseek_key.get().strip(),
                    "deepseek_keys": getattr(self, "_deepseek_keys", {}),
                    "deepseek_provider": self.deepseek_provider_var.get().strip(),
                    "deepseek_base_url": self.entry_deepseek_base_url.get().strip(),
                    "layout_threads": self.entry_layout_threads.get().strip(),
                    "auto_outside_ratio": self.entry_auto_outside_ratio.get().strip(),
                    "auto_min_text_ratio": self.entry_auto_min_text_ratio.get().strip(),
                    "auto_min_component_area": self.entry_auto_min_component_area.get().strip(),
                    "auto_gemini_probe": bool(self.var_auto_gemini_probe.get()),
                    "auto_gemini_model": self.entry_auto_gemini_model.get().strip(),
                    "auto_router_mode": self.router_mode_var.get().strip(),
                    "layout_model": model_key,
                }, f)
        except: pass

class EditorMixin:
    def _bind_editor_events(self):
        if not hasattr(self, "_text_widget"): return
        self._text_widget.bind("<KeyRelease>", self._on_editor_change, add=True)
        self._text_widget.bind("<MouseWheel>", self._on_editor_scroll, add=True)
        self._text_widget.bind("<ButtonRelease-1>", self._on_editor_scroll, add=True)
        self._text_widget.bind("<Configure>", self._on_editor_scroll, add=True)

    def _configure_editor_tags(self):
        if not hasattr(self, "_text_widget"): return
        self._text_widget.tag_configure("error_line", background="#3A1E1E" if ctk.get_appearance_mode()=="Dark" else "#FFECEC")
        self._text_widget.tag_configure("warning_line", background="#3A2B0F" if ctk.get_appearance_mode()=="Dark" else "#FFF6DD")

    def _on_editor_change(self, event=None): self._update_line_numbers()
    def _on_editor_scroll(self, event=None): self._update_line_numbers()

    def _update_line_numbers(self):
        if not hasattr(self, "line_numbers") or not hasattr(self, "_text_widget"): return
        self.line_numbers.delete("all")
        i = self._text_widget.index("@0,0")
        while True:
            dline = self._text_widget.dlineinfo(i)
            if dline is None: break
            self.line_numbers.create_text(35, dline[1], anchor="ne", text=i.split(".")[0], fill="#8E8E93", font=(Theme.FONT_CODE[0], 11))
            i = self._text_widget.index(f"{i}+1line")

    def _apply_issue_highlights(self, issues):
        if not hasattr(self, "_text_widget"): return
        self._text_widget.tag_remove("error_line", "1.0", "end")
        self._text_widget.tag_remove("warning_line", "1.0", "end")
        for it in issues:
            if it.line:
                tag = "error_line" if it.severity == "error" else "warning_line"
                self._text_widget.tag_add(tag, f"{it.line}.0", f"{it.line}.0 lineend")
        self._update_line_numbers()

    def on_json_change(self, event=None):
        if self._validation_after_id: self.after_cancel(self._validation_after_id)
        self._validation_after_id = self.after(300, self._run_validation_from_editor)

    def _run_validation_from_editor(self):
        self._validation_after_id = None
        json_str = self.json_textbox.get("0.0", "end").strip()
        self._validation_seq += 1
        with self._validation_lock:
            self._validation_pending_seq = self._validation_seq
            self._validation_pending_text = json_str
        self._set_issues_panel([], header="⏳ 校验中...")
        self._validation_request_event.set()

    def _set_issues_panel(self, issues, header=None):
        self._last_issues = issues
        errs = sum(1 for i in issues if i.severity == "error")
        warns = sum(1 for i in issues if i.severity == "warning")
        
        if header is None:
            if errs == 0 and warns == 0: header = "✓ 校验通过"
            else: header = f"⚠️ 发现 {errs} 个错误，{warns} 个警告"
            
        color = Theme.COLOR_GREEN_BTN if errs == 0 else "#FF3B30"
        if hasattr(self, "issues_header_label"):
            self.issues_header_label.configure(text=header, text_color=color)

        if hasattr(self, "issues_textbox"):
            text = ""
            for it in issues[:50]:
                text += f"[{it.severity.upper()}] Line {it.line}: {it.message}\n"
            self.issues_textbox.configure(state="normal")
            self.issues_textbox.delete("0.0", "end")
            self.issues_textbox.insert("end", text)
            self.issues_textbox.configure(state="disabled")
            self._apply_issue_highlights(issues)

class LogMixin:
    LOG_LEVEL_INFO = "info"
    LOG_LEVEL_WARN = "warn"
    LOG_LEVEL_ERROR = "error"
    LOG_LEVEL_DEBUG = "debug"

    def _append_log(self, msg: str, level: str = "info"):
        if not hasattr(self, "log_textbox"):
            return
        ts = time.strftime("%H:%M:%S", time.localtime())
        level = level.lower()
        prefix_map = {
            "info": "INFO",
            "warn": "WARN",
            "warning": "WARN",
            "error": "ERR ",
            "err": "ERR ",
            "debug": "DBG ",
        }
        prefix = prefix_map.get(level, "INFO")
        line = f"[{ts}] [{prefix}] {msg}\n"
        self.after(0, lambda: self._update_log_ui(line, level))
        with self._log_lock:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(line)

    def log_info(self, msg: str):
        self._append_log(msg, "info")

    def log_warn(self, msg: str):
        self._append_log(msg, "warn")

    def log_error(self, msg: str):
        self._append_log(msg, "error")

    def log_debug(self, msg: str):
        self._append_log(msg, "debug")

    def _update_log_ui(self, line: str, level: str = "info"):
        try:
            if not hasattr(self, "log_textbox"):
                return
            current_filter = getattr(self, "_log_filter_level", "all")
            if current_filter != "all" and level != current_filter:
                if not hasattr(self, "_log_buffer"):
                    self._log_buffer = []
                self._log_buffer.append((line, level))
                return

            self.log_textbox.configure(state="normal")
            start_idx = self.log_textbox.index("end-1c")
            self.log_textbox.insert("end", line)
            end_idx = self.log_textbox.index("end-1c")

            tag = f"log_{level}"
            self.log_textbox.tag_add(tag, start_idx, end_idx)

            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
        except Exception:
            pass

    def _configure_log_tags(self):
        if not hasattr(self, "log_textbox"):
            return
        try:
            self.log_textbox.tag_config("log_info", foreground=("#1A1A1A", "#E0E0E0"))
            self.log_textbox.tag_config("log_warn", foreground=("#B8860B", "#FFD700"))
            self.log_textbox.tag_config("log_error", foreground=("#CC0000", "#FF6B6B"))
            self.log_textbox.tag_config("log_debug", foreground=("#6C757D", "#888888"))
        except Exception:
            pass

    def _clear_log(self):
        if not hasattr(self, "log_textbox"):
            return
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("0.0", "end")
        self.log_textbox.configure(state="disabled")
        if hasattr(self, "_log_buffer"):
            self._log_buffer.clear()

    def _init_log_file(self) -> str:
        d = os.path.join("output", "logs")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, time.strftime("gui_%Y%m%d.log"))

    def _open_log_file(self):
        if not hasattr(self, "_log_path"):
            return
        path = self._log_path
        if os.path.exists(path):
            if os.name == "nt":
                os.startfile(path)
            else:
                subprocess.call(["open" if sys.platform == "darwin" else "xdg-open", path])

    def _set_log_filter(self, level: str):
        self._log_filter_level = level.lower()
        self._refresh_log_display()

    def _refresh_log_display(self):
        if not hasattr(self, "log_textbox") or not hasattr(self, "_log_path"):
            return
        try:
            with open(self._log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return

        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("0.0", "end")

        current_filter = getattr(self, "_log_filter_level", "all")
        for line in lines:
            level = "info"
            if "[WARN]" in line:
                level = "warn"
            elif "[ERR ]" in line:
                level = "error"
            elif "[DBG ]" in line:
                level = "debug"

            if current_filter != "all" and level != current_filter:
                continue

            start_idx = self.log_textbox.index("end-1c")
            self.log_textbox.insert("end", line)
            end_idx = self.log_textbox.index("end-1c")
            self.log_textbox.tag_add(f"log_{level}", start_idx, end_idx)

        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

class GenerationMixin:
    def start_generation_thread(self):
        self.btn_generate.configure(state="disabled", text="⏳ 处理中...")
        threading.Thread(target=self.run_generation, daemon=True).start()

    def run_generation(self):
        try:
            json_str = self.json_textbox.get("0.0", "end").strip()
            if not json_str:
                self.flash_status("❌ 请先在编辑器中输入 JSON 数据")
                return

            data, issues = validate_json_and_latex(json_str)
            self.after(0, lambda: self._set_issues_panel(issues))
            if data is None: return

            custom_fn = self.entry_filename.get().strip()
            folder_name = custom_fn or data.get('meta', {}).get('title', 'exam_output')
            folder_name = "".join([c for c in folder_name if c not in '<>:"/\\|?*']).strip()
            
            output_dir = os.path.abspath(os.path.join("output", folder_name))
            temp_dir = os.path.abspath("temp_build")
            
            self.flash_status(f"⚙️ 清理编译环境...")
            if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
            os.makedirs(temp_dir, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)

            processed = self.generator.process_data(json.dumps(data))
            missing_imgs = self.generator.replace_inline_images(processed, os.path.join(temp_dir, 'assets'))
            if missing_imgs:
                self._append_log(f"[warn] Missing images: {len(missing_imgs)}")
            tex_path = os.path.join(temp_dir, "main.tex")
            if not self.generator.render(processed, tex_path): raise Exception("渲染失败")

            self.flash_status("⚙️ 编译 LaTeX...")
            if self.generator.compile_pdf(tex_path):
                target_pdf = os.path.join(output_dir, f"{folder_name}.pdf")
                shutil.copy2(os.path.join(temp_dir, "main.pdf"), target_pdf)
                self.flash_status(f"🎉 成功！PDF已生成: {target_pdf}")
                try: 
                    if os.name=='nt': os.startfile(output_dir)
                    else: subprocess.call(['open' if sys.platform=='darwin' else 'xdg-open', output_dir])
                except: pass
            else:
                detail = extract_first_latex_error(os.path.join(temp_dir, "main.log"), tex_path)
                if detail: 
                    self.after(0, lambda: self._set_issues_panel(issues + [detail], header="❌ LaTeX 编译失败"))
                self.flash_status("❌ 编译失败，请检查 LaTeX 语法")

        except Exception as e:
            self.flash_status(f"❌ 异常: {e}")
        finally:
            self.after(0, lambda: self.btn_generate.configure(state="normal", text="✨ 生成 PDF 文件"))

class StatusMixin:
    def flash_status(self, msg):
        self.after(0, lambda: self.status_label.configure(text=msg))
        self._append_log(msg)
