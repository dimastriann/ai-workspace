//! CSV text extraction.
//!
//! Converts CSV content into a readable text format
//! suitable for embedding and semantic search.

/// Extract text from CSV content.
///
/// Converts rows into "column: value" format for
/// better semantic understanding by the LLM.
pub fn extract_text(content: &str) -> String {
    let mut lines = content.lines();

    // Parse header row
    let headers: Vec<&str> = match lines.next() {
        Some(header_line) => header_line.split(',').map(|h| h.trim()).collect(),
        None => return String::new(),
    };

    // Convert each row to "column: value" pairs
    let mut output = Vec::new();
    for (row_idx, line) in lines.enumerate() {
        let values: Vec<&str> = line.split(',').map(|v| v.trim()).collect();
        let mut row_text = format!("Row {}:", row_idx + 1);

        for (col_idx, value) in values.iter().enumerate() {
            let header = headers.get(col_idx).unwrap_or(&"unknown");
            row_text.push_str(&format!(" {} = {};", header, value));
        }

        output.push(row_text);
    }

    output.join("\n")
}
