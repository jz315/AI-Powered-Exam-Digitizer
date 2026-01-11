import os
import time
import typing
from pathlib import Path
from PIL import Image
import google.generativeai as genai
from layout_engine import DocLayoutExtractor

# 定义返回结果的数据结构
class OCRResult:
    def __init__(self, merged_text: str, out_dir: str):
        self.merged_text = merged_text
        self.out_dir = out_dir

def build_minimal_math_ocr_prompt() -> str:
    """返回极简模式的 Prompt"""
    return (
        "Transcribe this image into LaTeX/Markdown. "
        "Output ONLY the content. No explanations. "
        "Use $...$ for inline math and $$...$$ for display math."
    )

def _get_default_prompt() -> str:
    """返回标准详细 Prompt"""
    return (
        "You are a mathematical text digitizer. Please transcribe the content of this image into text.\n"
        "Rules:\n"
        "1. Identify the question number (e.g., 1., (1), [1]) if present.\n"
        "2. Output mathematical expressions in standard LaTeX format using $ for inline and $$ for block.\n"
        "3. Output format should be strictly JSON compatible string or pure Markdown.\n"
        "4. Do not include markdown code blocks like ```latex ... ```, just raw text.\n"
        "5. Keep the structure corresponding to the image."
    )

def run_pdf_ocr_pipeline(
    pdf_path: str,
    out_root: str,
    dpi: int = 200,
    lang: str = "ch",
    use_gpu: bool = False,         # YOLO/Paddle 相关，此处主要透传
    require_gpu: bool = False,
    do_gemini: bool = True,
    gemini_api_key: str = "",
    gemini_model: str = "gemini-1.5-flash",
    prompt: typing.Optional[str] = None,
    on_status: typing.Optional[typing.Callable[[str], None]] = None,
    on_progress: typing.Optional[typing.Callable[[float], None]] = None
) -> OCRResult:
    """
    完整的 PDF OCR 流程：
    1. 使用 Layout Engine (YOLO) 将 PDF 切分为单题图片。
    2. 使用 Gemini API 识别每一张图片。
    3. 合并结果。
    """
    
    # 0. 状态回调辅助函数
    def update_status(msg):
        if on_status:
            on_status(msg)
        print(f"[OCR Pipeline] {msg}")

    def update_progress(val):
        if on_progress:
            on_progress(val)

    if not gemini_api_key:
        raise ValueError("Gemini API Key 不能为空")

    # 1. 配置 Gemini
    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel(gemini_model)
    except Exception as e:
        raise RuntimeError(f"Gemini 配置失败: {e}")

    # 2. 调用版面分析引擎进行切图
    update_status("正在进行版面分析与切图 (YOLOv10)...")
    update_progress(0.1)

    extractor = DocLayoutExtractor()
    # 注意：layout_engine.process_pdf 内部已经处理了 output_dir 的创建
    # 我们传入 output_dir/pdf_name 的父级，layout_engine 会自己建立子文件夹
    try:
        # 这里的 out_root 是 'output/pdf_ocr'
        image_paths = extractor.process_pdf(
            pdf_path=pdf_path,
            output_dir=out_root,
            dpi=dpi,
            conf=0.25
        )
    except Exception as e:
        raise RuntimeError(f"版面分析失败: {e}")

    if not image_paths:
        raise RuntimeError("未提取到任何有效的题目切片。")

    update_status(f"切图完成，共 {len(image_paths)} 张图片。准备开始 AI 识别...")
    update_progress(0.2)

    # 3. 循环调用 Gemini
    results = []
    total_imgs = len(image_paths)
    current_prompt = prompt if prompt else _get_default_prompt()
    
    # 获取实际的输出目录 (layout_engine 生成的)
    actual_out_dir = str(Path(image_paths[0]).parent)

    for idx, img_path in enumerate(image_paths):
        file_name = os.path.basename(img_path)
        update_status(f"正在识别 ({idx+1}/{total_imgs}): {file_name} ...")
        
        try:
            # 打开图片
            img = Image.open(img_path)
            
            # 调用 API
            response = model.generate_content([current_prompt, img])
            text = response.text
            
            # 保存单题文本到同名 .txt
            txt_path = img_path.replace(".png", ".txt").replace(".jpg", ".txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)
            
            results.append(f"--- Segment: {file_name} ---\n{text}\n")
            
            # 简单的速率限制避免 429 (Flash 模型通常限制较宽，但安全起见)
            time.sleep(1) 

        except Exception as e:
            error_msg = f"Error processing {file_name}: {e}"
            print(error_msg)
            results.append(f"--- Segment: {file_name} ---\n[识别失败: {e}]\n")
        
        # 更新进度 (0.2 ~ 0.9)
        progress = 0.2 + (0.7 * ((idx + 1) / total_imgs))
        update_progress(progress)

    # 4. 合并结果
    update_status("正在合并文本...")
    merged_text = "\n".join(results)
    
    merged_path = os.path.join(actual_out_dir, "merged.txt")
    with open(merged_path, "w", encoding="utf-8") as f:
        f.write(merged_text)

    update_progress(1.0)
    return OCRResult(merged_text, actual_out_dir)