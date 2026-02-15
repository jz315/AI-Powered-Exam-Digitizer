from __future__ import annotations

import os
import subprocess
import sys
import threading


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
        self.task_manager.start("generation")
        threading.Thread(target=self.run_generation, daemon=True).start()

    def run_generation(self):
        try:
            if self._is_task_cancelled():
                self.flash_status("⏹ 任务已取消")
                return

            json_str = self.json_textbox.get("0.0", "end").strip()
            if not json_str:
                self.flash_status("❌ 请先在编辑器中输入 JSON 数据")
                return
            result = self.generation_service.generate(
                json_str=json_str,
                generator=self.generator,
                filename_override=self.entry_filename.get().strip(),
                on_log=self._append_log,
                on_status=self.flash_status,
                cancel_check=self._is_task_cancelled,
            )
            self.after(0, lambda: self._set_issues_panel(result.issues, source=json_str))

            if result.missing_images:
                uniq: list[str] = []
                seen = set()
                for p in result.missing_images:
                    if p not in seen:
                        uniq.append(p)
                        seen.add(p)
                self._append_log(f"[warn] Missing images: {len(uniq)}")
                for p in uniq:
                    lines = self._find_line_numbers(json_str, p)
                    if lines:
                        line_info = ",".join(str(x) for x in lines)
                        self._append_log(f"[warn] Missing image: {p} (file=editor JSON, lines={line_info})")
                    else:
                        self._append_log(f"[warn] Missing image: {p} (file=editor JSON, lines=? )")

            if self._is_task_cancelled():
                self.flash_status("⏹ 任务已取消")
            elif result.success and result.output_dir:
                self.flash_status(f"🎉 成功！PDF已生成: {result.output_dir}")
                try:
                    if os.name == "nt":
                        os.startfile(result.output_dir)
                    else:
                        subprocess.call(["open" if sys.platform == "darwin" else "xdg-open", result.output_dir])
                except Exception:
                    pass
            else:
                self.flash_status("❌ 编译失败，请检查 LaTeX 语法")

        except Exception as e:
            self.flash_status(f"❌ 异常: {e}")
        finally:
            self.after(0, lambda: self.btn_generate.configure(state="normal", text="✨ 生成 PDF 文件"))
            self.task_manager.finish()

