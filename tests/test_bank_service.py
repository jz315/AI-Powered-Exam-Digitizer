from __future__ import annotations

import json
from pathlib import Path

import pytest

from math_digitizer.gui.services import bank_service
from math_digitizer.gui.services.bank_service import BankService


def test_bank_service_import_success(tmp_path, monkeypatch):
    bank_dir = tmp_path / "bank"
    assets_dir = bank_dir / "assets"
    bank_file = bank_dir / "question_bank.json"

    monkeypatch.setattr(bank_service, "BANK_DIR", bank_dir)
    monkeypatch.setattr(bank_service, "ASSETS_DIR", assets_dir)
    monkeypatch.setattr(bank_service, "BANK_FILE", bank_file)

    image_base = tmp_path / "images"
    image_base.mkdir(parents=True, exist_ok=True)
    img_path = image_base / "foo.png"
    img_path.write_bytes(b"fake-png")

    data = {
        "meta": {"title": "T", "subject": "Math", "image_base_dir": str(image_base)},
        "sections": [
            {
                "type": "problem",
                "title": "S1",
                "questions": [
                    {"content": "Q1 ![img](foo.png)"},
                ],
            }
        ],
    }

    svc = BankService()
    result = svc.import_from_json(json.dumps(data, ensure_ascii=False))

    assert result.success is True
    assert result.added == 1
    assert result.copied == 1
    assert bank_file.exists()

    saved = json.loads(bank_file.read_text(encoding="utf-8"))
    assert isinstance(saved, dict)
    assert saved["questions"][0]["content"].startswith("Q1 ![img](assets/")


def test_bank_service_import_empty():
    svc = BankService()
    result = svc.import_from_json("")
    assert result.success is False


def test_bank_service_missing_image(tmp_path, monkeypatch):
    bank_dir = tmp_path / "bank"
    assets_dir = bank_dir / "assets"
    bank_file = bank_dir / "question_bank.json"

    monkeypatch.setattr(bank_service, "BANK_DIR", bank_dir)
    monkeypatch.setattr(bank_service, "ASSETS_DIR", assets_dir)
    monkeypatch.setattr(bank_service, "BANK_FILE", bank_file)

    image_base = tmp_path / "images"
    image_base.mkdir(parents=True, exist_ok=True)

    data = {
        "meta": {"title": "T", "subject": "Math", "image_base_dir": str(image_base)},
        "sections": [
            {
                "type": "problem",
                "title": "S1",
                "questions": [{"content": "Q1 ![img](missing.png)"}],
            }
        ],
    }

    svc = BankService()
    result = svc.import_from_json(json.dumps(data, ensure_ascii=False))

    assert result.success is True
    assert result.added == 1
    assert result.copied == 0
