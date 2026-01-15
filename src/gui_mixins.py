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

        # 状态指示器
        self.status_label = ctk.CTkLabel(header_frame, text="Ready", font=(Theme.FONT_FAMILY[0], 13), text_color=Theme.COLOR_TEXT_SECONDARY)
        self.status_label.pack(side="right")

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
        """Tab 1: OCR 相关控件"""
        # 使用两列布局：左侧控制，右侧说明/日志
        container = ctk.CTkFrame(self.tab_ocr, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        container.grid_columnconfigure(0, weight=2)
        container.grid_columnconfigure(1, weight=3)
        container.grid_rowconfigure(0, weight=1)

        # 左侧：控制面板
        left_panel = ctk.CTkFrame(container, fg_color=Theme.COLOR_BG_PANEL, corner_radius=Theme.CORNER_RADIUS_L)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ctk.CTkLabel(left_panel, text="🛠️配置与运行", font=(Theme.FONT_FAMILY_BOLD[0], 16)).pack(anchor="w", padx=20, pady=(20, 15))
        
        # 1. API Key
        key_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        key_frame.pack(fill="x", padx=25, pady=5)
        ctk.CTkLabel(key_frame, text="Gemini Key:", width=90, anchor="w").pack(side="left")
        env_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.entry_gemini_key = ctk.CTkEntry(key_frame, placeholder_text="粘贴 API Key...", show="•")
        self.entry_gemini_key.pack(side="left", fill="x", expand=True)
        if env_key: self.entry_gemini_key.insert(0, env_key)
        self.entry_gemini_key.bind("<FocusOut>", lambda _e: self._save_pdf_ocr_config())

        # 1.1 Modelverse Key (Deepseek OCR)
        mv_key_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        mv_key_frame.pack(fill="x", padx=25, pady=5)
        ctk.CTkLabel(mv_key_frame, text="Modelverse Key:", width=90, anchor="w").pack(side="left")
        mv_env_key = os.environ.get("MODELVERSE_API_KEY", "").strip()
        self.entry_modelverse_key = ctk.CTkEntry(mv_key_frame, placeholder_text="Paste API Key...", show="*")
        self.entry_modelverse_key.pack(side="left", fill="x", expand=True)
        if mv_env_key: self.entry_modelverse_key.insert(0, mv_env_key)
        self.entry_modelverse_key.bind("<FocusOut>", lambda _e: self._save_pdf_ocr_config())

        # 2. Model & DPI
        opts_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        opts_frame.pack(fill="x", padx=25, pady=5)
        self.entry_gemini_model = ctk.CTkEntry(opts_frame, placeholder_text="Model", width=140)
        self.entry_gemini_model.insert(0, "gemini-3-flash-preview")
        self.entry_gemini_model.pack(side="left", padx=(90, 5)) # Offset to align
        
        self.entry_pdf_dpi = ctk.CTkEntry(opts_frame, placeholder_text="DPI", width=60)
        self.entry_pdf_dpi.insert(0, "200")
        self.entry_pdf_dpi.pack(side="left")
        ctk.CTkLabel(opts_frame, text="DPI").pack(side="left", padx=5)

        # 2.5 Layout Model
        layout_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        layout_frame.pack(fill="x", padx=25, pady=5)
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

        # 2.6 Page Range
        page_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        page_frame.pack(fill="x", padx=25, pady=5)
        ctk.CTkLabel(page_frame, text="Pages:", width=90, anchor="w").pack(side="left")
        self.entry_page_range = ctk.CTkEntry(page_frame, placeholder_text="1-3,5,8")
        self.entry_page_range.pack(side="left", fill="x", expand=True)

        # 分割线
        ctk.CTkFrame(left_panel, height=2, fg_color=Theme.COLOR_BORDER).pack(fill="x", padx=20, pady=20)

        # 3. PDF 选择与运行
        ctk.CTkLabel(left_panel, text="📄 PDF 处理", font=(Theme.FONT_FAMILY_BOLD[0], 16)).pack(anchor="w", padx=20, pady=(0, 15))
        
        self.btn_select_pdf = ctk.CTkButton(left_panel, text="选择 PDF 文件...", command=self.select_pdf_file, fg_color=Theme.COLOR_BLUE_BTN, hover_color=Theme.COLOR_BLUE_HOVER)
        self.btn_select_pdf.pack(fill="x", padx=20, pady=5)
        
        self.pdf_path_label = ctk.CTkLabel(left_panel, text="未选择文件", text_color=Theme.COLOR_TEXT_SECONDARY, wraplength=250)
        self.pdf_path_label.pack(pady=(0, 15))

        self.btn_run_pdf_ocr = ctk.CTkButton(left_panel, text="🚀 开始切题与识别", command=self.start_pdf_ocr_thread, height=45, font=(Theme.FONT_FAMILY_BOLD[0], 15), fg_color=Theme.COLOR_GREEN_BTN, hover_color=Theme.COLOR_GREEN_HOVER)
        self.btn_run_pdf_ocr.pack(fill="x", padx=20, pady=(10, 20))

        # 进度条
        self.pdf_ocr_progress = ctk.CTkProgressBar(left_panel)
        self.pdf_ocr_progress.pack(fill="x", padx=20, pady=(0, 10))
        self.pdf_ocr_progress.set(0)


        # 右侧：状态与结果
        right_panel = ctk.CTkFrame(container, fg_color=Theme.COLOR_BG_PANEL, corner_radius=Theme.CORNER_RADIUS_L)
        right_panel.grid(row=0, column=1, sticky="nsew")
        
        ctk.CTkLabel(right_panel, text="识别状态 📜", font=(Theme.FONT_FAMILY_BOLD[0], 16)).pack(anchor="w", padx=20, pady=(20, 10))
        
        self.pdf_ocr_status_label = ctk.CTkLabel(right_panel, text="等待开始...", anchor="w", justify="left")
        self.pdf_ocr_status_label.pack(fill="x", padx=20, pady=(0, 10))

        # 结果操作区
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
        card_log.pack(fill="both", expand=True) # 让日志卡片占满剩余空间
        
        log_toolbar = ctk.CTkFrame(card_log, fg_color="transparent")
        log_toolbar.pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(log_toolbar, text="清空日志", command=self._clear_log, width=60, height=24, font=("Arial", 11), fg_color="gray").pack(side="right")
        
        self.log_textbox = ctk.CTkTextbox(card_log, font=(Theme.FONT_CODE[0], 11), activate_scrollbars=True)
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_textbox.configure(state="disabled")

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
            self.btn_run_pdf_ocr.configure(state=st)
            self.entry_gemini_key.configure(state=st)
            self.entry_modelverse_key.configure(state=st)
            self.entry_gemini_model.configure(state=st)
            self.layout_model_menu.configure(state=st)
            self.entry_page_range.configure(state=st)
        self.after(0, apply)

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

    def _run_pdf_ocr(self, pdf_path: str, api_key: str, model_name: str, dpi: int, page_range: str):
        try:
            pdf_path_obj = Path(pdf_path)
            output_root = Path("output") / "pdf_ocr"
            output_dir = output_root / pdf_path_obj.stem
            
            model_label = (self.layout_model_var.get() or "").strip()
            model_key = layout_model_key_from_label(model_label) or DEFAULT_LAYOUT_MODEL
            model_label = layout_model_label_from_key(model_key)

            self._set_pdf_ocr_status(f"正在加载布局模型: {model_label} ...")
            if model_key not in self._layout_extractors:
                try:
                    mv_key = (self.entry_modelverse_key.get() or os.environ.get("MODELVERSE_API_KEY", "")).strip()
                    if model_key == "deepseek_ocr" and not mv_key:
                        raise RuntimeError("è¯·å…ˆå¡«å†? Modelverse API Key (Deepseek OCR æ‰€éœ€)")
                    self._layout_extractors[model_key] = create_layout_extractor(
                        model_key,
                        deepseek_api_key=mv_key or None,
                    )
                except Exception as e:
                    raise RuntimeError(f"模型初始化失败: {e}")
            extractor = self._layout_extractors[model_key]

            range_note = f" (Pages: {page_range})" if page_range else ""
            self._set_pdf_ocr_status(f"正在分析 PDF: {pdf_path_obj.name}{range_note} ...")
            
            ignored = ["abandon"] if model_key == "doclayout_yolo" else None
            items = extractor.process_pdf(
                pdf_path=pdf_path_obj, output_dir=output_root, dpi=dpi, conf=0.25,
                ignored_labels=ignored, page_range=page_range or None, return_items=True
            )

            if not items: raise RuntimeError("?????????")

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

            max_workers = 8
            completed = 0

            def _ocr_one(seq: int, idx: int):
                self._set_pdf_ocr_status(f"正在识别 ({seq}/{len(ocr_indices)})...")
                item = items[idx]
                res = call_gemini_ocr(api_key, model_name, item["path"], prompt)
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
            if k := data.get("gemini_key"): 
                self.entry_gemini_key.delete(0, "end"); self.entry_gemini_key.insert(0, k)
            if mvk := data.get("modelverse_key"):
                self.entry_modelverse_key.delete(0, "end"); self.entry_modelverse_key.insert(0, mvk)
            if model_key := data.get("layout_model"):
                label = layout_model_label_from_key(model_key)
                if label in LAYOUT_MODEL_LABELS.values():
                    self.layout_model_var.set(label)
        except: pass

    def _save_pdf_ocr_config(self):
        try:
            model_label = (self.layout_model_var.get() or "").strip()
            model_key = layout_model_key_from_label(model_label) or DEFAULT_LAYOUT_MODEL
            with open(self._config_path, "w") as f:
                json.dump({
                    "gemini_key": self.entry_gemini_key.get().strip(),
                    "modelverse_key": self.entry_modelverse_key.get().strip(),
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
    def _append_log(self, msg: str):
        if not hasattr(self, "log_textbox"): return
        ts = time.strftime("%H:%M:%S", time.localtime())
        self.after(0, lambda: self._update_log_ui(f"[{ts}] {msg}\n"))
        with self._log_lock:
            with open(self._log_path, "a", encoding="utf-8") as f: f.write(f"[{ts}] {msg}\n")

    def _update_log_ui(self, line):
        try:
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", line)
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
        except: pass

    def _clear_log(self):
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("0.0", "end")
        self.log_textbox.configure(state="disabled")

    def _init_log_file(self) -> str:
        d = os.path.join("output", "logs")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, time.strftime("gui_%Y%m%d.log"))

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
