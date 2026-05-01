//! Route configuration module.
//!
//! Centralizes all route registration for the Actix-web application.

mod health;
mod parse;

use actix_web::web;

/// Configure all application routes.
pub fn configure(cfg: &mut web::ServiceConfig) {
    cfg.service(health::health_check)
        .service(parse::parse_document);
}
