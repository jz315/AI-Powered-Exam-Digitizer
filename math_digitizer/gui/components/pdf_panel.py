from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk

import customtkinter as ctk
from PIL import Image
import pyperclip

from math_digitizer.config import (
    get_config,
    save_config,
    get_api_key,
    set_api_key,
    SecretKey,
)
from math_digitizer.config.settings import AutoRouterConfig, LayoutConfig, DeepseekConfig, OcrConfig
from math_digitizer.gui.theme import Theme
from math_digitizer.gui.widgets.collapsible import CollapsibleFrame
from math_digitizer.ocr import (
    DEFAULT_LAYOUT_MODEL,
    LAYOUT_MODEL_LABELS,
    layout_model_key_from_label,
    layout_model_label_from_key,
)
from math_digitizer.gui.services import CancelledError

_logger = logging.getLogger(__name__)



class PdfOcrMixin:
    """PDF OCR 逻辑部分，已与 UI 分离，仅保留绑定逻辑"""

    def _init_ocr_tab_ui(self):
        self.tab_ocr.grid_columnconfigure(0, weight=4)
        self.tab_ocr.grid_columnconfigure(1, weight=6)
        self.tab_ocr.grid_rowconfigure(0, weight=1)

        # === Left Panel: Controls ===
        left_panel = ctk.CTkScrollableFrame(self.tab_ocr, fg_color="transparent")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

        file_card = ctk.CTkFrame(left_panel, fg_color=Theme.COLOR_BG_PANEL, corner_radius=Theme.CORNER_RADIUS_L)
        file_card.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(file_card, text="📄 PDF 文件", font=(Theme.FONT_FAMILY_BOLD[0], 15)).pack(anchor="w", padx=15, pady=(15, 5))

        path_box = ctk.CTkFrame(
            file_card,
            fg_color=Theme.COLOR_BG_MAIN,
            corner_radius=Theme.CORNER_RADIUS_S,
            border_width=1,
            border_color=Theme.COLOR_BORDER,
        )
        path_box.pack(fill="x", padx=15, pady=(0, 10))

        self.pdf_path_label = ctk.CTkLabel(
            path_box,
            text="未选择文件",
            text_color=Theme.COLOR_TEXT_SECONDARY,
            wraplength=360,
            anchor="w",
            justify="left",
        )
        self.pdf_path_label.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(
            file_card,
            text="支持多页 PDF，可在下方设置页码范围",
            font=(Theme.FONT_FAMILY[0], 11),
            text_color=Theme.COLOR_TEXT_SECONDARY,
        ).pack(anchor="w", padx=15, pady=(0, 10))

        btn_grid = ctk.CTkFrame(file_card, fg_color="transparent")
        btn_grid.pack(fill="x", padx=10, pady=(0, 15))
        btn_grid.grid_columnconfigure(0, weight=1)
        btn_grid.grid_columnconfigure(1, weight=1)

        self.btn_select_pdf = ctk.CTkButton(btn_grid, text="📂 选择 PDF", command=self.select_pdf_file, width=100, height=32, fg_color=Theme.COLOR_BLUE_BTN)
        self.btn_select_pdf.grid(row=0, column=0, padx=5, sticky="ew")

        self.btn_run_layout = ctk.CTkButton(btn_grid, text="🔍 仅版面", command=self.start_pdf_layout_thread, width=80, height=32, fg_color="transparent", border_width=1, text_color=Theme.COLOR_TEXT_PRIMARY)
        self.btn_run_layout.grid(row=0, column=1, padx=5, sticky="ew")

        self.btn_run_pdf_ocr = ctk.CTkButton(file_card, text="🚀 开始智能识别 (OCR)", command=self.start_pdf_ocr_thread, height=40, font=(Theme.FONT_FAMILY_BOLD[0], 15), fg_color=Theme.COLOR_GREEN_BTN, hover_color=Theme.COLOR_GREEN_HOVER)
        self.btn_run_pdf_ocr.pack(fill="x", padx=15, pady=(0, 15))

        self.pdf_ocr_progress = ctk.CTkProgressBar(file_card, height=4)
        self.pdf_ocr_progress.pack(fill="x", padx=0, pady=0, side="bottom")
        self.pdf_ocr_progress.set(0)

        config_card = ctk.CTkFrame(left_panel, fg_color=Theme.COLOR_BG_PANEL, corner_radius=Theme.CORNER_RADIUS_L)
        config_card.pack(fill="x", pady=0)

        ctk.CTkLabel(config_card, text="⚙️ 核心参数", font=(Theme.FONT_FAMILY_BOLD[0], 15)).pack(anchor="w", padx=15, pady=(15, 10))

        self.params_grid = ctk.CTkFrame(config_card, fg_color="transparent")
        self.params_grid.pack(fill="x", padx=15, pady=(0, 15))
        self.params_grid.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.params_grid, text="版面模型:", anchor="w").grid(row=0, column=0, sticky="w", pady=5)
        self.layout_model_var = tk.StringVar(value=layout_model_label_from_key(DEFAULT_LAYOUT_MODEL))
        self.layout_model_menu = ctk.CTkOptionMenu(self.params_grid, values=list(LAYOUT_MODEL_LABELS.values()), variable=self.layout_model_var, command=self._on_layout_model_change, height=28)
        self.layout_model_menu.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=5)

        ctk.CTkLabel(self.params_grid, text="OCR 引擎:", anchor="w").grid(row=1, column=0, sticky="w", pady=5)
        self.ocr_provider_var = tk.StringVar(value="gemini")
        self.ocr_provider_menu = ctk.CTkOptionMenu(self.params_grid, values=["gemini", "aliyun"], variable=self.ocr_provider_var, command=self._on_ocr_provider_change, height=28)
        self.ocr_provider_menu.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=5)

        ctk.CTkLabel(self.params_grid, text="OCR Model:", anchor="w").grid(row=2, column=0, sticky="w", pady=5)
        self.entry_gemini_model = ctk.CTkEntry(self.params_grid, placeholder_text="模型名", height=28)
        self.entry_gemini_model.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=5)
        self.entry_gemini_model.bind("<FocusOut>", lambda _e: self._save_pdf_ocr_config())

        ctk.CTkLabel(self.params_grid, text="API Key:", anchor="w").grid(row=3, column=0, sticky="w", pady=5)
        env_key = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("DASHSCOPE_API_KEY", "").strip()
        self.entry_gemini_key = ctk.CTkEntry(self.params_grid, placeholder_text="OCR API Key", show="•", height=28)
        self.entry_gemini_key.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=5)
        if env_key: self.entry_gemini_key.insert(0, env_key)
        self.entry_gemini_key.bind("<FocusOut>", lambda _e: self._save_pdf_ocr_config())

        ctk.CTkLabel(self.params_grid, text="页面范围:", anchor="w").grid(row=4, column=0, sticky="w", pady=5)
        self.entry_page_range = ctk.CTkEntry(self.params_grid, placeholder_text="例: 1-3, 5 (留空=全部)", height=28)
        self.entry_page_range.grid(row=4, column=1, sticky="ew", padx=(10, 0), pady=5)

        self.ds_config_frame = ctk.CTkFrame(config_card, fg_color="transparent")
        self.ds_config_frame.pack(fill="x", padx=15, pady=(0, 15))
        self.ds_config_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.ds_config_frame, text="DeepSeek:", anchor="w", text_color=Theme.COLOR_TEXT_SECONDARY).grid(row=0, column=0, sticky="w", pady=2)
        self.deepseek_provider_var = tk.StringVar(value="modelverse")
        self.deepseek_provider_menu = ctk.CTkOptionMenu(self.ds_config_frame, values=["modelverse", "siliconflow", "custom"], variable=self.deepseek_provider_var, command=self._on_deepseek_provider_change, height=24, width=120)
        self.deepseek_provider_menu.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=2)

        ctk.CTkLabel(self.ds_config_frame, text="DS Key:", anchor="w", text_color=Theme.COLOR_TEXT_SECONDARY).grid(row=1, column=0, sticky="w", pady=2)
        ds_env = os.environ.get("MODELVERSE_API_KEY", "") or os.environ.get("SILICONFLOW_API_KEY", "") or os.environ.get("DEEPSEEK_API_KEY", "")
        self.entry_deepseek_key = ctk.CTkEntry(self.ds_config_frame, placeholder_text="DeepSeek Key", show="•", height=24)
        if ds_env: self.entry_deepseek_key.insert(0, ds_env)
        self.entry_deepseek_key.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=2)
        self.entry_deepseek_key.bind("<FocusOut>", lambda _e: self._save_pdf_ocr_config())

        self._advanced_section = CollapsibleFrame(left_panel, title="🔧 调试设置", expanded=False)
        self._advanced_section.pack(fill="x", pady=(10, 0))
        adv_content = self._advanced_section.content

        self.ar_config_frame = ctk.CTkFrame(adv_content, fg_color="transparent")
        self.ar_config_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.ar_config_frame, text="Router:", anchor="w", text_color=Theme.COLOR_TEXT_SECONDARY).grid(row=0, column=0, sticky="w", pady=2)
        ar_box = ctk.CTkFrame(self.ar_config_frame, fg_color="transparent")
        ar_box.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=2)

        self.router_mode_var = tk.StringVar(value="second_pass")
        self.router_mode_menu = ctk.CTkOptionMenu(
            ar_box,
            values=["any", "textness", "second_pass", "gemini"],
            variable=self.router_mode_var,
            command=lambda _v: self._save_pdf_ocr_config(),
            width=90,
            height=24,
        )
        self.router_mode_menu.pack(side="left")

        ctk.CTkLabel(self.ar_config_frame, text="阈值:", anchor="w", text_color=Theme.COLOR_TEXT_SECONDARY).grid(row=1, column=0, sticky="w", pady=2)
        thresh_box = ctk.CTkFrame(self.ar_config_frame, fg_color="transparent")
        thresh_box.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=2)

        self.entry_auto_outside_ratio = ctk.CTkEntry(thresh_box, width=50, placeholder_text="out%", height=24)
        self.entry_auto_outside_ratio.pack(side="left", padx=(0, 5))
        self.entry_auto_outside_ratio.bind("<FocusOut>", lambda _e: self._save_pdf_ocr_config())

        self.entry_auto_min_text_ratio = ctk.CTkEntry(thresh_box, width=50, placeholder_text="txt%", height=24)
        self.entry_auto_min_text_ratio.pack(side="left", padx=(0, 5))
        self.entry_auto_min_text_ratio.bind("<FocusOut>", lambda _e: self._save_pdf_ocr_config())

        adv_grid = ctk.CTkFrame(adv_content, fg_color="transparent")
        adv_grid.pack(fill="x", padx=5, pady=5)
        adv_grid.grid_columnconfigure(1, weight=1)
        self._advanced_grid = adv_grid

        ctk.CTkLabel(adv_grid, text="DS Base URL:", anchor="w", text_color=Theme.COLOR_TEXT_SECONDARY).grid(row=0, column=0, sticky="w", pady=2)
        self.entry_deepseek_base_url = ctk.CTkEntry(adv_grid, placeholder_text="Custom URL", height=24)
        self.entry_deepseek_base_url.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=2)
        self.entry_deepseek_base_url.bind("<FocusOut>", lambda _e: self._save_pdf_ocr_config())

        self.lbl_gemini_probe = ctk.CTkLabel(adv_grid, text="Gemini Probe:", anchor="w", text_color=Theme.COLOR_TEXT_SECONDARY)
        self.lbl_gemini_probe.grid(row=1, column=0, sticky="w", pady=2)
        self.probe_box = ctk.CTkFrame(adv_grid, fg_color="transparent")
        self.probe_box.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=2)

        self.var_auto_gemini_probe = tk.BooleanVar(value=False)
        self.chk_auto_gemini_probe = ctk.CTkCheckBox(
            self.probe_box,
            text="Enable",
            variable=self.var_auto_gemini_probe,
            command=self._save_pdf_ocr_config,
            height=24,
            checkbox_width=20,
            checkbox_height=20,
        )
        self.chk_auto_gemini_probe.pack(side="left")

        self.entry_auto_gemini_model = ctk.CTkEntry(self.probe_box, placeholder_text="Probe Model", height=24)
        self.entry_auto_gemini_model.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self.entry_auto_gemini_model.bind("<FocusOut>", lambda _e: self._save_pdf_ocr_config())

        ctk.CTkLabel(adv_grid, text="Threads/DPI:", anchor="w", text_color=Theme.COLOR_TEXT_SECONDARY).grid(row=2, column=0, sticky="w", pady=2)
        misc_box = ctk.CTkFrame(adv_grid, fg_color="transparent")
        misc_box.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=2)

        self.entry_layout_threads = ctk.CTkEntry(misc_box, width=40, height=24)
        self.entry_layout_threads.pack(side="left", padx=(0, 5))
        self.entry_layout_threads.bind("<FocusOut>", lambda _e: self._save_pdf_ocr_config())

        self.entry_pdf_dpi = ctk.CTkEntry(misc_box, width=50, placeholder_text="DPI", height=24)
        self.entry_pdf_dpi.pack(side="left")

        self.entry_auto_min_component_area = ctk.CTkEntry(adv_grid) # Hidden

        # === Right Panel: Preview & Logs ===
        right_panel = ctk.CTkFrame(self.tab_ocr, fg_color=Theme.COLOR_BG_PANEL, corner_radius=Theme.CORNER_RADIUS_L)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right_panel.grid_rowconfigure(0, weight=0)
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_rowconfigure(2, weight=0)
        right_panel.grid_rowconfigure(3, weight=0)
        right_panel.grid_columnconfigure(0, weight=1)

        header_r = ctk.CTkFrame(right_panel, fg_color="transparent")
        header_r.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        ctk.CTkLabel(header_r, text="👁️ 识别预览 & 监视器", font=(Theme.FONT_FAMILY_BOLD[0], 15)).pack(side="left")
        self.pdf_ocr_status_label = ctk.CTkLabel(header_r, text="等待开始...", text_color=Theme.COLOR_TEXT_SECONDARY)
        self.pdf_ocr_status_label.pack(side="right")

        self.preview_frame = ctk.CTkFrame(
            right_panel,
            fg_color=("gray94", "#1E1E1E"),
            corner_radius=Theme.CORNER_RADIUS_S,
            border_width=1,
            border_color=Theme.COLOR_BORDER,
        )
        self.preview_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.preview_frame.grid_rowconfigure(0, weight=1)
        
        self.preview_image_label = ctk.CTkLabel(
            self.preview_frame,
            text="[暂无预览]\n运行“仅版面”或“智能识别”后在此显示结果",
            text_color=Theme.COLOR_TEXT_SECONDARY,
            justify="center",
            wraplength=420,
        )
        self.preview_image_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self._preview_source = None
        self._preview_ctk_image = None
        self._preview_resize_after = None
        self.preview_image_label.bind("<Configure>", self._on_preview_resize)

        self.log_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        self.log_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        
        self.btn_toggle_log = ctk.CTkButton(self.log_frame, text="显示日志", command=self._toggle_ocr_log, height=20, width=80, fg_color="transparent", border_width=1, text_color=("gray20", "gray80"))
        self.btn_toggle_log.pack(side="top", anchor="w", pady=(0, 5))
        
        self.ocr_console = ctk.CTkTextbox(self.log_frame, font=(Theme.FONT_CODE[0], 11), height=100, activate_scrollbars=True, fg_color=("gray95", "#2B2B2B"))
        self.ocr_console.pack(fill="x")
        self.ocr_console.insert("0.0", "--- 系统准备就绪 ---\n")
        self.ocr_console.configure(state="disabled")
        self.ocr_console.pack_forget()

        action_bar = ctk.CTkFrame(right_panel, fg_color="transparent")
        action_bar.grid(row=3, column=0, sticky="ew", padx=15, pady=15)
        
        self.btn_copy_prompt_and_ocr = ctk.CTkButton(action_bar, text="📋 复制 Prompt + JSON", command=self.copy_prompt_and_ocr, state="disabled", fg_color=Theme.COLOR_BLUE_BTN, height=36)
        self.btn_copy_prompt_and_ocr.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.btn_open_pdf_ocr_dir = ctk.CTkButton(action_bar, text="📂 打开文件夹", command=self.open_pdf_ocr_output_dir, state="disabled", width=100, height=36, fg_color="transparent", border_width=1, text_color=Theme.COLOR_TEXT_PRIMARY)
        self.btn_open_pdf_ocr_dir.pack(side="left", padx=(5, 0))

        self.btn_copy_pdf_ocr = ctk.CTkButton(action_bar, width=0, height=0) 

        self._load_pdf_ocr_config()
        self._apply_deepseek_provider(save=False)
        self._update_advanced_ui_state()

    def _on_layout_model_change(self, val):
        self._save_pdf_ocr_config()
        self._update_advanced_ui_state()

    def _update_advanced_ui_state(self):
        model_label = self.layout_model_var.get()
        model_key = layout_model_key_from_label(model_label)
        
        if model_key in ["deepseek_ocr", "auto_router"]:
            self.ds_config_frame.pack(fill="x", padx=15, pady=(0, 15), after=self.params_grid)
        else:
            self.ds_config_frame.pack_forget()

        if model_key == "auto_router":
            if not self.ar_config_frame.winfo_manager():
                self.ar_config_frame.pack(fill="x", padx=10, pady=(0, 10), before=self._advanced_grid)
        else:
            self.ar_config_frame.pack_forget()

        self._update_router_probe_visibility(model_key)

    def _update_router_probe_visibility(self, model_key: str | None = None):
        if model_key is None:
            model_label = self.layout_model_var.get()
            model_key = layout_model_key_from_label(model_label)
        provider = self._get_ocr_provider()
        show_probe = model_key == "auto_router" and provider == "gemini"
        if not show_probe and provider != "gemini":
            self.var_auto_gemini_probe.set(False)
        if show_probe:
            self.lbl_gemini_probe.grid()
            self.probe_box.grid()
        else:
            self.lbl_gemini_probe.grid_remove()
            self.probe_box.grid_remove()

    def _toggle_ocr_log(self):
        if self.ocr_console.winfo_viewable():
            self.ocr_console.pack_forget()
            self.btn_toggle_log.configure(text="显示日志")
        else:
            self.ocr_console.pack(fill="x")
            self.btn_toggle_log.configure(text="隐藏日志")

    def _on_preview_resize(self, _event=None):
        if self._preview_source is None:
            return
        if self._preview_resize_after:
            try:
                self.after_cancel(self._preview_resize_after)
            except Exception:
                pass
        self._preview_resize_after = self.after(120, self._render_preview_image)

    def _render_preview_image(self):
        self._preview_resize_after = None
        if self._preview_source is None:
            return
        try:
            self.preview_frame.update_idletasks()
            
            scaling = ctk.ScalingTracker.get_widget_scaling(self.preview_frame)
            frame_w = self.preview_frame.winfo_width()
            frame_h = self.preview_frame.winfo_height()
            img_w, img_h = self._preview_source.size
            
            if frame_w < 100 or frame_h < 100:
                return
            
            padding = 44
            available_w = max(100, frame_w - padding)
            available_h = max(100, frame_h - padding)
            scale = min(available_w / img_w, available_h / img_h, 1.0)
            
            target_w = max(80, int(img_w * scale / scaling))
            target_h = max(80, int(img_h * scale / scaling))
            
            if scale <= 0:
                return
            
            resized = self._preview_source.resize((int(img_w * scale), int(img_h * scale)), Image.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=resized, dark_image=resized, size=(target_w, target_h))
            self._preview_ctk_image = ctk_img
            self.preview_image_label.configure(image=ctk_img, text="")
        except Exception as e:
            _logger.error(f"Failed to render preview: {e}")

    def _update_preview(self, image_path: str):
        if not image_path or not os.path.exists(image_path):
            return
        try:
            with Image.open(image_path) as pil_img:
                self._preview_source = pil_img.copy()
            self._render_preview_image()
        except Exception as e:
            _logger.error(f"Failed to update preview: {e}")

    def _update_image_dir_entry(self, path: str):
        self._pdf_ocr_last_dir = path
        self.btn_open_pdf_ocr_dir.configure(state="normal")

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

    def _ensure_ocr_keys(self):
        if not hasattr(self, "_ocr_keys") or not isinstance(self._ocr_keys, dict):
            self._ocr_keys = {}

    def _ensure_ocr_models(self):
        if not hasattr(self, "_ocr_models") or not isinstance(self._ocr_models, dict):
            self._ocr_models = {}

    def _get_ocr_provider(self) -> str:
        return (self.ocr_provider_var.get() or "gemini").strip().lower()

    def _env_ocr_key(self, provider: str) -> str:
        if provider == "aliyun":
            return os.environ.get("DASHSCOPE_API_KEY", "").strip()
        return os.environ.get("GEMINI_API_KEY", "").strip()

    def _get_ocr_api_key(self, provider: str) -> str:
        entry_key = (self.entry_gemini_key.get() or "").strip()
        if entry_key:
            return entry_key
        if provider == "aliyun":
            keyring_key = get_api_key(SecretKey.DASHSCOPE)
        else:
            keyring_key = get_api_key(SecretKey.GEMINI)
        if keyring_key:
            return keyring_key
        return self._env_ocr_key(provider)

    def _default_ocr_model(self, provider: str) -> str:
        config = get_config()
        return config.ocr.get_model(provider)

    def _apply_ocr_provider(self, provider: str | None = None, save: bool = True):
        self._ensure_ocr_keys()
        self._ensure_ocr_models()
        new_provider = (provider or self._get_ocr_provider()).strip().lower()
        old_provider = getattr(self, "_ocr_provider_current", None)
        if old_provider:
            current_key = (self.entry_gemini_key.get() or "").strip()
            if current_key:
                self._ocr_keys[old_provider] = current_key
            current_model = (self.entry_gemini_model.get() or "").strip()
            if current_model:
                self._ocr_models[old_provider] = current_model

        key = (
            self._ocr_keys.get(new_provider)
            or (get_api_key(SecretKey.DASHSCOPE) if new_provider == "aliyun" else get_api_key(SecretKey.GEMINI))
            or self._env_ocr_key(new_provider)
        )
        self.entry_gemini_key.delete(0, "end")
        if key:
            self.entry_gemini_key.insert(0, key)
        model = self._ocr_models.get(new_provider) or self._default_ocr_model(new_provider)
        self.entry_gemini_model.delete(0, "end")
        if model:
            self.entry_gemini_model.insert(0, model)
        self._ocr_provider_current = new_provider
        if save:
            self._save_pdf_ocr_config()
        self._update_advanced_ui_state()

    def _on_ocr_provider_change(self, _val=None):
        self._apply_ocr_provider(_val, save=True)

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

        new_key = (
            self._deepseek_keys.get(new_provider)
            or get_api_key(SecretKey.for_provider(new_provider))
            or self._env_deepseek_key(new_provider)
        )
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
        if keyring_key := get_api_key(SecretKey.for_provider(provider)):
            return keyring_key
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
        self.ocr_service.reset_cancel()
        self.task_manager.start("layout", cancel_handlers=[self.ocr_service.request_cancel])

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

        ocr_provider = self._get_ocr_provider()
        api_key = self._get_ocr_api_key(ocr_provider)
        if not api_key:
            messagebox.showwarning("提示", "请填写 OCR API Key。")
            return

        model = (self.entry_gemini_model.get() or self._default_ocr_model(ocr_provider)).strip()
        config = get_config()
        try: dpi = int(self.entry_pdf_dpi.get() or str(config.layout.dpi))
        except: dpi = config.layout.dpi
        
        self._pdf_ocr_last_text = ""
        self._pdf_ocr_last_dir = ""
        self.btn_copy_pdf_ocr.configure(state="disabled")
        self.btn_open_pdf_ocr_dir.configure(state="disabled")

        self._set_pdf_ocr_controls_enabled(False)
        self._set_pdf_ocr_progress(0)
        self._set_pdf_ocr_status("正在初始化...")
        self.flash_status("📄 开始处理...")
        self.ocr_service.reset_cancel()
        self.task_manager.start("ocr", cancel_handlers=[self.ocr_service.request_cancel])

        page_range = (self.entry_page_range.get() or "").strip()

        threading.Thread(
            target=self._run_pdf_ocr,
            args=(self._pdf_path, ocr_provider, api_key, model, dpi, page_range),
            daemon=True,
        ).start()

    def _resolve_layout_context(self, api_key: str):
        if not hasattr(self, "ocr_workflow"):
            raise RuntimeError("OCR workflow 未初始化")

        model_label = (self.layout_model_var.get() or "").strip()
        model_key = layout_model_key_from_label(model_label) or DEFAULT_LAYOUT_MODEL
        provider = self._get_deepseek_provider()
        mv_key = self._get_deepseek_api_key(provider)
        base_url = self._resolve_deepseek_base_url(provider)

        auto_cfg = self.ocr_workflow.build_auto_router_config(
            enabled=model_key == "auto_router",
            outside_ratio=self.entry_auto_outside_ratio.get(),
            min_text_ratio=self.entry_auto_min_text_ratio.get(),
            min_component_area=self.entry_auto_min_component_area.get(),
            use_gemini_probe=bool(self.var_auto_gemini_probe.get()),
            gemini_api_key=api_key,
            gemini_model=self.entry_auto_gemini_model.get().strip(),
            router_mode=self.router_mode_var.get().strip(),
        )

        ctx = self.ocr_workflow.resolve_layout_context(
            layout_model_label=model_label,
            deepseek_provider=provider,
            deepseek_key=mv_key,
            deepseek_base_url=base_url,
            auto_router_config=auto_cfg,
        )
        return ctx

    def _run_pdf_layout(self, pdf_path: str, dpi: int, page_range: str, api_key: str):
        try:
            if self._is_task_cancelled():
                self._set_pdf_ocr_status("已取消")
                self.flash_status("⏹ 任务已取消")
                return

            pdf_path_obj = Path(pdf_path)
            output_root = Path("output") / "pdf_ocr"
            ctx = self._resolve_layout_context(api_key)
            self._append_log(f"[cfg] layout_model={ctx.model_key} ({ctx.model_label})")

            job = self.ocr_workflow.build_layout_job(
                pdf_path=pdf_path,
                dpi=dpi,
                page_range=page_range,
                layout_threads=self._get_layout_threads(),
                output_root=output_root,
                ctx=ctx,
            )

            def _preview_cb(path: str):
                self.after(0, lambda p=path: self._update_preview(p))

            result = self.ocr_workflow.ocr_service.run_layout(
                job,
                on_log=self._append_log,
                on_status=self._set_pdf_ocr_status,
                on_progress=self._set_pdf_ocr_progress,
                on_preview=_preview_cb,
            )

            items = result.items
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

            self._pdf_ocr_last_dir = str(result.output_dir)
            self.after(0, lambda d=str(result.output_dir): self._update_image_dir_entry(d))
            self._set_pdf_ocr_progress(1.0)
            self._set_pdf_ocr_status("版面识别完成。")
            self.flash_status("✅ 版面识别完成")
            self.after(0, lambda: self.btn_open_pdf_ocr_dir.configure(state="normal"))
            self.after(0, lambda: messagebox.showinfo("成功", "版面识别完成！"))

        except CancelledError:
            self._set_pdf_ocr_status("已取消")
            self.flash_status("⏹ 已取消")
        except Exception as e:
            self._set_pdf_ocr_status(f"错误: {e}")
            self.flash_status(f"❌ 失败: {e}")
            err_text = str(e)
            self.after(0, lambda msg=err_text: messagebox.showerror("出错", msg))
        finally:
            self._set_pdf_ocr_controls_enabled(True)
            self.task_manager.finish()

    def _run_pdf_ocr(self, pdf_path: str, ocr_provider: str, api_key: str, model_name: str, dpi: int, page_range: str):
        try:
            if self._is_task_cancelled():
                self._set_pdf_ocr_status("已取消")
                self.flash_status("⏹ 任务已取消")
                return

            pdf_path_obj = Path(pdf_path)
            output_root = Path("output") / "pdf_ocr"
            output_dir = output_root / pdf_path_obj.stem
            self._append_log(f"[cfg] pdf={pdf_path_obj}")
            self._append_log(f"[cfg] output_dir={output_dir}")

            ctx = self._resolve_layout_context(api_key)
            self._append_log(f"[cfg] layout_model={ctx.model_key} ({ctx.model_label})")

            prompt = "转文字。与题目无关内容（草稿，手写字）请忽略。特别注意补集符号。不确定的内容不要瞎猜而是插入'【不确定】'到文本里。不要输出解释性话语。"
            job = self.ocr_workflow.build_ocr_job(
                pdf_path=pdf_path,
                dpi=dpi,
                page_range=page_range,
                layout_threads=self._get_layout_threads(),
                output_root=output_root,
                ocr_provider=ocr_provider,
                ocr_api_key=api_key,
                ocr_model=model_name,
                prompt=prompt,
                ctx=ctx,
            )

            def _preview_cb(path: str):
                self.after(0, lambda p=path: self._update_preview(p))

            result = self.ocr_workflow.ocr_service.run_ocr(
                job,
                on_log=self._append_log,
                on_status=self._set_pdf_ocr_status,
                on_progress=self._set_pdf_ocr_progress,
                on_preview=_preview_cb,
            )

            self._pdf_ocr_last_text = result.merged_text
            self._pdf_ocr_last_dir = str(result.output_dir)
            self.after(0, lambda d=str(result.output_dir): self._update_image_dir_entry(d))
            try:
                pyperclip.copy(result.merged_text)
            except Exception:
                pass

            self._set_pdf_ocr_progress(1.0)
            self._set_pdf_ocr_status("完成！结果已复制。")
            self.flash_status("✅ OCR 完成")

            self.after(0, lambda: self.btn_copy_pdf_ocr.configure(state="normal"))
            self.after(0, lambda: self.btn_copy_prompt_and_ocr.configure(state="normal"))
            self.after(0, lambda: self.btn_open_pdf_ocr_dir.configure(state="normal"))
            self.after(0, lambda: messagebox.showinfo("成功", f"处理完成！\n文本已复制。"))

        except CancelledError:
            self._set_pdf_ocr_status("已取消")
            self.flash_status("⏹ 已取消")
        except Exception as e:
            self._set_pdf_ocr_status(f"错误: {e}")
            self.flash_status(f"❌ 失败: {e}")
            err_text = str(e)
            self.after(0, lambda msg=err_text: messagebox.showerror("出错", msg))
        finally:
            self._set_pdf_ocr_controls_enabled(True)
            self.task_manager.finish()

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
            config = get_config()
            self._deepseek_keys = {}
            self._ocr_keys = {}
            self._ocr_models = {}
            
            if config.ocr.provider in ["gemini", "aliyun"]:
                self.ocr_provider_var.set(config.ocr.provider)

            stored_models = getattr(config.ocr, "models_by_provider", {}) or {}
            if isinstance(stored_models, dict):
                self._ocr_models.update(stored_models)

            self._apply_ocr_provider(save=False)

            if config.deepseek.provider in ["modelverse", "siliconflow", "custom"]:
                self.deepseek_provider_var.set(config.deepseek.provider)
            if config.deepseek.base_url:
                self.entry_deepseek_base_url.delete(0, "end")
                self.entry_deepseek_base_url.insert(0, config.deepseek.base_url)
            if config.layout.threads is not None:
                self.entry_layout_threads.delete(0, "end")
                self.entry_layout_threads.insert(0, str(config.layout.threads))
            self.entry_pdf_dpi.delete(0, "end")
            self.entry_pdf_dpi.insert(0, str(config.layout.dpi))
            self.entry_auto_outside_ratio.delete(0, "end")
            self.entry_auto_outside_ratio.insert(0, str(config.auto_router.outside_ratio))
            self.entry_auto_min_text_ratio.delete(0, "end")
            self.entry_auto_min_text_ratio.insert(0, str(config.auto_router.min_text_ratio))
            self.entry_auto_min_component_area.delete(0, "end")
            self.entry_auto_min_component_area.insert(0, str(config.auto_router.min_component_area))
            self.var_auto_gemini_probe.set(config.auto_router.gemini_probe)
            if config.auto_router.gemini_model:
                self.entry_auto_gemini_model.delete(0, "end")
                self.entry_auto_gemini_model.insert(0, config.auto_router.gemini_model)
            if config.auto_router.router_mode in ["any", "textness", "second_pass", "gemini"]:
                self.router_mode_var.set(config.auto_router.router_mode)
            if config.layout.model:
                label = layout_model_label_from_key(config.layout.model)
                if label in LAYOUT_MODEL_LABELS.values():
                    self.layout_model_var.set(label)
            self._apply_deepseek_provider(save=False)
        except Exception as e:
            _logger.warning(f"Failed to load config: {e}")

    def _save_pdf_ocr_config(self):
        try:
            model_label = (self.layout_model_var.get() or "").strip()
            model_key = layout_model_key_from_label(model_label) or DEFAULT_LAYOUT_MODEL
            self._remember_current_deepseek_key()
            
            config = get_config()
            
            config.ocr.provider = self._get_ocr_provider()
            current_model = self.entry_gemini_model.get().strip()
            if current_model:
                if not isinstance(config.ocr.models_by_provider, dict):
                    config.ocr.models_by_provider = {}
                config.ocr.models_by_provider[config.ocr.provider] = current_model
            config.deepseek.provider = self.deepseek_provider_var.get().strip()
            config.deepseek.base_url = self.entry_deepseek_base_url.get().strip()
            config.deepseek.keys_by_provider = {}
            
            config.layout.model = model_key
            try:
                config.layout.threads = int(self.entry_layout_threads.get().strip() or str(config.layout.threads))
            except ValueError:
                pass
            
            try:
                config.auto_router.outside_ratio = float(self.entry_auto_outside_ratio.get().strip() or str(config.auto_router.outside_ratio))
            except ValueError:
                pass
            try:
                config.auto_router.min_text_ratio = float(self.entry_auto_min_text_ratio.get().strip() or str(config.auto_router.min_text_ratio))
            except ValueError:
                pass
            try:
                config.auto_router.min_component_area = int(self.entry_auto_min_component_area.get().strip() or str(config.auto_router.min_component_area))
            except ValueError:
                pass
            config.auto_router.gemini_probe = bool(self.var_auto_gemini_probe.get())
            config.auto_router.gemini_model = self.entry_auto_gemini_model.get().strip()
            config.auto_router.router_mode = self.router_mode_var.get().strip()
            
            save_config(config)
            
            ocr_key = self.entry_gemini_key.get().strip()
            if ocr_key:
                if config.ocr.provider == "aliyun":
                    ok = set_api_key(SecretKey.DASHSCOPE, ocr_key)
                else:
                    ok = set_api_key(SecretKey.GEMINI, ocr_key)
                if not ok:
                    messagebox.showwarning("提示", "系统密钥库不可用，OCR API Key 未能安全保存。")
            
            deepseek_key = self.entry_deepseek_key.get().strip()
            if deepseek_key:
                if not set_api_key(SecretKey.for_provider(config.deepseek.provider), deepseek_key):
                    messagebox.showwarning("提示", "系统密钥库不可用，DeepSeek API Key 未能安全保存。")
                
        except Exception as e:
            _logger.warning(f"Failed to save config: {e}")
