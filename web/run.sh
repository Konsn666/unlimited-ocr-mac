#!/bin/bash
set -e
VENV="/Users/macstudiodisplay/unlimited-ocr-mac/.venv-ocr/bin/activate"
source "$VENV"
cd "$(dirname "$0")"
python server.py
