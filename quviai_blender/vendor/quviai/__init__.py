"""QUVIAI Python SDK — official client for the QUVIAI AI rendering API."""

from .auth import JWTAuth
from .client import QuviClient
from .exceptions import (
    AuthError,
    ContentModerationError,
    InsufficientCreditsError,
    LoginError,
    QuviError,
    RateLimitError,
    TaskFailedError,
    TaskNotFoundError,
    TaskTimeoutError,
    TokenExpiredError,
)
from .models import GenerateResult, TaskStatus, UserInfo

__version__ = "0.2.0"

__all__ = [
    "QuviClient",
    "JWTAuth",
    # exceptions
    "QuviError",
    "AuthError",
    "LoginError",
    "TokenExpiredError",
    "RateLimitError",
    "ContentModerationError",
    "InsufficientCreditsError",
    "TaskFailedError",
    "TaskTimeoutError",
    "TaskNotFoundError",
    # models
    "GenerateResult",
    "TaskStatus",
    "UserInfo",
]
