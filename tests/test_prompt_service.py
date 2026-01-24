from __future__ import annotations

from math_digitizer.gui.services.prompt_service import PromptService


def test_prompt_service_read_and_build(tmp_path):
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("Hello", encoding="utf-8")

    svc = PromptService()
    content = svc.read_prompt(str(prompt_file))
    assert content == "Hello"

    combined = svc.build_prompt_and_ocr(content, "OCR_TEXT")
    assert "Hello" in combined
    assert "OCR_TEXT" in combined
