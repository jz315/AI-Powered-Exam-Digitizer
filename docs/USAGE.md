# 使用指南

## 启动应用

### 桌面版（推荐）

```bash
# Windows
双击 run.vbs

# 或命令行
uv run python main.py
```

### Web 版（开发中）

> ⚠️ Web 版功能尚未完善，建议使用桌面版。

```bash
# 首次运行需要安装前端依赖
cd frontend && npm install && cd ..

# 一键启动（Windows）
双击 start_app.bat
```

启动后会自动打开浏览器访问 `http://localhost:5173`

---

## 使用流程

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

## JSON 数据格式示例

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

## 组卷系统（题库 + 规则）

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

> 题库也支持直接使用"已有试卷 JSON（sections/questions）"，系统会自动扁平化提取题目。

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
- `strict`：`false` 时允许"题目不足"只报 warning
- `allow_reuse`：允许同题重复出现在多个 section

### 3) 使用方式

在 **"题库与组卷"** 页可以：

- 一键从编辑器导入题库（自动扁平化）
- 筛选 + 勾选题目手动组卷
- 使用规则 JSON 自动组卷

默认题库路径：`output/question_bank/question_bank.json`  
图片会自动拷贝到：`output/question_bank/assets` 并重写引用，避免丢图。
