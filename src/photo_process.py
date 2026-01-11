import customtkinter as ctk
from tkinter import filedialog, messagebox
import cv2
import numpy as np
from PIL import Image
import os
import threading

# --- 设置主题 ---
ctk.set_appearance_mode("System")  # 跟随系统 (System, Dark, Light)
ctk.set_default_color_theme("blue")  # 主题颜色

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 窗口基础设置
        self.title("试卷去水印工具 Pro")
        self.geometry("1200x750")
        
        # 数据变量
        self.cv_image = None        # 原始 OpenCV 图片
        self.processed_img = None   # 处理后的 OpenCV 图片
        self.file_path = ""
        self.batch_files = []
        
        # --- 布局配置 ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ================= 左侧侧边栏 (控制区) =================
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        # 标题
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Paper Cleaner", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # 1. 打开按钮
        self.btn_open = ctk.CTkButton(self.sidebar_frame, text="📂 打开图片 (支持批量)", command=self.open_image)
        self.btn_open.grid(row=1, column=0, padx=20, pady=10)

        # 2. 参数控制组
        self.lbl_thresh = ctk.CTkLabel(self.sidebar_frame, text="去水印强度: 175", anchor="w")
        self.lbl_thresh.grid(row=2, column=0, padx=20, pady=(20, 0), sticky="w")
        
        self.slider_thresh = ctk.CTkSlider(self.sidebar_frame, from_=100, to=230, number_of_steps=130, command=self.update_thresh_label)
        self.slider_thresh.set(175)
        self.slider_thresh.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")

        # 3. 加粗选项
        self.switch_thicken = ctk.CTkSwitch(self.sidebar_frame, text="文字加粗增强")
        self.switch_thicken.grid(row=4, column=0, padx=20, pady=10, sticky="w")
        self.switch_thicken.configure(command=self.process_image) # 点击即触发

        # 4. 保存按钮
        self.btn_save = ctk.CTkButton(self.sidebar_frame, text="💾 保存结果", fg_color="green", hover_color="darkgreen", state="disabled", command=self.save_result)
        self.btn_save.grid(row=5, column=0, padx=20, pady=20)

        # 进度条 (隐藏状态)
        self.progressbar = ctk.CTkProgressBar(self.sidebar_frame, mode="determinate")
        self.progressbar.grid(row=6, column=0, padx=20, pady=10, sticky="ew")
        self.progressbar.set(0)
        self.progressbar.grid_remove() # 默认隐藏

        # 状态标签
        self.lbl_status = ctk.CTkLabel(self.sidebar_frame, text="等待导入...", text_color="gray", wraplength=200)
        self.lbl_status.grid(row=7, column=0, padx=20, pady=10)

        # 外观模式切换
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="界面主题:", anchor="w")
        self.appearance_mode_label.grid(row=9, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["System", "Light", "Dark"], command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=10, column=0, padx=20, pady=(10, 20))


        # ================= 右侧主区域 (预览区) =================
        self.preview_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.preview_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.preview_frame.grid_columnconfigure(1, weight=1)
        self.preview_frame.grid_rowconfigure(1, weight=1)

        # 标题
        ctk.CTkLabel(self.preview_frame, text="原始图像", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, pady=5)
        ctk.CTkLabel(self.preview_frame, text="去水印效果", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, pady=5)

        # 图片容器
        self.img_label_orig = ctk.CTkLabel(self.preview_frame, text="", fg_color=("gray90", "gray20"), corner_radius=10)
        self.img_label_orig.grid(row=1, column=0, sticky="nsew", padx=5)
        
        self.img_label_proc = ctk.CTkLabel(self.preview_frame, text="请先打开图片", fg_color=("gray85", "gray25"), corner_radius=10)
        self.img_label_proc.grid(row=1, column=1, sticky="nsew", padx=5)


    # --- 逻辑处理 ---

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def update_thresh_label(self, value):
        # 滑块拖动回调：更新文字 + 触发处理（为了性能，可以用释放时触发，这里简化为实时）
        self.lbl_thresh.configure(text=f"去水印强度: {int(value)}")
        self.process_image()

    def open_image(self):
        file_paths = filedialog.askopenfilenames(
            title="选择图片",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
        )
        if not file_paths: return

        self.batch_files = file_paths
        self.file_path = file_paths[0]
        
        # 读取第一张用于预览 (imdecode 处理中文路径)
        self.cv_image = cv2.imdecode(np.fromfile(self.file_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        
        if self.cv_image is None:
            messagebox.showerror("错误", "无法读取图片")
            return

        # 更新状态
        if len(self.batch_files) > 1:
            self.lbl_status.configure(text=f"已加载 {len(self.batch_files)} 张图片\n当前预览第 1 张")
            self.btn_save.configure(text=f"💾 批量保存 ({len(self.batch_files)})", state="normal")
        else:
            self.lbl_status.configure(text=f"已加载: {os.path.basename(self.file_path)}")
            self.btn_save.configure(text="💾 保存当前", state="normal")

        # 显示原图
        self.display_image(self.cv_image, self.img_label_orig)
        # 触发第一次处理
        self.process_image()

    def process_image(self, _=None):
        if self.cv_image is None: return

        # 1. 获取参数
        thresh_val = int(self.slider_thresh.get())
        do_thicken = self.switch_thicken.get()

        # 2. 图像处理
        gray = cv2.cvtColor(self.cv_image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)

        if do_thicken:
            kernel = np.ones((2, 2), np.uint8)
            binary = cv2.erode(binary, kernel, iterations=1)

        self.processed_img = binary
        
        # 3. 显示结果
        # 转回 RGB 格式以便 PIL 读取 (虽然是灰度，但转一下兼容性好)
        disp_img = cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)
        self.display_image(disp_img, self.img_label_proc)

    def display_image(self, cv_img, label_widget):
        # 转换 OpenCV -> PIL -> CTkImage
        # 注意：OpenCV 是 BGR，PIL 需要 RGB
        if len(cv_img.shape) == 2: # 灰度图
            rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_GRAY2RGB)
        else:
            rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            
        pil_image = Image.fromarray(rgb_img)
        
        # 计算显示大小 (保持比例)
        # 假设预览区域大概是 400x500，这里我们动态计算稍微麻烦，
        # 直接指定一个较大的 CTkImage size，它会自动缩放显示
        
        # 获取 label 当前尺寸作为参考，或者给一个固定合理值
        display_w = 400
        display_h = 550
        
        ctk_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(display_w, display_h))
        
        label_widget.configure(image=ctk_img, text="") 

    def save_result(self):
        if len(self.batch_files) > 1:
            save_dir = filedialog.askdirectory(title="选择保存文件夹")
            if save_dir:
                threading.Thread(target=self.batch_process_thread, args=(save_dir,)).start()
        else:
            save_path = filedialog.asksaveasfilename(
                defaultextension=".jpg",
                filetypes=[("JPG", "*.jpg"), ("PNG", "*.png")],
                initialfile="clean_" + os.path.basename(self.file_path)
            )
            if save_path:
                cv2.imwrite(save_path, self.processed_img)
                messagebox.showinfo("成功", "保存成功！")

    def batch_process_thread(self, save_dir):
        # 锁定按钮
        self.btn_save.configure(state="disabled", text="处理中...")
        self.progressbar.grid()
        
        thresh_val = int(self.slider_thresh.get())
        do_thicken = self.switch_thicken.get()
        total = len(self.batch_files)
        
        for i, path in enumerate(self.batch_files):
            try:
                # 更新进度
                progress = (i + 1) / total
                self.progressbar.set(progress)
                self.lbl_status.configure(text=f"正在处理: {i+1}/{total}")
                
                # 读取
                img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
                if img is None: continue
                
                # 处理
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                _, binary = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
                
                if do_thicken:
                    kernel = np.ones((2, 2), np.uint8)
                    binary = cv2.erode(binary, kernel, iterations=1)
                
                # 保存
                filename = "clean_" + os.path.basename(path)
                save_path = os.path.join(save_dir, filename)
                cv2.imencode('.jpg', binary)[1].tofile(save_path)
                
            except Exception as e:
                print(f"Skipped {path}: {e}")

        self.progressbar.grid_remove()
        self.lbl_status.configure(text="全部处理完成")
        self.btn_save.configure(state="normal", text=f"💾 批量保存 ({total})")
        messagebox.showinfo("完成", "所有图片已处理完毕！")

if __name__ == "__main__":
    app = App()
    app.mainloop()