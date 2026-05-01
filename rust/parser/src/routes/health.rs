//! Health check endpoint for container orchestration and monitoring.

use actix_web::{HttpResponse, get};
use serde::Serialize;

#[derive(Serialize)]
struct HealthResponse {
    status: String,
    service: String,
    version: String,
}

/// GET /health — Returns service health status.
#[get("/health")]
pub async fn health_check() -> HttpResponse {
    let response = HealthResponse {
        status: "healthy".to_string(),
        service: "ai-workspace-parser".to_string(),
        version: "0.1.0".to_string(),
    };
    HttpResponse::Ok().json(response)
}
