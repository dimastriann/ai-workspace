//! AI Workspace Parser — Application Entry Point
//!
//! High-performance document parsing microservice built with Actix-web.
//! Handles text extraction, chunking, and preprocessing for the AI pipeline.

mod models;
mod parsers;
mod routes;

use actix_cors::Cors;
use actix_web::{App, HttpServer, middleware};

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Initialize logger
    env_logger::init_from_env(env_logger::Env::default().default_filter_or("info"));
    log::info!("🚀 AI Workspace Parser starting on port 8080");

    HttpServer::new(|| {
        let cors = Cors::default()
            .allow_any_origin()
            .allow_any_method()
            .allow_any_header();

        App::new()
            .wrap(cors)
            .wrap(middleware::Logger::default())
            .configure(routes::configure)
    })
    .bind("0.0.0.0:8080")?
    .run()
    .await
}
