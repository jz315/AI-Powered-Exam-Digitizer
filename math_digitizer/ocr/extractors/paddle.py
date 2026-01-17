from pathlib import Path
from typing import List, Union, Optional

import numpy as np
import fitz
from PIL import Image

from math_digitizer.ocr.base import parse_page_range


class PPDocLayoutPlusExtractor:
    def __init__(self):
        try:
            from paddleocr import LayoutDetection
        except Exception as e:
            raise RuntimeError(
                "PaddleOCR 未安装，无法使用 PP-DocLayout_plus-L。\n"
                "请先安装 paddlepaddle + paddleocr。"
            ) from e

        self.model = LayoutDetection(model_name="PP-DocLayout_plus-L")
        self.figure_labels = {"image", "table", "chart", "figure_table", "seal", "figure"}
        self.progress_cb = None

    def _iter_results(self, output):
        for res in output:
            if hasattr(res, "res"):
                data = res.res
            else:
                data = res
            if isinstance(data, dict) and "res" in data:
                data = data.get("res")
            yield data

    def process_pdf(
        self,
        pdf_path: Union[str, Path],
        output_dir: Union[str, Path],
        dpi: int = 200,
        conf: float = 0.25,
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

        selected_pages = set(parse_page_range(page_range, doc.page_count))
        for page_idx, page in enumerate(doc):
            if page_idx not in selected_pages:
                continue
            if cb:
                cb(event="page_start", page=page_idx + 1, total=total_pages, model="pp_doclayout_plus_l")
            pix = page.get_pixmap(dpi=dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            np_img = np.array(img)

            output = self.model.predict(np_img, batch_size=1, layout_nms=True)
            boxes = []

            for data in self._iter_results(output):
                if not isinstance(data, dict):
                    continue
                for item in data.get("boxes", []):
                    label = item.get("label")
                    score = float(item.get("score", 0))
                    if score < conf:
                        continue
                    coord = item.get("coordinate") or item.get("bbox")
                    if not coord or len(coord) != 4:
                        continue
                    x1, y1, x2, y2 = coord
                    boxes.append({
                        "label": label,
                        "xyxy": [int(x1), int(y1), int(x2), int(y2)],
                        "y1": int(y1),
                        "x1": int(x1),
                    })

            valid_items = [b for b in boxes if b["label"] not in ignored_labels]
            valid_items.sort(key=lambda item: (item["y1"] // 10, item["x1"]))
            if cb:
                cb(event="page_detected", page=page_idx + 1, total=total_pages, items=len(valid_items), model="pp_doclayout_plus_l")

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
                saved_files.append(file_str)
                saved_items.append({
                    "label": label,
                    "path": file_str,
                    "page": page_idx + 1,
                    "index": i,
                    "xyxy": [x1, y1, x2, y2],
                })

            if cb:
                cb(event="page_saved", page=page_idx + 1, total=total_pages, items=len(valid_items), model="pp_doclayout_plus_l")

        doc.close()
        if return_items:
            return saved_items
        return saved_files
