//! Document parsing endpoint.
//!
//! Receives raw document content and returns parsed, chunked text.

use actix_web::{HttpResponse, post, web};

use crate::models::document::{ParseRequest, ParseResponse};
use crate::parsers;

/// POST /parse — Parse a document into text chunks.
#[post("/parse")]
pub async fn parse_document(body: web::Json<ParseRequest>) -> HttpResponse {
    let request = body.into_inner();

    log::info!(
        "Parsing document: '{}' (type: {})",
        request.filename,
        request.document_type
    );

    // Delegate to the appropriate parser based on document type
    let chunks = parsers::parse(&request);

    let response = ParseResponse {
        filename: request.filename,
        chunk_count: chunks.len(),
        chunks,
    };

    HttpResponse::Ok().json(response)
}
