import os
from pathlib import Path
from typing import List, Union, Optional, Tuple

import numpy as np
import cv2
import torch
import torchvision
import fitz
from PIL import Image
from doclayout_yolo import YOLOv10
from doclayout_yolo.nn.tasks import YOLOv10DetectionModel
import dill

from math_digitizer.ocr.base import ensure_model_exists, parse_page_range

# PyTorch 2.6+ 安全序列化设置
try:
    import torch.serialization
    torch.serialization.add_safe_globals([YOLOv10DetectionModel, dill._dill._load_type])
except Exception:
    pass


class DocLayoutExtractor:
    def __init__(
        self,
        model_path: str = None,
        preprocess_layout: bool = True,
        binarize_method: str = "adaptive",
        adaptive_block_size: int = 31,
        adaptive_c: int = 15,
        open_kernel: int = 0,
        close_kernel: int = 0,
        binarize_invert: bool = False,
    ):
        if model_path is None:
            model_path = str(ensure_model_exists())
        
        self.model = YOLOv10(model_path)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.figure_labels = {"figure"}
        self.progress_cb = None
        self.preprocess_layout = bool(preprocess_layout)
        self.binarize_method = (binarize_method or "").strip().lower()
        self.adaptive_block_size = int(adaptive_block_size)
        self.adaptive_c = int(adaptive_c)
        self.open_kernel = int(open_kernel)
        self.close_kernel = int(close_kernel)
        self.binarize_invert = bool(binarize_invert)

        if self.adaptive_block_size % 2 == 0:
            self.adaptive_block_size += 1
        if self.adaptive_block_size < 3:
            self.adaptive_block_size = 3

    def check_and_pad(self, img: Image.Image, check_ratio: float = 0.01, min_pad: int = 50, threshold: int = 250) -> Tuple[Image.Image, int]:
        """
        智能检测边缘并添加白边。
        
        Args:
            img: PIL Image 对象
            check_ratio: 检查边缘宽度的比例 (默认 1%，即 0.01)
            min_pad: 最小添加的 Padding 像素值 (默认 50)
            threshold: 像素亮度阈值 (小于此值视为有内容，0-255)
            
        Returns:
            (处理后的图片, 添加的padding大小)
        """
        # 转换为灰度图的 numpy 数组进行快速计算
        img_gray = img.convert("L")
        img_arr = np.array(img_gray)
        h, w = img_arr.shape

        # 1. 计算检查区域的宽度 (按比例，且至少检查 5 个像素)
        margin_w = max(5, int(w * check_ratio))
        margin_h = max(5, int(h * check_ratio))

        # 2. 切片获取四个边缘区域
        top_edge = img_arr[0:margin_h, :]
        bottom_edge = img_arr[h-margin_h:h, :]
        left_edge = img_arr[:, 0:margin_w]
        right_edge = img_arr[:, w-margin_w:w]

        # 3. 检查是否有内容 (像素值 < 250)
        has_content_at_edge = (
            np.any(top_edge < threshold) or
            np.any(bottom_edge < threshold) or
            np.any(left_edge < threshold) or
            np.any(right_edge < threshold)
        )

        if has_content_at_edge:
            # 4. 计算需要添加的 Padding 大小
            # 策略：取长边的 5% 作为 Padding，但至少 min_pad (50px)
            # 这样大图加得多，小图加得少，但保证足够模型看清
            dynamic_pad = max(min_pad, int(max(w, h) * 0.1))
            
            # 5. 创建新画布并粘贴原图
            new_w = w + 2 * dynamic_pad
            new_h = h + 2 * dynamic_pad
            new_img = Image.new(img.mode, (new_w, new_h), (255, 255, 255))
            new_img.paste(img, (dynamic_pad, dynamic_pad))
            
            return new_img, dynamic_pad
        
        return img, 0

    def preprocess_for_layout(self, img: Image.Image) -> Image.Image:
        if not self.preprocess_layout:
            return img

        gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
        method = self.binarize_method

        if method in ("adaptive", "hybrid"):
            th_adapt = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                self.adaptive_block_size,
                self.adaptive_c,
            )
        else:
            th_adapt = None

        if method in ("otsu", "hybrid"):
            _, th_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:
            th_otsu = None

        if th_adapt is None and th_otsu is None:
            th = gray
        elif th_adapt is None:
            th = th_otsu
        elif th_otsu is None:
            th = th_adapt
        else:
            th = cv2.bitwise_or(th_adapt, th_otsu)

        if self.open_kernel > 0:
            k = np.ones((self.open_kernel, self.open_kernel), np.uint8)
            th = cv2.morphologyEx(th, cv2.MORPH_OPEN, k, iterations=1)
        if self.close_kernel > 0:
            k = np.ones((self.close_kernel, self.close_kernel), np.uint8)
            th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, k, iterations=1)

        if self.binarize_invert:
            th = cv2.bitwise_not(th)

        return Image.fromarray(cv2.cvtColor(th, cv2.COLOR_GRAY2RGB))

    def resolve_containment(self, boxes, scores, classes, iou_threshold=0.1, containment_threshold=0.9):
        """
        Simplified: keep all boxes, no containment filtering.
        """
        if len(boxes) == 0:
            return []
        return list(range(len(boxes)))

    def merge_overlapping_items(self, items, min_intersection: int = 1, no_merge_labels: Optional[set] = None):
        """
        Merge any overlapping boxes and return merged items.
        Label uses the first item in the cluster.
        """
        if not items:
            return []
        if no_merge_labels is None:
            no_merge_labels = set()

        def _intersects(a, b):
            ax1, ay1, ax2, ay2 = a
            bx1, by1, bx2, by2 = b
            ix1 = max(ax1, bx1)
            iy1 = max(ay1, by1)
            ix2 = min(ax2, bx2)
            iy2 = min(ay2, by2)
            return (ix2 - ix1) >= min_intersection and (iy2 - iy1) >= min_intersection

        def _union_box(a, b):
            return [
                min(a[0], b[0]),
                min(a[1], b[1]),
                max(a[2], b[2]),
                max(a[3], b[3]),
            ]

        fixed = [it for it in items if (it.get("label") in no_merge_labels)]
        remaining = [it for it in items if (it.get("label") not in no_merge_labels)]
        merged = []

        while remaining:
            seed = remaining.pop(0)
            cluster = [seed]
            changed = True
            while changed:
                changed = False
                i = 0
                while i < len(remaining):
                    if any(_intersects(remaining[i]["xyxy"], c["xyxy"]) for c in cluster):
                        cluster.append(remaining.pop(i))
                        changed = True
                    else:
                        i += 1

            merged_box = cluster[0]["xyxy"]
            for c in cluster[1:]:
                merged_box = _union_box(merged_box, c["xyxy"])

            merged.append({
                "label": cluster[0]["label"],
                "xyxy": merged_box,
                "y1": merged_box[1],
                "x1": merged_box[0],
            })

        if fixed:
            merged.extend(fixed)
        return merged
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

        cb = getattr(self, "progress_cb", None)
        total_pages = doc.page_count

        for page_idx, page in enumerate(doc):
            if cb:
                cb(event="page_start", page=page_idx + 1, total=total_pages, model="doclayout_yolo")
            pix = page.get_pixmap(dpi=dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            original_w, original_h = img.width, img.height

            # --- 步骤 0: 智能加白边 (按比例检测) ---
            # check_ratio=0.01 表示检查边缘 1% 的区域
            # min_pad=50 表示最少加 50px，如果图很大，会加更多(5%)
            img_input, pad_offset = self.check_and_pad(img, check_ratio=0.1, min_pad=50, threshold=250)
            img_input = self.preprocess_for_layout(img_input)

            # --- 步骤 1: 模型预测 ---
            results = self.model.predict(img_input, conf=conf, imgsz=1280, device=self.device, verbose=False)[0]

            boxes = results.boxes.xyxy.clone()
            scores = results.boxes.conf.clone()
            classes = results.boxes.cls.clone()

            # --- 步骤 1.5: 坐标还原 ---
            if pad_offset > 0:
                # 减去 padding
                boxes[:, [0, 2]] -= pad_offset
                boxes[:, [1, 3]] -= pad_offset
                
                # 边界截断 (防止越界)
                boxes[:, 0] = boxes[:, 0].clamp(min=0)
                boxes[:, 1] = boxes[:, 1].clamp(min=0)
                boxes[:, 2] = boxes[:, 2].clamp(max=original_w)
                boxes[:, 3] = boxes[:, 3].clamp(max=original_h)

            # --- 步骤 2: 初步 NMS ---
            nms_indices = torchvision.ops.nms(boxes, scores, iou_threshold=iou)
            
            final_boxes = boxes[nms_indices].cpu().numpy()
            final_scores = scores[nms_indices].cpu().numpy()
            final_classes = classes[nms_indices].cpu().numpy()

            # --- 步骤 3: 包含关系过滤 ---
            keep_indices = self.resolve_containment(final_boxes, final_scores, final_classes, iou_threshold=iou)
            
            final_boxes = final_boxes[keep_indices]
            final_classes = final_classes[keep_indices]

            final_boxes = final_boxes.astype(int)
            final_classes = final_classes.astype(int)
            names = results.names

            # --- 步骤 4: 收集有效元素 ---
            valid_items = []
            
            for i in range(len(final_boxes)):
                cls_id = final_classes[i]
                label = names[cls_id]
                xyxy = final_boxes[i]

                if label in ignored_labels:
                    continue

                valid_items.append({
                    "label": label,
                    "xyxy": xyxy,
                    "y1": xyxy[1],
                    "x1": xyxy[0],
                })

            # --- 步骤 5: 排序 ---
            valid_items = self.merge_overlapping_items(valid_items, no_merge_labels=set(self.figure_labels))
            valid_items.sort(key=lambda item: (item["y1"] // 10, item["x1"]))
            if cb:
                cb(event="page_detected", page=page_idx + 1, total=total_pages, items=len(valid_items), model="doclayout_yolo")

            # --- 步骤 6: 裁剪并保存 ---
            for i, item in enumerate(valid_items):
                label = item["label"]
                xyxy = item["xyxy"]
                
                x1 = max(0, xyxy[0])
                y1 = max(0, xyxy[1])
                x2 = min(original_w, xyxy[2])
                y2 = min(original_h, xyxy[3])
                
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
                cb(event="page_saved", page=page_idx + 1, total=total_pages, items=len(valid_items), model="doclayout_yolo")

        doc.close()
        if return_items:
            return saved_items
        return saved_files
