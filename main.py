from __future__ import annotations

import sys
import os
from pathlib import Path


def _fix_stdio_for_frozen() -> None:
    """PyInstaller + console=False 时 stdout/stderr 可能为 None"""
    if getattr(sys, 'frozen', False):
        if sys.stdout is None:
            sys.stdout = open(os.devnull, 'w', encoding='utf-8')
        if sys.stderr is None:
            sys.stderr = open(os.devnull, 'w', encoding='utf-8')


def _ensure_utf8_stdio() -> None:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main() -> None:
    _fix_stdio_for_frozen()
    _ensure_utf8_stdio()

    # 源码运行时需要添加 src 目录到路径
    if not getattr(sys, 'frozen', False):
        repo_root = Path(__file__).resolve().parent
        src_dir = repo_root / "src"
        sys.path.insert(0, str(src_dir))

    # Windows 高分屏适配
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    from gui import PremiumExamApp

    app = PremiumExamApp()
    app.mainloop()


if __name__ == "__main__":
    main()

