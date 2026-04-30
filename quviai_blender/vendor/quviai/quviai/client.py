from __future__ import annotations

from pathlib import Path
from typing import Callable

from .auth import APIKeyAuth
from .exceptions import QuviError
from .http import BASE_URL, HTTPClient
from .models import GenerateResult, TaskStatus
from .polling import JobPoller
from .utils import base64_to_bytes, bytes_to_base64, image_to_base64, normalize_result


class QuviClient:
    """Official QUVIAI Python SDK client.

    Usage::

        client = QuviClient(api_key="quvi_...")

        # Submit + wait (blocking)
        result = client.generate_from_image("shot.png", h_angle=63, v_angle=29, zoom=5.0)
        image_bytes = client.download_result(result)

        # Or: submit now, poll later
        task_id = client.submit_image("shot.png", h_angle=45, v_angle=30, zoom=4.0)
        result = client.poll_task(task_id)
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = BASE_URL,
        timeout: int = 30,
        poll_interval: float = 3.0,
        poll_timeout: float = 120.0,
    ) -> None:
        auth = APIKeyAuth(api_key)
        self._http = HTTPClient(
            auth_headers=auth.headers(),
            base_url=base_url,
            timeout=timeout,
        )
        self._poll_interval = poll_interval
        self._poll_timeout = poll_timeout

    # ------------------------------------------------------------------
    # High-level API
    # ------------------------------------------------------------------

    def generate_from_image(
        self,
        image: str | Path | bytes,
        h_angle: int = 63,
        v_angle: int = 29,
        zoom: float = 5.0,
        on_status: Callable[[TaskStatus], None] | None = None,
    ) -> GenerateResult:
        """Submit an image and block until the AI render is ready.

        Args:
            image: File path (str/Path) or raw PNG bytes.
            h_angle: Horizontal camera angle (0–360).
            v_angle: Vertical camera angle (-90–90).
            zoom: Zoom level (float, typically 1.0–20.0).
            on_status: Optional callback invoked on each poll with a TaskStatus.

        Returns:
            GenerateResult with either ``url`` or ``image_data`` populated.
        """
        task_id = self.submit_image(image, h_angle=h_angle, v_angle=v_angle, zoom=zoom)
        return self.poll_task(task_id, on_status=on_status)

    def submit_image(
        self,
        image: str | Path | bytes,
        h_angle: int = 63,
        v_angle: int = 29,
        zoom: float = 5.0,
    ) -> str:
        """Submit an image for rendering and return the task_id immediately."""
        b64 = self._encode(image)
        response = self._http.post("/api/multi-angle/", {
            "image": b64,
            "hAngle": h_angle,
            "vAngle": v_angle,
            "zoom": zoom,
        })
        return response["task_id"]

    def poll_task(
        self,
        task_id: str,
        on_status: Callable[[TaskStatus], None] | None = None,
    ) -> GenerateResult:
        """Poll a previously submitted task until it completes."""
        poller = JobPoller(
            http_client=self._http,
            interval=self._poll_interval,
            timeout=self._poll_timeout,
            on_status=on_status,
        )
        result = poller.poll(task_id)
        return self._parse_result(task_id, result)

    def download_result(self, result: GenerateResult) -> bytes:
        """Return raw image bytes from a GenerateResult.

        If image_data is already present (base64 response), returns it directly.
        If only url is present (S3 URL), fetches and returns the bytes.
        """
        if result.image_data is not None:
            return result.image_data
        if result.url:
            return self._http.get_bytes(result.url)
        raise QuviError("GenerateResult has neither image_data nor url")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _encode(image: str | Path | bytes) -> str:
        if isinstance(image, bytes):
            return bytes_to_base64(image)
        return image_to_base64(image)

    @staticmethod
    def _parse_result(task_id: str, result: dict) -> GenerateResult:
        outputs = normalize_result(result)
        if not outputs:
            raise QuviError(f"Task {task_id} completed but result payload is empty")
        first = outputs[0]
        if first.startswith(("http://", "https://")):
            return GenerateResult(task_id=task_id, url=first)
        return GenerateResult(task_id=task_id, image_data=base64_to_bytes(first))
