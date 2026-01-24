# Math Digitizer - 智能数学试卷排版工具

将 LLM 生成的结构化 JSON 数据自动转换为排版精美的 LaTeX 试卷 PDF。

## ✨ 主要功能

- **OCR 版面分析**：上传 PDF，自动识别题目结构（支持 YOLO 本地模型 / DeepSeek 云端）
- **LLM 转换**：配合 Claude/GPT/Gemini/DeepSeek 将 OCR 结果转为结构化 JSON
- **自动排版**：基于 `exam-zh` 模板，一键生成专业试卷 PDF
- **题库组卷**：支持题库管理和规则自动组卷

## 🚀 快速开始

### 1. 环境要求

- Python 3.11+
- XeLaTeX（[TeX Live](https://tug.org/texlive/) 或 [MiKTeX](https://miktex.org/)）

### 2. 安装

```bash
# Windows 快速安装
双击 setup.bat

# 或手动安装
git clone https://github.com/jz315/AI-Powered-Exam-Digitizer.git
cd AI-Powered-Exam-Digitizer
uv sync
```

### 3. 启动

```bash
# Windows
双击 run.vbs

# 或命令行
uv run python main.py
```

## 📖 使用流程

1. **上传 PDF** → 选择版面分析模型 → 获取 OCR 结果
2. **发送给 LLM** → 复制 Prompt + OCR 文本 → LLM 返回 JSON
3. **生成试卷** → 粘贴 JSON → 点击生成 → 输出 PDF

## 📚 详细文档

- [安装指南](docs/INSTALL.md) - XeLaTeX 安装、PyTorch GPU 配置、自定义 CUDA 版本
- [使用指南](docs/USAGE.md) - 详细使用流程、JSON 格式、题库组卷系统
- [开发者指南](docs/DEVELOPMENT.md) - 项目结构、源码开发、自定义模板

## ❓ 常见问题

| 问题 | 解决方案 |
|------|----------|
| `xelatex` 未找到 | 安装 TeX Live 或 MiKTeX，确保添加到 PATH |
| 没有 GPU | 可用，本地模型会慢一些；或配置 DeepSeek API 用云端 |
| DeepSeek 报错 | 在设置中配置 `DEEPSEEK_API_KEY` |

## 📜 License

MIT
