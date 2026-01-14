from __future__ import annotations

from gui_app import PremiumExamApp


if __name__ == "__main__":
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app = PremiumExamApp()
    app.mainloop()
