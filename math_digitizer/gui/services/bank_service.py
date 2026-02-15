from __future__ import annotations

import hashlib
import json
import re
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from math_digitizer.gui.services.deps import validate_json_and_latex


BANK_DIR = Path("output") / "question_bank"
ASSETS_DIR = BANK_DIR / "assets"
BANK_FILE = BANK_DIR / "question_bank.json"

MD_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


@dataclass
class BankImportResult:
    success: bool
    message: str
    added: int = 0
    copied: int = 0
    warnings: list[str] = field(default_factory=list)
    warning_count: int = 0


class BankService:
    def import_from_json(self, json_str: str) -> BankImportResult:
        if not json_str:
            return BankImportResult(False, "编辑器为空，无法导入")

        data, issues = validate_json_and_latex(json_str)
        if data is None:
            err = next((i for i in issues if i.severity == "error"), None)
            msg = err.message if err else "JSON 格式错误，无法导入"
            return BankImportResult(False, msg)

        error_issues = [i for i in issues if i.severity == "error"]
        if error_issues:
            first = error_issues[0]
            location = []
            if first.path:
                location.append(first.path)
            if first.line:
                location.append(f"line {first.line}")
            loc_text = f"（{'/'.join(location)}）" if location else ""
            msg = f"校验失败：发现 {len(error_issues)} 个错误，首个：{first.message}{loc_text}"
            return BankImportResult(False, msg)

        validation_warnings = [i for i in issues if i.severity == "warning"]

        image_base_dir = data.get("meta", {}).get("image_base_dir", "")
        base_path = Path(image_base_dir) if image_base_dir else None
        if base_path and base_path.exists() and base_path.is_file():
            base_path = base_path.parent

        BANK_DIR.mkdir(parents=True, exist_ok=True)
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)

        questions = self._flatten_sections_to_questions(data)
        if not questions:
            return BankImportResult(False, "未找到任何题目")

        warnings: list[str] = []
        warning_count = 0
        image_warning_count = 0

        def add_warning(message: str):
            nonlocal warning_count
            warning_count += 1
            if len(warnings) < 5:
                warnings.append(message)

        for warn in validation_warnings:
            add_warning(f"校验警告：{warn.message}")

        copied_count = 0
        for q in questions:
            copied, img_warnings = self._process_question_images(q, base_path)
            copied_count += copied
            for w in img_warnings:
                add_warning(w)
                image_warning_count += 1

        try:
            existing_questions = self._load_existing_bank()
        except Exception as e:
            return BankImportResult(False, f"题库文件读取失败，请修复后再导入：{e}")
        existing_hashes = {self._content_hash(q) for q in existing_questions}

        added = 0
        skipped = 0
        for q in questions:
            content_hash = self._content_hash(q)
            if content_hash in existing_hashes:
                skipped += 1
                continue
            
            q["id"] = f"Q_{uuid.uuid4().hex[:8]}"
            existing_questions.append(q)
            existing_hashes.add(content_hash)
            added += 1

        self._save_bank(existing_questions)
        msg = f"入库完成：新增 {added} 题，复制 {copied_count} 张图片"
        if skipped > 0:
            msg += f"，跳过 {skipped} 题重复"
        if validation_warnings:
            msg += f"，校验警告 {len(validation_warnings)} 条"
        if image_warning_count > 0:
            msg += f"，图片警告 {image_warning_count} 条"
        return BankImportResult(True, msg, added=added, copied=copied_count, warnings=warnings, warning_count=warning_count)
    
    def _content_hash(self, q: dict) -> str:
        normalized = self._normalize_question_for_hash(q)
        raw = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _normalize_question_for_hash(self, q: dict) -> dict:
        def norm_text(val: object) -> str:
            if isinstance(val, str):
                return val.strip().replace("\r\n", "\n")
            return ""

        options = q.get("options")
        sub_questions = q.get("sub_questions")
        return {
            "type": norm_text(q.get("type")),
            "content": norm_text(q.get("content")),
            "options": [norm_text(o) for o in options] if isinstance(options, list) else [],
            "answer": norm_text(q.get("answer")),
            "analysis": norm_text(q.get("analysis")),
            "sub_questions": [
                self._normalize_question_for_hash(sub) if isinstance(sub, dict) else sub
                for sub in (sub_questions if isinstance(sub_questions, list) else [])
            ],
            "image": q.get("image"),
            "figure": q.get("figure"),
        }

    def _flatten_sections_to_questions(self, data: dict) -> list[dict]:
        questions: list[dict] = []
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

    def _process_question_images(self, q: dict, base_path: Path | None) -> tuple[int, list[str]]:
        copied = 0
        warnings: list[str] = []

        if "content" in q and isinstance(q["content"], str):
            q["content"], c, w = self._replace_images_in_text(q["content"], base_path)
            copied += c
            warnings.extend(w)

        if "options" in q and isinstance(q["options"], list):
            new_options = []
            for opt in q["options"]:
                if isinstance(opt, str):
                    new_opt, c, w = self._replace_images_in_text(opt, base_path)
                    new_options.append(new_opt)
                    copied += c
                    warnings.extend(w)
                else:
                    new_options.append(opt)
            q["options"] = new_options

        if "sub_questions" in q and isinstance(q["sub_questions"], list):
            for sub in q["sub_questions"]:
                if isinstance(sub, dict):
                    sub_copied, sub_warnings = self._process_question_images(sub, base_path)
                    copied += sub_copied
                    warnings.extend(sub_warnings)

        return copied, warnings

    def _replace_images_in_text(self, text: str, base_path: Path | None) -> tuple[str, int, list[str]]:
        if not base_path or not base_path.exists():
            if MD_IMAGE_PATTERN.search(text):
                return text, 0, ["图片引用存在但未提供有效 image_base_dir，无法复制图片"]
            return text, 0, []

        copied = 0
        warnings: list[str] = []

        def replacer(match: re.Match) -> str:
            nonlocal copied
            img_ref = match.group(1).strip().strip("\"'")
            if img_ref.startswith("<") and img_ref.endswith(">"):
                img_ref = img_ref[1:-1].strip()

            lowered = img_ref.lower()
            if lowered.startswith("http://") or lowered.startswith("https://") or lowered.startswith("data:"):
                return match.group(0)

            candidate_paths: list[Path] = []
            ref_path = Path(img_ref)
            if ref_path.is_absolute():
                candidate_paths.append(ref_path)
            else:
                candidate_paths.append(base_path / ref_path)
                candidate_paths.append(base_path / ref_path.name)

            src_file = next((p for p in candidate_paths if p.exists()), None)
            if src_file is None:
                warnings.append(f"未找到图片文件：{img_ref}")
                return match.group(0)

            try:
                digest = self._hash_file(src_file)
            except Exception:
                warnings.append(f"读取图片失败：{src_file}")
                return match.group(0)

            new_name = f"{digest[:12]}_{src_file.name}"
            dest_file = ASSETS_DIR / new_name

            try:
                # Always create assets dir if it doesn't exist
                ASSETS_DIR.mkdir(parents=True, exist_ok=True)
                
                if not dest_file.exists():
                    shutil.copy2(src_file, dest_file)
                    copied += 1
                # Return path compatible with backend static mount
                return f"![img](/assets/{new_name})"
            except Exception:
                warnings.append(f"复制图片失败：{src_file}")
                return match.group(0)

        new_text = MD_IMAGE_PATTERN.sub(replacer, text)
        return new_text, copied, warnings

    def _hash_file(self, path: Path) -> str:
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _load_existing_bank(self) -> list[dict]:
        if not BANK_FILE.exists():
            return []
        try:
            with open(BANK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return data.get("questions", [])
        except Exception as e:
            raise RuntimeError(f"题库文件解析失败：{e}") from e

    def _save_bank(self, questions: list[dict]) -> None:
        """Save questions to bank file with atomic write and backup.
        
        Raises:
            RuntimeError: If write operation fails.
        """
        try:
            BANK_DIR.mkdir(parents=True, exist_ok=True)
            ASSETS_DIR.mkdir(parents=True, exist_ok=True)

            bank_data = {"questions": questions}
            tmp_file = BANK_FILE.with_suffix(".json.tmp")
            
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(bank_data, f, ensure_ascii=False, indent=2)

            if BANK_FILE.exists():
                backup_file = BANK_FILE.with_suffix(".json.bak")
                try:
                    shutil.copy2(BANK_FILE, backup_file)
                except Exception:
                    pass  # Backup failure is not critical

            tmp_file.replace(BANK_FILE)
        except OSError as e:
            raise RuntimeError(f"题库保存失败：{e}") from e
        except Exception as e:
            raise RuntimeError(f"题库保存时发生未知错误：{e}") from e
