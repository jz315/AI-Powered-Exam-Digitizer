# Math Digitizer - 智能数学试卷排版工具

将 LLM（大语言模型）生成的结构化 JSON 数据自动转换为排版精美的 LaTeX 试卷 PDF。

## ✨ 主要功能

- **智能化流程**：配合 LLM (如 Claude, ChatGPT, Gemini) 将题目文本/图片转换为结构化数据
- **自动化排版**：基于 `exam-zh` 试卷模板，自动生成专业的数学试卷布局
- **现代 GUI**：使用 CustomTkinter 构建的现代化图形界面，支持深色/浅色模式
- **PDF 版面分析**：基于 DocLayout-YOLO 的智能文档布局识别
- **一键编译**：内置 XeLaTeX 编译流程，直接输出最终 PDF

---

## 🛠️ 环境要求

| 组件 | 要求 |
|------|------|
| **Python** | 3.11 或更高版本 |
| **LaTeX** | TeX Live 或 MiKTeX (需包含 `xelatex` 命令并添加到 PATH) |
| **PyTorch** | 2.0+ (GPU 版本需要 CUDA 11.8/12.1) |

---

## 📥 XeLaTeX 安装教程

本项目使用 XeLaTeX 编译试卷 PDF，需要先安装 LaTeX 发行版。

### Windows

#### 方式一：TeX Live（推荐）

