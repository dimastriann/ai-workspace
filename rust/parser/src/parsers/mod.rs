//! Document parser modules.
//!
//! Each parser handles a specific document format and extracts plain text.
//! The chunker module then splits the extracted text into overlapping chunks.

mod chunker;
mod code;
mod csv;
mod markdown;
mod pdf;

use crate::models::document::{DocumentType, ParseRequest, TextChunk};

/// Parse a document based on its type and return chunked text.
pub fn parse(request: &ParseRequest) -> Vec<TextChunk> {
    // Step 1: Extract raw text based on document type
    let raw_text = match request.document_type {
        DocumentType::Pdf => pdf::extract_text(&request.content),
        DocumentType::Markdown => markdown::extract_text(&request.content),
        DocumentType::Csv => csv::extract_text(&request.content),
        DocumentType::Code => code::extract_text(&request.content),
        DocumentType::Text => request.content.clone(),
    };

    // Step 2: Split into overlapping chunks
    chunker::split_text(&raw_text, request.chunk_size, request.chunk_overlap)
}
