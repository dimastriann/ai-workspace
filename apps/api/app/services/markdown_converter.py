"""
AI Workspace API — Local Markdown Conversion

Converts PDF and DOCX documents to Markdown without AI services.
"""

import json
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import mammoth
from markdownify import markdownify as html_to_markdown
from PIL import Image
from pypdf import PdfReader

MAX_IMAGES = 50
Image.MAX_IMAGE_PIXELS = 25_000_000

_IMAGE_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
}
_DATA_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(data:[^)]+\)")
_MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\((assets/[^)]+)\)")


@dataclass(frozen=True)
class ConversionOutput:
    """Markdown and the number of extracted images."""

    markdown: str
    image_count: int


def convert_document(
    filename: str,
    data: bytes,
    output_dir: Path,
    include_images: bool,
) -> ConversionOutput:
    """Convert a supported document to Markdown, writing assets if requested."""
    suffix = Path(filename).suffix.lower()
    output_dir.mkdir(parents=True, exist_ok=True)

    if suffix == ".pdf":
        return _convert_pdf(data, output_dir, include_images)
    if suffix == ".docx":
        return _convert_docx(data, output_dir, include_images)

    return ConversionOutput(_decode_text(data), 0)


def _decode_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace").strip()


def _convert_pdf(
    data: bytes, output_dir: Path, include_images: bool
) -> ConversionOutput:
    reader = PdfReader(BytesIO(data))
    assets_dir = output_dir / "assets"
    sections: list[str] = []
    image_count = 0

    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        sections.append(f"# Page {page_number}\n\n{text}")

        if not include_images or image_count >= MAX_IMAGES:
            continue

        try:
            images = list(page.images)
        except Exception:
            images = []

        for index, image_file in enumerate(images):
            if image_count >= MAX_IMAGES:
                break
            try:
                image = image_file.image
            except Exception:
                continue
            if image is None:
                continue

            name = f"page-{page_number:03d}-image-{index + 1:02d}.png"
            assets_dir.mkdir(parents=True, exist_ok=True)
            image.save(assets_dir / name, format="PNG")
            sections.append(f"![Page {page_number} image {index + 1}](assets/{name})")
            image_count += 1

    return ConversionOutput("\n\n".join(sections), image_count)


def _convert_docx(
    data: bytes, output_dir: Path, include_images: bool
) -> ConversionOutput:
    assets_dir = output_dir / "assets"
    image_count = 0

    def convert_image(image: Any) -> dict[str, str]:
        nonlocal image_count
        if not include_images or image_count >= MAX_IMAGES:
            return {}

        image_count += 1
        extension = _IMAGE_EXTENSIONS.get(getattr(image, "content_type", ""), ".png")
        name = f"image-{image_count:03d}{extension}"
        assets_dir.mkdir(parents=True, exist_ok=True)
        with image.open() as stream:
            (assets_dir / name).write_bytes(stream.read())
        return {"src": f"assets/{name}"}

    if include_images:
        with BytesIO(data) as stream:
            result = mammoth.convert_to_html(
                stream,
                convert_image=cast(Any, mammoth.images.img_element(convert_image)),
            )
    else:
        with BytesIO(data) as stream:
            result = mammoth.convert_to_html(stream)

    markdown = html_to_markdown(result.value, heading_style="ATX")
    if not include_images:
        markdown = _DATA_IMAGE_RE.sub("", markdown)

    return ConversionOutput(markdown.strip(), image_count)


def render_json(filename: str, markdown: str, image_count: int) -> str:
    """Render a deterministic JSON representation of converted content."""
    images = _MARKDOWN_IMAGE_RE.findall(markdown)
    blocks: list[dict[str, str]] = []
    for chunk in markdown.split("\n\n"):
        text = chunk.strip()
        if not text:
            continue
        if text.startswith("#"):
            block_type = "heading"
        elif text.startswith("!["):
            block_type = "image"
        else:
            block_type = "paragraph"
        blocks.append({"type": block_type, "text": text})

    payload = {
        "filename": filename,
        "source_format": Path(filename).suffix.lower().lstrip("."),
        "image_count": image_count,
        "images": images,
        "blocks": blocks,
        "markdown": markdown,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
