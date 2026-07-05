"""Configuration for Unlimited-OCR Web."""
import os
from pathlib import Path

# Paths
OCR_REPO_DIR = Path("~/unlimited-ocr-mac").expanduser().resolve()
PROJECT_DIR = Path(__file__).parent.resolve()
UPLOAD_DIR = PROJECT_DIR / "uploads"
PUBLIC_DIR = PROJECT_DIR / "public"

# Ensure dirs
UPLOAD_DIR.mkdir(exist_ok=True)

# Server
HOST = "0.0.0.0"
PORT = 8800

# OCR defaults
DEFAULT_MAX_LENGTH = 8192
DEFAULT_BASE_SIZE = 1024
DEFAULT_IMAGE_SIZE = 640
PDF_DPI = 200

# Translation (OpenAI-compatible API)
TRANSLATE_API_BASE = os.environ.get("TRANSLATE_API_BASE", "")
TRANSLATE_API_KEY = os.environ.get("TRANSLATE_API_KEY", "")
TRANSLATE_MODEL = os.environ.get("TRANSLATE_MODEL", "gpt-4o")

# Session expiry (seconds)
SESSION_TTL = 7200
