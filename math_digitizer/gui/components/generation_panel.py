from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading

from math_digitizer.gui.services.deps import extract_first_latex_error, validate_json_and_latex


class GenerationMixin:

    @staticmethod
    def _find_line_numbers(text: str, needle: str) -> list[int]:
        if not text or not needle:
            return []
        lines: list[int] = []
        start = 0
        while True:
            idx = text.find(needle, start)
            if idx == -1:
                break
            line_no = text.count("\n", 0, idx) + 1
            lines.append(line_no)
            start = idx + len(needle)
        return lines

    def start_generation_thread(self):
        self.btn_generate.configure(state="disabled", text="⏳ 处理中...")
        threading.Thread(target=self.run_generation, daemon=True).start()

    def run_generation(self):
        try:
            json_str = self.json_textbox.get("0.0", "end").strip()
            if not json_str:
                self.flash_status("❌ 请先在编辑器中输入 JSON 数据")
                return

            data, issues = validate_json_and_latex(json_str)
            self.after(0, lambda: self._set_issues_panel(issues))
            if data is None: return

            custom_fn = self.entry_filename.get().strip()
            folder_name = custom_fn or data.get('meta', {}).get('title', 'exam_output')
            folder_name = "".join([c for c in folder_name if c not in '<>:"/\\|?*']).strip()
            
            output_dir = os.path.abspath(os.path.join("output", folder_name))
            temp_dir = os.path.abspath("temp_build")
            
            self.flash_status(f"⚙️ 清理编译环境...")
            if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
            os.makedirs(temp_dir, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)

            processed = self.generator.process_data(json.dumps(data))
            missing_imgs, img_warnings = self.generator.replace_inline_images(processed, os.path.join(temp_dir, 'assets'))
            for warn in img_warnings:
                self._append_log(f"[warn] {warn}")
            if missing_imgs:
                self._append_log(f"[warn] Missing images: {len(missing_imgs)}")
                uniq = []
                seen = set()
                for p in missing_imgs:
                    if p not in seen:
                        uniq.append(p)
                        seen.add(p)
                for p in uniq:
                    lines = self._find_line_numbers(json_str, p)
                    if lines:
                        line_info = ",".join(str(x) for x in lines)
                        self._append_log(f"[warn] Missing image: {p} (file=editor JSON, lines={line_info})")
                    else:
                        self._append_log(f"[warn] Missing image: {p} (file=editor JSON, lines=? )")
            tex_path = os.path.join(temp_dir, "main.tex")
            if not self.generator.render(processed, tex_path): raise Exception("渲染失败")

            self.flash_status("⚙️ 编译 LaTeX...")
            if self.generator.compile_pdf(tex_path):
                target_pdf = os.path.join(output_dir, f"{folder_name}.pdf")
                target_tex = os.path.join(output_dir, f"{folder_name}.tex")
                shutil.copy2(os.path.join(temp_dir, "main.pdf"), target_pdf)
                shutil.copy2(os.path.join(temp_dir, "main.tex"), target_tex)
                self.flash_status(f"🎉 成功！PDF已生成: {target_pdf}")
                try: 
                    if os.name=='nt': os.startfile(output_dir)
                    else: subprocess.call(['open' if sys.platform=='darwin' else 'xdg-open', output_dir])
                except: pass
            else:
                detail = extract_first_latex_error(os.path.join(temp_dir, "main.log"), tex_path)
                if detail: 
                    self.after(0, lambda: self._set_issues_panel(issues + [detail], header="❌ LaTeX 编译失败"))
                self.flash_status("❌ 编译失败，请检查 LaTeX 语法")

        except Exception as e:
            self.flash_status(f"❌ 异常: {e}")
        finally:
            self.after(0, lambda: self.btn_generate.configure(state="normal", text="✨ 生成 PDF 文件"))

