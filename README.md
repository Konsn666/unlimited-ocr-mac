# Unlimited OCR · Mac (Apple Silicon) 适配版

> **[English](#english)** | **中文**

---

## 中文

在 **Mac Apple Silicon (M1 / M2 / M3 / M4)** 上本地跑通 [baidu/Unlimited-OCR](https://github.com/baidu/Unlimited-OCR) (6.7B VLM) — 带 grounding 的 OCR,直接输出 `<|det|><类型> [bbox] <|/det|><文字>` 格式。

**官方只支持 NVIDIA CUDA 12.9+**。这个仓库是社区维护的 Mac 适配:打 3 个 patch,其它都和上游一致。

### ✨ 功能亮点

| 功能 | 说明 |
|---|---|
| 🔍 **本地 OCR** | 6.7B VLM 模型完全本地运行，无需联网，隐私安全 |
| 🖥️ **Web UI** | 浏览器直操作：上传 → 扫描 → 编辑 → 翻译 → 导出 Word |
| 🌐 **双语翻译** | 支持中/英/日/韩/法/德等 10+ 语言互译，原文+译文紧贴对照 |
| 📄 **导出 Word** | 支持仅原文 / 仅译文 / 双语对照三种导出模式 |
| ✏️ **在线编辑** | 识别结果可直接点击修改，实时保存 |
| 🤖 **MCP 服务** | 一键接入 Claude Code / Codex / 其他 AI 工具 |
| ⚡ **实时流式** | SSE 逐行推送扫描结果，边扫边看 |

### 实测性能 (M4 Pro 48GB)

| 任务 | 耗时 |
|---|---|
| 模型加载(从 SSD 读 6.7GB) | ~3s |
| 简单图 (768×1024) | ~9s |
| 复杂文档 (1024×1024, 13 行) | ~19s |
| 多图批处理 | ~20s/图 |

### 🚀 一键安装

```bash
git clone https://github.com/Konsn666/unlimited-ocr-mac.git
cd unlimited-ocr-mac
bash scripts/install.sh          # 安装 OCR 模型 (~5-10 分钟, 下载 6.7GB)
bash web/scripts/install_web.sh  # 安装 Web UI 依赖 (~1 分钟)
```

模型默认装到 `./model_dir`,缓存走 `~/.cache/huggingface/hub/`。装外置 SSD:

```bash
HF_HUB_CACHE="/Volumes/外置盘/Model/hub" bash scripts/install.sh
```

### 一键运行

**Web UI (推荐)**:

```bash
bash web/scripts/start_web.sh
# 打开 http://localhost:8800
```

**命令行**:

```bash
# 单图
bash scripts/run.sh /path/to/your.png

# 多图批处理
bash scripts/run.sh --image_dir /path/to/images/ --output_dir ./out

# 高级参数
bash scripts/run.sh /path/to/image.png \
    --base_size 1024 --image_size 640 --max_length 8192 \
    --no_repeat_ngram_size 35 --ngram_window 128
```

### 🖥️ Web UI 使用指南

#### 基本流程

```
上传 PDF/图片 → 点击「开始扫描」→ 实时查看识别结果 → 编辑 → 翻译 → 导出 Word
```

#### 界面布局

| 区域 | 功能 |
|---|---|
| 左侧面板 | 原始文件预览（PDF 自动按页切换） |
| 右侧面板 | OCR 识别结果（可编辑、翻译） |
| 顶部工具栏 | 上传 / 扫描 / 翻译语言选择 / 导出 |
| 底部状态栏 | 模型状态 / 设备信息 |

#### 翻译功能

1. 在顶部下拉框选择目标语言（如 `→ English`）
2. 点击 🌐 翻译 按钮
3. 译文以紫色缩进样式紧跟在原文下方
4. 再次点击可取消翻译

**翻译 API 配置**（编辑 `web/.env`）:

```bash
# 支持任何 OpenAI 兼容的 API
TRANSLATE_API_BASE=https://api.openai.com/v1    # OpenAI
# TRANSLATE_API_BASE=https://api.deepseek.com/v1 # DeepSeek
# TRANSLATE_API_BASE=http://localhost:11434/v1    # 本地 Ollama

TRANSLATE_API_KEY=sk-your-api-key-here
TRANSLATE_MODEL=gpt-4o
```

> 💡 **提示**: 翻译是**可选功能**。不配置 API Key 仍可正常使用 OCR 识别和导出，只是无法翻译。

#### 导出 Word

点击 📥 导出 Word 按钮后，可选择三种模式:

| 模式 | 说明 |
|---|---|
| 仅原文 | 只输出 OCR 识别的原始文字 |
| 仅译文 | 只输出翻译后的文字（需先翻译） |
| 双语对照 | 一行原文、一行译文交替排列 |

### 作为 MCP 服务 (给 Claude Code / Codex / 其他 AI 工具调用)

```bash
bash scripts/mcp.sh    # 启动 stdio MCP server
```

注册到 Claude Code (`~/.claude.json` 或项目 `.mcp.json`):
```json
{
  "mcpServers": {
    "unlimited-ocr": {
      "command": "python3",
      "args": ["/path/to/unlimited-ocr-mac/mcp_server/server.py"]
    }
  }
}
```

注册到 OpenAI Codex CLI (`~/.codex/config.toml`):
```toml
[mcp_servers.unlimited-ocr]
command = "python3"
args = ["/abs/path/to/unlimited-ocr-mac/mcp_server/server.py"]
```

启动后,你的 AI 工具就能调用:
- `ocr_image(path)` — 单张图 OCR,返回 JSON
- `ocr_directory(path)` — 批处理目录
- `model_status()` — 看模型加载状态

### 🏗️ 项目结构

```
unlimited-ocr-mac/
├── patches/              # Mac 适配补丁 (3 个核心 patch)
│   ├── modeling_unlimitedocr.py   # .cuda() → .to('mps') + 禁用 autocast
│   ├── modeling_deepseekv2.py     # DeepSeek V2 模型适配
│   └── ...
├── scripts/              # CLI 安装/运行脚本
│   ├── install.sh               # 一键安装 OCR 模型
│   ├── run.sh                   # 一键运行 OCR
│   └── mcp.sh                   # 启动 MCP 服务
├── mcp_server/           # MCP Server (给 AI 工具调用)
│   └── server.py
├── web/                  # 🌐 Web UI
│   ├── server.py                # FastAPI 主服务 (SSE 实时流)
│   ├── ocr_engine.py            # OCR 引擎封装 (懒加载)
│   ├── ocr_parser.py            # OCR 输出解析 → 结构化 + HTML
│   ├── translator.py            # 翻译引擎 (OpenAI 兼容 API)
│   ├── docx_exporter.py         # Word 文档导出
│   ├── pdf_converter.py         # PDF → PNG 转换
│   ├── config.py                # 配置管理
│   ├── public/                  # 前端静态文件
│   │   ├── index.html
│   │   ├── style.css
│   │   └── app.js
│   ├── scripts/
│   │   ├── install_web.sh       # Web UI 一键安装
│   │   └── start_web.sh         # Web UI 一键启动
│   ├── .env.example             # 翻译 API 配置模板
│   └── requirements.txt         # Python 依赖
├── run_mac.py            # Mac 适配核心 (应用 patch + 推理)
└── README.md
```

### 三个 Mac 适配 patch (核心)

模型官方代码假设 NVIDIA GPU,在 Mac 上要改三处:

1. **`.cuda()` 硬编码 → `.to('mps')`** (`modeling_unlimitedocr.py` 里 13+ 处)
   - `run_mac.py::apply_patches()` 自动改写

2. **`torch.autocast("cuda", ...)` → 禁用** ⭐ **最关键**
   - PyTorch MPS backend 对 `torch.autocast(device_type="mps", dtype=bfloat16)` 有 bug,会让 MLA+MoE 算子精度漂移
   - 直接去掉 autocast,让模型用自然 bf16 推理
   - 表现:有 autocast → 5-10 token 后 logits 塌缩成 `168168168...` 死循环;去掉 → 完美工作

3. **`SlidingWindowNoRepeatNgramProcessor` 继承 `LogitsProcessor`**
   - 原版是个普通类,transformers 4.57 不会调用它
   - 加 `from transformers import LogitsProcessor` + `(LogitsProcessor)` 让 ngram 真正生效

这些 patch 都在 `patches/` 目录里,`install.sh` 自动覆盖到下载的 HF 模型。

### 🔧 系统要求

#### OCR 模型 (核心)

| 项目 | 要求 |
|---|---|
| 操作系统 | macOS 14+ (Sonoma) on Apple Silicon (M1/M2/M3/M4) |
| Python | 3.12 或 3.13 (推荐 3.13) |
| 统一内存 | **≥ 24GB** (推荐 32GB+; 48GB 实测无压力) |
| 磁盘 | 约 **8GB** 给模型权重 |

#### Web UI (额外)

| 项目 | 要求 |
|---|---|
| Python 依赖 | fastapi, sse-starlette, python-multipart, uvicorn, python-docx |
| 翻译功能 (可选) | 任意 OpenAI 兼容 API (OpenAI / DeepSeek / 星火 / Ollama) |
| 浏览器 | Chrome / Safari / Firefox 现代浏览器 |

#### 安装 Python 3.13 (如果尚未安装)

```bash
# macOS (Homebrew)
brew install python@3.13

# 验证
python3.13 --version
```

### 输出格式

每行一个 detection:
```
<|det|><type> [x1, y1, x2, y2]<|/det|><text>
```

- `<type>`: `title` / `text` / `header` / `table` / `[Non-Text]` 等
- `[x1, y1, x2, y2]`: 4-corner bounding box(像素)
- `<text>`: 识别出的文本

示例输出:
```markdown
<|det|>title [35, 38, 685, 88]<|/det|>Unlimited OCR 真实文档测试
<|det|>text [33, 114, 761, 150]<|/det|>百度于2026年6月22日发布 Unlimited-OCR 模型。
<|det|>text [33, 150, 576, 179]<|/det|>模型基于 Deepseek V2 架构,采用 MoE 路由机制。
```

### ❓ 常见问题

<details>
<summary><b>Web UI 启动报错 "ModuleNotFoundError"</b></summary>

```bash
# 确保激活了虚拟环境
source .venv-ocr/bin/activate
# 重新安装 Web 依赖
bash web/scripts/install_web.sh
```
</details>

<details>
<summary><b>翻译按钮灰色 / 无法翻译</b></summary>

翻译需要配置 API Key。编辑 `web/.env`:

```bash
TRANSLATE_API_BASE=https://api.openai.com/v1
TRANSLATE_API_KEY=sk-your-key
TRANSLATE_MODEL=gpt-4o
```

修改后重启服务器生效。
</details>

<details>
<summary><b>模型加载很慢</b></summary>

模型约 6.7GB，首次加载从磁盘读取。建议:
- 将模型放在内置 SSD（而非外置硬盘）
- 确保内存充足（≥24GB），避免频繁换页
</details>

<details>
<summary><b>OCR 识别结果有误，可以修改吗？</b></summary>

可以！Web UI 中所有识别文字都可以直接点击编辑，修改后自动保存。编辑后的结果也会反映在导出的 Word 文档中。
</details>

<details>
<summary><b>支持哪些文件格式？</b></summary>

- **上传**: PDF, PNG, JPG, JPEG, WebP, BMP
- **导出**: Word (.docx)，支持仅原文 / 仅译文 / 双语对照
</details>

### 已知限制

- **不官方支持**:社区 patch,不是 Baidu 官方 Mac 路径
- **流式输出禁用**:PyTorch MPS 有 "Placeholder storage" bug(2.12+);用 `eval_mode=True` 一次性返回代替
- **fp16 路径有 dtype mismatch**:推荐 bf16
- **速度** ~20s/图,比 NVIDIA GPU 慢 5-10x,比 PaddleOCR 等传统 OCR 准确度高

### 致谢

- [baidu/Unlimited-OCR](https://github.com/baidu/Unlimited-OCR) - 原始仓库 (MIT)
- [huggingface.co/baidu/Unlimited-OCR](https://huggingface.co/baidu/Unlimited-OCR) - 模型权重
- PyTorch MPS backend 团队

---

<a id="english"></a>

## English

Run [baidu/Unlimited-OCR](https://github.com/baidu/Unlimited-OCR) (6.7B VLM) **locally on Mac Apple Silicon (M1/M2/M3/M4)** — with a beautiful Web UI, real-time translation, and Word export.

**Officially NVIDIA CUDA 12.9+ only.** This repo is a community-maintained Mac adaptation with 3 patches; everything else is identical to upstream.

### ✨ Features

| Feature | Description |
|---|---|
| 🔍 **Local OCR** | 6.7B VLM runs entirely locally, no internet, privacy-safe |
| 🖥️ **Web UI** | Browser-based: Upload → Scan → Edit → Translate → Export Word |
| 🌐 **Bilingual Translation** | 10+ languages, original + translation side-by-side |
| 📄 **Word Export** | Original-only / Translated-only / Bilingual modes |
| ✏️ **Inline Edit** | Click any text to edit, auto-save |
| 🤖 **MCP Service** | One-click integration with Claude Code / Codex / AI tools |
| ⚡ **Real-time SSE** | Line-by-line streaming as OCR progresses |

### Benchmarks (M4 Pro 48GB)

| Task | Time |
|---|---|
| Model load (6.7GB from SSD) | ~3s |
| Simple image (768×1024) | ~9s |
| Complex doc (1024×1024, 13 lines) | ~19s |
| Batch processing | ~20s/image |

### 🚀 One-click install

```bash
git clone https://github.com/Konsn666/unlimited-ocr-mac.git
cd unlimited-ocr-mac
bash scripts/install.sh          # Install OCR model (~5-10 min, downloads 6.7GB)
bash web/scripts/install_web.sh  # Install Web UI deps (~1 min)
```

Model installs to `./model_dir`; cache goes to `~/.cache/huggingface/hub/`. For an external SSD:

```bash
HF_HUB_CACHE="/Volumes/external/Model/hub" bash scripts/install.sh
```

### One-click run

**Web UI (recommended)**:

```bash
bash web/scripts/start_web.sh
# Open http://localhost:8800
```

**CLI**:

```bash
# Single image
bash scripts/run.sh /path/to/your.png

# Batch
bash scripts/run.sh --image_dir /path/to/images/ --output_dir ./out

# Advanced
bash scripts/run.sh /path/to/image.png \
    --base_size 1024 --image_size 640 --max_length 8192 \
    --no_repeat_ngram_size 35 --ngram_window 128
```

### 🖥️ Web UI Guide

#### Workflow

```
Upload PDF/Image → Click "Scan" → View real-time results → Edit → Translate → Export Word
```

#### Translation

1. Select target language from the dropdown (e.g., `→ English`)
2. Click the 🌐 Translate button
3. Translations appear in purple, tightly paired below originals
4. Click again to toggle off

**Translation API config** (edit `web/.env`):

```bash
# Any OpenAI-compatible API works
TRANSLATE_API_BASE=https://api.openai.com/v1
TRANSLATE_API_KEY=sk-your-api-key-here
TRANSLATE_MODEL=gpt-4o
```

> 💡 **Note**: Translation is **optional**. Without an API key, OCR and export still work fine.

#### Word Export

Three export modes:

| Mode | Description |
|---|---|
| Original only | OCR text only |
| Translated only | Translated text only (requires translation first) |
| Bilingual | Original + translation alternating |

### MCP service (for Claude Code / Codex / other AI tools)

```bash
bash scripts/mcp.sh    # start stdio MCP server
```

Register with Claude Code (`~/.claude.json` or project `.mcp.json`):
```json
{
  "mcpServers": {
    "unlimited-ocr": {
      "command": "python3",
      "args": ["/path/to/unlimited-ocr-mac/mcp_server/server.py"]
    }
  }
}
```

Register with OpenAI Codex CLI (`~/.codex/config.toml`):
```toml
[mcp_servers.unlimited-ocr]
command = "python3"
args = ["/abs/path/to/unlimited-ocr-mac/mcp_server/server.py"]
```

Once registered, your AI client can call:
- `ocr_image(path)` — single image OCR, returns JSON
- `ocr_directory(path)` — batch directory
- `model_status()` — check model load state

### 🏗️ Project Structure

```
unlimited-ocr-mac/
├── patches/              # Mac adaptation patches (3 core patches)
│   ├── modeling_unlimitedocr.py   # .cuda() → .to('mps') + disable autocast
│   ├── modeling_deepseekv2.py     # DeepSeek V2 model adaptation
│   └── ...
├── scripts/              # CLI install/run scripts
│   ├── install.sh               # One-click install OCR model
│   ├── run.sh                   # One-click run OCR
│   └── mcp.sh                   # Start MCP service
├── mcp_server/           # MCP Server (for AI tool integration)
│   └── server.py
├── web/                  # 🌐 Web UI
│   ├── server.py                # FastAPI server (SSE streaming)
│   ├── ocr_engine.py            # OCR engine wrapper (lazy load)
│   ├── ocr_parser.py            # OCR output parser → structured + HTML
│   ├── translator.py            # Translation engine (OpenAI-compatible)
│   ├── docx_exporter.py         # Word document export
│   ├── pdf_converter.py         # PDF → PNG conversion
│   ├── config.py                # Configuration
│   ├── public/                  # Frontend static files
│   │   ├── index.html
│   │   ├── style.css
│   │   └── app.js
│   ├── scripts/
│   │   ├── install_web.sh       # Web UI one-click install
│   │   └── start_web.sh         # Web UI one-click start
│   ├── .env.example             # Translation API config template
│   └── requirements.txt         # Python dependencies
├── run_mac.py            # Core Mac adaptation (apply patches + inference)
└── README.md
```

### Three Mac adaptation patches (key)

Upstream code assumes NVIDIA GPUs; on Mac you need to patch three things:

1. **`.cuda()` hardcoded → `.to('mps')`** (13+ places in `modeling_unlimitedocr.py`)
   - `run_mac.py::apply_patches()` rewrites these automatically

2. **Disable `torch.autocast("cuda", ...)`** ⭐ **most critical**
   - PyTorch's MPS backend has a bug with `torch.autocast(device_type="mps", dtype=bfloat16)` — it causes precision drift in MLA+MoE ops
   - Remove autocast; let the model use its natural bf16 dtype
   - Symptom with autocast: 5-10 tokens in, logits collapse into `168168168...` infinite loop. Without: works perfectly.

3. **`SlidingWindowNoRepeatNgramProcessor` inherit from `LogitsProcessor`**
   - Upstream is a plain class, transformers 4.57 won't call it
   - Add `from transformers import LogitsProcessor` + `(LogitsProcessor)` to make ngram actually apply

Patches live in `patches/`; `install.sh` overlays them on the downloaded HF model automatically.

### 🔧 System Requirements

#### OCR Model (core)

| Item | Requirement |
|---|---|
| OS | macOS 14+ (Sonoma) on Apple Silicon (M1/M2/M3/M4) |
| Python | 3.12 or 3.13 (3.13 recommended) |
| Unified Memory | **≥ 24GB** (32GB+ recommended; 48GB tested) |
| Disk | ~**8GB** for model weights |

#### Web UI (additional)

| Item | Requirement |
|---|---|
| Python deps | fastapi, sse-starlette, python-multipart, uvicorn, python-docx |
| Translation (optional) | Any OpenAI-compatible API (OpenAI / DeepSeek / Ollama) |
| Browser | Chrome / Safari / Firefox (modern) |

#### Installing Python 3.13 (if not installed)

```bash
# macOS (Homebrew)
brew install python@3.13

# Verify
python3.13 --version
```

### Output format

One line per detection:
```
<|det|><type> [x1, y1, x2, y2]<|/det|><text>
```

- `<type>`: `title` / `text` / `header` / `table` / `[Non-Text]` etc.
- `[x1, y1, x2, y2]`: 4-corner bounding box (pixels)
- `<text>`: recognized text

Example:
```markdown
<|det|>title [35, 38, 685, 88]<|/det|>Unlimited OCR Real Document Test
<|det|>text [33, 114, 761, 150]<|/det|>Baidu released Unlimited-OCR model on 2026-06-22.
<|det|>text [33, 150, 576, 179]<|/det|>Model is based on Deepseek V2 architecture with MoE routing.
```

### ❓ FAQ

<details>
<summary><b>Web UI shows "ModuleNotFoundError"</b></summary>

```bash
# Make sure venv is activated
source .venv-ocr/bin/activate
# Reinstall web deps
bash web/scripts/install_web.sh
```
</details>

<details>
<summary><b>Translate button is grayed out</b></summary>

Translation requires an API key. Edit `web/.env`:

```bash
TRANSLATE_API_BASE=https://api.openai.com/v1
TRANSLATE_API_KEY=sk-your-key
TRANSLATE_MODEL=gpt-4o
```

Restart the server after editing.
</details>

<details>
<summary><b>Model loading is slow</b></summary>

The model is ~6.7GB. Tips:
- Place model on internal SSD (not external HDD)
- Ensure sufficient RAM (≥24GB) to avoid swapping
</details>

<details>
<summary><b>Can I edit OCR results?</b></summary>

Yes! All recognized text is directly editable in the Web UI. Click any text to edit, changes are auto-saved and reflected in exported Word documents.
</details>

<details>
<summary><b>What file formats are supported?</b></summary>

- **Upload**: PDF, PNG, JPG, JPEG, WebP, BMP
- **Export**: Word (.docx) — Original-only / Translated-only / Bilingual
</details>

### Known limitations

- **Not officially supported** — community patches, not Baidu's official Mac path
- **Streaming output disabled** — PyTorch MPS has a "Placeholder storage" bug; we use `eval_mode=True` (returns full string at once) instead
- **fp16 path has dtype mismatch** — use bf16
- **Speed** ~20s/image, ~5-10× slower than NVIDIA GPU but more accurate than traditional OCR (PaddleOCR, etc.)

### Credits

- [baidu/Unlimited-OCR](https://github.com/baidu/Unlimited-OCR) — original repo (MIT)
- [huggingface.co/baidu/Unlimited-OCR](https://huggingface.co/baidu/Unlimited-OCR) — model weights
- PyTorch MPS backend team
