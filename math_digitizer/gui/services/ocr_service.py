from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from PIL import Image, ImageDraw

from math_digitizer.ocr import (
    DEFAULT_LAYOUT_MODEL,
    create_layout_extractor,
    layout_model_label_from_key,
)
from math_digitizer.gui.widgets.ocr_widget import call_ocr


LogFn = Callable[[str], None]
StatusFn = Callable[[str], None]
ProgressFn = Callable[[float], None]
PreviewFn = Callable[[str], None]


@dataclass
class LayoutJob:
    pdf_path: str
    layout_model_key: str
    deepseek_provider: str
    deepseek_key: str
    deepseek_base_url: str | None
    auto_router_config: dict | None
    dpi: int
    page_range: str
    layout_threads: int
    output_root: Path = Path("output") / "pdf_ocr"


@dataclass
class LayoutResult:
    items: list[dict]
    output_dir: Path
    layout_model_key: str


@dataclass
class OcrJob:
    pdf_path: str
    layout_model_key: str
    deepseek_provider: str
    deepseek_key: str
    deepseek_base_url: str | None
    auto_router_config: dict | None
    dpi: int
    page_range: str
    layout_threads: int
    ocr_provider: str
    ocr_api_key: str
    ocr_model: str
    prompt: str
    output_root: Path = Path("output") / "pdf_ocr"


@dataclass
class OcrResult:
    merged_text: str
    output_dir: Path
    items: list[dict]


class CancelledError(Exception):
    pass


