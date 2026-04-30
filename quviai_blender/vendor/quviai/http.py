from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import TYPE_CHECKING, Any

from .exceptions import (
    AuthError,
    ContentModerationError,
    InsufficientCreditsError,
    QuviError,
    RateLimitError,
    TaskNotFoundError,
    TokenExpiredError,
)

if TYPE_CHECKING:
    from .auth import JWTAuth

BASE_URL = "https://quvi.ai"

# Paths that must NOT trigger an automatic token refresh (avoids retry loops).
_NO_REFRESH_PATHS = {"/auth/jwt/refresh/", "/auth/jwt/create/"}


class HTTPClient:
    """urllib-based HTTP client with automatic JWT refresh on 401."""

    def __init__(
        self,
        auth: JWTAuth,
        base_url: str = BASE_URL,
        timeout: int = 120,
    ) -> None:
        self._auth = auth
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._post(path, body, self._auth.headers())
        except AuthError as exc:
            if exc.status_code == 401 and self._auth.refresh_token and path not in _NO_REFRESH_PATHS:
                self._refresh()
                return self._post(path, body, self._auth.headers())
            raise

    def get_bytes(self, url: str) -> bytes:
        """Fetch raw bytes from an arbitrary URL (for downloading result images)."""
        with urllib.request.urlopen(url, timeout=self._timeout) as resp:
            return resp.read()

    # ------------------------------------------------------------------

    def _post(self, path: str, body: dict[str, Any], extra_headers: dict[str, str]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        data = json.dumps(body).encode()
        headers = {"Content-Type": "application/json", "Accept": "application/json", **extra_headers}
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            try:
                error_body = json.loads(exc.read())
            except Exception:
                error_body = {}
            self._raise_for_status(exc.code, error_body)

    def _refresh(self) -> None:
        try:
            resp = self._post(
                "/auth/jwt/refresh/",
                {"refresh": self._auth.refresh_token},
                {},
            )
            self._auth.update(resp["access"])
        except (AuthError, QuviError) as exc:
            raise TokenExpiredError(
                "Session expired. Please log in again."
            ) from exc

    @staticmethod
    def _raise_for_status(status_code: int, body: dict[str, Any]) -> None:
        message = (
            body.get("error")
            or body.get("detail")
            or body.get("non_field_errors", [""])[0]
            or f"HTTP {status_code}"
        )

        if status_code in (401, 403):
            raise AuthError(message, status_code=status_code)
        if status_code == 404:
            raise TaskNotFoundError(message)
        if status_code == 429:
            raise RateLimitError(message, status_code=429)
        if status_code == 400:
            if "credit" in message.lower():
                raise InsufficientCreditsError(message, status_code=400)
            if "moderation" in message.lower():
                raise ContentModerationError(
                    message,
                    reason=body.get("reason", ""),
                    category=body.get("category", ""),
                )
        raise QuviError(message, status_code=status_code)
