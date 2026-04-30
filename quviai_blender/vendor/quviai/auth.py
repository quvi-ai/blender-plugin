from __future__ import annotations


class JWTAuth:
    """JWT Bearer token authentication with automatic refresh support."""

    def __init__(self, access_token: str, refresh_token: str | None = None) -> None:
        self._access = access_token
        self._refresh = refresh_token

    @property
    def access_token(self) -> str:
        return self._access

    @property
    def refresh_token(self) -> str | None:
        return self._refresh

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access}"}

    def update(self, access: str, refresh: str | None = None) -> None:
        """Update stored tokens after a refresh or re-login."""
        self._access = access
        if refresh:
            self._refresh = refresh
