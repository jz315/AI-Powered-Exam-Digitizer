from pathlib import Path
from typing import List, Union, Optional

import fitz  # PyMuPDF
from PIL import Image
from doclayout_yolo import YOLOv10
import dill 
class DocLayoutExtractor:
    def __init__(self):
        """
        初始化提取器，加载模型。
        :param model_path: YOLO 模型权重路径 (.pt)
        """
        self.model_path = str("layout_models\doclayout_yolo_docstructbench_imgsz1280_2501.pt")
        self.model = YOLOv10(self.model_path)

    def process_pdf(
        self, 
        pdf_path: Union[str, Path], 
        output_dir: Union[str, Path], 
        dpi: int = 200, 
        conf: float = 0.25,
        ignored_labels: Optional[List[str]] = None
    ) -> List[str]:
        """
        处理单个 PDF 文件，提取版面元素。
        **输出图片将严格按照页面从上到下、从左到右的顺序命名。**
        
        :param pdf_path: PDF 文件路径
        :param output_dir: 输出根目录
        :param dpi: 渲染 PDF 的清晰度 (默认 200)
        :param conf: YOLO 预测置信度阈值 (默认 0.25)
        :param ignored_labels: 不需要导出的标签列表 (默认包含 "abandon")
        :return: 生成的图片文件路径列表
        """
        # 默认忽略 abandon
        if ignored_labels is None:
            ignored_labels = ["abandon"]
            
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")

        save_dir = Path(output_dir) / pdf_path.stem
        save_dir.mkdir(parents=True, exist_ok=True)

        saved_files = []
        
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            raise RuntimeError(f"无法打开 PDF 文件: {e}")

        for page_idx, page in enumerate(doc):
            pix = page.get_pixmap(dpi=dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # 模型预测
            results = self.model.predict(img, conf=conf, verbose=False, imgsz=1280,)

            # --- 步骤 1: 收集本页所有有效元素 ---
            valid_items = []
            
            for r in results:
                names = r.names
                boxes = r.boxes

                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    label = names[cls_id]

                    # 过滤忽略的标签
                    if label in ignored_labels:
                        continue

                    # 获取坐标 [x1, y1, x2, y2]
                    xyxy = box.xyxy[0].cpu().numpy().astype(int)
                    
                    valid_items.append({
                        "label": label,
                        "xyxy": xyxy,
                        "y1": xyxy[1], # 顶部 y 坐标
                        "x1": xyxy[0]  # 左侧 x 坐标
                    })

            # --- 步骤 2: 排序 ---
            # 主要关键字: y1 (从上到下)
            # 次要关键字: x1 (如果高度完全一致，则从左到右)
            valid_items.sort(key=lambda item: (item["y1"], item["x1"]))

            # --- 步骤 3: 按顺序裁剪保存 ---
            for i, item in enumerate(valid_items):
                label = item["label"]
                xyxy = item["xyxy"]
                
                crop = img.crop(xyxy)
                
                # 文件名序号 i 现在对应视觉顺序
                # p页码_序号_类别.png (把序号放在类别前，方便在文件夹里按名称排序查看)
                filename = f"p{page_idx+1:03d}_{i:03d}_{label}.png"
                file_path = save_dir / filename
                
                crop.save(file_path)
                saved_files.append(str(file_path))

        doc.close()
        return saved_files