from __future__ import annotations

import sys
from pathlib import Path


def _ensure_utf8_stdio() -> None:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main() -> None:
    _ensure_utf8_stdio()

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

