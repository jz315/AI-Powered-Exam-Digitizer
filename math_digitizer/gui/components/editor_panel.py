from __future__ import annotations

import customtkinter as ctk

from math_digitizer.gui.theme import Theme


class EditorMixin:
    def _bind_editor_events(self):
        if not hasattr(self, "_text_widget"): return
        self._text_widget.bind("<KeyRelease>", self._on_editor_change, add=True)
        self._text_widget.bind("<MouseWheel>", self._on_editor_scroll, add=True)
        self._text_widget.bind("<ButtonRelease-1>", self._on_editor_scroll, add=True)
        self._text_widget.bind("<Configure>", self._on_editor_scroll, add=True)

    def _configure_editor_tags(self):
        if not hasattr(self, "_text_widget"): return
        self._text_widget.tag_configure("error_line", background="#3A1E1E" if ctk.get_appearance_mode()=="Dark" else "#FFECEC")
        self._text_widget.tag_configure("warning_line", background="#3A2B0F" if ctk.get_appearance_mode()=="Dark" else "#FFF6DD")

    def _on_editor_change(self, event=None): self._update_line_numbers()
    def _on_editor_scroll(self, event=None): self._update_line_numbers()

    def _update_line_numbers(self):
        if not hasattr(self, "line_numbers") or not hasattr(self, "_text_widget"): return
        self.line_numbers.delete("all")
        i = self._text_widget.index("@0,0")
        while True:
            dline = self._text_widget.dlineinfo(i)
            if dline is None: break
            self.line_numbers.create_text(35, dline[1], anchor="ne", text=i.split(".")[0], fill="#8E8E93", font=(Theme.FONT_CODE[0], 11))
            i = self._text_widget.index(f"{i}+1line")

    def _apply_issue_highlights(self, issues):
        if not hasattr(self, "_text_widget"): return
        self._text_widget.tag_remove("error_line", "1.0", "end")
        self._text_widget.tag_remove("warning_line", "1.0", "end")
        for it in issues:
            if it.line:
                tag = "error_line" if it.severity == "error" else "warning_line"
                self._text_widget.tag_add(tag, f"{it.line}.0", f"{it.line}.0 lineend")
        self._update_line_numbers()

    def on_json_change(self, event=None):
        if self._validation_after_id: self.after_cancel(self._validation_after_id)
        self._validation_after_id = self.after(300, self._run_validation_from_editor)

    def _run_validation_from_editor(self):
        self._validation_after_id = None
        json_str = self.json_textbox.get("0.0", "end").strip()
        self._validation_seq += 1
        with self._validation_lock:
            self._validation_pending_seq = self._validation_seq
            self._validation_pending_text = json_str
        self._set_issues_panel([], header="⏳ 校验中...")
        self._validation_request_event.set()

    def _set_issues_panel(self, issues, header=None):
        self._last_issues = issues
        errs = sum(1 for i in issues if i.severity == "error")
        warns = sum(1 for i in issues if i.severity == "warning")
        
        if header is None:
            if errs == 0 and warns == 0: header = "✓ 校验通过"
            else: header = f"⚠️ 发现 {errs} 个错误，{warns} 个警告"
            
        color = Theme.COLOR_GREEN_BTN if errs == 0 else "#FF3B30"
        if hasattr(self, "issues_header_label"):
            self.issues_header_label.configure(text=header, text_color=color)

        if hasattr(self, "issues_textbox"):
            text = ""
            for it in issues[:50]:
                text += f"[{it.severity.upper()}] Line {it.line}: {it.message}\n"
            self.issues_textbox.configure(state="normal")
            self.issues_textbox.delete("0.0", "end")
            self.issues_textbox.insert("end", text)
            self.issues_textbox.configure(state="disabled")
            self._apply_issue_highlights(issues)

