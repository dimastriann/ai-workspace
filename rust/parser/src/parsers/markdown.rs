//! Markdown text extraction.
//!
//! Converts Markdown content to plain text by stripping formatting.
//! Currently implements a basic approach; Phase 3 will add full Markdown parsing.

/// Extract plain text from Markdown content.
///
/// Strips common Markdown syntax for clean text extraction.
pub fn extract_text(content: &str) -> String {
    // Basic Markdown stripping (Phase 3 will use a proper parser)
    content
        .lines()
        .map(|line| {
            line.trim_start_matches('#')  // Strip heading markers
                .trim_start_matches('>')  // Strip blockquotes
                .trim_start_matches('-')  // Strip list markers
                .trim_start_matches('*')  // Strip bold/italic/list
                .trim()
        })
        .collect::<Vec<&str>>()
        .join("\n")
}