1. **下载安装程序**
   - 访问 [TeX Live 官网](https://tug.org/texlive/acquire-netinstall.html)
   - 下载 `install-tl-windows.exe`

2. **运行安装**
   ```
   双击 install-tl-windows.exe
   选择 "Simple install" (约 5GB)
   等待安装完成（可能需要 1-2 小时）
   ```

3. **验证安装**
   ```powershell
   # 重新打开 PowerShell
   xelatex --version
   ```

#### 方式二：MiKTeX（更轻量）

1. **下载安装程序**
   - 访问 [MiKTeX 官网](https://miktex.org/download)
   - 下载 Windows 安装包

2. **运行安装**
   - 选择 "Install for all users"
   - 勾选 "Install missing packages on-the-fly: Yes"

3. **验证安装**
   ```powershell
   xelatex --version
   ```

> **提示**：MiKTeX 会在首次编译时自动下载缺失的宏包，首次运行可能较慢。

---

### macOS

#### 方式一：MacTeX（推荐）

```bash
# 使用 Homebrew 安装（约 4GB）
brew install --cask mactex

# 安装完成后，重新打开终端
xelatex --version
```

#### 方式二：BasicTeX（精简版）

```bash
# 精简版（约 100MB），按需下载宏包
brew install --cask basictex

# 安装必要的中文支持包
sudo tlmgr update --self
sudo tlmgr install ctex xecjk fontspec exam-zh
```

---

### Linux

#### Ubuntu / Debian

```bash
# 完整安装（推荐，约 5GB）
sudo apt update
sudo apt install texlive-full

# 或精简安装 + 中文支持
sudo apt install texlive-xetex texlive-lang-chinese texlive-fonts-recommended
```

#### Arch Linux

```bash
sudo pacman -S texlive-most texlive-langchinese
```

#### Fedora

```bash
sudo dnf install texlive-scheme-full
```

---

### 验证 XeLaTeX 安装

安装完成后，运行以下命令验证：

```bash
# 检查 xelatex 是否可用
xelatex --version

# 应该输出类似：
# XeTeX 3.141592653-2.6-0.999995 (TeX Live 2024)
```

如果提示 "command not found"，需要将 LaTeX 添加到系统 PATH：

| 系统 | 默认安装路径 |
|------|-------------|
| Windows (TeX Live) | `C:\texlive\2024\bin\windows` |
| Windows (MiKTeX) | `C:\Program Files\MiKTeX\miktex\bin\x64` |
| macOS | `/Library/TeX/texbin` |
| Linux | `/usr/bin` (通常已在 PATH) |

---

## 📦 安装

### 第一步：安装pytorch
> **为什么 PyTorch 要单独装？**  
> PyTorch 的 GPU/CPU 版本不同，无法在 `pyproject.toml` 中统一指定。用户需根据自己的硬件环境选择安装。


PyTorch 需要根据你的硬件环境单独安装。访问 [PyTorch 官网](https://pytorch.org/get-started/locally/) 获取最新安装命令。

#### 常用安装命令

| 环境 | 命令 |
|------|------|
| **CUDA 12.1** (推荐) | `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121` |
| **CUDA 11.8** | `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118` |
| **CPU only** | `pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu` |

#### 验证安装

```python
import torch
print(f"PyTorch 版本: {torch.__version__}")
print(f"CUDA 可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA 版本: {torch.version.cuda}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
```

---
### 第二步：安装项目

本项目使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理。

```bash
# 1. 安装 uv（如果还没有）
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 克隆仓库
git clone https://github.com/jz315/AI-Powered-Exam-Digitizer.git
cd AI-Powered-Exam-Digitizer

# 3. 同步项目依赖（自动创建 .venv 虚拟环境）
uv sync

# 4. 运行
uv run python main.py
```




---

## 🚀 快速开始

### 启动 GUI

```bash
# 使用 uv
uv run python main.py

# 或直接运行
python main.py

# 或使用安装后的命令
math-digitizer
```

Windows 用户也可以双击 `run.vbs` 启动（无控制台窗口）。

### PDF 版面分析 CLI （没啥用可以忽略）

```bash
# 分析 PDF 并提取版面元素
python pdf_ocr_cli.py your_file.pdf --out output --dpi 200

# 或使用安装后的命令
pdf-layout your_file.pdf --out output --dpi 200
```

---

## 📖 使用流程

1. **准备题目**：找到你需要排版的数学试题（pdf）
2. **提取数据**：
   - 打开本应用，上传PDF
   - 等待处理，复制OCR结构
   - 如果不需要转换为PDF, 更改后缀为.md即可查看
3. **转换格式**：   
   - 复制Prompt和OCR文本
   - 一起发送给 LLM (Claude/GPT/Gemini)
   - LLM 会返回结构化的 JSON 数据
3. **生成试卷**：
   - 将 JSON 代码粘贴到输入框
   - 点击 **"生成试卷"**
4. **获取结果**：
   - 程序会自动校验数据、生成 `.tex` 文件并调用 `xelatex` 编译
   - 输出文件位于 `output/` 目录下

---

## 📄 JSON 数据格式示例

```json
{
  "meta": {
    "title": "高三数学模拟考试",
    "subject": "数学"
  },
  "sections": [
    {
      "type": "problem",
      "title": "选择题",
      "questions": [
        {
          "id": 1,
          "content": "已知集合 $A=\\{x|x^2-1<0\\}$，则...",
          "options": ["$(-1,1)$", "$(0,1)$", "$(-1,0)$", "$(1,+\\infty)$"]
        }
      ]
    },
    {
      "type": "problem",
      "title": "填空题",
      "questions": [
        {
          "id": 13,
          "content": "函数 $f(x)=x^2$ 的导数为 __BLANK__ 。"
        }
      ]
    }
  ]
}
```

---

## 📂 项目结构

```
.
├── main.py              # GUI 程序入口
├── pdf_ocr_cli.py       # PDF 版面分析 CLI
├── pyproject.toml       # 项目配置与依赖
├── src/
│   ├── gui.py           # 图形界面实现
│   ├── generator.py     # LaTeX 生成与编译核心逻辑
│   ├── validator.py     # JSON 数据校验
│   ├── layout_engine.py # DocLayout-YOLO 版面分析引擎
│   ├── exam_template.txt # Jinja2 LaTeX 模板
│   └── prompt.md        # LLM 提示词
├── layout_models/       # YOLO 模型文件
└── output/              # 生成结果目录
```

---

## 🔨 开发者指南

### 从源码开发

```bash
# 克隆仓库
git clone https://github.com/jz315/AI-Powered-Exam-Digitizer.git
cd AI-Powered-Exam-Digitizer

# 使用 uv 创建开发环境
uv sync

# 或使用 pip
pip install -e ".[dev]"
```

### 自定义试卷样式

修改 `src/exam_template.txt` 可调整试卷的整体样式（页眉、页脚、装订线等）。

### 图片支持

在 JSON 中通过 `image` 字段指定图片路径或尺寸，生成器会自动生成占位空间。

---

## ❓ 常见问题

### Q: 没有 GPU，能用吗？

可以。安装 CPU 版本的 PyTorch 即可：
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```
PDF 版面分析会较慢，但 GUI 主要功能正常使用。

### Q: CUDA 版本不匹配怎么办？

检查你的 CUDA 版本：
```bash
nvidia-smi
```
然后选择对应的 PyTorch 安装命令（CUDA 11.8 或 12.1）。

### Q: xelatex 命令未找到？

确保已安装 TeX Live 或 MiKTeX，并将其添加到系统 PATH：
- Windows: 检查 `C:\texlive\2024\bin\windows` 或 MiKTeX 安装目录
- macOS: `brew install --cask mactex`
- Linux: `sudo apt install texlive-full`

---

## 📜 License

MIT
