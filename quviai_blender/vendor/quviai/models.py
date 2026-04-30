from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TaskStatus:
    """Status snapshot returned on each poll iteration."""

    task_id: str
    status: str  # queued | processing | completed | failed
    position: int = 0
    queue_position: int = 0
    eta_seconds: int | None = None
    eta_formatted: str | None = None


@dataclass
class GenerateResult:
    """Result of a completed generation task."""

    task_id: str
    url: str | None = None           # S3 signed URL (valid ~1 hour)
    image_data: bytes | None = None  # raw bytes when API returns base64


@dataclass
class UserInfo:
    """Basic account information returned after login."""

    id: int
    email: str
    username: str
    credit: int
    is_sub: int
    access_token: str
    refresh_token: str
    extra: dict = field(default_factory=dict)  # remaining fields from the API
