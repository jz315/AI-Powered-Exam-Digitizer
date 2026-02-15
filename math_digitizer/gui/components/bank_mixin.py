from __future__ import annotations

import threading


class BankMixin:

    def _start_import_from_editor(self):
        self.btn_import_bank.configure(state="disabled", text="⏳ 导入中...")
        threading.Thread(target=self._run_import_from_editor, daemon=True).start()

    def _run_import_from_editor(self):
        try:
            json_str = self.json_textbox.get("0.0", "end").strip()
            result = self.bank_service.import_from_json(json_str)
            if result.success:
                self.flash_status(f"✅ {result.message}")
            else:
                self.flash_status(f"❌ {result.message}")

        except Exception as e:
            self.flash_status(f"❌ 入库异常: {e}")
        finally:
            self.after(0, lambda: self.btn_import_bank.configure(state="normal", text="📥 导入到题库"))
