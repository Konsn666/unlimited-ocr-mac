#!/usr/bin/env bash
# 一键安装 Unlimited OCR Web UI / One-click install for Unlimited OCR Web UI
#
# Usage:
#   bash web/scripts/install_web.sh
#
# Prerequisites:
#   - Unlimited OCR Mac model already installed (run scripts/install.sh first)
#   - Python 3.12+
#   - macOS with Apple Silicon (M1/M2/M3/M4) recommended
#
# This script will:
#   1. Check prerequisites (OCR model, Python)
#   2. Install web UI Python dependencies into the existing .venv-ocr
#   3. Create .env from .env.example if not exists
#   4. Print usage instructions

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$REPO_DIR/web"
VENV_DIR="${VENV_DIR:-$REPO_DIR/.venv-ocr}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERR]${NC} $*" >&2; }
step()  { echo -e "${CYAN}[STEP]${NC} $*"; }

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   Unlimited OCR · Web UI Installer                       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── 1. Check Python ──────────────────────────────────────
step "Checking Python ..."
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    err "Python 3 not found. Install via: brew install python@3.13"
    exit 1
fi
PY_VERSION=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$($PYTHON_BIN -c "import sys; print(sys.version_info.major)")
PY_MINOR=$($PYTHON_BIN -c "import sys; print(sys.version_info.minor)")

if [[ "$PY_MAJOR" -lt 3 ]] || [[ "$PY_MINOR" -lt 12 ]]; then
    err "Python 3.12+ required, found $PY_VERSION"
    exit 1
fi
info "Python $PY_VERSION ✓"

# ── 2. Check OCR model ──────────────────────────────────
step "Checking OCR model installation ..."
MODEL_DIR="$REPO_DIR/model_dir"
if [[ ! -d "$MODEL_DIR" ]] || [[ ! -f "$MODEL_DIR/config.json" ]]; then
    err "OCR model not found at $MODEL_DIR"
    err "Please run the base installation first:"
    err "  cd $REPO_DIR && bash scripts/install.sh"
    exit 1
fi
info "OCR model found at $MODEL_DIR ✓"

# ── 3. Setup venv ───────────────────────────────────────
step "Setting up Python virtual environment ..."
if [[ ! -d "$VENV_DIR" ]]; then
    info "Creating venv at $VENV_DIR ..."
    $PYTHON_BIN -m venv "$VENV_DIR"
else
    info "Reusing existing venv: $VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# ── 4. Install web dependencies ─────────────────────────
step "Installing Web UI dependencies ..."
pip install --quiet --upgrade pip

# Core OCR deps (in case not already installed by base installer)
pip install --quiet \
    "torch>=2.4" \
    torchvision \
    "transformers==4.57.1" \
    "huggingface_hub>=0.30" \
    Pillow matplotlib einops addict easydict pymupdf psutil \
    accelerate safetensors requests tqdm 2>/dev/null || true

# Web UI specific deps
pip install --quiet \
    "fastapi>=0.115.0" \
    "sse-starlette>=2.0.0" \
    "python-multipart>=0.0.9" \
    "uvicorn>=0.30.0" \
    "python-docx>=1.1.0"

info "Dependencies installed ✓"

# ── 5. Create .env if not exists ────────────────────────
step "Configuring translation API ..."
ENV_FILE="$WEB_DIR/.env"
ENV_EXAMPLE="$WEB_DIR/.env.example"

if [[ ! -f "$ENV_FILE" ]]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    warn "Created .env from template. To enable translation, edit:"
    warn "  $ENV_FILE"
    warn ""
    warn "Set TRANSLATE_API_BASE, TRANSLATE_API_KEY, TRANSLATE_MODEL."
    warn "Any OpenAI-compatible API works (星火/OpenAI/DeepSeek/Ollama)."
else
    info ".env already exists ✓"
fi

# ── 6. Verify ───────────────────────────────────────────
step "Verifying installation ..."

# Quick import check
python3 -c "
import fastapi; import sse_starlette; import uvicorn
import docx; print('All web dependencies OK')
" 2>/dev/null || {
    err "Dependency check failed. Try: pip install -r $WEB_DIR/requirements.txt"
    exit 1
}

echo ""
echo "══════════════════════════════════════════════════════════"
echo -e "${GREEN}  ✓  Web UI installation complete!${NC}"
echo "══════════════════════════════════════════════════════════"
echo ""
echo "  Start the server:"
echo ""
echo -e "    ${CYAN}bash web/scripts/start_web.sh${NC}"
echo ""
echo "  Or manually:"
echo ""
echo -e "    ${CYAN}source .venv-ocr/bin/activate${NC}"
echo -e "    ${CYAN}cd web && python3 server.py${NC}"
echo ""
echo "  Then open http://localhost:8800 in your browser."
echo ""
echo "  Translation config (optional):"
echo -e "    ${YELLOW}nano web/.env${NC}  # set TRANSLATE_API_BASE/KEY/MODEL"
echo ""
