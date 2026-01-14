from __future__ import annotations

import os
import tkinter.font as tkfont
import zipfile

import customtkinter as ctk

class Theme:
    # 字体 stack：优先使用系统无衬线字体
    FONT_FAMILY_BOLD = ("Inter", "Segoe UI", "Microsoft YaHei UI Bold", "Arial")
    FONT_FAMILY = ("Inter", "Segoe UI", "Microsoft YaHei UI", "Arial")
    FONT_CODE = ("JetBrains Mono", "Cascadia Code", "Consolas", "Courier New")

    @classmethod
    def init_fonts(cls, root, base_dir: str | None = None) -> None:
        families = cls._get_families(root)
        if "inter" not in families:
            cls._try_load_inter(base_dir)
            families = cls._get_families(root)

        cls.FONT_FAMILY = (cls._pick_family(cls.FONT_FAMILY, families),)
        cls.FONT_FAMILY_BOLD = (cls._pick_family(cls.FONT_FAMILY_BOLD, families),)
        cls.FONT_CODE = (cls._pick_family(cls.FONT_CODE, families),)

    @staticmethod
    def _get_families(root):
        try:
            return {f.lower(): f for f in tkfont.families(root)}
        except Exception:
            try:
                return {f.lower(): f for f in tkfont.families()}
            except Exception:
                return {}

    @staticmethod
    def _pick_family(candidates, families):
        if isinstance(candidates, (list, tuple)):
            for name in candidates:
                if name.lower() in families:
                    return families[name.lower()]
            if candidates:
                return candidates[0]
        return "Segoe UI"

    @classmethod
    def _try_load_inter(cls, base_dir: str | None) -> None:
        if base_dir is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        zip_path = os.path.join(base_dir, "Inter.zip")
        if not os.path.exists(zip_path):
            return

        font_dir = os.path.join(base_dir, "output", "fonts", "inter")
        os.makedirs(font_dir, exist_ok=True)
        try:
            with zipfile.ZipFile(zip_path) as zf:
                targets = [
                    "static/Inter_18pt-Regular.ttf",
                    "static/Inter_18pt-Medium.ttf",
                    "static/Inter_18pt-Bold.ttf",
                ]
                for name in targets:
                    if name not in zf.namelist():
                        continue
                    dest = os.path.join(font_dir, os.path.basename(name))
                    if not os.path.exists(dest):
                        with zf.open(name) as src, open(dest, "wb") as dst:
                            dst.write(src.read())
        except Exception:
            return

        if not hasattr(ctk, "FontManager") or not hasattr(ctk.FontManager, "load_font"):
            return
        for filename in os.listdir(font_dir):
            if filename.lower().endswith(".ttf"):
                try:
                    ctk.FontManager.load_font(os.path.join(font_dir, filename))
                except Exception:
                    pass

    # 配色：使用更高级的微调色彩
    COLOR_BG_MAIN = ("#F8F9FA", "#121212")    # 极浅灰 / 纯黑
    COLOR_BG_PANEL = ("#FFFFFF", "#1E1E1E")   # 纯白 / 深灰
    
    COLOR_TEXT_PRIMARY = ("#1A1A1A", "#E0E0E0")
    COLOR_TEXT_SECONDARY = ("#6C757D", "#A0A0A0")
    
    # 品牌色：降低饱和度，更有质感
    COLOR_BLUE_BTN = ("#0066FF", "#3385FF")
    COLOR_BLUE_HOVER = ("#0052CC", "#1A75FF")
    
    COLOR_GREEN_BTN = ("#28A745", "#34C759")
    COLOR_GREEN_HOVER = ("#218838", "#28A745")
    
    COLOR_BORDER = ("#E9ECEF", "#2D2D2D")     # 极其浅的边框
    
    # 间距与圆角
    PAD_OUTER = 30
    PAD_INNER = 20
    CORNER_RADIUS_L = 12
    CORNER_RADIUS_S = 8