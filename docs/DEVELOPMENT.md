# 开发者指南

## 项目结构

```
.
├── main.py                     # 桌面版 GUI 入口 (CustomTkinter)
├── server.py                   # Web 版后端入口 (FastAPI)
├── start_app.bat               # Web 版一键启动脚本
├── run.vbs                     # 桌面版启动脚本
├── pyproject.toml              # 项目配置与依赖
├── frontend/                   # Web 前端 (React + Vite + TailwindCSS)
│   ├── src/
│   │   ├── pages/              # 页面组件 (OCR, Editor, Settings 等)
│   │   ├── components/         # UI 组件
│   │   ├── hooks/              # React Hooks
│   │   └── types/              # TypeScript 类型定义
│   └── package.json
├── math_digitizer/             # 核心源码包
│   ├── api/                    # FastAPI 路由
│   │   └── routers/            # OCR, 题库, 设置等 API
│   ├── core/                   # 核心逻辑
│   │   ├── generator.py        # LaTeX 生成器
│   │   └── validator.py        # JSON 校验器
│   ├── gui/                    # 桌面版 GUI (CustomTkinter)
│   ├── ocr/                    # OCR 与版面分析引擎
│   │   ├── extractors/         # 模型实现 (YOLO, DeepSeek, AutoRouter)
│   │   └── photo_process.py    # 图像处理工具
│   ├── config/                 # 配置管理
│   ├── layout_models/          # YOLO 模型文件
│   └── resources/              # 静态资源 (LaTeX 模板, Prompt)
├── examples/                   # 组卷系统示例数据
└── output/                     # 生成结果目录
```

---

## 从源码开发

```bash
# 克隆仓库
git clone https://github.com/jz315/AI-Powered-Exam-Digitizer.git
cd AI-Powered-Exam-Digitizer

# 安装后端依赖
uv sync

# 安装前端依赖（如需开发 Web 版）
cd frontend && npm install && cd ..

# 运行测试
pytest
```

---

## 自定义试卷样式

修改 `math_digitizer/resources/exam_template.txt` 可调整试卷的整体样式（页眉、页脚、装订线等）。

---

## 图片支持

在 JSON 中通过 `image` 字段指定图片路径或尺寸，生成器会自动生成占位空间。
