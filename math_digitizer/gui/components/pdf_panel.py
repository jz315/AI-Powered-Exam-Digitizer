from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tkinter import filedialog, messagebox

import pyperclip

from math_digitizer.config import (
    get_config,
    save_config,
    get_api_key,
    set_api_key,
    SecretKey,
)
from math_digitizer.gui.widgets.ocr_widget import call_ocr
from math_digitizer.ocr import (
    DEFAULT_LAYOUT_MODEL,
    LAYOUT_MODEL_LABELS,
    create_layout_extractor,
    layout_model_key_from_label,
    layout_model_label_from_key,
)

_logger = logging.getLogger(__name__)


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

    def _apply_ocr_provider(self, provider: str | None = None, save: bool = True):
        new_provider = (provider or self._get_ocr_provider()).strip().lower()
        key = self._get_ocr_api_key(new_provider)
        self.entry_gemini_key.delete(0, "end")
        if key:
            self.entry_gemini_key.insert(0, key)
        if new_provider == "aliyun":
            current_model = (self.entry_gemini_model.get() or "").strip()
            if not current_model or current_model.startswith("gemini"):
                self.entry_gemini_model.delete(0, "end")
                self.entry_gemini_model.insert(0, "qwen3-vl-plus")
        if save:
            self._save_pdf_ocr_config()

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
            args=(self._pdf_path, ocr_provider, api_key, model, dpi, page_range),
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
            self.after(0, lambda d=str(output_dir): self._update_image_dir_entry(d))
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

    def _run_pdf_ocr(self, pdf_path: str, ocr_provider: str, api_key: str, model_name: str, dpi: int, page_range: str):
        try:
            pdf_path_obj = Path(pdf_path)
            output_root = Path("output") / "pdf_ocr"
            output_dir = output_root / pdf_path_obj.stem
            self._append_log(f"[cfg] pdf={pdf_path_obj}")
            self._append_log(f"[cfg] output_dir={output_dir}")
            self._append_log(f"[cfg] dpi={dpi}, page_range={page_range or 'ALL'}")
            self._append_log(f"[cfg] ocr_provider={ocr_provider}")
            self._append_log(f"[cfg] ocr_model={model_name}")
            
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
                res = call_ocr(ocr_provider, api_key, model_name, item["path"], prompt)
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
            self.after(0, lambda d=str(output_dir): self._update_image_dir_entry(d))
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

    def _update_image_dir_entry(self, path: str):
        if hasattr(self, "entry_image_dir"):
            self.entry_image_dir.delete(0, "end")
            self.entry_image_dir.insert(0, path)

    def _load_pdf_ocr_config(self):
        try:
            config = get_config()
            self._deepseek_keys = {}
            
            if config.ocr.provider in ["gemini", "aliyun"]:
                self.ocr_provider_var.set(config.ocr.provider)

            self._apply_ocr_provider(save=False)

            if config.gemini.model:
                self.entry_gemini_model.delete(0, "end")
                self.entry_gemini_model.insert(0, config.gemini.model)
            
            if config.deepseek.provider in ["modelverse", "siliconflow", "custom"]:
                self.deepseek_provider_var.set(config.deepseek.provider)
            if config.deepseek.base_url:
                self.entry_deepseek_base_url.delete(0, "end")
                self.entry_deepseek_base_url.insert(0, config.deepseek.base_url)
            if config.layout.threads is not None:
                self.entry_layout_threads.delete(0, "end")
                self.entry_layout_threads.insert(0, str(config.layout.threads))
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
            config.gemini.model = self.entry_gemini_model.get().strip() or config.gemini.model
            config.deepseek.provider = self.deepseek_provider_var.get().strip()
            config.deepseek.base_url = self.entry_deepseek_base_url.get().strip()
            config.deepseek.keys_by_provider = {}
            
            config.layout.model = model_key
            try:
                config.layout.threads = int(self.entry_layout_threads.get().strip() or "1")
            except ValueError:
                pass
            
            try:
                config.auto_router.outside_ratio = float(self.entry_auto_outside_ratio.get().strip() or "0.01")
            except ValueError:
                pass
            try:
                config.auto_router.min_text_ratio = float(self.entry_auto_min_text_ratio.get().strip() or "0.0005")
            except ValueError:
                pass
            try:
                config.auto_router.min_component_area = int(self.entry_auto_min_component_area.get().strip() or "30")
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

