import os
import base64
import io
import re
from pathlib import Path
from typing import List, Union, Optional, Tuple

import fitz  # PyMuPDF
from PIL import Image
import torch
import torchvision
import numpy as np
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
}

MODEL_FILENAME = "doclayout_yolo_docstructbench_imgsz1280_2501.pt"
MODEL_DIR = get_resource_path("layout_models")
HF_REPO_ID = "juliozhao/DocLayout-YOLO-DocStructBench-imgsz1280-2501"


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
    def __init__(self, model_path: str = None):
        if model_path is None:
            model_path = str(ensure_model_exists())
        
        self.model = YOLOv10(model_path)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.figure_labels = {"figure"}

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

    def resolve_containment(self, boxes, scores, classes, iou_threshold=0.1):
        """
        处理包含关系：如果一个框被另一个框完全包含（或包含比例很高），
        则根据置信度保留分高的那个。
        """
        if len(boxes) == 0:
            return []

        areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        order = scores.argsort()[::-1]
        keep = []

        while order.size > 0:
            i = order[0]
            keep.append(i)
            
            if order.size == 1:
                break
            
            rest_indices = order[1:]
            xx1 = np.maximum(boxes[i, 0], boxes[rest_indices, 0])
            yy1 = np.maximum(boxes[i, 1], boxes[rest_indices, 1])
            xx2 = np.minimum(boxes[i, 2], boxes[rest_indices, 2])
            yy2 = np.minimum(boxes[i, 3], boxes[rest_indices, 3])

            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h

            rest_areas = areas[rest_indices]
            
            # 包含率：交集 / 剩余框自身的面积
            containment_ratio = inter / (rest_areas + 1e-6)
            
            union = areas[i] + rest_areas - inter
            iou = inter / (union + 1e-6)

            # 剔除掉：(包含率 > 0.9) 或者 (IoU > iou_threshold) 的框
            mask = (containment_ratio < 0.90) & (iou < iou_threshold)
            
            order = order[1:][mask]

        return keep

    def process_pdf(
        self, 
        pdf_path: Union[str, Path], 
        output_dir: Union[str, Path], 
        dpi: int = 200, 
        conf: float = 0.25,
        iou: float = 0.45,
        ignored_labels: Optional[List[str]] = None,
        page_range: Optional[str] = None,
        return_items: bool = False
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

        for page_idx, page in enumerate(doc):
            pix = page.get_pixmap(dpi=dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            original_w, original_h = img.width, img.height

            # --- 步骤 0: 智能加白边 (按比例检测) ---
            # check_ratio=0.01 表示检查边缘 1% 的区域
            # min_pad=50 表示最少加 50px，如果图很大，会加更多(5%)
            img_input, pad_offset = self.check_and_pad(img, check_ratio=0.1, min_pad=50, threshold=250)

            # --- 步骤 1: 模型预测 ---
            results = self.model.predict(img_input, conf=conf, imgsz=1280, device=self.device, verbose=False)[0]

            boxes = results.boxes.xyxy
            scores = results.boxes.conf
            classes = results.boxes.cls

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
                    "x1": xyxy[0]  
                })

            # --- 步骤 5: 排序 ---
            valid_items.sort(key=lambda item: (item["y1"] // 10, item["x1"]))

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

        selected_pages = set(parse_page_range(page_range, doc.page_count))
        for page_idx, page in enumerate(doc):
            if page_idx not in selected_pages:
                continue
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

        doc.close()
        if return_items:
            return saved_items
        return saved_files


class DeepseekOcrLayoutExtractor:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.modelverse.cn/v1/",
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

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self.figure_labels = set()

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

        selected_pages = set(parse_page_range(page_range, doc.page_count))
        for page_idx, page in enumerate(doc):
            if page_idx not in selected_pages:
                continue
            pix = page.get_pixmap(dpi=dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

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

        doc.close()
        if return_items:
            return saved_items
        return saved_files
