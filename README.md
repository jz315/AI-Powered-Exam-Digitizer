# Math Digitizer - 智能数学试卷排版工具

这是一个基于 Python 和 LaTeX 的智能试卷生成工具。它能够将 LLM（大语言模型）生成的结构化 JSON 数据自动转换为排版精美的 LaTeX 试卷 PDF。

## ✨ 主要功能

- **智能化流程**：配合 LLM (如 Claude, ChatGPT) 将题目文本/图片转换为结构化数据
- **自动化排版**：基于 `exam-zh` 试卷模板，自动生成专业的数学试卷布局
- **现代 GUI**：使用 CustomTkinter 构建的现代化图形界面，支持深色/浅色模式
- **智能处理**：
  - 自动处理填空题下划线 (`__BLANK__` -> `\fillin`)
  - 自动清洗选择题选项前缀 (A., B. 等)
  - 灵活的图片占位符支持
- **一键编译**：内置 XeLaTeX 编译流程，直接输出最终 PDF

## 🛠️ 环境要求

- **Python**: 3.12 或更高版本
- **LaTeX 环境**: 安装 TeX Live 或 MiKTeX (必须包含 `xelatex` 命令并添加到 PATH)
- **包管理器**: [uv](https://github.com/astral-sh/uv) (推荐) 或 pip

## 🚀 快速开始

### 1. 安装依赖

本项目使用 `uv` 进行依赖管理：

```bash
# 同步依赖环境
uv sync
```

### 2. 运行应用

```bash
# 启动图形界面
uv run python main.py
```

或者在 Windows 上直接运行 `run.vbs` (无控制台窗口模式)。

## 📖 使用流程

1. **准备题目**：找到你需要排版的数学试题（文本或截图）。
2. **提取数据**：
   - 打开本应用。
   - 复制提示词。
   - 发送给 LLM (Claude/GPT)，并附上你的题目。
   - LLM 会返回一段标准的 JSON 代码。
3. **生成试卷**：
   - 将 JSON 代码粘贴到输入框。
   - 点击 **"生成试卷"**。
4. **获取结果**：
   - 程序会自动校验数据、生成 `.tex` 文件并调用 `xelatex` 编译。
   - 输出文件位于 `output/` 目录下。

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
          "options": ["$(-1,1)$", "$(0,1)$", "$(-1,0)$", "$(1,+\\infty)$"],
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

## 📂 项目结构

```text
.
├── main.py              # 程序入口
├── src/
│   ├── gui.py           # 图形界面实现
│   ├── generator.py     # LaTeX 生成与编译核心逻辑
│   ├── validator.py     # JSON 数据校验
│   ├── exam_template.txt # Jinja2 LaTeX 模板
│   └── prompt.md        # LLM 提示词
├── output/              # 生成结果目录
└── pyproject.toml       # 项目配置与依赖
```

## 📝 开发说明

- 修改 `src/exam_template.txt` 可调整试卷的整体样式（页眉、页脚、装订线等）。
- 图片支持：在 JSON 中通过 `image` 字段指定图片路径或尺寸，生成器会自动生成占位空间。

## License

MIT
