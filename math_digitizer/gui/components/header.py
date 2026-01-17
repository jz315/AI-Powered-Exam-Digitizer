from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pyperclip

from math_digitizer.gui.services.deps import ImagePreprocessTool
from math_digitizer.gui.theme import Theme
from math_digitizer.ocr import (
    DEFAULT_LAYOUT_MODEL,
    LAYOUT_MODEL_LABELS,
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
        
        ocr_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        ocr_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(ocr_frame, text="OCR Provider:", width=90, anchor="w").pack(side="left")
        self.ocr_provider_var = tk.StringVar(value="gemini")
        self.ocr_provider_menu = ctk.CTkOptionMenu(
            ocr_frame,
            values=["gemini", "aliyun"],
            variable=self.ocr_provider_var,
            command=self._on_ocr_provider_change,
        )
        self.ocr_provider_menu.pack(side="left", fill="x", expand=True)

        key_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        key_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(key_frame, text="OCR Key:", width=90, anchor="w").pack(side="left")
        env_key = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("DASHSCOPE_API_KEY", "").strip()
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
        ctk.CTkLabel(opts_frame, text="OCR Model:", width=90, anchor="w").pack(side="left")
        self.entry_gemini_model = ctk.CTkEntry(opts_frame, placeholder_text="Model", width=140)
        self.entry_gemini_model.insert(0, "gemini-3-flash-preview")
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
        
        img_dir_frame = ctk.CTkFrame(card_gen, fg_color="transparent")
        img_dir_frame.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkLabel(img_dir_frame, text="图片目录:", width=70, anchor="w").pack(side="left")
        self.entry_image_dir = ctk.CTkEntry(img_dir_frame, placeholder_text="OCR 输出目录 (自动填充)")
        self.entry_image_dir.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(img_dir_frame, text="📂", width=32, command=self._select_image_dir).pack(side="left")
        
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
            prompt_path = self.prompt_file
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    pyperclip.copy(f.read())
                self.flash_status("✅ 提示词已成功复制！")
            else:
                self.flash_status(f"❌ 错误：找不到文件 {prompt_path}")
                self._append_log(f"[error] prompt file not found: {prompt_path}")
        except Exception as e:
            self.flash_status(f"❌ 复制出错: {e}")
            self._append_log(f"[error] copy_prompt failed: {e}")

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

    def _select_image_dir(self):
        path = filedialog.askdirectory(title="选择图片目录 (OCR 输出文件夹)")
        if path:
            self.entry_image_dir.delete(0, "end")
            self.entry_image_dir.insert(0, path)

