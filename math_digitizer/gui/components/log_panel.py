from __future__ import annotations

import os
import subprocess
import sys
import time


class LogMixin:

    def _append_log(self, msg: str, level: str = "info"):
        ts = time.strftime("%H:%M:%S", time.localtime())
        level = level.lower()
        prefix_map = {
            "info": "INFO",
            "warn": "WARN",
            "warning": "WARN",
            "error": "ERR ",
            "err": "ERR ",
            "debug": "DBG ",
        }
        prefix = prefix_map.get(level, "INFO")
        line = f"[{ts}] [{prefix}] {msg}\n"
        if hasattr(self, "log_textbox"):
            self.after(0, lambda l=line, lv=level: self._update_log_ui(l, lv))
        if hasattr(self, "ocr_console"):
            self.after(0, lambda l=line: self._update_ocr_console_ui(l))
        if hasattr(self, "_log_lock") and hasattr(self, "_log_path"):
            with self._log_lock:
                with open(self._log_path, "a", encoding="utf-8") as f:
                    f.write(line)

    def flash_status(self, msg: str):
        self.after(0, lambda: self.status_label.configure(text=msg))
        self._append_log(msg)

    def _update_log_ui(self, line: str, level: str = "info"):
        try:
            if not hasattr(self, "log_textbox"):
                return
            current_filter = getattr(self, "_log_filter_level", "all")
            if current_filter != "all" and level != current_filter:
                if not hasattr(self, "_log_buffer"):
                    self._log_buffer = []
                self._log_buffer.append((line, level))
                return

            self.log_textbox.configure(state="normal")
            start_idx = self.log_textbox.index("end-1c")
            self.log_textbox.insert("end", line)
            end_idx = self.log_textbox.index("end-1c")

            tag = f"log_{level}"
            self.log_textbox.tag_add(tag, start_idx, end_idx)

            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
        except Exception:
            pass

    def _update_ocr_console_ui(self, line: str):
        try:
            if not hasattr(self, "ocr_console"):
                return
            self.ocr_console.configure(state="normal")
            self.ocr_console.insert("end", line)
            self.ocr_console.see("end")
            self.ocr_console.configure(state="disabled")
        except Exception:
            pass

    def _configure_log_tags(self):
        if not hasattr(self, "log_textbox"):
            return
        try:
            self.log_textbox.tag_config("log_info", foreground=("#1A1A1A", "#E0E0E0"))
            self.log_textbox.tag_config("log_warn", foreground=("#B8860B", "#FFD700"))
            self.log_textbox.tag_config("log_error", foreground=("#CC0000", "#FF6B6B"))
            self.log_textbox.tag_config("log_debug", foreground=("#6C757D", "#888888"))
        except Exception:
            pass

    def _clear_log(self):
        if not hasattr(self, "log_textbox"):
            return
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("0.0", "end")
        self.log_textbox.configure(state="disabled")
        if hasattr(self, "_log_buffer"):
            self._log_buffer.clear()

    def _init_log_file(self) -> str:
        d = os.path.join("output", "logs")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, time.strftime("gui_%Y%m%d.log"))

    def _open_log_file(self):
        if not hasattr(self, "_log_path"):
            return
        path = self._log_path
        if os.path.exists(path):
            if os.name == "nt":
                os.startfile(path)
            else:
                subprocess.call(["open" if sys.platform == "darwin" else "xdg-open", path])

    def _set_log_filter(self, level: str):
        self._log_filter_level = level.lower()
        self._refresh_log_display()

    def _refresh_log_display(self):
        if not hasattr(self, "log_textbox") or not hasattr(self, "_log_path"):
            return
        try:
            with open(self._log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return

        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("0.0", "end")

        current_filter = getattr(self, "_log_filter_level", "all")
        for line in lines:
            level = "info"
            if "[WARN]" in line:
                level = "warn"
            elif "[ERR ]" in line:
                level = "error"
            elif "[DBG ]" in line:
                level = "debug"

            if current_filter != "all" and level != current_filter:
                continue

            start_idx = self.log_textbox.index("end-1c")
            self.log_textbox.insert("end", line)
            end_idx = self.log_textbox.index("end-1c")
            self.log_textbox.tag_add(f"log_{level}", start_idx, end_idx)

        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

