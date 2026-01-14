import os
from pathlib import Path
from typing import List, Union, Optional

import fitz  # PyMuPDF
from PIL import Image
import torch
import torchvision
import numpy as np
from doclayout_yolo import YOLOv10
from doclayout_yolo.nn.tasks import YOLOv10DetectionModel
import dill

# PyTorch 2.6+ defaults to weights_only=True and requires allowlisting custom classes.
try:
    import torch.serialization
    torch.serialization.add_safe_globals([YOLOv10DetectionModel, dill._dill._load_type])
except Exception:
    # If torch serialization API changes or unavailable, defer to runtime errors.
    pass

class DocLayoutExtractor:
    def __init__(self, model_path: str = None):
        if model_path is None:
            # 请确保路径正确
            model_path = r"layout_models/doclayout_yolo_docstructbench_imgsz1280_2501.pt"
        
        self.model = YOLOv10(model_path)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

    def resolve_containment(self, boxes, scores, classes, iou_threshold=0.1):
        """
        处理包含关系：如果一个框被另一个框完全包含（或包含比例很高），
        则根据置信度保留分高的那个。
        
        解决了 NMS 无法过滤“大框套小框”的问题。
        """
        if len(boxes) == 0:
            return []

        # 计算所有框的面积
        areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        
        # 按置信度从高到低排序的索引
        order = scores.argsort()[::-1]
        keep = []

        while order.size > 0:
            i = order[0]
            keep.append(i)
            
            # 这种暴力循环虽然在Python里慢，但因为通常页面框不多（几十个），速度完全可以接受
            # 这里的逻辑是：拿当前最高分的框 i，去和剩余所有框比较
            
            if order.size == 1:
                break
            
            # 获取剩余的框
            rest_indices = order[1:]
            xx1 = np.maximum(boxes[i, 0], boxes[rest_indices, 0])
            yy1 = np.maximum(boxes[i, 1], boxes[rest_indices, 1])
            xx2 = np.minimum(boxes[i, 2], boxes[rest_indices, 2])
            yy2 = np.minimum(boxes[i, 3], boxes[rest_indices, 3])

            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h

            # 关键点：这里计算的是 "交叉面积 / 较小框的面积" (Intersection over Smaller)
            # 如果这个值接近 1，说明较小的框被较大的框包含了（或者反之）
            # 我们拿剩余框的面积来做分母
            rest_areas = areas[rest_indices]
            
            # 计算包含率：交集 / 剩余框自身的面积
            # 如果 > 0.8 (即80%的区域都在当前高分框i里面)，则认为是重复/包含，需要剔除
            containment_ratio = inter / (rest_areas + 1e-6)
            
            # 同时我们也做标准的 IoU 检查，双重保险
            union = areas[i] + rest_areas - inter
            iou = inter / (union + 1e-6)

            # 标记需要保留的框（即：既不是由于包含关系，也不是由于高IoU重叠）
            # 我们剔除掉：(包含率 > 0.9) 或者 (IoU > iou_threshold) 的框
            mask = (containment_ratio < 0.90) & (iou < iou_threshold)
            
            order = order[1:][mask]

        return keep

    def process_pdf(
        self, 
        pdf_path: Union[str, Path], 
        output_dir: Union[str, Path], 
        dpi: int = 200, 
        conf: float = 0.25,
        iou: float = 0.45,  # 传递给 torchvision.ops.nms
        ignored_labels: Optional[List[str]] = None,
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

            # --- 步骤 1: 模型预测 ---
            results = self.model.predict(img, conf=conf, imgsz=1280, device=self.device, verbose=False)[0]

            boxes = results.boxes.xyxy
            scores = results.boxes.conf
            classes = results.boxes.cls

            # --- 步骤 2: 初步 NMS (解决完全重叠) ---
            # 使用 torchvision 的 NMS 快速过滤高度重叠的框
            nms_indices = torchvision.ops.nms(boxes, scores, iou_threshold=iou)
            
            # 获取 NMS 后的结果
            final_boxes = boxes[nms_indices].cpu().numpy()
            final_scores = scores[nms_indices].cpu().numpy()
            final_classes = classes[nms_indices].cpu().numpy()

            # --- 步骤 3: 包含关系过滤 (解决大框套小框) ---
            # 这是为了解决你图中出现的“大段落框包含小行框”的问题
            # 我们传入 NMS 筛选后的框进行二次清洗
            keep_indices = self.resolve_containment(final_boxes, final_scores, final_classes, iou_threshold=iou)
            
            # 二次过滤
            final_boxes = final_boxes[keep_indices]
            final_classes = final_classes[keep_indices]
            # final_scores = final_scores[keep_indices] # 不需要了

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
            # 按垂直位置排序，如果垂直位置相近(10像素内)则按水平位置排
            valid_items.sort(key=lambda item: (item["y1"] // 10, item["x1"]))

            # --- 步骤 6: 裁剪并保存 ---
            for i, item in enumerate(valid_items):
                label = item["label"]
                xyxy = item["xyxy"]
                
                # 安全检查，防止坐标越界
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
