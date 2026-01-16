import gradio as gr
import numpy as np
import cv2
from PIL import Image, ImageDraw
import torch
import torchvision
import time

# 导入你之前写的类
try:
    from layout_engine import DocLayoutExtractor
except ImportError:
    print("请确保 layout_engine.py 存在，或者将 DocLayoutExtractor 类的代码粘贴到本文件中。")
    pass

# --- 初始化模型 ---
print("正在加载模型，请稍候...")
try:
    extractor = DocLayoutExtractor()
    print("模型加载完成！")
except NameError:
    print("错误：未找到 DocLayoutExtractor 类。")
    exit()

def draw_boxes(image, boxes, classes, names, scores, conf_thres):
    """在图片上画框"""
    img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    for i, box in enumerate(boxes):
        score = scores[i]
        if score < conf_thres:
            continue
            
        x1, y1, x2, y2 = map(int, box)
        cls_id = int(classes[i])
        if cls_id < len(names):
            label = names[cls_id]
        else:
            label = str(cls_id)
        
        np.random.seed(cls_id)
        color = np.random.randint(0, 255, size=3).tolist()
        
        # 画框 (蓝色/绿色等随机色)
        cv2.rectangle(img_cv, (x1, y1), (x2, y2), color, 2)
        
        # 标签
        label_text = f"{label} {score:.2f}"
        (w, h), _ = cv2.getTextSize(label_text, 0, 0.5, 1)
        cv2.rectangle(img_cv, (x1, y1 - 20), (x1 + w, y1), color, -1)
        cv2.putText(img_cv, label_text, (x1, y1 - 5), 0, 0.5, (255, 255, 255), 1)
        
    return cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)

def test_layout(
    image, 
    check_ratio, 
    padding_ratio, 
    min_pad, 
    threshold, 
    conf_thres, 
    iou_thres
):
    if image is None:
        return None, "请先上传图片"

    start_time = time.time()
    pil_image = Image.fromarray(image)
    w, h = pil_image.size
    
    logs = []
    logs.append(f"原始尺寸: {w} x {h}")

    # --- 1. 边缘检测逻辑 ---
    img_gray = pil_image.convert("L")
    img_arr = np.array(img_gray)
    
    margin_w = max(5, int(w * check_ratio))
    margin_h = max(5, int(h * check_ratio))
    
    top_edge = img_arr[0:margin_h, :]
    bottom_edge = img_arr[h-margin_h:h, :]
    left_edge = img_arr[:, 0:margin_w]
    right_edge = img_arr[:, w-margin_w:w]
    
    has_content = (
        np.any(top_edge < threshold) or
        np.any(bottom_edge < threshold) or
        np.any(left_edge < threshold) or
        np.any(right_edge < threshold)
    )
    
    pad_offset = 0
    
    # 准备两张图：
    # img_input: 给模型看的 (白底)
    # img_vis:   给你看的 (灰底，方便区分边界)
    img_input = pil_image
    img_vis = pil_image
    
    if has_content:
        dynamic_pad = max(int(min_pad), int(max(w, h) * padding_ratio))
        pad_offset = dynamic_pad
        
        new_w = w + 2 * dynamic_pad
        new_h = h + 2 * dynamic_pad
        
        # A. 模型用图 (全白背景)
        model_bg = Image.new(pil_image.mode, (new_w, new_h), (255, 255, 255))
        model_bg.paste(pil_image, (dynamic_pad, dynamic_pad))
        img_input = model_bg
        
        # B. 可视化用图 (灰色背景，RGB: 200,200,200)
        # 这样你能清楚看到哪里是加出来的边
        vis_bg = Image.new("RGB", (new_w, new_h), (200, 200, 200))
        vis_bg.paste(pil_image, (dynamic_pad, dynamic_pad))
        img_vis = vis_bg
        
        logs.append(f"⚠️ 检测到边缘内容！")
        logs.append(f"   - 检查范围: {check_ratio*100:.1f}%")
        logs.append(f"✅ 已添加 Padding: {dynamic_pad} px")
        logs.append(f"   (灰色区域为添加的 Padding)")
    else:
        logs.append(f"✅ 边缘干净，无需加边。")

    # --- 2. 推理 (使用全白的 img_input) ---
    results = extractor.model.predict(
        img_input, 
        conf=conf_thres, 
        imgsz=1280, 
        device=extractor.device, 
        verbose=False
    )[0]
    
    boxes = results.boxes.xyxy.cpu().numpy()
    scores = results.boxes.conf.cpu().numpy()
    classes = results.boxes.cls.cpu().numpy()
    
    # --- 3. 后处理 ---
    keep_indices = torchvision.ops.nms(
        torch.tensor(boxes), 
        torch.tensor(scores), 
        iou_threshold=iou_thres
    )
    keep_indices = keep_indices.numpy()
    
    final_boxes = boxes[keep_indices]
    final_scores = scores[keep_indices]
    final_classes = classes[keep_indices]
    
    keep_containment = extractor.resolve_containment(
        final_boxes, final_scores, final_classes, iou_threshold=iou_thres
    )
    final_boxes = final_boxes[keep_containment]
    final_scores = final_scores[keep_containment]
    final_classes = final_classes[keep_containment]
    
    # --- 4. 绘图 (在灰底的 img_vis 上画) ---
    result_img = draw_boxes(
        img_vis, 
        final_boxes, 
        final_classes, 
        results.names, 
        final_scores, 
        conf_thres
    )
    
    # 画红色的原图边界框
    if pad_offset > 0:
        cv_res = np.array(result_img)
        cv2.rectangle(
            cv_res, 
            (pad_offset, pad_offset), 
            (pad_offset + w, pad_offset + h), 
            (255, 0, 0), # 红色
            3 # 线条加粗
        )
        result_img = Image.fromarray(cv_res)
        logs.append("ℹ️ 红色框: 原图边界 | 灰色区: 填充Padding")

    logs.append(f"检测到目标数: {len(final_boxes)}")
    logs.append(f"耗时: {time.time() - start_time:.4f}s")
    
    return result_img, "\n".join(logs)

