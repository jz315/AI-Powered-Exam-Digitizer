from __future__ import annotations

import json
from pathlib import Path

from math_digitizer.gui.services.generation_service import GenerationService


class FakeGenerator:
    def process_data(self, json_str: str):
        return json.loads(json_str)

    def replace_inline_images(self, processed, asset_dir: str):
        Path(asset_dir).mkdir(parents=True, exist_ok=True)
        return [], []

    def render(self, processed, output_tex: str):
        Path(output_tex).write_text("tex", encoding="utf-8")
        return True

    def compile_pdf(self, tex_file: str):
        pdf_path = Path(tex_file).with_suffix(".pdf")
        pdf_path.write_bytes(b"%PDF-1.4 fake")
        return True


def test_generation_service_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    json_data = {
        "meta": {"title": "Exam", "subject": "Math"},
        "sections": [{"type": "problem", "title": "S1", "questions": [{"content": "Q1"}]}],
    }
    svc = GenerationService()
    result = svc.generate(
        json_str=json.dumps(json_data, ensure_ascii=False),
        generator=FakeGenerator(),
        filename_override="Exam",
        output_root="out",
    )

    assert result.success is True
    assert result.output_dir is not None
    assert Path(result.output_dir).exists()
    assert Path(result.output_pdf).exists()
    assert Path(result.output_tex).exists()


def test_generation_service_empty_input():
    svc = GenerationService()
    result = svc.generate(json_str="", generator=FakeGenerator())
    assert result.success is False
