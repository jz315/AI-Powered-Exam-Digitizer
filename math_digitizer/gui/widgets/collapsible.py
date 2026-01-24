from __future__ import annotations

import customtkinter as ctk
from math_digitizer.gui.theme import Theme

class CollapsibleFrame(ctk.CTkFrame):
    """可折叠面板组件 - 用于隐藏高级设置"""

    def __init__(
        self,
        parent,
        title: str = "高级设置",
        expanded: bool = False,
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._expanded = expanded

        self._header = ctk.CTkFrame(self, fg_color="transparent", cursor="hand2")
        self._header.pack(fill="x")

        self._arrow = ctk.CTkLabel(
            self._header,
            text="▶" if not expanded else "▼",
            width=20,
            font=(Theme.FONT_FAMILY[0], 12),
            text_color=Theme.COLOR_TEXT_SECONDARY,
        )
        self._arrow.pack(side="left", padx=(0, 5))

        self._title_label = ctk.CTkLabel(
            self._header,
            text=title,
            font=(Theme.FONT_FAMILY[0], 13),
            text_color=Theme.COLOR_TEXT_SECONDARY,
        )
        self._title_label.pack(side="left")

        self._content = ctk.CTkFrame(self, fg_color="transparent")
        if expanded:
            self._content.pack(fill="x", pady=(8, 0))

        self._header.bind("<Button-1>", self._toggle)
        self._arrow.bind("<Button-1>", self._toggle)
        self._title_label.bind("<Button-1>", self._toggle)

    @property
    def content(self) -> ctk.CTkFrame:
        """返回内容区域供外部添加控件"""
        return self._content

    def _toggle(self, event=None):
        self._expanded = not self._expanded
        if self._expanded:
            self._arrow.configure(text="▼")
            self._content.pack(fill="x", pady=(8, 0))
        else:
            self._arrow.configure(text="▶")
            self._content.pack_forget()

    def expand(self):
        if not self._expanded:
            self._toggle()

    def collapse(self):
        if self._expanded:
            self._toggle()
