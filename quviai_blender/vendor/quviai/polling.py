from __future__ import annotations

import http.client
import socket
import time
import urllib.error
from typing import Callable

from .exceptions import TaskFailedError, TaskTimeoutError
from .models import TaskStatus

# How many consecutive network errors to tolerate before giving up.
# When Blender moves to the background the OS may reset open sockets;
# we need enough retries to survive that and reestablish the connection.
_MAX_NETWORK_RETRIES = 10

# Exceptions that indicate a transient network problem worth retrying.
# All are subclasses of OSError; listed explicitly for clarity.
_TRANSIENT = (
    TimeoutError,           # includes socket.timeout on Python 3.3+
    ConnectionResetError,
    ConnectionAbortedError,
    ConnectionRefusedError,
    BrokenPipeError,
    http.client.RemoteDisconnected,
    http.client.IncompleteRead,
    http.client.HTTPException,
)


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
        network_retries = 0

        while time.monotonic() < deadline:
            try:
                response = self._http.post(
                    "/api/check-queue-status/", {"task_id": task_id}
                )
                network_retries = 0  # reset on any successful response
            except _TRANSIENT as exc:
                network_retries += 1
                if network_retries > _MAX_NETWORK_RETRIES:
                    raise
                time.sleep(self._interval)
                continue
            except urllib.error.URLError as exc:
                # URLError wraps OS-level network errors in its .reason field
                if isinstance(getattr(exc, "reason", None), OSError):
                    network_retries += 1
                    if network_retries > _MAX_NETWORK_RETRIES:
                        raise
                    time.sleep(self._interval)
                    continue
                raise

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
