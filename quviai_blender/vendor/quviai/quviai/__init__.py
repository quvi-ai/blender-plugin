"""QUVIAI Python SDK — official client for the QUVIAI AI rendering API."""

from .client import QuviClient
from .exceptions import (
    AuthError,
    ContentModerationError,
    InsufficientCreditsError,
    QuviError,
    RateLimitError,
    TaskFailedError,
    TaskNotFoundError,
    TaskTimeoutError,
)
from .models import GenerateResult, TaskStatus

__version__ = "0.1.0"

__all__ = [
    "QuviClient",
    # exceptions
    "QuviError",
    "AuthError",
    "RateLimitError",
    "ContentModerationError",
    "InsufficientCreditsError",
    "TaskFailedError",
    "TaskTimeoutError",
    "TaskNotFoundError",
    # models
    "GenerateResult",
    "TaskStatus",
]
