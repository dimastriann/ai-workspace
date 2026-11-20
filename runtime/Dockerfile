# =============================================================================
# AI Workspace runtime — optional IDE and terminal services
#
# Build profile: `docker compose --profile runtime build runtime-ide runtime-terminal`
#
# - code-server for the browser IDE
# - ttyd for the browser terminal
# - optional Node/Python runtimes controlled by build args
#
# The image never mounts the Docker socket and runs as a non-root user.
# =============================================================================

ARG CODE_SERVER_VERSION=4.145.2

FROM codercom/code-server:${CODE_SERVER_VERSION}

ARG TARGETARCH
ARG TTYD_VERSION=1.7.7
ARG INSTALL_NODE=false
ARG INSTALL_PYTHON=false

USER root

# Map Docker's TARGETARCH to ttyd release names.
RUN case "${TARGETARCH}" in \
      "amd64") TTYD_ARCH="x86_64" ;; \
      "arm64") TTYD_ARCH="aarch64" ;; \
      "arm") TTYD_ARCH="armhf" ;; \
      "arm/v7") TTYD_ARCH="armhf" ;; \
      "386") TTYD_ARCH="i686" ;; \
      *) TTYD_ARCH="x86_64" ;; \
    esac; \
    echo "ttyd architecture: ${TTYD_ARCH}" && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      git \
      jq \
      unzip && \
    curl -fsSL \
      "https://github.com/tsl0922/ttyd/releases/download/${TTYD_VERSION}/ttyd.${TTYD_ARCH}" \
      -o /usr/local/bin/ttyd && \
    chmod 0755 /usr/local/bin/ttyd && \
    if [ "${INSTALL_NODE}" = "true" ]; then \
      apt-get install -y --no-install-recommends nodejs npm; \
    fi && \
    if [ "${INSTALL_PYTHON}" = "true" ]; then \
      apt-get install -y --no-install-recommends python3 python3-pip; \
    fi && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Keep the default coder user (uid/gid 1000). Docker initializes an empty
# api_uploads volume from the image's /home/coder/workspace directory, so the
# first mount retains coder ownership.
USER coder

EXPOSE 8080 7681
