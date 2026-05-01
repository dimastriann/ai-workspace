# =============================================================================
# AI Workspace Parser — Dockerfile
# =============================================================================

# ── Build Stage ──────────────────────────────────────────────────────────────
FROM rust:1.94-slim AS builder

WORKDIR /app

# Copy manifests and build dependencies first (for Docker layer caching)
COPY Cargo.toml .
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release
RUN rm -rf src

# Copy actual source and rebuild
COPY src/ src/
RUN touch src/main.rs && cargo build --release

# ── Runtime Stage ────────────────────────────────────────────────────────────
FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/ai-workspace-parser /usr/local/bin/parser

EXPOSE 8080

CMD ["parser"]
