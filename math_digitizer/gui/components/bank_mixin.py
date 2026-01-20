from __future__ import annotations

import json
import os
import re
import shutil
import threading
import uuid
from pathlib import Path

from math_digitizer.gui.services.deps import validate_json_and_latex

BANK_DIR = Path(__file__).parent.parent.parent.parent / "output" / "question_bank"
ASSETS_DIR = BANK_DIR / "assets"
BANK_FILE = BANK_DIR / "question_bank.json"

MD_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


class BankMixin:

    def _start_import_from_editor(self):
        self.btn_import_bank.configure(state="disabled", text="⏳ 导入中...")
        threading.Thread(target=self._run_import_from_editor, daemon=True).start()

    def _run_import_from_editor(self):
        try:
            json_str = self.json_textbox.get("0.0", "end").strip()
            if not json_str:
                self.flash_status("❌ 编辑器为空，无法导入")
                return

            data, issues = validate_json_and_latex(json_str)
            if data is None:
                self.flash_status("❌ JSON 格式错误，无法导入")
                return

            image_base_dir = data.get("meta", {}).get("image_base_dir", "")
            base_path = Path(image_base_dir) if image_base_dir else None

            BANK_DIR.mkdir(parents=True, exist_ok=True)
            ASSETS_DIR.mkdir(parents=True, exist_ok=True)

            questions = self._flatten_sections_to_questions(data)
            if not questions:
                self.flash_status("❌ 未找到任何题目")
                return

            copied_count = 0
            for q in questions:
                copied_count += self._process_question_images(q, base_path)

            existing_questions = self._load_existing_bank()
            existing_ids = {q.get("id") for q in existing_questions if q.get("id")}

            added = 0
            for q in questions:
                if not q.get("id"):
                    q["id"] = f"Q_{uuid.uuid4().hex[:8]}"
                if q["id"] not in existing_ids:
                    existing_questions.append(q)
                    existing_ids.add(q["id"])
                    added += 1

            self._save_bank(existing_questions)
            self.flash_status(f"✅ 入库完成：新增 {added} 题，复制 {copied_count} 张图片")

        except Exception as e:
            self.flash_status(f"❌ 入库异常: {e}")
        finally:
            self.after(0, lambda: self.btn_import_bank.configure(state="normal", text="📥 导入到题库"))

    def _flatten_sections_to_questions(self, data: dict) -> list[dict]:
        questions = []
        for section in data.get("sections", []):
            section_title = section.get("title", "")
            section_type = section.get("type", "")
            for q in section.get("questions", []):
                if isinstance(q, dict):
                    if section_title and "section_title" not in q:
                        q["section_title"] = section_title
                    if section_type and "type" not in q:
                        q["type"] = section_type
                    questions.append(q)
        return questions

    def _process_question_images(self, q: dict, base_path: Path | None) -> int:
        copied = 0

        if "content" in q and isinstance(q["content"], str):
            q["content"], c = self._replace_images_in_text(q["content"], base_path)
            copied += c

        if "options" in q and isinstance(q["options"], list):
            new_options = []
            for opt in q["options"]:
                if isinstance(opt, str):
                    new_opt, c = self._replace_images_in_text(opt, base_path)
                    new_options.append(new_opt)
                    copied += c
                else:
                    new_options.append(opt)
            q["options"] = new_options

        if "sub_questions" in q and isinstance(q["sub_questions"], list):
            for sub in q["sub_questions"]:
                if isinstance(sub, dict):
                    copied += self._process_question_images(sub, base_path)

        return copied

    def _replace_images_in_text(self, text: str, base_path: Path | None) -> tuple[str, int]:
        if not base_path or not base_path.exists():
            return text, 0

        copied = 0

        def replacer(match: re.Match) -> str:
            nonlocal copied
            img_ref = match.group(1).strip().strip("\"'")
            
            src_file = base_path / Path(img_ref).name
            if not src_file.exists():
                return match.group(0)

            new_name = f"{uuid.uuid4().hex[:8]}_{src_file.name}"
            dest_file = ASSETS_DIR / new_name

            try:
                shutil.copy2(src_file, dest_file)
                copied += 1
                return f"![img](assets/{new_name})"
            except Exception:
                return match.group(0)

        new_text = MD_IMAGE_PATTERN.sub(replacer, text)
        return new_text, copied

    def _load_existing_bank(self) -> list[dict]:
        if not BANK_FILE.exists():
            return []
        try:
            with open(BANK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return data.get("questions", [])
        except Exception:
            return []

    def _save_bank(self, questions: list[dict]):
        bank_data = {"questions": questions}
        with open(BANK_FILE, "w", encoding="utf-8") as f:
            json.dump(bank_data, f, ensure_ascii=False, indent=2)