class OcrService:
    def __init__(self) -> None:
        self._layout_extractors: dict[str, object] = {}
        self._cancel_requested = False

    def reset_cancel(self) -> None:
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def _check_cancel(self) -> None:
        if self._cancel_requested:
            raise CancelledError("操作已取消")

    def _preview_color(self, label: str | None):
        label = (label or "").lower()
        if label in ["title", "header", "footer", "page_no"]:
            return (128, 128, 128)
        if label in ["text", "plain_text"]:
            return (0, 102, 255)
        if label in ["formula", "equation"]:
            return (0, 200, 80)
        if label in ["figure", "image", "table", "chart", "seal", "figure_table"]:
            return (255, 140, 0)
        if label == "abandon":
            return (255, 0, 0)
        return (180, 0, 220)

    def _render_preview_for_page(
        self,
        pdf_path: Path,
        page_num: int,
        dpi: int,
        items_list: list[dict],
        output_dir: Path,
    ) -> str | None:
        if not items_list:
            return None
        doc = None
        try:
            import fitz

            doc = fitz.open(str(pdf_path))
            page_idx = max(0, page_num - 1)
            if page_idx >= doc.page_count:
                return None
            page = doc.load_page(page_idx)
            pix = page.get_pixmap(dpi=dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            draw = ImageDraw.Draw(img)

            for it in items_list:
                bbox = it.get("xyxy")
                if bbox is None:
                    bbox = it.get("bbox")
                if bbox is None:
                    bbox = it.get("coordinate")
                if bbox is None:
                    continue
                try:
                    if len(bbox) != 4:
                        continue
                except Exception:
                    continue
                try:
                    x1, y1, x2, y2 = [int(v) for v in bbox]
                except Exception:
                    continue
                if x2 <= x1 or y2 <= y1:
                    continue
                color = self._preview_color(it.get("label"))
                draw.rectangle([x1, y1, x2, y2], outline=color, width=2)

            preview_path = output_dir / f"preview_p{page_num}.png"
            output_dir.mkdir(parents=True, exist_ok=True)
            img.save(preview_path)
            return str(preview_path)
        finally:
            if doc is not None:
                try:
                    doc.close()
                except Exception:
                    pass

    def _get_extractor(
        self,
        model_key: str,
        deepseek_key: str,
        deepseek_base_url: str | None,
        auto_router_config: dict | None,
    ):
        key = model_key or DEFAULT_LAYOUT_MODEL
        if key in self._layout_extractors:
            return self._layout_extractors[key]
        self._layout_extractors[key] = create_layout_extractor(
            key,
            deepseek_api_key=deepseek_key or None,
            deepseek_base_url=deepseek_base_url or None,
            auto_router_config=auto_router_config,
        )
        return self._layout_extractors[key]

    def run_layout(
        self,
        job: LayoutJob,
        *,
        on_log: LogFn | None = None,
        on_status: StatusFn | None = None,
        on_progress: ProgressFn | None = None,
        on_preview: PreviewFn | None = None,
    ) -> LayoutResult:
        pdf_path_obj = Path(job.pdf_path)
        output_root = Path(job.output_root)
        output_dir = output_root / pdf_path_obj.stem

        model_key = job.layout_model_key or DEFAULT_LAYOUT_MODEL
        model_label = layout_model_label_from_key(model_key)
        if on_log:
            on_log(f"[cfg] pdf={pdf_path_obj}")
            on_log(f"[cfg] output_dir={output_dir}")
            on_log(f"[cfg] dpi={job.dpi}, page_range={job.page_range or 'ALL'}")
            on_log(f"[cfg] layout_model={model_key} ({model_label})")

        if on_status:
            range_note = f" (Pages: {job.page_range})" if job.page_range else ""
            on_status(f"正在分析 PDF: {pdf_path_obj.name}{range_note} ...")

        extractor = self._get_extractor(
            model_key,
            deepseek_key=job.deepseek_key,
            deepseek_base_url=job.deepseek_base_url,
            auto_router_config=job.auto_router_config,
        )

        def _layout_log(**info):
            self._check_cancel()
            event = info.get("event")
            page = info.get("page")
            total = info.get("total")
            model = info.get("model")
            if on_log:
                if event == "page_start":
                    on_log(f"[layout] page {page}/{total} start ({model})")
                elif event == "page_detected":
                    on_log(f"[layout] page {page}/{total} detected items={info.get('items')} ({model})")
                elif event == "page_saved":
                    on_log(f"[layout] page {page}/{total} saved items={info.get('items')} ({model})")
                elif event == "router_textness":
                    on_log(
                        f"[router] page {page}/{total} text_ratio={info.get('text_ratio', 0):.6f} "
                        f"outside_ratio={info.get('outside_ratio', 0):.6f} use_deepseek={info.get('use_deepseek')}"
                    )
                elif event == "router_gemini_probe":
                    on_log(
                        f"[router] page {page}/{total} gemini_probe={info.get('gemini_has_text')} use_deepseek={info.get('use_deepseek')}"
                    )
                elif event == "router_decision":
                    on_log(f"[router] page {page}/{total} choose={info.get('chosen')} items={info.get('items')}")
                elif event == "router_second_pass":
                    on_log(f"[router] page {page}/{total} second_pass items={info.get('second_items')}")
                else:
                    on_log(f"[layout] page {page}/{total} event={event} info={info}")

            if event == "page_saved":
                items_list = info.get("items_list")
                if items_list and on_preview:
                    preview_path = self._render_preview_for_page(
                        pdf_path_obj,
                        int(page),
                        job.dpi,
                        items_list,
                        output_dir,
                    )
                    if preview_path:
                        on_preview(preview_path)

        if hasattr(extractor, "progress_cb"):
            extractor.progress_cb = _layout_log

        ignored = ["abandon"] if model_key == "doclayout_yolo" else None
        if on_log:
            on_log(f"[cfg] ignored_labels={ignored}")

        self._check_cancel()
        layout_kwargs = {}
        if model_key == "deepseek_ocr":
            layout_kwargs["num_workers"] = job.layout_threads
            if on_log:
                on_log(f"[cfg] layout_threads={job.layout_threads}")

        items = extractor.process_pdf(
            pdf_path=pdf_path_obj,
            output_dir=output_root,
            dpi=job.dpi,
            conf=0.25,
            ignored_labels=ignored,
            page_range=job.page_range or None,
            return_items=True,
            **layout_kwargs,
        )

        self._check_cancel()
        if on_progress:
            on_progress(1.0)

        return LayoutResult(items=items, output_dir=output_dir, layout_model_key=model_key)

    def run_ocr(
        self,
        job: OcrJob,
        *,
        on_log: LogFn | None = None,
        on_status: StatusFn | None = None,
        on_progress: ProgressFn | None = None,
        on_preview: PreviewFn | None = None,
    ) -> OcrResult:
        pdf_path_obj = Path(job.pdf_path)
        output_root = Path(job.output_root)
        output_dir = output_root / pdf_path_obj.stem

        if on_log:
            on_log(f"[cfg] pdf={pdf_path_obj}")
            on_log(f"[cfg] output_dir={output_dir}")
            on_log(f"[cfg] dpi={job.dpi}, page_range={job.page_range or 'ALL'}")
            on_log(f"[cfg] ocr_provider={job.ocr_provider}")
            on_log(f"[cfg] ocr_model={job.ocr_model}")

        model_key = job.layout_model_key or DEFAULT_LAYOUT_MODEL
        model_label = layout_model_label_from_key(model_key)
        if on_log:
            on_log(f"[cfg] layout_model={model_key} ({model_label})")

        if on_status:
            range_note = f" (Pages: {job.page_range})" if job.page_range else ""
            on_status(f"正在分析 PDF: {pdf_path_obj.name}{range_note} ...")

        extractor = self._get_extractor(
            model_key,
            deepseek_key=job.deepseek_key,
            deepseek_base_url=job.deepseek_base_url,
            auto_router_config=job.auto_router_config,
        )

        def _layout_log(**info):
            self._check_cancel()
            event = info.get("event")
            page = info.get("page")
            total = info.get("total")
            model = info.get("model")
            if on_log:
                if event == "page_start":
                    on_log(f"[layout] page {page}/{total} start ({model})")
                elif event == "page_detected":
                    on_log(f"[layout] page {page}/{total} detected items={info.get('items')} ({model})")
                elif event == "page_saved":
                    on_log(f"[layout] page {page}/{total} saved items={info.get('items')} ({model})")
                elif event == "router_textness":
                    on_log(
                        f"[router] page {page}/{total} text_ratio={info.get('text_ratio', 0):.6f} "
                        f"outside_ratio={info.get('outside_ratio', 0):.6f} use_deepseek={info.get('use_deepseek')}"
                    )
                elif event == "router_gemini_probe":
                    on_log(
                        f"[router] page {page}/{total} gemini_probe={info.get('gemini_has_text')} use_deepseek={info.get('use_deepseek')}"
                    )
                elif event == "router_decision":
                    on_log(f"[router] page {page}/{total} choose={info.get('chosen')} items={info.get('items')}")
                elif event == "router_second_pass":
                    on_log(f"[router] page {page}/{total} second_pass items={info.get('second_items')}")
                else:
                    on_log(f"[layout] page {page}/{total} event={event} info={info}")

            if event == "page_saved":
                items_list = info.get("items_list")
                if items_list and on_preview:
                    preview_path = self._render_preview_for_page(
                        pdf_path_obj,
                        int(page),
                        job.dpi,
                        items_list,
                        output_dir,
                    )
                    if preview_path:
                        on_preview(preview_path)

        if hasattr(extractor, "progress_cb"):
            extractor.progress_cb = _layout_log

        ignored = ["abandon"] if model_key == "doclayout_yolo" else None
        if on_log:
            on_log(f"[cfg] ignored_labels={ignored}")

        self._check_cancel()
        layout_kwargs = {}
        if model_key == "deepseek_ocr":
            layout_kwargs["num_workers"] = job.layout_threads
            if on_log:
                on_log(f"[cfg] layout_threads={job.layout_threads}")

        items = extractor.process_pdf(
            pdf_path=pdf_path_obj,
            output_dir=output_root,
            dpi=job.dpi,
            conf=0.25,
            ignored_labels=ignored,
            page_range=job.page_range or None,
            return_items=True,
            **layout_kwargs,
        )
        self._check_cancel()
        if not items:
            raise RuntimeError("No OCR items detected")

        if on_log:
            on_log(f"[layout] detected_items={len(items)}")
        page_counts: dict[int, int] = {}
        for it in items:
            p = it.get("page")
            if not p:
                continue
            page_counts[p] = page_counts.get(p, 0) + 1
        if page_counts and on_log:
            pages = ",".join(str(p) for p in sorted(page_counts))
            on_log(f"[layout] pages={pages}")
            for p in sorted(page_counts):
                on_log(f"[layout] page {p} items={page_counts[p]}")

        figure_labels = getattr(extractor, "figure_labels", {"figure"})
        full_text_list: list[str] = []
        total_items = len(items)
        results: list[str | None] = [None] * total_items
        ocr_indices: list[int] = []

        for idx, item in enumerate(items):
            label = item.get("label")
            if label in figure_labels:
                path_str = item.get("path", "")
                if path_str:
                    try:
                        rel = Path(path_str).relative_to(output_dir)
                        rel_str = str(rel)
                    except Exception:
                        rel_str = path_str
                    rel_str = rel_str.replace("\\", "/")
                else:
                    rel_str = ""
                results[idx] = f"![img]({rel_str})"
            else:
                ocr_indices.append(idx)

        if on_progress:
            on_progress(0.3)
        if on_status:
            on_status(
                f"正在识别（共 {total_items} 项，OCR {len(ocr_indices)} 项 / 图像 {total_items - len(ocr_indices)} 项）处理中..."
            )
        if on_log:
            on_log(f"[ocr] queue={len(ocr_indices)}")

        max_workers = 8
        completed = 0

        def _ocr_one(seq: int, idx: int):
            self._check_cancel()
            if on_status:
                on_status(f"正在识别 ({seq}/{len(ocr_indices)})...")
            item = items[idx]
            item_name = Path(item.get("path", "")).name
            if on_log:
                on_log(f"[ocr] start {seq}/{len(ocr_indices)} file={item_name}")
            res = call_ocr(job.ocr_provider, job.ocr_api_key, job.ocr_model, item["path"], job.prompt)
            if on_log:
                on_log(f"[ocr] done {seq}/{len(ocr_indices)} file={item_name} len={len(res)}")
            self._check_cancel()
            return idx, res

        if ocr_indices:
            from concurrent.futures import ThreadPoolExecutor, as_completed

            executor = ThreadPoolExecutor(max_workers=max_workers)
            futures = [executor.submit(_ocr_one, seq + 1, idx) for seq, idx in enumerate(ocr_indices)]
            cancelled = False
            try:
                for future in as_completed(futures):
                    self._check_cancel()
                    idx, txt = future.result()
                    results[idx] = txt
                    completed += 1
                    if on_progress:
                        on_progress(0.3 + (0.6 * completed / len(ocr_indices)))
            except CancelledError:
                cancelled = True
                for fut in futures:
                    fut.cancel()
                executor.shutdown(wait=False, cancel_futures=True)
                raise
            finally:
                if not cancelled:
                    executor.shutdown(wait=True)
        else:
            if on_progress:
                on_progress(0.9)

        for txt in results:
            if txt:
                full_text_list.append(f"{txt}")

        image_dir_path = str(output_dir.resolve()).replace("\\", "/")
        header = f"<!-- image_dir: {image_dir_path} -->\n\n"
        merged_text = header + "\n".join(full_text_list)

        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_dir / "merged.md", "w", encoding="utf-8") as f:
            f.write(merged_text)

        if on_progress:
            on_progress(1.0)

        return OcrResult(merged_text=merged_text, output_dir=output_dir, items=items)
