"""Tests for local Markdown conversion."""

import io
from pathlib import Path

from docx import Document as DocxDocument
from PIL import Image
from reportlab.pdfgen import canvas

from app.services.markdown_converter import convert_document


def test_text_passthrough(tmp_path: Path) -> None:
    output = convert_document("notes.md", b"# Title\n\nHello", tmp_path, False)

    assert "# Title" in output.markdown
    assert output.image_count == 0


def test_pdf_extracts_text(tmp_path: Path) -> None:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(100, 750, "Hello PDF")
    pdf.save()

    output = convert_document("report.pdf", buffer.getvalue(), tmp_path, False)

    assert "# Page 1" in output.markdown
    assert "Hello PDF" in output.markdown


def _docx_with_image() -> bytes:
    document = DocxDocument()
    document.add_heading("Report title", level=1)
    document.add_paragraph("Hello DOCX")
    image_buffer = io.BytesIO()
    Image.new("RGB", (10, 10), (255, 0, 0)).save(image_buffer, format="PNG")
    image_buffer.seek(0)
    document.add_picture(image_buffer)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_docx_converts_with_images(tmp_path: Path) -> None:
    output = convert_document("report.docx", _docx_with_image(), tmp_path, True)

    assert "Report title" in output.markdown
    assert "Hello DOCX" in output.markdown
    assert output.image_count == 1
    assert list((tmp_path / "assets").iterdir())
    assert "assets/" in output.markdown


def test_docx_strips_images_when_disabled(tmp_path: Path) -> None:
    output = convert_document("report.docx", _docx_with_image(), tmp_path, False)

    assert output.image_count == 0
    assert "data:image" not in output.markdown
    assert "assets/" not in output.markdown
    assert not (tmp_path / "assets").exists()
