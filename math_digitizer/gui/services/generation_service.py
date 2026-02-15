from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from math_digitizer.core.validator import ValidationIssue, extract_first_latex_error, validate_json_and_latex


LogFn = Callable[[str], None]
StatusFn = Callable[[str], None]


@dataclass
class GenerationResult:
    success: bool
    output_dir: str | None
    output_pdf: str | None
    output_tex: str | None
    issues: list[ValidationIssue]
    missing_images: list[str]
    warnings: list[str]


class GenerationService:
    def generate(
        self,
        *,
        json_str: str,
        generator,
        filename_override: str = "",
        output_root: str = "output",
        on_log: LogFn | None = None,
        on_status: StatusFn | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> GenerationResult:
        issues: list[ValidationIssue] = []
        missing_imgs: list[str] = []
        warnings: list[str] = []

        if not json_str:
            return GenerationResult(
                success=False,
                output_dir=None,
                output_pdf=None,
                output_tex=None,
                issues=issues,
                missing_images=missing_imgs,
                warnings=warnings,
            )

        if cancel_check and cancel_check():
            warnings.append("任务已取消")
            return GenerationResult(
                success=False,
                output_dir=None,
                output_pdf=None,
                output_tex=None,
                issues=issues,
                missing_images=missing_imgs,
                warnings=warnings,
            )

        data, issues = validate_json_and_latex(json_str)
        if data is None:
            return GenerationResult(
                success=False,
                output_dir=None,
                output_pdf=None,
                output_tex=None,
                issues=issues,
                missing_images=missing_imgs,
                warnings=warnings,
            )

        if cancel_check and cancel_check():
            warnings.append("任务已取消")
            return GenerationResult(
                success=False,
                output_dir=None,
                output_pdf=None,
                output_tex=None,
                issues=issues,
                missing_images=missing_imgs,
                warnings=warnings,
            )

        custom_fn = (filename_override or "").strip()
        folder_name = custom_fn or data.get("meta", {}).get("title", "exam_output")
        folder_name = "".join([c for c in folder_name if c not in '<>:"/\\|?*']).strip()

        output_dir = os.path.abspath(os.path.join(output_root, folder_name))
        temp_dir = os.path.abspath("temp_build")

        if on_status:
            on_status("⚙️ 清理编译环境...")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        processed = generator.process_data(json.dumps(data))
        if cancel_check and cancel_check():
            warnings.append("任务已取消")
            return GenerationResult(
                success=False,
                output_dir=output_dir,
                output_pdf=None,
                output_tex=None,
                issues=issues,
                missing_images=missing_imgs,
                warnings=warnings,
            )
        missing_imgs, img_warnings = generator.replace_inline_images(processed, os.path.join(temp_dir, "assets"))
        warnings.extend(img_warnings)
        if on_log:
            for warn in img_warnings:
                on_log(f"[warn] {warn}")
        if missing_imgs and on_log:
            on_log(f"[warn] Missing images: {len(missing_imgs)}")

        tex_path = os.path.join(temp_dir, "main.tex")
        if not generator.render(processed, tex_path):
            return GenerationResult(
                success=False,
                output_dir=output_dir,
                output_pdf=None,
                output_tex=None,
                issues=issues,
                missing_images=missing_imgs,
                warnings=warnings,
            )

        if on_status:
            on_status("⚙️ 编译 LaTeX...")

        if generator.compile_pdf(tex_path, cancel_check=cancel_check):
            target_pdf = os.path.join(output_dir, f"{folder_name}.pdf")
            target_tex = os.path.join(output_dir, f"{folder_name}.tex")
            shutil.copy2(os.path.join(temp_dir, "main.pdf"), target_pdf)
            shutil.copy2(os.path.join(temp_dir, "main.tex"), target_tex)
            assets_src = os.path.join(temp_dir, "assets")
            if os.path.exists(assets_src):
                assets_dest = os.path.join(output_dir, "assets")
                try:
                    shutil.copytree(assets_src, assets_dest, dirs_exist_ok=True)
                except Exception as e:
                    warn_msg = f"复制资源文件失败: {e}"
                    warnings.append(warn_msg)
                    if on_log:
                        on_log(f"[warn] {warn_msg}")
            return GenerationResult(
                success=True,
                output_dir=output_dir,
                output_pdf=target_pdf,
                output_tex=target_tex,
                issues=issues,
                missing_images=missing_imgs,
                warnings=warnings,
            )

        if cancel_check and cancel_check():
            warnings.append("任务已取消")
            return GenerationResult(
                success=False,
                output_dir=output_dir,
                output_pdf=None,
                output_tex=None,
                issues=issues,
                missing_images=missing_imgs,
                warnings=warnings,
            )

        detail = extract_first_latex_error(os.path.join(temp_dir, "main.log"), tex_path)
        if detail:
            issues = issues + [detail]
        return GenerationResult(
            success=False,
            output_dir=output_dir,
            output_pdf=None,
            output_tex=None,
            issues=issues,
            missing_images=missing_imgs,
            warnings=warnings,
        )
