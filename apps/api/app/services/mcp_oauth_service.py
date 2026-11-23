"""MCP OAuth 2.1 flows for remote servers.

Implements the MCP authorization spec primitives the app needs:
authorization-server discovery, dynamic client registration, the
authorization-code + PKCE browser flow, token exchange, and refresh.
Tokens are stored encrypted on the MCP server row.
"""

import base64
import hashlib
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx

from app.config import settings as app_settings
from app.core.security import decrypt_secret, encrypt_secret
from app.models.database import McpServer

STATE_TTL_SECONDS = 600
TOKEN_EXPIRY_MARGIN_SECONDS = 60


class McpOAuthError(Exception):
    """Raised when an OAuth step fails."""


@dataclass(frozen=True)
class PendingAuthorization:
    """A started browser flow awaiting the authorization callback."""

    server_id: str
    state: str
    code_verifier: str
    redirect_uri: str
    token_endpoint: str
    client_id: str
    client_secret: str | None
    created_at: float


class McpOAuthService:
    """OAuth client state machine for MCP servers."""

    def __init__(self) -> None:
        self._pending: dict[str, PendingAuthorization] = {}
        self._client: httpx.AsyncClient | None = None

    def set_client(self, client: httpx.AsyncClient | None) -> None:
        """Replace the HTTP client (used by tests with a mock transport)."""
        self._client = client

    def _http(self) -> httpx.AsyncClient:
        return self._client or httpx.AsyncClient(timeout=30)

    # -- discovery and registration ---------------------------------------

    async def discover_authorization_server(self, resource_url: str) -> dict[str, Any]:
        """Resolve the authorization server metadata for an MCP server URL."""
        parsed = urlparse(resource_url)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise McpOAuthError("Server URL must be an absolute HTTP(S) URL")
        origin = f"{parsed.scheme}://{parsed.netloc}"

        protected = await self._get_json(
            f"{origin}/.well-known/oauth-protected-resource"
        )
        authorization_servers = protected.get("authorization_servers") or []
        issuer = str(authorization_servers[0]) if authorization_servers else origin
        issuer_parsed = urlparse(issuer)
        issuer_origin = f"{issuer_parsed.scheme}://{issuer_parsed.netloc}"
        suffix = "/.well-known/oauth-authorization-server"
        if issuer_parsed.path.rstrip("/"):
            suffix = f"{issuer_parsed.path.rstrip('/')}{suffix}"

        metadata = await self._get_json(f"{issuer_origin}{suffix}")
        for field in ("authorization_endpoint", "token_endpoint"):
            if not metadata.get(field):
                raise McpOAuthError(f"Authorization server metadata missing {field}")
        return metadata

    async def _get_json(self, url: str) -> dict[str, Any]:
        try:
            response = await self._http().get(url)
        except httpx.HTTPError as exc:
            raise McpOAuthError(f"OAuth discovery request failed: {exc}") from exc
        if response.status_code != 200:
            raise McpOAuthError(
                f"OAuth discovery failed for {url}: HTTP {response.status_code}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise McpOAuthError("OAuth discovery returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise McpOAuthError("OAuth discovery returned an unexpected payload")
        return data

    async def register_client(
        self, metadata: dict[str, Any], redirect_uri: str
    ) -> dict[str, Any]:
        """Dynamically register the app as an OAuth client."""
        registration_endpoint = metadata.get("registration_endpoint")
        if not registration_endpoint:
            raise McpOAuthError(
                "Authorization server does not support dynamic client registration"
            )
        payload = {
            "client_name": "AI Workspace",
            "redirect_uris": [redirect_uri],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        }
        try:
            response = await self._http().post(str(registration_endpoint), json=payload)
        except httpx.HTTPError as exc:
            raise McpOAuthError(f"Client registration failed: {exc}") from exc
        if response.status_code not in {200, 201}:
            raise McpOAuthError(
                f"Client registration failed: HTTP {response.status_code}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise McpOAuthError("Client registration returned invalid JSON") from exc
        if not isinstance(data, dict) or not data.get("client_id"):
            raise McpOAuthError("Client registration returned no client_id")
        return data

    # -- browser flow ------------------------------------------------------

    async def start_authorization(self, server: McpServer, redirect_uri: str) -> str:
        """Discover, register, and return the URL the browser must open."""
        metadata = await self.discover_authorization_server(server.url)
        client = await self.register_client(metadata, redirect_uri)

        state = secrets.token_urlsafe(24)
        code_verifier = secrets.token_urlsafe(48)
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        self._pending[state] = PendingAuthorization(
            server_id=str(server.id),
            state=state,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            token_endpoint=str(metadata["token_endpoint"]),
            client_id=str(client["client_id"]),
            client_secret=(
                str(client["client_secret"]) if client.get("client_secret") else None
            ),
            created_at=time.monotonic(),
        )
        self._sweep_expired()

        params: dict[str, str] = {
            "response_type": "code",
            "client_id": str(client["client_id"]),
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{metadata['authorization_endpoint']}?{urlencode(params)}"

    def get_pending(self, state: str) -> PendingAuthorization | None:
        """Return a valid pending flow for a callback state, if any."""
        pending = self._pending.get(state)
        if pending is None or time.monotonic() - pending.created_at > STATE_TTL_SECONDS:
            self._pending.pop(state, None)
            return None
        return pending

    async def complete_authorization(
        self,
        server: McpServer,
        pending: PendingAuthorization | None,
        code: str,
    ) -> None:
        """Exchange the callback code for tokens and persist them encrypted."""
        if pending is None:
            raise McpOAuthError("Unknown or expired OAuth state")
        self._pending.pop(pending.state, None)
        form: dict[str, str] = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": pending.redirect_uri,
            "client_id": pending.client_id,
            "code_verifier": pending.code_verifier,
        }
        if pending.client_secret:
            form["client_secret"] = pending.client_secret

        try:
            response = await self._http().post(
                pending.token_endpoint,
                data=form,
                headers={"accept": "application/json"},
            )
        except httpx.HTTPError as exc:
            raise McpOAuthError(f"Token exchange failed: {exc}") from exc
        if response.status_code != 200:
            raise McpOAuthError(f"Token exchange failed: HTTP {response.status_code}")
        try:
            tokens = response.json()
        except ValueError as exc:
            raise McpOAuthError("Token endpoint returned invalid JSON") from exc
        if not isinstance(tokens, dict) or not tokens.get("access_token"):
            raise McpOAuthError("Token endpoint returned no access_token")

        self.persist_tokens(
            server,
            client_id=pending.client_id,
            client_secret=pending.client_secret,
            token_endpoint=pending.token_endpoint,
            tokens=tokens,
        )

    # -- token storage -----------------------------------------------------

    @staticmethod
    def persist_tokens(
        server: McpServer,
        *,
        client_id: str,
        client_secret: str | None,
        token_endpoint: str,
        tokens: dict[str, Any],
    ) -> None:
        """Store tokens encrypted on the server row."""
        expires_in = tokens.get("expires_in")
        bundle = {
            "client_id": client_id,
            "client_secret": client_secret,
            "token_endpoint": token_endpoint,
            "access_token": str(tokens["access_token"]),
            "refresh_token": (
                str(tokens["refresh_token"]) if tokens.get("refresh_token") else None
            ),
            "expires_at": (
                time.time() + float(expires_in)
                if isinstance(expires_in, (int, float))
                else None
            ),
        }
        server.oauth_encrypted = encrypt_secret(
            json.dumps(bundle), app_settings.app_secret_key
        )

    @staticmethod
    def load_bundle(server: McpServer) -> dict[str, Any] | None:
        """Return the decrypted token bundle for a server, if connected."""
        if not server.oauth_encrypted:
            return None
        try:
            bundle = json.loads(
                decrypt_secret(server.oauth_encrypted, app_settings.app_secret_key)
            )
        except (ValueError, json.JSONDecodeError):
            return None
        return (
            bundle if isinstance(bundle, dict) and bundle.get("access_token") else None
        )

    @staticmethod
    def disconnect(server: McpServer) -> None:
        server.oauth_encrypted = None

    def bundle_expired(self, bundle: dict[str, Any]) -> bool:
        expires_at = bundle.get("expires_at")
        if not isinstance(expires_at, (int, float)):
            return False
        return time.time() >= float(expires_at) - TOKEN_EXPIRY_MARGIN_SECONDS

    async def refresh(self, server: McpServer, bundle: dict[str, Any]) -> bool:
        """Refresh the access token in place. Returns whether it succeeded."""
        refresh_token = bundle.get("refresh_token")
        if not refresh_token:
            return False
        form: dict[str, str] = {
            "grant_type": "refresh_token",
            "refresh_token": str(refresh_token),
            "client_id": str(bundle.get("client_id") or ""),
        }
        if bundle.get("client_secret"):
            form["client_secret"] = str(bundle["client_secret"])
        try:
            response = await self._http().post(
                str(bundle.get("token_endpoint") or ""), data=form
            )
        except httpx.HTTPError:
            return False
        if response.status_code != 200:
            return False
        try:
            tokens = response.json()
        except ValueError:
            return False
        if not isinstance(tokens, dict) or not tokens.get("access_token"):
            return False

        self.persist_tokens(
            server,
            client_id=str(bundle.get("client_id") or ""),
            client_secret=(
                str(bundle["client_secret"]) if bundle.get("client_secret") else None
            ),
            token_endpoint=str(bundle.get("token_endpoint") or ""),
            tokens=tokens,
        )
        return True

    def _sweep_expired(self) -> None:
        expired = [
            state
            for state, pending in self._pending.items()
            if time.monotonic() - pending.created_at > STATE_TTL_SECONDS
        ]
        for state in expired:
            self._pending.pop(state, None)


mcp_oauth_service = McpOAuthService()
