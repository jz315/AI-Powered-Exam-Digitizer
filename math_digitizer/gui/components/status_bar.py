from __future__ import annotations


class StatusMixin:
    def flash_status(self, msg):
        self.after(0, lambda: self.status_label.configure(text=msg))
        self._append_log(msg)
