from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .exceptions import (
    AuthError,
    ContentModerationError,
    InsufficientCreditsError,
    QuviError,
    RateLimitError,
    TaskNotFoundError,
)

BASE_URL = "https://quvi.ai"


class HTTPClient:
    """Thin urllib wrapper — zero external dependencies."""

    def __init__(
        self,
        auth_headers: dict[str, str],
        base_url: str = BASE_URL,
        timeout: int = 30,
    ) -> None:
        self._auth_headers = auth_headers
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        data = json.dumps(body).encode()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self._auth_headers,
        }
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            try:
                error_body = json.loads(exc.read())
            except Exception:
                error_body = {}
            self._raise_for_status(exc.code, error_body)

    def get_bytes(self, url: str) -> bytes:
        """Fetch raw bytes from an arbitrary URL (used to download result images)."""
        with urllib.request.urlopen(url, timeout=self._timeout) as resp:
            return resp.read()

    @staticmethod
    def _raise_for_status(status_code: int, body: dict[str, Any]) -> None:
        message = body.get("error", f"HTTP {status_code}")

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
