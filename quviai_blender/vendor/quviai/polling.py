from __future__ import annotations

import time
from typing import Callable

from .exceptions import TaskFailedError, TaskTimeoutError
from .models import TaskStatus


class JobPoller:
    """Polls /api/check-queue-status/ until a task completes, fails, or times out."""

    def __init__(
        self,
        http_client: object,
        interval: float = 2.0,
        timeout: float = 900.0,
        on_status: Callable[[TaskStatus], None] | None = None,
    ) -> None:
        self._http = http_client
        self._interval = interval
        self._timeout = timeout
        self._on_status = on_status

    def poll(self, task_id: str) -> dict:
        """Block until task completes. Returns the result dict on success.

        Raises:
            TaskFailedError: Task finished with status 'failed'.
            TaskTimeoutError: Polling exceeded the configured timeout.
            TaskNotFoundError: 404 from the API (task expired or never existed).
        """
        deadline = time.monotonic() + self._timeout

        while time.monotonic() < deadline:
            response = self._http.post(
                "/api/check-queue-status/", {"task_id": task_id}
            )
            status = self._parse(task_id, response)

            if self._on_status:
                self._on_status(status)

            if status.status == "completed":
                return response.get("result") or {}

            if status.status == "failed":
                raise TaskFailedError(
                    response.get("error", "Task failed without a reason"),
                    task_id=task_id,
                )

            time.sleep(self._interval)

        raise TaskTimeoutError(task_id=task_id, timeout=int(self._timeout))

    @staticmethod
    def _parse(task_id: str, response: dict) -> TaskStatus:
        eta = response.get("eta") or {}
        return TaskStatus(
            task_id=task_id,
            status=response.get("status", "unknown"),
            position=response.get("position", 0),
            queue_position=response.get("queue_position", 0),
            eta_seconds=eta.get("eta_seconds"),
            eta_formatted=eta.get("eta_formatted"),
            progress_percentage=eta.get("progress_percentage"),
        )
