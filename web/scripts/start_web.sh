#!/usr/bin/env bash
# 启动 Unlimited OCR Web UI / Start the Unlimited OCR Web UI server
#
# Usage:
#   bash web/scripts/start_web.sh [port]
#
# Options:
#   port   Server port (default: 8800)

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$REPO_DIR/web"
VENV_DIR="${VENV_DIR:-$REPO_DIR/.venv-ocr}"
PORT="${1:-8800}"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

# Activate venv
if [[ ! -d "$VENV_DIR" ]]; then
    echo "Error: venv not found at $VENV_DIR"
    echo "Run: bash web/scripts/install_web.sh first"
    exit 1
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

cd "$WEB_DIR"

echo ""
echo -e "${GREEN}  🚀 Starting Unlimited OCR Web UI on port ${PORT}...${NC}"
echo -e "  ${CYAN}http://localhost:${PORT}${NC}"
echo ""
echo "  Press Ctrl+C to stop."
echo ""

python3 server.py
