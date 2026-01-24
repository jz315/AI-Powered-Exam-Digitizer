from __future__ import annotations

import os


class PromptService:
    def read_prompt(self, prompt_path: str) -> str:
        if not prompt_path or not os.path.exists(prompt_path):
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def build_prompt_and_ocr(self, prompt_content: str, ocr_content: str) -> str:
        prompt_content = prompt_content or ""
        ocr_content = ocr_content or ""
        return f"{prompt_content}\n\n---\n\n# OCR 识别结果\n\n{ocr_content}"
