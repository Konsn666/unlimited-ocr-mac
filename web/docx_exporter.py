"""Export OCR results to Word (.docx) with formatting."""
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH


def export_docx(pages: list[dict], output_path: Path, export_mode: str = "original") -> Path:
    """Build a .docx from page data.

    Uses detections (not blocks) for export so that detection indices
    map 1:1 to translation results.

    export_mode: "original" | "translated" | "bilingual"
    """
    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "SimSun"
    style.font.size = Pt(12)

    for pi, page in enumerate(pages):
        detections = page.get("detections", [])
        translations = page.get("translations", [])

        # Build translation map: detection_index -> translated text
        trans_map = {}
        if translations:
            for t in translations:
                if "index" in t and "translated" in t:
                    trans_map[t["index"]] = t["translated"]

        if pi > 0:
            doc.add_page_break()

        for i, det in enumerate(detections):
            det_type = det.get("type", "text")
            text = det.get("text", "").strip()
            if not text:
                continue

            translated = trans_map.get(i, "")

            if det_type == "title":
                bbox = det.get("bbox", [])
                h = (bbox[3] - bbox[1]) if len(bbox) >= 4 else 0
                level = 1 if h > 60 else 2

                if export_mode == "translated" and translated:
                    _add_heading(doc, translated, level)
                elif export_mode == "bilingual" and translated:
                    _add_heading(doc, text, level)
                    _add_translation_para(doc, translated, is_heading=True)
                else:
                    _add_heading(doc, text, level)

            elif det_type == "table":
                if export_mode == "translated" and translated:
                    _add_table_para(doc, translated)
                elif export_mode == "bilingual" and translated:
                    _add_table_para(doc, text)
                    _add_translation_para(doc, translated)
                else:
                    _add_table_para(doc, text)

            elif det_type == "image":
                p = doc.add_paragraph()
                run = p.add_run("[图片]")
                run.font.color.rgb = RGBColor(128, 128, 128)
                run.font.italic = True

            elif det_type == "page_number":
                p = doc.add_paragraph()
                run = p.add_run(text)
                run.font.color.rgb = RGBColor(128, 128, 128)
                run.font.size = Pt(9)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER

            else:  # text and others
                if export_mode == "translated" and translated:
                    doc.add_paragraph(translated)
                elif export_mode == "bilingual" and translated:
                    doc.add_paragraph(text)
                    _add_translation_para(doc, translated)
                else:
                    doc.add_paragraph(text)

    doc.save(str(output_path))
    return output_path


def _add_heading(doc, text, level):
    h = doc.add_heading(text, level=min(level, 3))
    if level == 1:
        h.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _add_translation_para(doc, text, is_heading=False):
    """Add a translated text paragraph with distinct styling."""
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.color.rgb = RGBColor(79, 70, 229)  # Indigo
    if is_heading:
        run.font.size = Pt(13)
        run.bold = True
    else:
        run.font.size = Pt(11)
    # Left border via indentation
    p.paragraph_format.left_indent = Pt(12)
    p.paragraph_format.space_after = Pt(6)


def _add_table_para(doc, text):
    """Add a table text paragraph with monospace font."""
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = "Courier New"
    run.font.size = Pt(10)
