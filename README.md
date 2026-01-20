# Math Digitizer - 智能数学试卷排版工具

将 LLM（大语言模型）生成的结构化 JSON 数据自动转换为排版精美的 LaTeX 试卷 PDF。

## 📑 目录

- [✨ 主要功能](#-主要功能)
- [🛠️ 环境要求](#️-环境要求)
- [📥 XeLaTeX 安装教程](#-xelatex-安装教程)
  - [Windows](#windows)
  - [macOS](#macos)
  - [Linux](#linux)
- [📦 安装](#-安装)
- [🔧 高级：自定义 PyTorch 版本](#-高级自定义-pytorch-版本)
- [🚀 快速开始](#-快速开始)
- [📖 使用流程](#-使用流程)
- [📄 JSON 数据格式示例](#-json-数据格式示例)
- [🧩 组卷系统（题库 + 规则）](#-组卷系统题库--规则)
- [📂 项目结构](#-项目结构)
- [🔨 开发者指南](#-开发者指南)
- [🤖 AI 助手指南](AI_INSTRUCTIONS.md)
- [❓ 常见问题](#-常见问题)
- [📜 License](#-license)

---

## ✨ 主要功能

- **智能化流程**：配合 LLM (如 Claude, ChatGPT, Gemini, DeepSeek) 将题目文本/图片转换为结构化数据
- **自动化排版**：基于 `exam-zh` 试卷模板，自动生成专业的数学试卷布局
- **现代 GUI**：使用 CustomTkinter 构建的现代化图形界面，支持深色/浅色模式
- **智能版面分析**：
  - **Auto Router**: 智能路由模式，优先使用本地模型，识别效果不佳时自动切换到 DeepSeek OCR
  - **DocLayout-YOLO**: 本地高性能版面分析模型 (默认)
  - **DeepSeek OCR**: 纯云端版面分析，支持复杂手写体和公式
  - **PP-DocLayout**: 支持 PaddleOCR 布局模型
- **一键编译**：内置 XeLaTeX 编译流程，直接输出最终 PDF

---

## 🛠️ 环境要求

| 组件 | 要求 |
|------|------|
| **Python** | 3.11 或更高版本 |
| **LaTeX** | TeX Live 或 MiKTeX (需包含 `xelatex` 命令并添加到 PATH) |
| **PyTorch** | 2.0+ (自动配置 GPU 支持) |
| **PaddleOCR (可选)** | 需要使用 PP-DocLayout_plus-L 时安装 |

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

## 📦 安装

本项目使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理，支持 **Windows 一键配置 CUDA 环境**。

### 快速安装（推荐）
双击setup.bat

### 手动安装
```bash
# 1. 安装 uv（如果还没有）
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 克隆仓库
git clone https://github.com/jz315/AI-Powered-Exam-Digitizer.git
cd AI-Powered-Exam-Digitizer

# 3. 一键安装依赖
# Windows: 自动识别并安装 CUDA 12.4 版本的 PyTorch (无需手动配置)
# macOS/Linux: 自动安装 CPU 版本
uv sync
```

#### 验证 GPU 是否可用 (Windows)

```powershell
# 使用 .venv 中的 python 直接运行
.venv\Scripts\python.exe -c "import torch; print('CUDA Available:', torch.cuda.is_available(), torch.version.cuda)"
# 预期输出: CUDA Available: True 12.4
```

> **注意**：如果通过 `uv sync` 安装后无法识别 GPU，请检查显卡驱动是否更新到最新版本。

---

#### 🔧 高级：自定义 PyTorch 版本

默认配置会自动为 Windows 用户安装 **CUDA 12.4** 版本。如果你的显卡较旧（需要 CUDA 11.8）或者仅使用 CPU，请按以下说明修改 `pyproject.toml`。

##### 1. 切换到 CPU 版本 (Windows)

编辑 `pyproject.toml`，找到 `[tool.uv.sources]` 部分，**删除或注释掉** Windows 相关的配置：

```toml
# [tool.uv.sources]
# torch = [
#     { index = "pytorch-cu124", marker = "sys_platform == 'win32'" },
# ]
# ...
```

保存后运行同步命令：
```bash
uv sync
```

##### 2. 切换到 CUDA 11.8 版本

如果你需要 CUDA 11.8，修改 `pyproject.toml` 中的 `tool.uv.index` 和 `tool.uv.sources`：

1. 修改 index URL：
```toml
[[tool.uv.index]]
name = "pytorch-cu118"  # 改名
url = "https://download.pytorch.org/whl/cu118"  # 改 URL
explicit = true
```

2. 修改 sources 引用：
```toml
[tool.uv.sources]
torch = [
    { index = "pytorch-cu118", marker = "sys_platform == 'win32'" },
]
torchvision = [
    { index = "pytorch-cu118", marker = "sys_platform == 'win32'" },
]
```

3. 重新同步：
```bash
uv sync
```

---

## 🚀 快速开始

### 启动 GUI
- 双击run.vbs
- 或 执行```uv run python main.py```

---

## 📖 使用流程

1. **准备题目**：找到你需要排版的数学试题（pdf）
2. **提取数据**：
   - 打开本应用，上传PDF
   - 选择版面分析模型（推荐 Auto Router）
   - 等待处理，复制OCR结构
   - 如果不需要转换为PDF, 更改后缀为.md即可查看
3. **转换格式**：   
   - 复制Prompt和OCR文本
   - 一起发送给 LLM (Claude/GPT/Gemini/DeepSeek)
   - LLM 会返回结构化的 JSON 数据
4. **生成试卷**：
   - 将 JSON 代码粘贴到输入框
   - 点击 **"生成试卷"**
5. **获取结果**：
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
          "content": "已知集合 $A=\{x|x^2-1<0\}$，则...",
          "options": ["$(-1,1)$", "$(0,1)$", "$(-1,0)$", "$(1,+\infty)$"]
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

## 🧩 组卷系统（题库 + 规则）

你可以使用题库 + 规则自动组卷，并直接生成可导出的 JSON（与模板完全兼容）。

### 1) 题库格式（示例）

```json
{
  "meta": { "subject": "Math" },
  "questions": [
    {
      "id": "SC001",
      "type": "single_choice",
      "difficulty": "easy",
      "tags": ["functions"],
      "content": "若 $f(x)=x^2$，则 $f'(x)=$ __BLANK__。",
      "options": ["$x$", "$2x$", "$x^2$", "$2$"]
    }
  ]
}
```

> 题库也支持直接使用“已有试卷 JSON（sections/questions）”，系统会自动扁平化提取题目。

### 2) 组卷规则（示例）

```json
{
  "meta": { "title": "Sample Exam", "subject": "Math" },
  "seed": 42,
  "sections": [
    { "title": "选择题", "type": "single_choice", "count": 10, "difficulty": { "easy": 4, "medium": 4, "hard": 2 } },
    { "title": "填空题", "type": "fill", "count": 5, "tags": ["functions", "calculus"] },
    { "title": "解答题", "type": "problem", "count": 3 }
  ]
}
```

可选字段说明（简要）：

- `include_ids` / `exclude_ids`：指定必选或排除题目 ID
- `tags` / `exclude_tags` + `tag_mode`（`any`/`all`）：标签筛选
- `difficulty`：可用 `easy/medium/hard`，也支持数值（0~1、1~5、1~10）
- `strict`：`false` 时允许“题目不足”只报 warning
- `allow_reuse`：允许同题重复出现在多个 section

### 3) GUI 使用方式

在 **“题库与组卷”** 页可以：

- 一键从编辑器导入题库（自动扁平化）
- 筛选 + 勾选题目手动组卷
- 使用规则 JSON 自动组卷

默认题库路径：`output/question_bank/question_bank.json`  
图片会自动拷贝到：`output/question_bank/assets` 并重写引用，避免丢图。

### 4) CLI 使用方式

```bash
# 生成输出文件到 output/assembled/
uv run python -m math_digitizer.core.paper_builder --bank examples/question_bank.sample.json --spec examples/paper_spec.sample.json
```

---

## 📂 项目结构

```
.
├── main.py                     # GUI 程序入口
├── pdf_ocr_cli.py              # PDF 版面分析 CLI
├── pyproject.toml              # 项目配置与依赖
├── math_digitizer/             # 核心源码包
│   ├── core/                   # 核心逻辑
│   │   ├── generator.py        # LaTeX 生成器
│   │   └── validator.py        # JSON 校验器
│   ├── gui/                    # CustomTkinter 图形界面
│   ├── ocr/                    # OCR 与版面分析引擎
│   │   ├── extractors/         # 各种模型实现 (YOLO, DeepSeek, AutoRouter)
│   │   └── photo_process.py    # 图像处理工具
│   ├── layout_models/          # YOLO 模型文件目录
│   └── resources/              # 静态资源
│       ├── exam_template.txt   # Jinja2 LaTeX 模板
│       └── prompt.md           # LLM 提示词
├── examples/                   # 组卷系统示例数据
└── output/                     # 生成结果目录
```

---

## 🔨 开发者指南

### 从源码开发

```bash
# 克隆仓库
git clone https://github.com/jz315/AI-Powered-Exam-Digitizer.git
cd AI-Powered-Exam-Digitizer

# 创建开发环境
uv sync

# 运行测试
pytest
```

### 自定义试卷样式

修改 `math_digitizer/resources/exam_template.txt` 可调整试卷的整体样式（页眉、页脚、装订线等）。

### 图片支持

在 JSON 中通过 `image` 字段指定图片路径或尺寸，生成器会自动生成占位空间。

---



## ❓ 常见问题

### Q: 没有 GPU，能用吗？

可以。`uv sync` 在非 Windows 系统会自动安装 CPU 版本 PyTorch。Windows 用户如果想用 CPU 版本，可以修改 `pyproject.toml` 中的配置。
Auto Router 模式下，如果本地模型跑得慢，可以配置 DeepSeek API Key 使用云端模式。

### Q: xelatex 命令未找到？

确保已安装 TeX Live 或 MiKTeX，并将其添加到系统 PATH：
- Windows: 检查 `C:\texlive\2024\bin\windows` 或 MiKTeX 安装目录
- macOS: `brew install --cask mactex`
- Linux: `sudo apt install texlive-full`

### Q: DeepSeek OCR 报错？

请确保已在 `.env` 文件或环境变量中配置了 `DEEPSEEK_API_KEY`。如果是自定义部署的 DeepSeek，还需要配置 `DEEPSEEK_BASE_URL`。

---

## 📜 License

MIT
