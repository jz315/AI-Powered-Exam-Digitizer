
# 📝 AI-Powered Exam Digitizer (AI 试卷数字化系统)

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg) ![LaTeX](https://img.shields.io/badge/LaTeX-XeLaTeX-red.svg) ![Status](https://img.shields.io/badge/Status-Active-success)

这是一个基于 **LLM (大语言模型)** 与 **LaTeX** 的自动化工具链。它能将模糊的数学试卷图片，通过 AI 识别提取为结构化 JSON 数据，再利用 Python + Jinja2 引擎渲染成排版完美的 PDF 试卷。

告别手动录入公式，告别排版烦恼，实现“**拍图 -> 识别 -> 高清重制**”的全自动流程。

## ✨ 核心功能

- **🤖 智能识别**：利用专门设计的 Prompt 指令，精准提取试题结构（单选、多选、填空、解答）。
- **➗ 公式重构**：自动将数学公式转换为标准的 LaTeX 格式。
- **🌲 递归结构**：支持多层级嵌套问题（如：大题 -> 小问 (1) -> 子问 (i)）。
- **📄 完美排版**：基于国内主流的 `exam-zh` 试卷宏包，自动生成符合印刷标准的 PDF。
- **🔌 模板引擎**：使用 Jinja2 动态渲染，数据与样式分离，易于扩展。

## 🛠️ 环境依赖

在使用本工具前，请确保您的环境已安装以下软件：

1.  **Python 3.12+**
    *   安装 uv
    *   执行命令：`uv sync`
2.  **TeX Live 或 MiKTeX**
    *   必须包含 `xelatex` 编译器。
    *   必须安装 [`exam-zh`](https://gitee.com/xkwxdyy/exam-zh) 宏包。

## 🚀 快速开始

### 第一步：获取 JSON 数据
1.  准备一张数学试卷图片。
2.  复制项目中的 `prompt.md` 内容。
3.  打开 Qwen3VL 或 Gemini 3 Pro（这两个准确率高）。
4.  输入 Prompt 并上传图片。
5.  将 AI 返回的 JSON 内容保存为项目根目录下的 `exam_data.json`。

### 第二步：生成试卷
在终端运行以下命令：

```bash
uv run python main.py
```

将启动 GUI 工具，流程如下：
1.  复制项目里的 `src/prompt.md` 到 LLM，并上传试卷图片。
2.  将 LLM 返回的 JSON 粘贴到右侧编辑器。
3.  点击“生成 PDF”，会在 `output/<标题>/` 下生成同名 `.tex` 和 `.pdf`。

## 📂 文件结构

```text
.
├── main.py              # 启动入口（GUI）
├── src/
│   ├── gui.py           # GUI 主程序
│   ├── generator.py     # 数据清洗、模板渲染、LaTeX 编译
│   ├── validator.py     # JSON/LaTeX 预校验与错误提取
│   ├── exam_template.txt# Jinja2 + LaTeX 模板
│   └── prompt.md        # 给 LLM 的系统提示词 (System Prompt)
└── output/
    └── <标题>/
        ├── <标题>.tex   # 生成的 LaTeX 源码
        └── <标题>.pdf   # 最终的高清试卷
```

## 🧩 自定义开发

- **修改模板**：编辑 `src/exam_template.txt`。注意我们使用了 `(( variable ))` 作为变量分隔符，以免与 LaTeX 的 `{}` 冲突。
- **扩展题型**：在 `src/generator.py` 的 `process_data` 中添加新的清洗逻辑。

## ⚠️ 常见问题


**Q: 数学公式渲染报错？**
A: 检查 JSON 中的公式是否正确转义了反斜杠（例如 `\\frac` 而不是 `\frac`）。

## 📄 License

MIT License
