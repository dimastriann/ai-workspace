//! PDF text extraction.
//!
//! Extracts plain text from PDF file content.
//! Full implementation with the `pdf-extract` crate will be added in Phase 3.

/// Extract text from PDF content.
///
/// Currently returns a placeholder. Phase 3 will implement
/// actual PDF parsing using the `pdf-extract` or `lopdf` crate.
pub fn extract_text(content: &str) -> String {
    // TODO (Phase 3): Implement actual PDF text extraction
    // - Decode base64 content
    // - Use pdf-extract crate for text extraction
    // - Handle multi-page documents
    // - Preserve reading order

    log::info!("PDF parser called (stub) — content length: {} bytes", content.len());
    format!("[PDF content placeholder — {} bytes received]", content.len())
}
