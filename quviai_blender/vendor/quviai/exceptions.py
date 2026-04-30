from __future__ import annotations


class QuviError(Exception):
    """Base exception for all QUVIAI SDK errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthError(QuviError):
    """Raised on 401/403 — invalid or expired credentials."""


class LoginError(QuviError):
    """Raised when login fails (wrong password, inactive account, etc.)."""


class TokenExpiredError(AuthError):
    """Raised when the access token is expired and refresh also failed."""


class RateLimitError(QuviError):
    """Raised on 429 — concurrent task limit reached for the subscription tier."""


class ContentModerationError(QuviError):
    """Raised when the prompt or image is blocked by content moderation."""

    def __init__(self, message: str, reason: str = "", category: str = "") -> None:
        super().__init__(message, status_code=400)
        self.reason = reason
        self.category = category


class InsufficientCreditsError(QuviError):
    """Raised when the account has insufficient credits."""


class TaskFailedError(QuviError):
    """Raised when a generation task finishes with status 'failed'."""

    def __init__(self, message: str, task_id: str = "") -> None:
        super().__init__(message)
        self.task_id = task_id


class TaskTimeoutError(QuviError):
    """Raised when polling exceeds the configured timeout."""

    def __init__(self, task_id: str, timeout: int) -> None:
        super().__init__(f"Task {task_id} did not complete within {timeout}s")
        self.task_id = task_id
        self.timeout = timeout


class TaskNotFoundError(QuviError):
    """Raised on 404 — task not found (results kept ~15 minutes after completion)."""

    def __init__(self, message: str = "", task_id: str = "") -> None:
        super().__init__(message or "Task not found (may have expired)", status_code=404)
        self.task_id = task_id
