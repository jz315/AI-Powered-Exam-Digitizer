# 🤖 AI 助手项目部署指南 (AI Agent Deployment Protocol)

**致 AI 助手 (Cursor, Windsurf, Copilot, Cline 等)：**
**请将本文档视为您的「系统提示词」或「标准执行程序 (SOP)」。当用户要求「帮我安装」、「配置项目」或「初始化环境」时，请严格按照以下 5 个阶段顺序执行。**

---

## 🔁 Phase 1: 环境检测与工具准备

1.  **检测 `uv`**：
    - 执行命令：`uv --version`
    - ❌ **失败**：根据用户操作系统运行安装命令（见下方），并告知用户正在安装 uv。
      - Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
      - Mac/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
    - ✅ **成功**：继续下一步。

2.  **检测 Python**：
    - 确保系统 Python 版本 >= 3.11。如果不满足，提示用户升级。

---

## 🔁 Phase 2: PyTorch 版本策略 (自动硬件检测)

**⚠️ 严禁直接运行 `uv sync`，必须先检测硬件环境。**

### 1. 检测操作系统
- 如果是 **Linux / macOS**：直接跳到执行 `uv sync`（系统会自动处理）。
- 如果是 **Windows**：**请按以下步骤执行硬件检测**。

### 2. Windows 硬件检测 (AI 自动执行)

请在终端尝试执行以下命令来检测显卡：
`nvidia-smi`

#### 🅰️ 分支 A：检测到 NVIDIA 显卡 (命令成功执行)
> 现象：终端输出了显卡信息表格。

**操作**：虽然检测到独显，但考虑到 CUDA 版本体积巨大 (~4GB)，**必须询问用户意图**。
**请询问**：
> "🤖 自动检测到您的设备拥有 NVIDIA 显卡 (`[插入显卡型号]`)。
>
> 默认将安装 **GPU 加速版** PyTorch (需下载约 4GB 依赖)。
> **是否继续安装 GPU 版？** (如果您的网速较慢或只需轻度使用，可以选择 N 使用 CPU 版)
>
> **[Y] 是，安装 GPU 版 (推荐)**
> **[N] 否，改为安装 CPU 版 (轻量)**"

- **用户选 Y**：无需修改，直接运行 `uv sync`。
- **用户选 N**：请执行 **[修改为 CPU 模式]** 的操作（见下文）。

#### 🅱️ 分支 B：未检测到 NVIDIA 显卡 (AMD/Intel/无独显)
> 现象：命令报错 `command not found` 或提示无设备。

**操作**：PyTorch 在 Windows 上仅支持 NVIDIA CUDA 加速。AMD 或 Intel 显卡只能使用 CPU 模式。
**请告知用户**：
> "🤖 未检测到 NVIDIA 显卡 (或是 AMD/Intel 显卡)。
> 将自动为您配置 **CPU 版本** (轻量化安装)。"

**执行**：请立即执行 **[修改为 CPU 模式]** 的操作。

---

### 🔧 操作：修改为 CPU 模式 (Windows)
如果不使用 GPU，请在运行 `uv sync` 前修改 `pyproject.toml`：

1. 读取 `pyproject.toml`。
2. 找到 `[tool.uv.sources]` 部分。
3. **注释掉或删除** 所有带 `marker = "sys_platform == 'win32'"` 的行（通常是 `torch` 和 `torchvision`）。
4. 保存文件。
5. 运行 `uv sync`。

---

## 🔁 Phase 3: OCR 服务配置 (交互节点)

**在依赖安装等待期间，或者安装完成后，请向用户询问 API 配置。**

**请向用户发送询问：**
> "本项目推荐使用 **DeepSeek OCR** (云端) 以获得最佳的公式识别体验，或者配置 **Gemini** 进行智能路由。
>
> 请问您是否有 DeepSeek 或 Gemini 的 API Key？
> (如果没有，您可以跳过，后续将使用本地离线模型，速度快但手写公式识别能力较弱)"

**根据回答行动：**

- **用户提供 Key**：
  1. 检查根目录是否有 `.env`。如果没有则创建。
  2. 将 Key 写入文件：
     ```env
     DEEPSEEK_API_KEY=sk-xxxxxx
     # 如果用户提及 siliconflow 或其他中转，请询问并添加:
     # DEEPSEEK_BASE_URL=...
     
     GEMINI_API_KEY=AIza-xxxxxx
     ```
  3. 告知用户已保存。

- **用户跳过**：
  - 生成一个包含注释的 `.env` 模板，方便用户日后填入。

---

## 🔁 Phase 4: 外部依赖核查 (XeLaTeX)

1.  **执行检测**：`xelatex --version`
2.  **结果处理**：
    - ❌ **未找到**：**必须发出警告**。
      > "⚠️ **警告：未检测到 LaTeX 环境！**
      > 程序将无法把生成的 LaTeX 代码编译为最终 PDF 文件。
      > 请务必安装 **TeX Live** (推荐) 或 **MiKTeX**。安装后请重启终端/编辑器。
      > (您可以参考 README.md 中的详细安装教程)"
    - ✅ **成功**：告知用户 LaTeX 环境就绪。

---

## 🔁 Phase 5: 最终验证与启动

1.  **运行自检脚本**：
    - Windows: `.venv\Scripts\python.exe -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')"`
    - Mac/Linux: `.venv/bin/python -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')"`

2.  **汇报结果**：
    向用户展示最终状态报告：
    > "✅ **项目配置完成！**
    > - 依赖安装：已完成
    > - PyTorch 模式：`[显示检测结果]`
    > - OCR 配置：`[已配置/未配置]`
    > - LaTeX 环境：`[已就绪/未检测到]`
    >
    > **🚀 启动方式：**
    > 运行 `python main.py` 即可启动图形界面。"

---

