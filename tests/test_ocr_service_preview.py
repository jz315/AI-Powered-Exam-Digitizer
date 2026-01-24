from __future__ import annotations

from pathlib import Path

import fitz
import numpy as np

from math_digitizer.gui.services.ocr_service import OcrService


def test_render_preview_for_page_with_numpy_bbox(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    doc.save(pdf_path)
    doc.close()

    svc = OcrService()
    items = [{"label": "text", "xyxy": np.array([10, 10, 100, 50])}]
    out = svc._render_preview_for_page(Path(pdf_path), 1, 72, items, tmp_path)

    assert out is not None
    assert Path(out).exists()
