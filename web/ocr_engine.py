"""OCR Engine: lazy model loading + per-page inference."""
import sys
import time
import threading
from pathlib import Path

from config import OCR_REPO_DIR

# Add OCR repo to path so we can import run_mac
sys.path.insert(0, str(OCR_REPO_DIR))

_model = None
_tokenizer = None
_device = None
_lock = threading.Lock()
_load_time = None


def ensure_model():
    """Load model on first call (thread-safe). Returns (model, tokenizer, device)."""
    global _model, _tokenizer, _device, _load_time
    if _model is not None:
        return _model, _tokenizer, _device

    with _lock:
        if _model is not None:
            return _model, _tokenizer, _device

        from run_mac import pick_device, apply_patches, load_model

        _device = pick_device()
        patched_dir = apply_patches(_device)
        _model, _tokenizer = load_model(patched_dir, _device)
        _load_time = time.time()
        print(f"[ocr_engine] model loaded on {_device} in {_load_time:.1f}s")

    return _model, _tokenizer, _device


def get_status():
    """Return model status dict."""
    return {
        "loaded": _model is not None,
        "device": str(_device) if _device else None,
        "load_time_s": round(_load_time, 1) if _load_time else None,
    }


def ocr_page(image_path: str, max_length: int = 8192) -> str:
    """Run OCR on a single image. Returns raw <|det|>...<|/det|>... string."""
    model, tokenizer, device = ensure_model()

    result = model.infer(
        tokenizer,
        prompt="<image>document parsing.",
        image_file=str(image_path),
        output_path="/tmp/ocr_web_out",
        base_size=1024,
        image_size=640,
        crop_mode=True,
        eval_mode=True,
        max_length=max_length,
        no_repeat_ngram_size=35,
        ngram_window=128,
        temperature=0.0,
        save_results=False,
    )
    return result or ""
