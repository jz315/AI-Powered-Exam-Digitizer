from __future__ import annotations

import os
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog
from PIL import Image


class _FallbackTheme:
    FONT_FAMILY_BOLD = (
        "Bahnschrift SemiBold",
        "Segoe UI Variable Display Semibold",
        "Segoe UI Semibold",
    )
    FONT_FAMILY = ("Bahnschrift", "Segoe UI Variable Text", "Segoe UI")
    COLOR_BG_MAIN = ("#F4F0EA", "#121212")
    COLOR_BG_PANEL = ("#FFFFFF", "#1C1C1C")
    COLOR_TEXT_PRIMARY = ("#1E1B16", "#F5F5F4")
    COLOR_TEXT_SECONDARY = ("#6B625A", "#A1A1AA")
    COLOR_BLUE_BTN = ("#1D4ED8", "#3B82F6")
    COLOR_BLUE_HOVER = ("#1E40AF", "#2563EB")
    COLOR_GREEN_BTN = ("#0F766E", "#14B8A6")
    COLOR_GREEN_HOVER = ("#0B5F59", "#0D9488")
    COLOR_BORDER = ("#E4DED4", "#2B2B2B")
    PAD_OUTER = 22
    PAD_INNER = 12
    CORNER_RADIUS_L = 18
    CORNER_RADIUS_S = 12


