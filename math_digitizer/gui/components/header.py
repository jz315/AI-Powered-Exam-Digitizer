from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

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

        self.cancel_task_btn = ctk.CTkButton(
            header_frame,
            text="⏹ 取消",
            command=self._cancel_current_task,
            width=70,
            height=28,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=(Theme.FONT_FAMILY[0], 12),
        )
        self.cancel_task_btn.pack(side="right", padx=(10, 0))
        self.cancel_task_btn.pack_forget()

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
        
        # 创建主要选项卡
        self.tab_ocr = self.tabview.add(" 1. 智能提取 (OCR) ")
        self.tab_edit = self.tabview.add(" 2. 数据编辑 (Editor) ")
        self.tab_export = self.tabview.add(" 3. 导出与工具 (Export) ")

        # 配置 Tab 内部布局
        self.tab_ocr.grid_columnconfigure(0, weight=1)
        self.tab_edit.grid_columnconfigure(0, weight=1)
        self.tab_edit.grid_rowconfigure(2, weight=1) # 编辑器占满
        self.tab_export.grid_columnconfigure(0, weight=1)
        self.tab_export.grid_columnconfigure(1, weight=1)

        # 填充内容
        if hasattr(self, "_init_ocr_tab_ui"):
             self._init_ocr_tab_ui()
        self._init_editor_tab_ui()
        self._init_export_tab_ui()

    def _init_editor_tab_ui(self):
        """Tab 2: 纯净的编辑器界面"""
        # 顶部提示
        top_bar = ctk.CTkFrame(self.tab_edit, fg_color="transparent", height=30)
        top_bar.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        ctk.CTkLabel(top_bar, text="JSON 编辑器", font=(Theme.FONT_FAMILY_BOLD[0], 14)).pack(side="left")
        ctk.CTkLabel(top_bar, text=" (请将 OCR 得到的 JSON 粘贴至此处)", text_color=Theme.COLOR_TEXT_SECONDARY).pack(side="left")

        self.btn_copy = ctk.CTkButton(top_bar, text="Copy OCR Prompt", command=self.copy_prompt, fg_color=Theme.COLOR_BLUE_BTN, width=150)
        self.btn_copy.pack(side="right")

        self.btn_import_bank = ctk.CTkButton(
            top_bar, 
            text="📥 导入到题库", 
            command=self._start_import_from_editor,
            fg_color=Theme.COLOR_GREEN_BTN, 
            width=120
        )
        self.btn_import_bank.pack(side="right", padx=(0, 10))

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
            prompt_path = self.prompt_file
            content = self.prompt_service.read_prompt(prompt_path)
            pyperclip.copy(content)
            self.flash_status("✅ 提示词已成功复制！")
        except Exception as e:
            prompt_path = getattr(self, "prompt_file", "")
            self.flash_status(f"❌ 复制出错: {e}")
            if prompt_path:
                self._append_log(f"[error] prompt file not found: {prompt_path}")
            self._append_log(f"[error] copy_prompt failed: {e}")

    def copy_prompt_and_ocr(self):
        try:
            prompt_path = self.prompt_file
            prompt_content = self.prompt_service.read_prompt(prompt_path)
            ocr_content = getattr(self, "_pdf_ocr_last_text", "")
            if not ocr_content:
                self.flash_status("❌ 没有OCR结果可复制")
                return
            combined = self.prompt_service.build_prompt_and_ocr(prompt_content, ocr_content)
            pyperclip.copy(combined)
            self.flash_status("✅ 提示词+OCR结果已复制！")
        except Exception as e:
            self.flash_status(f"❌ 复制出错: {e}")
            self._append_log(f"[error] copy_prompt_and_ocr failed: {e}")

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

    def _cancel_current_task(self):
        self.task_manager.request_cancel()

    def _show_cancel_button(self, task_name: str = ""):
        self.after(0, lambda: self.cancel_task_btn.pack(side="right", padx=(10, 0)))

    def _hide_cancel_button(self):
        self.after(0, lambda: self.cancel_task_btn.pack_forget())

    def _is_task_cancelled(self) -> bool:
        return self.task_manager.is_cancelled()
