"""Parse OCR raw output into structured detections and HTML."""
import re
from typing import Optional


def parse_ocr_output(raw: str) -> list[dict]:
    """Parse <|det|>type [bbox]<|/det|>text into structured list."""
    if not raw:
        return []

    detections = []
    pattern = re.compile(r"<\|det\|>(\w+)\s*\[([^\]]*)\]<\|/det\|>(.+)")
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        m = pattern.match(line)
        if m:
            det_type = m.group(1)
            bbox_str = m.group(2)
            text = m.group(3).strip()
            bbox = [int(x.strip()) for x in bbox_str.split(",") if x.strip()]
            detections.append({"type": det_type, "bbox": bbox, "text": text})
        else:
            # Fallback: treat whole line as text
            if line and not line.startswith("<|") :
                detections.append({"type": "text", "bbox": [], "text": line})

    return detections


def reconstruct_structure(detections: list[dict]) -> list[dict]:
    """Group detections into logical blocks (headings, paragraphs, images, etc.)."""
    if not detections:
        return []

    blocks = []
    current_para = None

    for det in detections:
        det_type = det["type"]

        if det_type == "title":
            # Flush current paragraph
            if current_para:
                blocks.append(current_para)
                current_para = None
            # Determine heading level from bbox height (larger = higher level)
            bbox = det.get("bbox", [])
            level = 2  # default
            if len(bbox) >= 4:
                h = bbox[3] - bbox[1]
                if h > 60:
                    level = 1
            blocks.append({
                "block_type": "heading",
                "level": level,
                "text": det["text"],
                "bbox": bbox,
            })

        elif det_type == "image":
            if current_para:
                blocks.append(current_para)
                current_para = None
            blocks.append({
                "block_type": "image",
                "text": det["text"],
                "bbox": det.get("bbox", []),
            })

        elif det_type == "page_number":
            if current_para:
                blocks.append(current_para)
                current_para = None
            blocks.append({
                "block_type": "page_number",
                "text": det["text"],
                "bbox": det.get("bbox", []),
            })

        elif det_type == "table":
            if current_para:
                blocks.append(current_para)
                current_para = None
            blocks.append({
                "block_type": "table",
                "text": det["text"],
                "bbox": det.get("bbox", []),
            })

        else:  # text and others
            if current_para is None:
                current_para = {
                    "block_type": "paragraph",
                    "text": det["text"],
                    "bbox": det.get("bbox", []),
                }
            else:
                # Append to existing paragraph
                current_para["text"] += "\n" + det["text"]

    if current_para:
        blocks.append(current_para)

    return blocks


def generate_html(detections: list[dict], page_num: int = 1) -> str:
    """Convert detections to HTML for the right panel.

    Uses the raw detections list (not blocks) so that data-detection-index
    values match 1:1 with the detections array index.  This is critical for
    the translation feature which looks up DOM elements by detection index.
    """
    if not detections:
        return '<div class="ocr-page empty"><p class="muted">No content detected</p></div>'

    parts = [f'<div class="ocr-page" data-page="{page_num}">']

    for i, det in enumerate(detections):
        det_type = det.get("type", "text")
        text = _escape_html(det.get("text", ""))
        idx_attr = f'data-detection-index="{i}"'

        if det_type == "title":
            bbox = det.get("bbox", [])
            h = (bbox[3] - bbox[1]) if len(bbox) >= 4 else 0
            level = 1 if h > 60 else 2
            tag = f"h{min(level, 3)}"
            parts.append(
                f'<{tag} class="ocr-heading" contenteditable="true" '
                f'{idx_attr}>{text}</{tag}>'
            )

        elif det_type == "image":
            parts.append(
                f'<div class="ocr-image" {idx_attr}>'
                f'<span class="image-placeholder">🖼 图片区域</span>'
                f'</div>'
            )

        elif det_type == "table":
            parts.append(
                f'<div class="ocr-table" contenteditable="true" '
                f'{idx_attr}>{text}</div>'
            )

        elif det_type == "page_number":
            parts.append(
                f'<span class="ocr-page-number" {idx_attr}>{text}</span>'
            )

        else:  # text and others
            parts.append(
                f'<p class="ocr-text" contenteditable="true" '
                f'{idx_attr}>{text}</p>'
            )

    parts.append('</div>')
    return "\n".join(parts)


def _escape_html(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def generate_det_html(det: dict, index: int) -> str:
    """Generate HTML for a single detection (for real-time line-by-line push)."""
    det_type = det.get("type", "text")
    text = _escape_html(det.get("text", ""))

    if det_type == "title":
        bbox = det.get("bbox", [])
        h = (bbox[3] - bbox[1]) if len(bbox) >= 4 else 0
        level = 1 if h > 60 else 2
        tag = f"h{min(level, 3)}"
        return f'<{tag} class="ocr-heading" contenteditable="true" data-detection-index="{index}">{text}</{tag}>'

    elif det_type == "image":
        return f'<div class="ocr-image" data-detection-index="{index}"><span class="image-placeholder">🖼 图片区域</span></div>'

    elif det_type == "table":
        return f'<div class="ocr-table" contenteditable="true" data-detection-index="{index}">{text}</div>'

    elif det_type == "page_number":
        return f'<span class="ocr-page-number" data-detection-index="{index}">{text}</span>'

    else:  # text and others
        return f'<p class="ocr-text" contenteditable="true" data-detection-index="{index}">{text}</p>'
