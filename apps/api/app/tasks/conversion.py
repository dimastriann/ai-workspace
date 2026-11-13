"""
AI Workspace API — Document Conversion Handler

Runs local Markdown conversion and updates the conversion record.
"""

import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, DocumentConversion
from app.services.markdown_converter import convert_document, render_json
from app.services.storage import conversion_dir, document_file_path, remove_tree


async def process_conversion(db: AsyncSession, payload: dict[str, Any]) -> None:
    """Handle a Markdown conversion job."""
    conversion_id = UUID(str(payload["conversion_id"]))
    conversion = await db.get(DocumentConversion, conversion_id)
    if conversion is None:
        raise ValueError(f"Conversion not found: {conversion_id}")

    document = await db.get(Document, conversion.document_id)
    if document is None:
        raise ValueError(f"Document not found: {conversion.document_id}")

    source = document_file_path(document.workspace_id, document.id, document.filename)
    output_dir = conversion_dir(document.workspace_id, document.id)

    try:
        data = await asyncio.to_thread(source.read_bytes)
        await asyncio.to_thread(remove_tree, output_dir)
        result = await asyncio.to_thread(
            convert_document,
            document.filename,
            data,
            output_dir,
            conversion.include_images,
        )

        markdown_path = output_dir / "document.md"
        json_path = output_dir / "document.json"
        formats = (
            {"markdown", "json"} if conversion.format == "both" else {conversion.format}
        )

        if "markdown" in formats:
            await asyncio.to_thread(
                markdown_path.write_text, result.markdown, encoding="utf-8"
            )
        if "json" in formats:
            json_payload = render_json(
                document.filename, result.markdown, result.image_count
            )
            await asyncio.to_thread(
                json_path.write_text, json_payload, encoding="utf-8"
            )

        conversion.status = "completed"
        conversion.markdown_path = str(markdown_path) if "markdown" in formats else None
        conversion.json_path = str(json_path) if "json" in formats else None
        conversion.assets_path = (
            str(output_dir / "assets") if conversion.include_images else None
        )
        conversion.error = None
        await db.commit()
    except Exception as exc:
        conversion.status = "error"
        conversion.error = str(exc)[:2000]
        await db.commit()
        raise
