//! Document-related data structures.
//!
//! Defines the request and response types for the parse endpoint,
//! as well as the chunk representation.

use serde::{Deserialize, Serialize};

/// Supported document types for parsing.
#[derive(Debug, Deserialize, Serialize, Clone)]
#[serde(rename_all = "lowercase")]
pub enum DocumentType {
    Pdf,
    Markdown,
    Csv,
    Code,
    Text,
}

impl std::fmt::Display for DocumentType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            DocumentType::Pdf => write!(f, "pdf"),
            DocumentType::Markdown => write!(f, "markdown"),
            DocumentType::Csv => write!(f, "csv"),
            DocumentType::Code => write!(f, "code"),
            DocumentType::Text => write!(f, "text"),
        }
    }
}

/// Request body for the /parse endpoint.
#[derive(Debug, Deserialize)]
pub struct ParseRequest {
    /// Original filename of the document.
    pub filename: String,

    /// Type of the document being parsed.
    pub document_type: DocumentType,

    /// Raw content of the document (base64 for binary, plain text for text formats).
    pub content: String,

    /// Maximum characters per chunk (default: 1000).
    #[serde(default = "default_chunk_size")]
    pub chunk_size: usize,

    /// Number of overlapping characters between chunks (default: 200).
    #[serde(default = "default_chunk_overlap")]
    pub chunk_overlap: usize,
}

fn default_chunk_size() -> usize {
    1000
}

fn default_chunk_overlap() -> usize {
    200
}

/// A single text chunk extracted from a document.
#[derive(Debug, Serialize)]
pub struct TextChunk {
    /// Zero-based index of this chunk within the document.
    pub index: usize,

    /// The text content of this chunk.
    pub content: String,

    /// Character count of the chunk content.
    pub char_count: usize,
}

/// Response from the /parse endpoint.
#[derive(Debug, Serialize)]
pub struct ParseResponse {
    /// Original filename.
    pub filename: String,

    /// Total number of chunks generated.
    pub chunk_count: usize,

    /// The parsed text chunks.
    pub chunks: Vec<TextChunk>,
}
