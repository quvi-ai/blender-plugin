from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TaskStatus:
    """Status snapshot returned by each poll iteration."""

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
    url: str | None = None          # S3 signed URL (valid ~1 hour)
    image_data: bytes | None = None  # raw PNG bytes when API returns base64
