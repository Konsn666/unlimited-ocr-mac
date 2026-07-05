"""PDF to image conversion using PyMuPDF."""
import fitz
from pathlib import Path
from config import PDF_DPI


def pdf_to_images(pdf_path: str, output_dir: Path, dpi: int = PDF_DPI) -> list[Path]:
    """Convert PDF pages to PNG images. Returns sorted list of image paths."""
    doc = fitz.open(pdf_path)
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    images = []

    for i, page in enumerate(doc):
        out_path = output_dir / f"page_{i + 1:04d}.png"
        pix = page.get_pixmap(matrix=mat)
        pix.save(str(out_path))
        images.append(out_path)

    doc.close()
    return images


def image_to_base64(image_path: Path) -> str:
    """Read image file and return base64-encoded string."""
    import base64
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
