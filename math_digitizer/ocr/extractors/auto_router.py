import os
from pathlib import Path
from typing import List, Union, Optional

import numpy as np
import cv2
import fitz
import torchvision
from PIL import Image, ImageDraw

from math_digitizer.ocr.base import parse_page_range
from math_digitizer.ocr.extractors.yolo import DocLayoutExtractor
from math_digitizer.ocr.extractors.deepseek import DeepseekOcrLayoutExtractor
from math_digitizer.config import get_api_key, get_config, SecretKey


class AutoRouterLayoutExtractor:
    def __init__(
        self,
        doclayout_kwargs: Optional[dict] = None,
        deepseek_kwargs: Optional[dict] = None,
        require_deepseek: bool = True,
        text_outside_ratio: float = 0.01,
        min_text_ratio: float = 0.0005,
        min_component_area: int = 30,
        binarize_method: str = "hybrid",
        adaptive_block_size: int = 31,
        adaptive_c: int = 15,
        open_kernel: int = 2,
        close_kernel: int = 3,
        use_gemini_probe: bool = False,
        gemini_api_key: Optional[str] = None,
        gemini_model: str = "gemini-2.5-flash-lite",
        use_second_pass: bool = True,
        router_mode: str = "any",
    ):
        self._doclayout = DocLayoutExtractor(**(doclayout_kwargs or {}))
        self._deepseek = None
        self._deepseek_kwargs = deepseek_kwargs or {}
        self._require_deepseek = require_deepseek
        self.progress_cb = None
        self.figure_labels = getattr(self._doclayout, "figure_labels", {"figure"})
        self._cover_ratio = 0.5
        self._text_outside_ratio = float(text_outside_ratio)
        self._min_text_ratio = float(min_text_ratio)
        self._min_component_area = int(min_component_area)
        self._binarize_method = (binarize_method or "hybrid").strip().lower()
        self._adaptive_block_size = int(adaptive_block_size)
        self._adaptive_c = int(adaptive_c)
        self._open_kernel = int(open_kernel)
        self._close_kernel = int(close_kernel)
        self._use_gemini_probe = bool(use_gemini_probe)
        self._gemini_api_key = (gemini_api_key or get_api_key(SecretKey.GEMINI) or os.getenv("GEMINI_API_KEY", "")).strip()
        self._gemini_model = (gemini_model or get_config().auto_router.gemini_model).strip()
        self._use_second_pass = bool(use_second_pass)
        self._router_mode = (router_mode or "any").strip().lower()

        if self._adaptive_block_size % 2 == 0:
            self._adaptive_block_size += 1
        if self._adaptive_block_size < 3:
            self._adaptive_block_size = 3

        if self._require_deepseek:
            self._deepseek = DeepseekOcrLayoutExtractor(**self._deepseek_kwargs)

    def _doclayout_detect_items(
        self,
        img: Image.Image,
        conf: float,
        iou: float,
        ignored_labels: list[str],
        include_ignored: bool = False,
    ) -> list[dict]:
        original_w, original_h = img.width, img.height
        img_input, pad_offset = self._doclayout.check_and_pad(
            img, check_ratio=0.1, min_pad=50, threshold=250
        )
        img_input = self._doclayout.preprocess_for_layout(img_input)
        results = self._doclayout.model.predict(
            img_input, conf=conf, imgsz=1280, device=self._doclayout.device, verbose=False
        )[0]

        boxes = results.boxes.xyxy.clone()
        scores = results.boxes.conf.clone()
        classes = results.boxes.cls.clone()

        if pad_offset > 0:
            boxes[:, [0, 2]] -= pad_offset
            boxes[:, [1, 3]] -= pad_offset
            boxes[:, 0] = boxes[:, 0].clamp(min=0)
            boxes[:, 1] = boxes[:, 1].clamp(min=0)
            boxes[:, 2] = boxes[:, 2].clamp(max=original_w)
            boxes[:, 3] = boxes[:, 3].clamp(max=original_h)

        nms_indices = torchvision.ops.nms(boxes, scores, iou_threshold=iou)
        final_boxes = boxes[nms_indices].cpu().numpy()
        final_scores = scores[nms_indices].cpu().numpy()
        final_classes = classes[nms_indices].cpu().numpy()

        keep_indices = self._doclayout.resolve_containment(
            final_boxes, final_scores, final_classes, iou_threshold=iou
        )
        final_boxes = final_boxes[keep_indices]
        final_classes = final_classes[keep_indices]

        final_boxes = final_boxes.astype(int)
        final_classes = final_classes.astype(int)
        names = results.names

        valid_items = []
        for i in range(len(final_boxes)):
            cls_id = final_classes[i]
            label = names[cls_id]
            if (not include_ignored) and label in ignored_labels:
                continue
            xyxy = final_boxes[i]
            valid_items.append({
                "label": label,
                "xyxy": xyxy,
                "y1": xyxy[1],
                "x1": xyxy[0],
            })

        valid_items = self._doclayout.merge_overlapping_items(
            valid_items, no_merge_labels=set(self._doclayout.figure_labels)
        )
        valid_items.sort(key=lambda item: (item["y1"] // 10, item["x1"]))
        return valid_items

    @staticmethod
    def _inter_area(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
        x1 = max(a[0], b[0])
        y1 = max(a[1], b[1])
        x2 = min(a[2], b[2])
        y2 = min(a[3], b[3])
        if x2 <= x1 or y2 <= y1:
            return 0
        return (x2 - x1) * (y2 - y1)

    def _block_covered(self, block: tuple[int, int, int, int], boxes: list[dict]) -> bool:
        bx1, by1, bx2, by2 = block
        area = max(0, bx2 - bx1) * max(0, by2 - by1)
        if area <= 0:
            return True
        cx = (bx1 + bx2) / 2
        cy = (by1 + by2) / 2
        for item in boxes:
            x1, y1, x2, y2 = item.get("xyxy", [0, 0, 0, 0])
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                return True
        for item in boxes:
            x1, y1, x2, y2 = item.get("xyxy", [0, 0, 0, 0])
            inter = self._inter_area((bx1, by1, bx2, by2), (x1, y1, x2, y2))
            if inter / area >= self._cover_ratio:
                return True
        return False

    def _textness_mask(self, img: Image.Image) -> np.ndarray:
        gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)

        th_otsu = None
        if self._binarize_method in ("otsu", "hybrid"):
            _, th_otsu = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )

        th_adapt = None
        if self._binarize_method in ("adaptive", "hybrid"):
            th_adapt = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                self._adaptive_block_size,
                self._adaptive_c,
            )

        if th_otsu is None and th_adapt is None:
            _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        elif th_otsu is None:
            th = th_adapt
        elif th_adapt is None:
            th = th_otsu
        else:
            th = cv2.bitwise_or(th_otsu, th_adapt)

        if self._open_kernel > 0:
            k = np.ones((self._open_kernel, self._open_kernel), np.uint8)
            th = cv2.morphologyEx(th, cv2.MORPH_OPEN, k, iterations=1)
        if self._close_kernel > 0:
            k = np.ones((self._close_kernel, self._close_kernel), np.uint8)
            th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, k, iterations=1)

        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(th, connectivity=8)
        mask = np.zeros_like(th, dtype=np.uint8)
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area < self._min_component_area:
                continue
            mask[labels == i] = 1
        return mask

    def _erase_boxes(self, img: Image.Image, boxes: list[dict]) -> Image.Image:
        if not boxes:
            return img
        out = img.copy()
        draw = ImageDraw.Draw(out)
        for item in boxes:
            x1, y1, x2, y2 = item.get("xyxy", [0, 0, 0, 0])
            if x2 <= x1 or y2 <= y1:
                continue
            draw.rectangle([int(x1), int(y1), int(x2), int(y2)], fill=(255, 255, 255))
        return out

    def _gemini_has_text(self, img: Image.Image) -> Optional[bool]:
        if not self._gemini_api_key:
            return None
        try:
            from google import genai
            from google.genai import types
        except Exception:
            return None

        client = genai.Client(api_key=self._gemini_api_key)
        generation_config = types.GenerateContentConfig(
            temperature=0.0,
            top_p=0.95,
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
            ],
            thinking_config=types.ThinkingConfig(thinking_level="minimal"),
        )
        prompt = (
            "Look at the image and answer with only YES or NO. "
            "YES if there is any readable text content (letters, digits, math). "
            "NO if there is no readable text (blank or noise)."
        )
        try:
            response = client.models.generate_content(
                model=self._gemini_model,
                contents=[prompt, img],
                config=generation_config,
            )
            text = (response.text or "").strip().upper()
            if "YES" in text:
                return True
            if "NO" in text:
                return False
            return None
        except Exception:
            return None

    def _has_text_outside_boxes(self, img: Image.Image, boxes: list[dict]) -> tuple[bool, dict]:
        text_mask = self._textness_mask(img)
        total_text = int(text_mask.sum())
        if total_text <= 0:
            return False, {"text_ratio": 0.0, "outside_ratio": 0.0}

        if total_text / (img.width * img.height) < self._min_text_ratio:
            return False, {"text_ratio": total_text / (img.width * img.height), "outside_ratio": 0.0}

        box_mask = np.zeros_like(text_mask, dtype=np.uint8)
        for item in boxes:
            x1, y1, x2, y2 = item.get("xyxy", [0, 0, 0, 0])
            x1 = max(0, min(img.width, int(x1)))
            x2 = max(0, min(img.width, int(x2)))
            y1 = max(0, min(img.height, int(y1)))
            y2 = max(0, min(img.height, int(y2)))
            if x2 <= x1 or y2 <= y1:
                continue
            cv2.rectangle(box_mask, (x1, y1), (x2, y2), 1, thickness=-1)

        outside = int((text_mask & (1 - box_mask)).sum())
        ratio = outside / total_text if total_text > 0 else 0.0
        return ratio >= self._text_outside_ratio, {"text_ratio": total_text / (img.width * img.height), "outside_ratio": ratio}

    def _normalize_items(self, items: list[dict], ignored_labels: list[str]) -> list[dict]:
        valid_items = []
        for item in items:
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
        return valid_items

    def _save_items(
        self,
        img: Image.Image,
        items: list[dict],
        save_dir: Path,
        page_idx: int,
        saved_files: list[str],
        saved_items: list[dict],
    ) -> None:
        for i, item in enumerate(items):
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

            saved_files.append(file_str)
            saved_items.append({
                "label": label,
                "path": file_str,
                "page": page_idx + 1,
                "index": i,
                "xyxy": [x1, y1, x2, y2],
            })

    def process_pdf(
        self,
        pdf_path: Union[str, Path],
        output_dir: Union[str, Path],
        dpi: int = 200,
        conf: float = 0.25,
        iou: float = 0.45,
        ignored_labels: Optional[List[str]] = None,
        page_range: Optional[str] = None,
        return_items: bool = False,
        num_workers: int = 1,
    ) -> List[str]:
        cb = self.progress_cb
        if ignored_labels is None:
            ignored_labels = ["abandon"]

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

        total_pages = doc.page_count
        selected_pages = set(parse_page_range(page_range, doc.page_count))
        for page_idx, page in enumerate(doc):
            if page_idx not in selected_pages:
                continue
            if cb:
                cb(event="page_start", page=page_idx + 1, total=total_pages, model="auto_router")
            pix = page.get_pixmap(dpi=dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            doc_items_all = self._doclayout_detect_items(
                img, conf=conf, iou=iou, ignored_labels=ignored_labels, include_ignored=True
            )
            doc_items = [it for it in doc_items_all if it.get("label") not in ignored_labels]
            # --- router signals ---
            use_deepseek_text, stats = self._has_text_outside_boxes(img, doc_items_all)
            if cb:
                cb(event="router_textness", page=page_idx + 1, total=total_pages, model="auto_router", use_deepseek=use_deepseek_text, text_ratio=stats.get("text_ratio", 0.0), outside_ratio=stats.get("outside_ratio", 0.0))

            use_deepseek_second = False
            if self._use_second_pass:
                erased = self._erase_boxes(img, doc_items_all)
                second_items = self._doclayout_detect_items(
                    erased, conf=conf, iou=iou, ignored_labels=ignored_labels, include_ignored=False
                )
                if cb:
                    cb(event="router_second_pass", page=page_idx + 1, total=total_pages, model="auto_router", second_items=len(second_items))
                if len(second_items) > 0:
                    use_deepseek_second = True

            use_deepseek_gemini = False
            if self._use_gemini_probe:
                probe_img = self._erase_boxes(img, doc_items_all)
                gemini_has_text = self._gemini_has_text(probe_img)
                if gemini_has_text is not None:
                    use_deepseek_gemini = bool(gemini_has_text)
                if cb:
                    cb(event="router_gemini_probe", page=page_idx + 1, total=total_pages, model="auto_router", gemini_has_text=gemini_has_text, use_deepseek=use_deepseek_gemini)

            # --- select decision mode ---
            mode = self._router_mode
            if mode in ("textness", "text"):
                use_deepseek = use_deepseek_text
            elif mode in ("second", "second_pass"):
                use_deepseek = use_deepseek_second
            elif mode in ("gemini", "probe"):
                use_deepseek = use_deepseek_gemini
            else:
                # default: any
                use_deepseek = (use_deepseek_text or use_deepseek_second or use_deepseek_gemini)
            if use_deepseek:
                if self._deepseek is None:
                    self._deepseek = DeepseekOcrLayoutExtractor(**self._deepseek_kwargs)
                raw_items = self._deepseek._detect_layout(img)
                raw_items = self._deepseek._scale_boxes_if_needed(raw_items, img.width, img.height)
                items = self._normalize_items(raw_items, ignored_labels=[])
                if cb:
                    cb(event="router_decision", page=page_idx + 1, total=total_pages, model="auto_router", chosen="deepseek_ocr", items=len(items))
            else:
                items = doc_items

            self._save_items(img, items, save_dir, page_idx, saved_files, saved_items)
            if cb:
                cb(
                    event="page_saved",
                    page=page_idx + 1,
                    total=total_pages,
                    items=len(items),
                    items_list=items,
                    model="auto_router",
                )

        doc.close()
        if return_items:
            return saved_items
        return saved_files
