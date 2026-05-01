//! Text chunker with configurable size and overlap.
//!
//! Splits extracted text into overlapping chunks for optimal
//! embedding generation and retrieval accuracy.

use crate::models::document::TextChunk;

/// Split text into overlapping chunks.
///
/// # Arguments
/// * `text` - The raw text to split
/// * `chunk_size` - Maximum characters per chunk
/// * `chunk_overlap` - Number of overlapping characters between chunks
///
/// # Returns
/// A vector of `TextChunk` with sequential indices.
pub fn split_text(text: &str, chunk_size: usize, chunk_overlap: usize) -> Vec<TextChunk> {
    if text.is_empty() {
        return vec![];
    }

    let mut chunks = Vec::new();
    let chars: Vec<char> = text.chars().collect();
    let total_chars = chars.len();

    let step = if chunk_size > chunk_overlap {
        chunk_size - chunk_overlap
    } else {
        1 // Fallback: ensure we always advance
    };

    let mut start = 0;
    let mut index = 0;

    while start < total_chars {
        let end = (start + chunk_size).min(total_chars);
        let content: String = chars[start..end].iter().collect();
        let char_count = content.len();

        chunks.push(TextChunk {
            index,
            content,
            char_count,
        });

        start += step;
        index += 1;
    }

    chunks
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty_text() {
        let chunks = split_text("", 100, 20);
        assert!(chunks.is_empty());
    }

    #[test]
    fn test_short_text() {
        let chunks = split_text("Hello, world!", 100, 20);
        assert_eq!(chunks.len(), 1);
        assert_eq!(chunks[0].content, "Hello, world!");
        assert_eq!(chunks[0].index, 0);
    }

    #[test]
    fn test_chunking_with_overlap() {
        let text = "abcdefghij"; // 10 chars
        let chunks = split_text(text, 5, 2);

        // Step = 5 - 2 = 3
        // Chunk 0: [0..5] = "abcde"
        // Chunk 1: [3..8] = "defgh"
        // Chunk 2: [6..10] = "ghij"
        assert_eq!(chunks.len(), 3);
        assert_eq!(chunks[0].content, "abcde");
        assert_eq!(chunks[1].content, "defgh");
        assert_eq!(chunks[2].content, "ghij");
    }
}
