import customtkinter as ctk
import tkinter as tk
import os
import json
import threading
import pyperclip
import subprocess
import sys
import shutil  # 关键库：用于文件搬运
from generator import ExamGenerator
from validator import ValidationIssue, extract_first_latex_error, validate_json_and_latex

# --- 全局配置 ---
ctk.set_appearance_mode("System")  # 跟随系统深色/浅色模式

# --- 高级设计常量 (Theme) ---
class Theme:
    # 字体栈：优先使用系统自带的高品质中文字体
    FONT_FAMILY_BOLD = ("Microsoft YaHei UI Bold", ".PingFang SC Semibold", "Helvetica Neue Bold", "Arial Bold")
    FONT_FAMILY = ("Microsoft YaHei UI", ".PingFang SC", "Helvetica Neue", "Arial")
    FONT_CODE = ("JetBrains Mono", "Consolas", "Courier New")

    # 颜色系统 (Light, Dark)
    COLOR_BG_MAIN = ("#F2F2F7", "#1C1C1E")      # 窗口背景
    COLOR_BG_PANEL = ("#FFFFFF", "#2C2C2E")     # 面板/卡片背景
    COLOR_TEXT_PRIMARY = ("#000000", "#FFFFFF")
    COLOR_TEXT_SECONDARY = ("#8E8E93", "#98989E")
    
    # 功能色
    COLOR_BLUE_BTN = ("#007AFF", "#0A84FF")     # iOS Blue
    COLOR_BLUE_HOVER = ("#0062CC", "#0070E0")
    COLOR_GREEN_BTN = ("#34C759", "#30D158")    # iOS Green
    COLOR_GREEN_HOVER = ("#248A3D", "#28CD41")
    COLOR_BORDER = ("#E5E5EA", "#3A3A3C")       # 边框色

    # 布局参数
    PAD_OUTER = 25
    PAD_INNER = 15
    CORNER_RADIUS_L = 16
    CORNER_RADIUS_S = 10

class PremiumExamApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. 窗口基础设置
        self.title("数学试卷数字化工具 (Math Digitizer)")
        self.geometry("1100x760")
        self.configure(fg_color=Theme.COLOR_BG_MAIN)
        
        # 2. 核心网格布局 (左右分栏)
        # column 0: 左侧控制区 (占3份)
        # column 1: 右侧代码区 (占5份)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=5)
        self.grid_rowconfigure(0, weight=0)    # 标题栏
        self.grid_rowconfigure(1, weight=1)    # 主内容区

        # 初始化业务逻辑
        self.generator = ExamGenerator(template_file='src/exam_template.txt')
        self.prompt_file = 'src/prompt.md'

        # === 顶部 Header ===
        self.setup_header()

        # === 左侧面板 (Controls) ===
        self.left_frame = ctk.CTkFrame(
            self, 
            fg_color="transparent", 
            corner_radius=0
        )
        self.left_frame.grid(row=1, column=0, sticky="nsew", padx=(Theme.PAD_OUTER, Theme.PAD_INNER/2), pady=(0, Theme.PAD_OUTER))
        
        self.setup_step1_card() # 复制 Prompt
        self.setup_step2_card() # 文件名配置
        self.setup_action_card() # 生成按钮

        # === 右侧面板 (JSON Editor) ===
        self.right_frame = ctk.CTkFrame(
            self, 
            fg_color=Theme.COLOR_BG_PANEL, 
            corner_radius=Theme.CORNER_RADIUS_L,
            border_width=1,
            border_color=Theme.COLOR_BORDER
        )
        self.right_frame.grid(row=1, column=1, sticky="nsew", padx=(Theme.PAD_INNER/2, Theme.PAD_OUTER), pady=(0, Theme.PAD_OUTER))
        
        # 右侧内部布局
        self.right_frame.grid_rowconfigure(1, weight=4) # JSON 区域伸缩
        self.right_frame.grid_rowconfigure(2, weight=1) # 问题面板伸缩
        self.right_frame.grid_columnconfigure(0, weight=1)

        self._validation_after_id = None
        self._last_issues = []
        self._validation_seq = 0
        self._validation_lock = threading.Lock()
        self._validation_pending_seq = 0
        self._validation_pending_text = ""
        self._validation_request_event = threading.Event()
        self._validation_stop_event = threading.Event()
        self._validation_worker: threading.Thread | None = None

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.setup_json_editor()
        self._ensure_validation_worker()

    # ---------------- 界面构建 ----------------

    def _on_close(self):
        try:
            self._validation_stop_event.set()
            self._validation_request_event.set()
        except Exception:
            pass
        self.destroy()

    def _ensure_validation_worker(self):
        if self._validation_worker is not None and self._validation_worker.is_alive():
            return

        self._validation_worker = threading.Thread(target=self._validation_worker_loop, daemon=True)
        self._validation_worker.start()

    def _validation_worker_loop(self):
        while not self._validation_stop_event.is_set():
            self._validation_request_event.wait()
            self._validation_request_event.clear()

            if self._validation_stop_event.is_set():
                break

            with self._validation_lock:
                seq = self._validation_pending_seq
                json_str = self._validation_pending_text

            data, issues = validate_json_and_latex(json_str)

            def apply_result():
                if self._validation_stop_event.is_set():
                    return
                if seq != self._validation_seq:
                    return

                self._set_issues_panel(issues)

                if data and isinstance(data, dict):
                    try:
                        new_t = data.get("meta", {}).get("title")
                        if new_t and not self.entry_filename.get().strip():
                            self.entry_filename.delete(0, "end")
                            self.entry_filename.insert(0, str(new_t))
                    except Exception:
                        pass

            try:
                self.after(0, apply_result)
            except Exception:
                pass

    def setup_header(self):
        """顶部通栏"""
        header_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=Theme.PAD_OUTER, pady=(20, 20))
        
        title_label = ctk.CTkLabel(
            header_frame, 
            text="📐 数学试卷数字化工具", 
            font=(Theme.FONT_FAMILY_BOLD[0], 22),
            text_color=Theme.COLOR_TEXT_PRIMARY
        )
        title_label.pack(side="left")

        self.status_label = ctk.CTkLabel(
            header_frame, 
            text="准备就绪", 
            font=(Theme.FONT_FAMILY[0], 13),
            text_color=Theme.COLOR_TEXT_SECONDARY
        )
        self.status_label.pack(side="right", pady=(5, 0))

    def create_left_card(self, title, icon):
        """左侧卡片工厂方法"""
        card = ctk.CTkFrame(
            self.left_frame, 
            fg_color=Theme.COLOR_BG_PANEL, 
            corner_radius=Theme.CORNER_RADIUS_L,
            border_width=1,
            border_color=Theme.COLOR_BORDER
        )
        card.pack(fill="x", pady=(0, 20))
        
        lbl = ctk.CTkLabel(
            card,
            text=f"{icon}  {title}",
            font=(Theme.FONT_FAMILY_BOLD[0], 15),
            text_color=Theme.COLOR_TEXT_PRIMARY
        )
        lbl.pack(anchor="w", padx=Theme.PAD_INNER, pady=(Theme.PAD_INNER, 5))
        return card

    def setup_step1_card(self):
        """Step 1: OCR Prompt"""
        card = self.create_left_card("识别提示词 (OCR Prompt)", "📄")
        
        desc = ctk.CTkLabel(
            card, 
            text="将此提示词发送给 AI 模型 (如 GPT-4o, Claude 3.5) 以提取 JSON 格式数据。",
            font=(Theme.FONT_FAMILY[0], 12),
            text_color=Theme.COLOR_TEXT_SECONDARY,
            anchor="w", justify="left", wraplength=320
        )
        desc.pack(fill="x", padx=Theme.PAD_INNER, pady=(0, 15))

        self.btn_copy = ctk.CTkButton(
            card,
            text="📋 复制提示词",
            command=self.copy_prompt,
            height=40,
            corner_radius=Theme.CORNER_RADIUS_S,
            font=(Theme.FONT_FAMILY_BOLD[0], 14),
            fg_color=Theme.COLOR_BLUE_BTN,
            hover_color=Theme.COLOR_BLUE_HOVER
        )
        self.btn_copy.pack(fill="x", padx=Theme.PAD_INNER, pady=(0, Theme.PAD_INNER))

    def setup_step2_card(self):
        """Step 2: Config"""
        card = self.create_left_card("文件配置", "⚙️")
        
        self.entry_filename = ctk.CTkEntry(
            card,
            placeholder_text="📝 文件名 (留空自动从JSON检测)",
            height=40,
            corner_radius=Theme.CORNER_RADIUS_S,
            font=(Theme.FONT_FAMILY[0], 13),
            border_width=1,
            fg_color=("gray98", "gray20")
        )
        self.entry_filename.pack(fill="x", padx=Theme.PAD_INNER, pady=(5, Theme.PAD_INNER))

    def setup_action_card(self):
        """Action Area"""
        container = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        container.pack(fill="x", pady=(10, 0))

        self.btn_generate = ctk.CTkButton(
            container,
            text="✨ 生成 PDF 文件",
            command=self.start_generation_thread,
            height=55,
            corner_radius=27, # Pill Shape
            font=(Theme.FONT_FAMILY_BOLD[0], 18),
            fg_color=Theme.COLOR_GREEN_BTN,
            hover_color=Theme.COLOR_GREEN_HOVER
        )
        self.btn_generate.pack(fill="x")

    def setup_json_editor(self):
        """右侧 JSON 编辑器"""
        # 标题区
        title_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=Theme.PAD_INNER, pady=Theme.PAD_INNER)
        
        lbl = ctk.CTkLabel(
            title_frame,
            text="💻  JSON 数据输入",
            font=(Theme.FONT_FAMILY_BOLD[0], 15),
            text_color=Theme.COLOR_TEXT_PRIMARY
        )
        lbl.pack(side="left")

        sub_lbl = ctk.CTkLabel(
            title_frame,
            text="请粘贴 AI 返回的完整 JSON",
            font=(Theme.FONT_FAMILY[0], 12),
            text_color=Theme.COLOR_TEXT_SECONDARY
        )
        sub_lbl.pack(side="right")

        # 文本框
        editor_frame = ctk.CTkFrame(
            self.right_frame,
            fg_color=("gray95", "#1E1E1E"),
            corner_radius=Theme.CORNER_RADIUS_S,
            border_width=0,
        )
        editor_frame.grid(row=1, column=0, sticky="nsew", padx=Theme.PAD_INNER, pady=(0, Theme.PAD_INNER))
        editor_frame.grid_rowconfigure(0, weight=1)
        editor_frame.grid_columnconfigure(1, weight=1)

        self.line_numbers = tk.Canvas(
            editor_frame,
            width=46,
            highlightthickness=0,
            bd=0,
        )
        self.line_numbers.grid(row=0, column=0, sticky="ns")

        self.json_textbox = ctk.CTkTextbox(
            editor_frame,
            font=(Theme.FONT_CODE[0], 13),
            corner_radius=Theme.CORNER_RADIUS_S,
            fg_color=("gray95", "#1E1E1E"), # 代码区颜色区分
            border_width=0,
            activate_scrollbars=True
        )
        self.json_textbox.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        # 绑定自动检测标题
        self.json_textbox.bind("<KeyRelease>", self.on_json_change)
        self._text_widget = self.json_textbox._textbox
        self._bind_editor_events()
        self._configure_editor_tags()
        self._update_line_numbers()

        # 校验/错误提示面板（只提示，不自动修复）
        issues_frame = ctk.CTkFrame(
            self.right_frame,
            fg_color=("gray98", "gray20"),
            corner_radius=Theme.CORNER_RADIUS_S,
            border_width=1,
            border_color=Theme.COLOR_BORDER,
        )
        issues_frame.grid(row=2, column=0, sticky="nsew", padx=Theme.PAD_INNER, pady=(0, Theme.PAD_INNER))
        issues_frame.grid_rowconfigure(1, weight=1)
        issues_frame.grid_columnconfigure(0, weight=1)

        self.issues_header_label = ctk.CTkLabel(
            issues_frame,
            text="🧪 校验结果：未校验",
            font=(Theme.FONT_FAMILY_BOLD[0], 13),
            text_color=Theme.COLOR_TEXT_SECONDARY,
        )
        self.issues_header_label.grid(row=0, column=0, sticky="w", padx=Theme.PAD_INNER, pady=(10, 6))

        self.issues_textbox = ctk.CTkTextbox(
            issues_frame,
            font=(Theme.FONT_CODE[0], 12),
            corner_radius=Theme.CORNER_RADIUS_S,
            fg_color=("gray95", "#1A1A1A"),
            border_width=0,
            height=140,
            activate_scrollbars=True,
        )
        self.issues_textbox.grid(row=1, column=0, sticky="nsew", padx=Theme.PAD_INNER, pady=(0, Theme.PAD_INNER))
        self._set_issues_panel([], header="🧪 校验结果：未校验")

    def _bind_editor_events(self):
        if not hasattr(self, "_text_widget"):
            return
        self._text_widget.bind("<KeyRelease>", self._on_editor_change, add=True)
        self._text_widget.bind("<MouseWheel>", self._on_editor_scroll, add=True)
        self._text_widget.bind("<ButtonRelease-1>", self._on_editor_scroll, add=True)
        self._text_widget.bind("<Configure>", self._on_editor_scroll, add=True)

    def _configure_editor_tags(self):
        if not hasattr(self, "_text_widget"):
            return
        error_bg, warn_bg = self._issue_tag_colors()
        self._text_widget.tag_configure("error_line", background=error_bg)
        self._text_widget.tag_configure("warning_line", background=warn_bg)

    def _issue_tag_colors(self) -> tuple[str, str]:
        mode = ctk.get_appearance_mode()
        if mode == "Dark":
            return "#3A1E1E", "#3A2B0F"
        return "#FFECEC", "#FFF6DD"

    def _line_number_colors(self) -> tuple[str, str]:
        mode = ctk.get_appearance_mode()
        if mode == "Dark":
            return "#252525", "#6E6E73"
        return "#ECECF1", "#8E8E93"

    def _on_editor_change(self, event=None):
        self._update_line_numbers()

    def _on_editor_scroll(self, event=None):
        self._update_line_numbers()

    def _update_line_numbers(self):
        if not hasattr(self, "line_numbers") or not hasattr(self, "_text_widget"):
            return
        bg, fg = self._line_number_colors()
        self.line_numbers.configure(background=bg)
        self.line_numbers.delete("all")

        i = self._text_widget.index("@0,0")
        while True:
            dline = self._text_widget.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            line_num = i.split(".")[0]
            self.line_numbers.create_text(
                40,
                y,
                anchor="ne",
                text=line_num,
                fill=fg,
                font=(Theme.FONT_CODE[0], 11),
            )
            i = self._text_widget.index(f"{i}+1line")

    def _apply_issue_highlights(self, issues: list[ValidationIssue]):
        if not hasattr(self, "_text_widget"):
            return
        self._text_widget.tag_remove("error_line", "1.0", "end")
        self._text_widget.tag_remove("warning_line", "1.0", "end")

        error_lines = set()
        warning_lines = set()
        for it in issues:
            if it.line is None:
                continue
            if it.severity == "error":
                error_lines.add(it.line)
            elif it.severity == "warning":
                warning_lines.add(it.line)

        for line in warning_lines:
            self._text_widget.tag_add("warning_line", f"{line}.0", f"{line}.0 lineend")
        for line in error_lines:
            self._text_widget.tag_add("error_line", f"{line}.0", f"{line}.0 lineend")

        self._update_line_numbers()

    # ---------------- 逻辑功能 ----------------

    def copy_prompt(self):
        """复制 Prompt"""
        try:
            if os.path.exists(self.prompt_file):
                with open(self.prompt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                pyperclip.copy(content)
                self.flash_status("✅ 提示词已成功复制！")
            else:
                self.flash_status(f"❌ 错误：找不到文件 {self.prompt_file}")
        except Exception as e:
            self.flash_status(f"❌ 复制出错: {e}")

    def on_json_change(self, event=None):
        """输入 JSON 时：节流校验 + 自动提取 Title"""
        self._schedule_validation()

    def _schedule_validation(self, delay_ms: int = 250):
        if self._validation_after_id is not None:
            try:
                self.after_cancel(self._validation_after_id)
            except Exception:
                pass
        self._validation_after_id = self.after(delay_ms, self._run_validation_from_editor)

    def _run_validation_from_editor(self):
        self._validation_after_id = None
        json_str = self.json_textbox.get("0.0", "end").strip()

        self._validation_seq += 1
        seq = self._validation_seq

        self._set_issues_panel([], header="🧪 校验中...")

        with self._validation_lock:
            self._validation_pending_seq = seq
            self._validation_pending_text = json_str

        self._validation_request_event.set()

    def _set_issues_panel(self, issues: list[ValidationIssue], header: str | None = None):
        self._last_issues = issues
        errors = sum(1 for i in issues if i.severity == "error")
        warnings = sum(1 for i in issues if i.severity == "warning")

        if header is None:
            header = f"🧪 校验结果：{errors} 错误，{warnings} 警告"

        header_color = Theme.COLOR_TEXT_SECONDARY
        if errors:
            header_color = ("#FF3B30", "#FF453A")
        elif warnings:
            header_color = ("#FF9F0A", "#FF9F0A")

        if hasattr(self, "issues_header_label"):
            self.issues_header_label.configure(text=header, text_color=header_color)

        if not hasattr(self, "issues_textbox"):
            return

        text = self._format_issues_text(issues)
        self.issues_textbox.configure(state="normal")
        self.issues_textbox.delete("0.0", "end")
        self.issues_textbox.insert("end", text)
        self.issues_textbox.configure(state="disabled")
        self._apply_issue_highlights(issues)

    def _format_issues_text(self, issues: list[ValidationIssue], limit: int = 200) -> str:
        if not issues:
            return "未发现明显问题（仍建议以 LaTeX 编译结果为准）。\n"

        lines: list[str] = []
        shown = issues[:limit]
        for it in shown:
            tag = {"error": "E", "warning": "W", "info": "I"}.get(it.severity, "?")
            loc = ""
            if it.line is not None and it.col is not None:
                loc = f" (line {it.line}, col {it.col})"
            path = f"{it.path}: " if it.path else ""
            lines.append(f"[{tag}]{loc} {path}{it.message}")
            if it.context:
                lines.append(it.context.rstrip("\n"))
                lines.append("")

        if len(issues) > limit:
            lines.append(f"... 还有 {len(issues) - limit} 条未显示")

        return "\n".join(lines).rstrip() + "\n"

    def start_generation_thread(self):
        """后台线程处理，防止卡顿"""
        self.btn_generate.configure(state="disabled", text="⏳ 正在处理...")
        threading.Thread(target=self.run_generation, daemon=True).start()

    def run_generation(self):
        """
        核心生成逻辑：
        1. 在 temp_build (纯英文路径) 下生成 main.tex 并编译
        2. 编译成功后，将 main.pdf 复制到 output/中文名/ 下并重命名
        """
        try:
            # --- 1. 获取输入数据 ---
            json_str = self.json_textbox.get("0.0", "end").strip()
            custom_fn = self.entry_filename.get().strip()

            if not json_str:
                self.flash_status("❌ 请输入 JSON 数据")
                return

            # 生成前强制做一次校验（只提示，不修复）
            data, issues = validate_json_and_latex(json_str)
            self._set_issues_panel(issues)

            err_n = sum(1 for i in issues if i.severity == "error")
            warn_n = sum(1 for i in issues if i.severity == "warning")
            if err_n:
                self.flash_status(f"❌ 发现 {err_n} 个错误，请先修正后再生成")
                return
            if warn_n:
                self.flash_status(f"⚠️ 发现 {warn_n} 个警告（仍将继续生成）")

            # --- 2. 规划路径 ---
            
            # A. 用户想要的最终路径 (包含中文)
            # 例如: output/长沙一中2024/
            final_folder_name = custom_fn if custom_fn else data.get('meta', {}).get('title', 'exam_output')
            invalid_chars = '<>:"/\\|?*'
            final_folder_name = "".join([c for c in final_folder_name if c not in invalid_chars]).strip() or "exam_output"
            
            final_output_dir = os.path.abspath(os.path.join("output", final_folder_name))
            
            # B. 编译用的临时安全路径 (纯英文，绝对路径)
            # 例如: ./temp_build/
            safe_temp_dir = os.path.abspath("temp_build") 

            self.flash_status(f"📂 准备编译环境...")

            # --- 3. 环境初始化 ---
            
            # 清理并重建临时目录
            if os.path.exists(safe_temp_dir):
                shutil.rmtree(safe_temp_dir)
            os.makedirs(safe_temp_dir, exist_ok=True)

            # 确保最终输出目录存在
            if not os.path.exists(final_output_dir):
                os.makedirs(final_output_dir, exist_ok=True)

            # --- 4. 生成 TeX (在安全区) ---
            
            # 强制使用 main.tex，保证文件名纯英文，XeLaTeX 友好
            temp_tex_path = os.path.join(safe_temp_dir, "main.tex")
            
            # 处理数据
            processed = self.generator.process_data(json.dumps(data))
            if not processed:
                self.flash_status("❌ 数据处理失败")
                return

            # 渲染模板到临时目录
            if not self.generator.render(processed, output_tex=temp_tex_path):
                self.flash_status("❌ 模板渲染失败")
                return

            # --- 5. 编译 PDF (在安全区) ---
            self.flash_status("⚙️ 正在沙盒中编译 PDF...")
            
            # 调用 generator 编译，因为它是在 safe_temp_dir 下，且文件名是 main.tex
            # 路径全是英文，XeLaTeX 极其稳定
            self.generator.compile_pdf(temp_tex_path)

            # --- 6. 搬运结果 (从安全区 -> 中文区) ---
            
            temp_pdf_path = os.path.join(safe_temp_dir, "main.pdf")
            
            if os.path.exists(temp_pdf_path):
                # 目标文件名
                target_pdf_name = f"{final_folder_name}.pdf"
                target_path = os.path.join(final_output_dir, target_pdf_name)
                
                # 同时也把 tex 文件拷过去给用户看，方便修改
                target_tex_name = f"{final_folder_name}.tex"
                target_tex_path = os.path.join(final_output_dir, target_tex_name)

                try:
                    # 复制 PDF
                    shutil.copy2(temp_pdf_path, target_path)
                    # 复制 TeX
                    shutil.copy2(temp_tex_path, target_tex_path)
                    
                    self.flash_status("🎉 成功！PDF 已生成并保存")
                    
                    # 尝试打开最终的中文文件夹
                    try:
                        if os.name == 'nt': os.startfile(final_output_dir)
                        elif sys.platform == 'darwin': subprocess.call(['open', final_output_dir])
                        else: subprocess.call(['xdg-open', final_output_dir])
                    except: pass
                    
                except Exception as e:
                    self.flash_status(f"❌ 移动文件失败: {e}")
            else:
                log_path = os.path.join(safe_temp_dir, "main.log")
                detail = extract_first_latex_error(log_path, temp_tex_path)
                if detail:
                    merged = issues + [detail]
                    self._set_issues_panel(merged, header="❌ LaTeX 编译失败（已提取首个错误）")
                    self.flash_status("❌ LaTeX 编译失败：请查看右侧问题面板")
                else:
                    self.flash_status("❌ 编译失败，请检查 temp_build 目录下的日志")

        except Exception as e:
            self.flash_status(f"❌ 异常: {e}")
            print(e)
        finally:
            # 恢复按钮
            self.after(0, lambda: self.btn_generate.configure(state="normal", text="✨ 生成 PDF 文件"))

    def flash_status(self, msg):
        """线程安全地更新状态"""
        self.after(0, lambda: self._update_status(msg))

    def _update_status(self, msg):
        self.status_label.configure(text=msg)
        color = Theme.COLOR_TEXT_SECONDARY
        if "❌" in msg: color = "#FF3B30"       # Red
        elif "🎉" in msg or "✅" in msg: color = Theme.COLOR_GREEN_BTN
        elif "⚙️" in msg or "📂" in msg: color = Theme.COLOR_BLUE_BTN
        self.status_label.configure(text_color=color)

if __name__ == "__main__":
    # Windows 高分屏适配
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = PremiumExamApp()
    app.mainloop()