class ImagePreprocessTool(ctk.CTkToplevel):
    def __init__(self, master=None, *, theme=None, on_close=None):
        super().__init__(master)
        self._theme = theme or _FallbackTheme
        self._on_close = on_close

        self._image_original = None
        self._image_gray = None
        self._image_processed = None
        self._image_path = None

        self._preview_original = None
        self._preview_processed = None
        self._preview_size = (440, 320)
        self._update_job = None

        self.title("图片预处理 - 去水印（二值化）")
        self.geometry("980x700")
        self.minsize(860, 620)
        self.configure(fg_color=self._theme.COLOR_BG_MAIN)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.protocol("WM_DELETE_WINDOW", self._handle_close)
        self._build_ui()

    def _build_ui(self):
        pad_outer = self._theme.PAD_OUTER
        pad_inner = self._theme.PAD_INNER

        toolbar = ctk.CTkFrame(
            self,
            fg_color=self._theme.COLOR_BG_PANEL,
            corner_radius=self._theme.CORNER_RADIUS_L,
            border_width=1,
            border_color=self._theme.COLOR_BORDER,
        )
        toolbar.grid(row=0, column=0, sticky="ew", padx=pad_outer, pady=(pad_outer, pad_inner))
        toolbar.grid_columnconfigure(1, weight=1)

        self.btn_open = ctk.CTkButton(
            toolbar,
            text="打开图片",
            command=self._open_image,
            height=40,
            corner_radius=self._theme.CORNER_RADIUS_S,
            font=(self._theme.FONT_FAMILY_BOLD[0], 13),
            fg_color=self._theme.COLOR_BLUE_BTN,
            hover_color=self._theme.COLOR_BLUE_HOVER,
        )
        self.btn_open.grid(row=0, column=0, padx=(pad_inner, 10), pady=pad_inner)

        self.path_label = ctk.CTkLabel(
            toolbar,
            text="未选择图片",
            font=(self._theme.FONT_FAMILY[0], 12),
            text_color=self._theme.COLOR_TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=520,
        )
        self.path_label.grid(row=0, column=1, sticky="ew", padx=10, pady=pad_inner)

        self.btn_save = ctk.CTkButton(
            toolbar,
            text="保存结果",
            command=self._save_image,
            height=40,
            corner_radius=self._theme.CORNER_RADIUS_S,
            font=(self._theme.FONT_FAMILY_BOLD[0], 13),
            fg_color=self._theme.COLOR_GREEN_BTN,
            hover_color=self._theme.COLOR_GREEN_HOVER,
            state="disabled",
        )
        self.btn_save.grid(row=0, column=2, padx=(10, pad_inner), pady=pad_inner)

        preview_frame = ctk.CTkFrame(self, fg_color="transparent")
        preview_frame.grid(row=1, column=0, sticky="nsew", padx=pad_outer, pady=(0, pad_inner))
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_columnconfigure(1, weight=1)
        preview_frame.grid_rowconfigure(0, weight=1)

        self.original_panel = self._build_image_panel(preview_frame, "原图")
        self.original_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.processed_panel = self._build_image_panel(preview_frame, "二值化结果")
        self.processed_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        controls = ctk.CTkFrame(
            self,
            fg_color=self._theme.COLOR_BG_PANEL,
            corner_radius=self._theme.CORNER_RADIUS_L,
            border_width=1,
            border_color=self._theme.COLOR_BORDER,
        )
        controls.grid(row=2, column=0, sticky="ew", padx=pad_outer, pady=(0, pad_inner))
        controls.grid_columnconfigure(1, weight=1)

        self.threshold_label = ctk.CTkLabel(
            controls,
            text="阈值: 180",
            font=(self._theme.FONT_FAMILY_BOLD[0], 12),
            text_color=self._theme.COLOR_TEXT_PRIMARY,
        )
        self.threshold_label.grid(row=0, column=0, padx=pad_inner, pady=pad_inner)

        self.threshold_slider = ctk.CTkSlider(
            controls,
            from_=0,
            to=255,
            number_of_steps=255,
            command=self._on_threshold_change,
        )
        self.threshold_slider.grid(row=0, column=1, sticky="ew", padx=(0, pad_inner), pady=pad_inner)
        self.threshold_slider.set(180)
        self.threshold_slider.configure(state="disabled")

        self.status_label = ctk.CTkLabel(
            self,
            text="打开一张图片开始处理",
            font=(self._theme.FONT_FAMILY[0], 12),
            text_color=self._theme.COLOR_TEXT_SECONDARY,
        )
        self.status_label.grid(row=3, column=0, sticky="ew", padx=pad_outer, pady=(0, pad_outer))

        self.original_image_label = self._attach_image_label(self.original_panel, "暂无图片")
        self.processed_image_label = self._attach_image_label(self.processed_panel, "暂无图片")

    def _build_image_panel(self, master, title):
        panel = ctk.CTkFrame(
            master,
            fg_color=self._theme.COLOR_BG_PANEL,
            corner_radius=self._theme.CORNER_RADIUS_L,
            border_width=1,
            border_color=self._theme.COLOR_BORDER,
        )
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)

        title_label = ctk.CTkLabel(
            panel,
            text=title,
            font=(self._theme.FONT_FAMILY_BOLD[0], 13),
            text_color=self._theme.COLOR_TEXT_PRIMARY,
        )
        title_label.grid(row=0, column=0, sticky="w", padx=self._theme.PAD_INNER, pady=(self._theme.PAD_INNER, 6))

        return panel

    def _attach_image_label(self, panel, placeholder):
        label = ctk.CTkLabel(
            panel,
            text=placeholder,
            font=(self._theme.FONT_FAMILY[0], 12),
            text_color=self._theme.COLOR_TEXT_SECONDARY,
            anchor="center",
            justify="center",
        )
        label.grid(row=1, column=0, sticky="nsew", padx=self._theme.PAD_INNER, pady=(0, self._theme.PAD_INNER))
        return label

    def _handle_close(self):
        if callable(self._on_close):
            try:
                self._on_close()
            except Exception:
                pass
        self.destroy()

    def _set_status(self, msg):
        self.status_label.configure(text=msg)

    def _open_image(self):
        filetypes = [
            ("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.tiff"),
            ("All Files", "*.*"),
        ]
        path = filedialog.askopenfilename(title="选择图片", filetypes=filetypes)
        if not path:
            return

        try:
            img = Image.open(path)
            img.load()
        except Exception as exc:
            self._set_status(f"打开失败: {exc}")
            return

        img = self._normalize_image(img)
        self._image_path = path
        self._image_original = img
        self._image_gray = img.convert("L")

        self.path_label.configure(text=path)
        self.threshold_slider.configure(state="normal")
        self.btn_save.configure(state="normal")

        self._render_preview(self._image_original, target="original")
        self._update_processed()
        self._set_status(f"已加载: {os.path.basename(path)}")

    def _normalize_image(self, img: Image.Image) -> Image.Image:
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            base = Image.new("RGB", img.size, (255, 255, 255))
            base.paste(img.convert("RGBA"), mask=img.split()[-1])
            return base
        return img.convert("RGB")

    def _on_threshold_change(self, value):
        threshold = int(float(value))
        self.threshold_label.configure(text=f"阈值: {threshold}")

        if self._update_job is not None:
            self.after_cancel(self._update_job)
        self._update_job = self.after(80, self._update_processed)

    def _update_processed(self):
        self._update_job = None
        if self._image_gray is None:
            return

        threshold = int(self.threshold_slider.get())
        table = [0] * threshold + [255] * (256 - threshold)
        self._image_processed = self._image_gray.point(table, mode="L")

        self._render_preview(self._image_processed, target="processed")

    def _render_preview(self, image, *, target):
        if image is None:
            if target == "original":
                self.original_image_label.configure(text="暂无图片", image=None)
            else:
                self.processed_image_label.configure(text="暂无图片", image=None)
            return

        preview = image.copy()
        preview.thumbnail(self._preview_size, Image.LANCZOS)
        ctk_image = ctk.CTkImage(light_image=preview, dark_image=preview, size=preview.size)

        if target == "original":
            self._preview_original = ctk_image
            self.original_image_label.configure(image=ctk_image, text="")
        else:
            self._preview_processed = ctk_image
            self.processed_image_label.configure(image=ctk_image, text="")

    def _save_image(self):
        if self._image_processed is None:
            self._set_status("暂无可保存的结果")
            return

        default_name = "binarized.png"
        if self._image_path:
            stem = Path(self._image_path).stem
            default_name = f"{stem}_binary.png"

        save_path = filedialog.asksaveasfilename(
            title="保存二值化结果",
            defaultextension=".png",
            initialfile=default_name,
            filetypes=[
                ("PNG", "*.png"),
                ("JPEG", "*.jpg;*.jpeg"),
                ("Bitmap", "*.bmp"),
                ("TIFF", "*.tif;*.tiff"),
            ],
        )
        if not save_path:
            return

        try:
            self._image_processed.save(save_path)
            self._set_status(f"已保存: {save_path}")
        except Exception as exc:
            self._set_status(f"保存失败: {exc}")
