from __future__ import annotations

import os


class APIKeyAuth:
    """Provides the X-API-Key header required by the QUVIAI API."""

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("QUVI_API_KEY")
        if not key:
            raise ValueError(
                "API key is required. Pass api_key= to QuviClient or set the "
                "QUVI_API_KEY environment variable."
            )
        self._key = key

    def headers(self) -> dict[str, str]:
        return {"X-API-Key": self._key}
