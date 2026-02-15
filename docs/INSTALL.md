# 安装指南

## 环境要求

| 组件 | 要求 |
|------|------|
| **Python** | 3.11 或更高版本 |
| **LaTeX** | TeX Live 或 MiKTeX (需包含 `xelatex` 命令并添加到 PATH) |
| **PyTorch** | 2.0+ (自动配置 GPU 支持) |
| **Node.js (Web 版)** | 18+ (用于前端开发服务器) |

---

## XeLaTeX 安装教程

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

## Python 依赖安装

本项目使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理，支持 **Windows 一键配置 CUDA 环境**。

### 快速安装（推荐）

双击 `setup.bat`

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

## 高级：自定义 PyTorch 版本

默认配置会自动为 Windows 用户安装 **CUDA 12.4** 版本。如果你的显卡较旧（需要 CUDA 11.8）或者仅使用 CPU，请按以下说明修改 `pyproject.toml`。

### 1. 切换到 CPU 版本 (Windows)

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

### 2. 切换到 CUDA 11.8 版本

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
