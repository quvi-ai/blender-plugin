from __future__ import annotations


class JWTAuth:
    """JWT Bearer token authentication with automatic refresh support.

    ``client_key`` is an optional application-level API key sent as
    ``X-API-Key`` on every request to identify the client application
    (web, mobile, Blender plugin, etc.) at the CORS middleware layer.
    It is separate from user authentication and does not grant any
    user-level permissions on its own.
    """

    def __init__(
        self,
        access_token: str,
        refresh_token: str | None = None,
        client_key: str | None = None,
    ) -> None:
        self._access = access_token
        self._refresh = refresh_token
        self._client_key = client_key

    @property
    def access_token(self) -> str:
        return self._access

    @property
    def refresh_token(self) -> str | None:
        return self._refresh

    def headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Authorization": f"Bearer {self._access}"}
        if self._client_key:
            h["X-API-Key"] = self._client_key
        return h

    def update(self, access: str, refresh: str | None = None) -> None:
        """Update stored tokens after a refresh or re-login."""
        self._access = access
        if refresh:
            self._refresh = refresh
