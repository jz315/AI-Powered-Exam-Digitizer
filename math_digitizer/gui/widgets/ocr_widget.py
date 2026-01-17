from __future__ import annotations

import os

from google import genai
from google.genai import types
from PIL import Image
import base64
import io

ALIYUN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

class OCRPipelineResult:
    def __init__(self, merged_text: str, out_dir: str):
        self.merged_text = merged_text
        self.out_dir = out_dir

# --- Gemini 助手函数 ---

def call_gemini_ocr(api_key: str, model_name: str, image_path: str, prompt_text: str) -> str:
    """调用 Gemini API 进行单张图片 OCR"""
    client = genai.Client(api_key=api_key)

    generation_config = types.GenerateContentConfig(
        temperature=0.3,
        top_p=0.95,
        safety_settings=[
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="BLOCK_NONE",
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="BLOCK_NONE",
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="BLOCK_NONE",
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_NONE",
            ),
        ],
        thinking_config=types.ThinkingConfig(thinking_level="minimal")
    )

    try:
        # 加载图片
        with Image.open(image_path) as img:
            img = img.copy()

        response = client.models.generate_content(
            model=model_name,
            contents=[prompt_text, img],
            config=generation_config,
        )
        return response.text or ""
    except Exception as e:
        print(f"Gemini API Error on {image_path}: {e}")
        return f"[OCR Failed for {os.path.basename(image_path)}: {e}]"


def call_aliyun_ocr(api_key: str, model_name: str, image_path: str, prompt_text: str) -> str:
    """调用阿里云 DashScope (OpenAI 兼容) 进行单张图片 OCR"""
    try:
        from openai import OpenAI
    except Exception as e:
        return f"[OCR Failed for {os.path.basename(image_path)}: openai SDK missing: {e}]"

    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=90)
            b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        client = OpenAI(api_key=api_key, base_url=ALIYUN_BASE_URL)
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    ],
                }
            ],
        )
        content = response.choices[0].message.content or ""
        return content
    except Exception as e:
        print(f"Aliyun API Error on {image_path}: {e}")
        return f"[OCR Failed for {os.path.basename(image_path)}: {e}]"


def call_ocr(provider: str, api_key: str, model_name: str, image_path: str, prompt_text: str) -> str:
    """Dispatch OCR by provider."""
    provider = (provider or "gemini").strip().lower()
    if provider == "aliyun":
        return call_aliyun_ocr(api_key, model_name, image_path, prompt_text)
    return call_gemini_ocr(api_key, model_name, image_path, prompt_text)
