import os
import base64
import io
import re
from pathlib import Path
from typing import List, Union, Optional

import fitz
from PIL import Image

from math_digitizer.ocr.base import _resolve_deepseek_base_url, parse_page_range
from math_digitizer.config import get_api_key, SecretKey


class DeepseekOcrLayoutExtractor:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "deepseek-ai/DeepSeek-OCR",
    ):
        try:
            from openai import OpenAI
        except Exception as e:
            raise RuntimeError(
                "openai SDK 未安装，无法使用 Deepseek OCR。\n"
                "请先安装 openai 包（例如: pip install openai）。"
            ) from e

        resolved_key = api_key or get_api_key(SecretKey.DEEPSEEK_MODELVERSE) or os.getenv("MODELVERSE_API_KEY", "").strip()
        if not resolved_key:
            raise RuntimeError("缺少 MODELVERSE_API_KEY，无法调用 Deepseek OCR。")

        resolved_base_url = _resolve_deepseek_base_url(base_url)
        self._client = OpenAI(api_key=resolved_key, base_url=resolved_base_url)
        self._model = model
        self.figure_labels = set()
        self.progress_cb = None

    def _encode_image(self, img: Image.Image) -> str:
        rgb = img.convert("RGB")
        buffer = io.BytesIO()
        rgb.save(buffer, format="JPEG", quality=90)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _parse_layout(self, content: str):
        if not content:
            return []
        pattern = re.compile(
            r"<\|ref\|>\s*(?P<label>.*?)\s*<\|/ref\|>\s*"
            r"<\|det\|>\s*\[\[\s*"
            r"(?P<x1>-?\d+(?:\.\d+)?)\s*,\s*"
            r"(?P<y1>-?\d+(?:\.\d+)?)\s*,\s*"
            r"(?P<x2>-?\d+(?:\.\d+)?)\s*,\s*"
            r"(?P<y2>-?\d+(?:\.\d+)?)\s*\]\]\s*<\|/det\|>",
            re.S,
        )
        items = []
        for match in pattern.finditer(content):
            label = (match.group("label") or "text").strip()
            if label.lower() == "image":
                label = "figure"
            x1 = int(float(match.group("x1")))
            y1 = int(float(match.group("y1")))
            x2 = int(float(match.group("x2")))
            y2 = int(float(match.group("y2")))
            if x2 <= x1 or y2 <= y1:
                continue
            items.append({"label": label, "xyxy": [x1, y1, x2, y2]})
        return items

    def _detect_layout(self, img: Image.Image) -> list[dict]:
        base64_image = self._encode_image(img)
        prompt = (
            "Detect layout only. Return detection tags like "
            "<|ref|>label<|/ref|><|det|>[[x1, y1, x2, y2]]<|/det|>. "
            "Do not convert to markdown and do not output extra text."
        )
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ],
                }
            ],
        )
        content = response.choices[0].message.content or ""
        return self._parse_layout(content)

    def _scale_boxes_if_needed(self, items: list[dict], img_w: int, img_h: int) -> list[dict]:
        if not items:
            return items
        max_coord = 0
        for it in items:
            x1, y1, x2, y2 = it.get("xyxy", [0, 0, 0, 0])
            max_coord = max(max_coord, x1, y1, x2, y2)

        max_dim = max(img_w, img_h)
        # Heuristic: DeepSeek OCR often returns normalized coords in [0, 1000].
        # If all coords are <= 1000 and the image is larger, scale to pixel space.
        should_scale = False
        if max_coord <= 1000:
            if max_dim > 1000:
                should_scale = True
            elif max_coord > max_dim:
                should_scale = True

        if not should_scale:
            return items

        w_scale = img_w / 1000.0
        h_scale = img_h / 1000.0
        scaled = []
        for it in items:
            x1, y1, x2, y2 = it.get("xyxy", [0, 0, 0, 0])
            sx1 = int(x1 * w_scale)
            sy1 = int(y1 * h_scale)
            sx2 = int(x2 * w_scale)
            sy2 = int(y2 * h_scale)
            new_it = dict(it)
            new_it["xyxy"] = [sx1, sy1, sx2, sy2]
            scaled.append(new_it)
        return scaled

    def process_pdf(
        self,
        pdf_path: Union[str, Path],
        output_dir: Union[str, Path],
        dpi: int = 200,
        conf: float = 0.0,
        ignored_labels: Optional[List[str]] = None,
        page_range: Optional[str] = None,
        return_items: bool = False,
        num_workers: int = 1,
    ) -> List[str]:
        if ignored_labels is None:
            ignored_labels = []

        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")

        save_dir = Path(output_dir) / pdf_path.stem
        save_dir.mkdir(parents=True, exist_ok=True)

        saved_files = []
        saved_items = []

        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            raise RuntimeError(f"无法打开 PDF 文件: {e}")

        cb = getattr(self, "progress_cb", None)
        total_pages = doc.page_count

        selected_pages = list(parse_page_range(page_range, doc.page_count))

        def _process_page(page_idx: int, img: Image.Image):
            if cb:
                cb(event="page_start", page=page_idx + 1, total=total_pages, model="deepseek_ocr")
            detected = self._detect_layout(img)
            detected = self._scale_boxes_if_needed(detected, img.width, img.height)
            valid_items = []
            for item in detected:
                label = item.get("label") or "text"
                if label in ignored_labels:
                    continue
                x1, y1, x2, y2 = item.get("xyxy", [0, 0, 0, 0])
                valid_items.append({
                    "label": label,
                    "xyxy": [int(x1), int(y1), int(x2), int(y2)],
                    "y1": int(y1),
                    "x1": int(x1),
                })

            valid_items.sort(key=lambda item: (item["y1"] // 10, item["x1"]))
            if cb:
                cb(event="page_detected", page=page_idx + 1, total=total_pages, items=len(valid_items), model="deepseek_ocr")

            page_files = []
            page_items = []
            for i, item in enumerate(valid_items):
                label = item["label"]
                xyxy = item["xyxy"]

                x1 = max(0, xyxy[0])
                y1 = max(0, xyxy[1])
                x2 = min(img.width, xyxy[2])
                y2 = min(img.height, xyxy[3])

                if x2 <= x1 or y2 <= y1:
                    continue

                crop = img.crop((x1, y1, x2, y2))
                filename = f"p{page_idx+1:03d}_{i:03d}_{label}.png"
                file_path = save_dir / filename
                crop.save(file_path)
                file_str = str(file_path)
                page_files.append(file_str)
                page_items.append({
                    "label": label,
                    "path": file_str,
                    "page": page_idx + 1,
                    "index": i,
                    "xyxy": [x1, y1, x2, y2],
                })

            if cb:
                cb(event="page_saved", page=page_idx + 1, total=total_pages, items=len(valid_items), model="deepseek_ocr")
            return page_files, page_items

        if num_workers and num_workers > 1:
            from concurrent.futures import ThreadPoolExecutor, as_completed

            page_imgs = []
            for page_idx in selected_pages:
                page = doc.load_page(page_idx)
                pix = page.get_pixmap(dpi=dpi)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                page_imgs.append((page_idx, img))

            with ThreadPoolExecutor(max_workers=int(num_workers)) as executor:
                futures = [executor.submit(_process_page, page_idx, img) for page_idx, img in page_imgs]
                for fut in as_completed(futures):
                    page_files, page_items = fut.result()
                    saved_files.extend(page_files)
                    saved_items.extend(page_items)
        else:
            for page_idx in selected_pages:
                page = doc.load_page(page_idx)
                pix = page.get_pixmap(dpi=dpi)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                page_files, page_items = _process_page(page_idx, img)
                saved_files.extend(page_files)
                saved_items.extend(page_items)

        if saved_items:
            saved_items.sort(key=lambda item: (item["page"], item["index"]))
            saved_files = [item["path"] for item in saved_items]

        doc.close()
        if return_items:
            return saved_items
        return saved_files
