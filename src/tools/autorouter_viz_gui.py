import argparse
import os
import threading
from pathlib import Path
import sys

import customtkinter as ctk
import cv2
import numpy as np
import fitz  # PyMuPDF
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from layout_engine import AutoRouterLayoutExtractor
from gui_theme import Theme


def render_pdf_page(pdf_path: Path, page_index: int, dpi: int) -> Image.Image:
    doc = fitz.open(pdf_path)
    try:
        page = doc.load_page(page_index)
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    finally:
        doc.close()
    return img


def draw_boxes(img: Image.Image, items: list[dict], color=(0, 255, 0)) -> Image.Image:
    arr = np.array(img).copy()
    for item in items:
        x1, y1, x2, y2 = item.get("xyxy", [0, 0, 0, 0])
        cv2.rectangle(arr, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
    return Image.fromarray(arr)


def overlay_mask(img: Image.Image, mask: np.ndarray, color=(255, 0, 0), alpha=0.4) -> Image.Image:
    base = np.array(img).copy()
    overlay = base.copy()
    overlay[mask > 0] = color
    blended = cv2.addWeighted(overlay, alpha, base, 1 - alpha, 0)
    return Image.fromarray(blended)


class AutoRouterVizApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        Theme.init_fonts(self, base_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
        self.title("Auto Router Visualizer")
        self.geometry("1200x780")
        self.configure(fg_color=Theme.COLOR_BG_MAIN)

        self._images: dict[str, Image.Image] = {}
        self._tk_image = None
        self._second_pass_items: list[dict] = []
        self._pdf_page_count = 0

        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(self, fg_color=Theme.COLOR_BG_PANEL, corner_radius=Theme.CORNER_RADIUS_L)
        left.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        left.grid_columnconfigure(0, weight=1)

        right = ctk.CTkFrame(self, fg_color=Theme.COLOR_BG_PANEL, corner_radius=Theme.CORNER_RADIUS_L)
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 15), pady=15)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Input", font=(Theme.FONT_FAMILY_BOLD[0], 15)).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        self.mode_var = ctk.StringVar(value="pdf")
        mode_frame = ctk.CTkFrame(left, fg_color="transparent")
        mode_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=5)
        ctk.CTkLabel(mode_frame, text="Mode:", width=90, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(mode_frame, values=["pdf", "image"], variable=self.mode_var).pack(side="left", fill="x", expand=True)

        path_frame = ctk.CTkFrame(left, fg_color="transparent")
        path_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=5)
        ctk.CTkLabel(path_frame, text="Path:", width=90, anchor="w").pack(side="left")
        self.path_entry = ctk.CTkEntry(path_frame, placeholder_text="Select PDF or image...")
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(path_frame, text="Browse", width=80, command=self._browse).pack(side="left")

        pdf_frame = ctk.CTkFrame(left, fg_color="transparent")
        pdf_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=5)
        ctk.CTkLabel(pdf_frame, text="Page:", width=90, anchor="w").pack(side="left")
        self.page_entry = ctk.CTkEntry(pdf_frame, width=80)
        self.page_entry.insert(0, "1")
        self.page_entry.pack(side="left", padx=(0, 8))
        self.page_total_label = ctk.CTkLabel(pdf_frame, text="/ 0", width=50, anchor="w")
        self.page_total_label.pack(side="left", padx=(0, 8))
        self.btn_prev_page = ctk.CTkButton(pdf_frame, text="Prev", width=50, command=lambda: self._step_page(-1))
        self.btn_prev_page.pack(side="left", padx=(0, 4))
        self.btn_next_page = ctk.CTkButton(pdf_frame, text="Next", width=50, command=lambda: self._step_page(1))
        self.btn_next_page.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(pdf_frame, text="DPI:", width=40, anchor="w").pack(side="left")
        self.dpi_entry = ctk.CTkEntry(pdf_frame, width=80)
        self.dpi_entry.insert(0, "200")
        self.dpi_entry.pack(side="left")

        ctk.CTkLabel(left, text="DocLayout", font=(Theme.FONT_FAMILY_BOLD[0], 15)).grid(row=4, column=0, sticky="w", padx=15, pady=(15, 5))
        doc_frame = ctk.CTkFrame(left, fg_color="transparent")
        doc_frame.grid(row=5, column=0, sticky="ew", padx=15, pady=5)
        ctk.CTkLabel(doc_frame, text="Conf:", width=90, anchor="w").pack(side="left")
        self.conf_entry = ctk.CTkEntry(doc_frame, width=80)
        self.conf_entry.insert(0, "0.25")
        self.conf_entry.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(doc_frame, text="IoU:", width=40, anchor="w").pack(side="left")
        self.iou_entry = ctk.CTkEntry(doc_frame, width=80)
        self.iou_entry.insert(0, "0.45")
        self.iou_entry.pack(side="left")

        ctk.CTkLabel(left, text="Auto Router Params", font=(Theme.FONT_FAMILY_BOLD[0], 15)).grid(row=6, column=0, sticky="w", padx=15, pady=(15, 5))
        auto_frame = ctk.CTkFrame(left, fg_color="transparent")
        auto_frame.grid(row=7, column=0, sticky="ew", padx=15, pady=5)
        ctk.CTkLabel(auto_frame, text="Outside:", width=90, anchor="w").pack(side="left")
        self.outside_entry = ctk.CTkEntry(auto_frame, width=80)
        self.outside_entry.insert(0, "0.01")
        self.outside_entry.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(auto_frame, text="MinText:", width=60, anchor="w").pack(side="left")
        self.min_text_entry = ctk.CTkEntry(auto_frame, width=80)
        self.min_text_entry.insert(0, "0.0005")
        self.min_text_entry.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(auto_frame, text="MinArea:", width=60, anchor="w").pack(side="left")
        self.min_area_entry = ctk.CTkEntry(auto_frame, width=80)
        self.min_area_entry.insert(0, "30")
        self.min_area_entry.pack(side="left")

        auto2_frame = ctk.CTkFrame(left, fg_color="transparent")
        auto2_frame.grid(row=8, column=0, sticky="ew", padx=15, pady=5)
        ctk.CTkLabel(auto2_frame, text="Second Pass:", width=90, anchor="w").pack(side="left")
        self.var_second_pass = ctk.BooleanVar(value=True)
        self.chk_second_pass = ctk.CTkCheckBox(auto2_frame, text="Enable", variable=self.var_second_pass)
        self.chk_second_pass.pack(side="left")
        ctk.CTkLabel(auto2_frame, text="Mode:", width=50, anchor="w").pack(side="left", padx=(10, 0))
        self.router_mode_var = ctk.StringVar(value="any")
        self.router_mode_menu = ctk.CTkOptionMenu(
            auto2_frame,
            values=["any", "textness", "second_pass"],
            variable=self.router_mode_var,
            width=120,
        )
        self.router_mode_menu.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(left, text="Binarization", font=(Theme.FONT_FAMILY_BOLD[0], 15)).grid(row=8, column=0, sticky="w", padx=15, pady=(15, 5))
        bin_frame = ctk.CTkFrame(left, fg_color="transparent")
        bin_frame.grid(row=9, column=0, sticky="ew", padx=15, pady=5)
        ctk.CTkLabel(bin_frame, text="Method:", width=90, anchor="w").pack(side="left")
        self.method_var = ctk.StringVar(value="hybrid")
        ctk.CTkOptionMenu(bin_frame, values=["hybrid", "otsu", "adaptive"], variable=self.method_var).pack(side="left", fill="x", expand=True)

        bin2_frame = ctk.CTkFrame(left, fg_color="transparent")
        bin2_frame.grid(row=10, column=0, sticky="ew", padx=15, pady=5)
        ctk.CTkLabel(bin2_frame, text="Block:", width=90, anchor="w").pack(side="left")
        self.block_entry = ctk.CTkEntry(bin2_frame, width=80)
        self.block_entry.insert(0, "31")
        self.block_entry.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(bin2_frame, text="C:", width=40, anchor="w").pack(side="left")
        self.c_entry = ctk.CTkEntry(bin2_frame, width=80)
        self.c_entry.insert(0, "15")
        self.c_entry.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(bin2_frame, text="Open:", width=50, anchor="w").pack(side="left")
        self.open_entry = ctk.CTkEntry(bin2_frame, width=60)
        self.open_entry.insert(0, "2")
        self.open_entry.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(bin2_frame, text="Close:", width=50, anchor="w").pack(side="left")
        self.close_entry = ctk.CTkEntry(bin2_frame, width=60)
        self.close_entry.insert(0, "3")
        self.close_entry.pack(side="left")

        out_frame = ctk.CTkFrame(left, fg_color="transparent")
        out_frame.grid(row=11, column=0, sticky="ew", padx=15, pady=10)
        ctk.CTkLabel(out_frame, text="Output:", width=90, anchor="w").pack(side="left")
        self.out_entry = ctk.CTkEntry(out_frame)
        self.out_entry.insert(0, "output/auto_router_viz")
        self.out_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(out_frame, text="Open", width=70, command=self._open_output_dir).pack(side="left")

        self.run_btn = ctk.CTkButton(left, text="Run", height=40, command=self._run)
        self.run_btn.grid(row=12, column=0, sticky="ew", padx=15, pady=(10, 15))

        ctk.CTkLabel(right, text="Preview", font=(Theme.FONT_FAMILY_BOLD[0], 15)).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        view_frame = ctk.CTkFrame(right, fg_color="transparent")
        view_frame.grid(row=0, column=0, sticky="e", padx=15, pady=(15, 5))
        self.view_var = ctk.StringVar(value="outside_overlay")
        self.view_menu = ctk.CTkOptionMenu(
            view_frame,
            values=["page", "doclayout_boxes", "text_mask", "outside_mask", "outside_overlay", "second_pass_boxes"],
            variable=self.view_var,
            command=lambda _v: self._update_view(),
            width=160,
        )
        self.view_menu.pack(side="right")

        self.image_label = ctk.CTkLabel(right, text="")
        self.image_label.grid(row=1, column=0, sticky="nsew", padx=15, pady=(5, 10))

        self.status_label = ctk.CTkLabel(right, text="Ready", anchor="w", justify="left")
        self.status_label.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 15))

    def _browse(self) -> None:
        if self.mode_var.get() == "pdf":
            path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF Files", "*.pdf")])
        else:
            path = filedialog.askopenfilename(
                title="Select Image",
                filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.tiff")],
            )
        if path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, path)
            if self.mode_var.get() == "pdf":
                try:
                    doc = fitz.open(path)
                    self._pdf_page_count = doc.page_count
                    doc.close()
                except Exception:
                    self._pdf_page_count = 0
                self.page_total_label.configure(text=f"/ {self._pdf_page_count}")

    def _open_output_dir(self) -> None:
        path = self.out_entry.get().strip()
        if not path:
            return
        os.makedirs(path, exist_ok=True)
        if os.name == "nt":
            os.startfile(path)
        else:
            messagebox.showinfo("Info", f"Output dir: {path}")

    def _run(self) -> None:
        self.run_btn.configure(state="disabled")
        self.status_label.configure(text="Running...")
        threading.Thread(target=self._run_worker, daemon=True).start()

    def _run_worker(self) -> None:
        try:
            mode = self.mode_var.get()
            path = self.path_entry.get().strip()
            if not path:
                raise ValueError("Please select a PDF or image.")

            if mode == "pdf":
                page_idx = max(1, int(float(self.page_entry.get().strip() or "1"))) - 1
                if self._pdf_page_count > 0:
                    if page_idx < 0:
                        page_idx = 0
                    if page_idx >= self._pdf_page_count:
                        page_idx = self._pdf_page_count - 1
                    self.after(0, lambda: self.page_entry.delete(0, "end"))
                    self.after(0, lambda v=page_idx + 1: self.page_entry.insert(0, str(v)))
                dpi = int(float(self.dpi_entry.get().strip() or "200"))
                img = render_pdf_page(Path(path), page_idx, dpi)
            else:
                img = Image.open(path).convert("RGB")

            conf = float(self.conf_entry.get().strip() or "0.25")
            iou = float(self.iou_entry.get().strip() or "0.45")
            outside_ratio = float(self.outside_entry.get().strip() or "0.01")
            min_text_ratio = float(self.min_text_entry.get().strip() or "0.0005")
            min_area = int(float(self.min_area_entry.get().strip() or "30"))
            use_second_pass = bool(self.var_second_pass.get())
            router_mode = (self.router_mode_var.get().strip() or "any").lower()
            bin_method = self.method_var.get()
            block = int(float(self.block_entry.get().strip() or "31"))
            c_val = int(float(self.c_entry.get().strip() or "15"))
            open_k = int(float(self.open_entry.get().strip() or "2"))
            close_k = int(float(self.close_entry.get().strip() or "3"))

            router = AutoRouterLayoutExtractor(
                require_deepseek=False,
                text_outside_ratio=outside_ratio,
                min_text_ratio=min_text_ratio,
                min_component_area=min_area,
                binarize_method=bin_method,
                adaptive_block_size=block,
                adaptive_c=c_val,
                open_kernel=open_k,
                close_kernel=close_k,
                use_second_pass=use_second_pass,
            )

            doc_items_all = router._doclayout_detect_items(
                img, conf=conf, iou=iou, ignored_labels=["abandon"], include_ignored=True
            )
            doc_items = [it for it in doc_items_all if it.get("label") != "abandon"]
            text_mask = router._textness_mask(img)

            h, w = text_mask.shape
            total_text = int(text_mask.sum())
            text_ratio = total_text / float(w * h)

            box_mask = np.zeros_like(text_mask, dtype=np.uint8)
            for item in doc_items_all:
                x1, y1, x2, y2 = item.get("xyxy", [0, 0, 0, 0])
                x1 = max(0, min(w, int(x1)))
                x2 = max(0, min(w, int(x2)))
                y1 = max(0, min(h, int(y1)))
                y2 = max(0, min(h, int(y2)))
                if x2 <= x1 or y2 <= y1:
                    continue
                cv2.rectangle(box_mask, (x1, y1), (x2, y2), 1, thickness=-1)

            outside_mask = (text_mask & (1 - box_mask)).astype(np.uint8)
            outside = int(outside_mask.sum())
            outside_ratio_val = (outside / total_text) if total_text > 0 else 0.0
            use_deepseek = (text_ratio >= min_text_ratio) and (outside_ratio_val >= outside_ratio)

            second_items = []
            if use_second_pass:
                erased = router._erase_boxes(img, doc_items_all)
                second_items = router._doclayout_detect_items(
                    erased, conf=conf, iou=iou, ignored_labels=["abandon"], include_ignored=False
                )
                if len(second_items) > 0:
                    use_deepseek = True

            self._second_pass_items = second_items

            if router_mode == "textness":
                use_deepseek = (text_ratio >= min_text_ratio) and (outside_ratio_val >= outside_ratio)
            elif router_mode == "second_pass":
                use_deepseek = len(second_items) > 0

            out_dir = Path(self.out_entry.get().strip() or "output/auto_router_viz")
            out_dir.mkdir(parents=True, exist_ok=True)

            self._images = {
                "page": img,
                "doclayout_boxes": draw_boxes(img, doc_items),
                "text_mask": Image.fromarray((text_mask * 255).astype(np.uint8)),
                "outside_mask": Image.fromarray((outside_mask * 255).astype(np.uint8)),
                "outside_overlay": overlay_mask(img, outside_mask),
                "second_pass_boxes": draw_boxes(img, second_items, color=(255, 165, 0)),
            }

            self._images["page"].save(out_dir / "page.png")
            self._images["doclayout_boxes"].save(out_dir / "doclayout_boxes.png")
            self._images["text_mask"].save(out_dir / "text_mask.png")
            self._images["outside_mask"].save(out_dir / "outside_mask.png")
            self._images["outside_overlay"].save(out_dir / "outside_overlay.png")

            status = (
                f"Text ratio: {text_ratio:.6f} | Outside ratio: {outside_ratio_val:.6f} "
                f"| Second pass: {len(second_items)} | Use Deepseek: {use_deepseek}"
            )
            self.after(0, lambda: self._set_status(status))
            self.after(0, self._update_view)
        except Exception as e:
            err = str(e)
            self.after(0, lambda: messagebox.showerror("Error", err))
            self.after(0, lambda: self._set_status(f"Error: {err}"))
        finally:
            self.after(0, lambda: self.run_btn.configure(state="normal"))

    def _set_status(self, text: str) -> None:
        self.status_label.configure(text=text)

    def _step_page(self, delta: int) -> None:
        try:
            cur = int(float(self.page_entry.get().strip() or "1"))
        except Exception:
            cur = 1
        cur += delta
        if cur < 1:
            cur = 1
        if self._pdf_page_count > 0 and cur > self._pdf_page_count:
            cur = self._pdf_page_count
        self.page_entry.delete(0, "end")
        self.page_entry.insert(0, str(cur))

    def _update_view(self) -> None:
        key = self.view_var.get()
        if not self._images or key not in self._images:
            return
        img = self._images[key]
        w = self.image_label.winfo_width() or 800
        h = self.image_label.winfo_height() or 600
        if w <= 10 or h <= 10:
            w, h = 900, 600
        img_copy = img.copy()
        img_copy.thumbnail((w, h))
        self._tk_image = ImageTk.PhotoImage(img_copy)
        self.image_label.configure(image=self._tk_image)


def main() -> None:
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = AutoRouterVizApp()
    app.mainloop()


if __name__ == "__main__":
    main()