# --- Gradio 界面 ---
with gr.Blocks(title="DocLayout 智能白边测试工具") as demo:
    gr.Markdown("## 📐 DocLayout-YOLO 智能白边与检测测试")
    gr.Markdown("灰色区域表示自动添加的 Padding，红色框表示原图边界。")
    
    with gr.Row():
        with gr.Column(scale=1):
            input_img = gr.Image(label="上传图片", type="numpy")
            
            with gr.Group():
                gr.Markdown("### 🛠️ 边缘检测参数")
                check_ratio = gr.Slider(0.001, 0.05, value=0.01, step=0.001, label="检查范围比例")
                threshold = gr.Slider(0, 255, value=250, step=1, label="亮度阈值 (越小越严)")
                
            with gr.Group():
                gr.Markdown("### ⬜ 填充参数")
                padding_ratio = gr.Slider(0.01, 0.2, value=0.05, step=0.01, label="填充宽度比例")
                min_pad = gr.Slider(10, 200, value=50, step=10, label="最小填充像素")
                
            with gr.Group():
                gr.Markdown("### 🧠 模型参数")
                conf = gr.Slider(0.01, 1.0, value=0.25, label="置信度")
                iou = gr.Slider(0.01, 1.0, value=0.45, label="NMS IoU")
                
            btn = gr.Button("🚀 开始分析", variant="primary")
            
        with gr.Column(scale=2):
            output_img = gr.Image(label="检测结果 (灰色背景为Padding)", type="pil")
            log_box = gr.Textbox(label="运行日志", lines=10)

    btn.click(
        fn=test_layout,
        inputs=[input_img, check_ratio, padding_ratio, min_pad, threshold, conf, iou],
        outputs=[output_img, log_box]
    )

if __name__ == "__main__":
    demo.launch()