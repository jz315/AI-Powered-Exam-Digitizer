import os
import base64
import io
import re
from pathlib import Path
from typing import List, Union, Optional, Tuple

import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import torch
import torchvision
import numpy as np
import cv2
from doclayout_yolo import YOLOv10
from doclayout_yolo.nn.tasks import YOLOv10DetectionModel
import dill

# 假设 app_paths 是你项目中的模块
from app_paths import get_resource_path

DEFAULT_LAYOUT_MODEL = "doclayout_yolo"
LAYOUT_MODEL_LABELS = {
    "doclayout_yolo": "DocLayout-YOLO (DocStructBench 1280)",
    "pp_doclayout_plus_l": "PP-DocLayout_plus-L (PaddleOCR)",
    "deepseek_ocr": "Deepseek OCR (Layout Only)",
    "auto_router": "Auto (DocLayout->Deepseek if missed)",
}

MODEL_FILENAME = "doclayout_yolo_docstructbench_imgsz1280_2501.pt"
MODEL_DIR = get_resource_path("layout_models")
HF_REPO_ID = "juliozhao/DocLayout-YOLO-DocStructBench-imgsz1280-2501"


def _resolve_deepseek_base_url(explicit_base_url: Optional[str]) -> str:
    if explicit_base_url:
        return explicit_base_url
    provider = (os.getenv("DEEPSEEK_OCR_PROVIDER", "") or "").strip().lower()
    if provider == "siliconflow":
        return "https://api.siliconflow.cn/v1"
    env_base_url = (os.getenv("DEEPSEEK_OCR_BASE_URL", "") or "").strip()
    if env_base_url:
        return env_base_url
    return "https://api.modelverse.cn/v1/"


def ensure_model_exists() -> Path:
    model_path = MODEL_DIR / MODEL_FILENAME
    
    if model_path.exists():
        return model_path
    
    print(f"模型文件不存在，尝试从 HuggingFace 下载: {MODEL_FILENAME}")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        from huggingface_hub import hf_hub_download
        downloaded_path = hf_hub_download(
            repo_id=HF_REPO_ID,
            filename=MODEL_FILENAME,
            local_dir=str(MODEL_DIR),
        )
        print(f"模型下载完成: {downloaded_path}")
        return Path(downloaded_path)
    except Exception as e:
        raise RuntimeError(
            f"无法下载模型文件: {e}\n\n"
            f"请手动下载模型:\n"
            f"  1. 访问 https://huggingface.co/{HF_REPO_ID}\n"
            f"  2. 下载 {MODEL_FILENAME}\n"
            f"  3. 放到 {MODEL_DIR}/ 目录下"
        ) from e

# PyTorch 2.6+ 安全序列化设置
try:
    import torch.serialization
    torch.serialization.add_safe_globals([YOLOv10DetectionModel, dill._dill._load_type])
except Exception:
    pass

def layout_model_label_from_key(key: str) -> str:
    return LAYOUT_MODEL_LABELS.get(key, key)


def layout_model_key_from_label(label: str) -> str:
    for key, value in LAYOUT_MODEL_LABELS.items():
        if value == label:
            return key
    return label


def create_layout_extractor(
    model_key: str,
    deepseek_api_key: Optional[str] = None,
    deepseek_base_url: Optional[str] = None,
    deepseek_model: Optional[str] = None,
    auto_router_config: Optional[dict] = None,
):
    if model_key == "pp_doclayout_plus_l":
        return PPDocLayoutPlusExtractor()
    if model_key == "deepseek_ocr":
        kwargs = {}
        if deepseek_api_key:
            kwargs["api_key"] = deepseek_api_key
        if deepseek_base_url:
            kwargs["base_url"] = deepseek_base_url
        if deepseek_model:
            kwargs["model"] = deepseek_model
        return DeepseekOcrLayoutExtractor(**kwargs)
    if model_key == "auto_router":
        kwargs = {}
        if deepseek_api_key:
            kwargs["api_key"] = deepseek_api_key
        if deepseek_base_url:
            kwargs["base_url"] = deepseek_base_url
        if deepseek_model:
            kwargs["model"] = deepseek_model
        return AutoRouterLayoutExtractor(deepseek_kwargs=kwargs, **(auto_router_config or {}))
    return DocLayoutExtractor()


def parse_page_range(page_range: str, max_pages: int) -> list[int]:
    if not page_range:
        return list(range(max_pages))
    page_range = page_range.replace(" ", "")
    if not page_range:
        return list(range(max_pages))

    pages: set[int] = set()
    parts = [p for p in page_range.split(",") if p]
    for part in parts:
        if "-" in part:
            left, right = part.split("-", 1)
            start = int(left) if left else 1
            end = int(right) if right else max_pages
        else:
            start = end = int(part)

        if start < 1:
            start = 1
        if end > max_pages:
            end = max_pages
        if end < start:
            continue
        for p in range(start, end + 1):
            pages.add(p - 1)

    return sorted(pages)


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

        api_key = api_key or os.getenv("MODELVERSE_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("缺少 MODELVERSE_API_KEY，无法调用 Deepseek OCR。")

        resolved_base_url = _resolve_deepseek_base_url(base_url)
        self._client = OpenAI(api_key=api_key, base_url=resolved_base_url)
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
        self._gemini_api_key = (gemini_api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        self._gemini_model = (gemini_model or "gemini-2.5-flash-lite").strip()
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
                cb(event="page_saved", page=page_idx + 1, total=total_pages, items=len(items), model="auto_router")

        doc.close()
        if return_items:
            return saved_items
        return saved_files
