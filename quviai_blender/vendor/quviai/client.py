from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

from .auth import JWTAuth
from .exceptions import AuthError, LoginError, QuviError
from .http import BASE_URL, HTTPClient
from .models import GenerateResult, TaskStatus, UserInfo
from .polling import JobPoller
from .utils import base64_to_bytes, bytes_to_base64, image_to_base64, normalize_result


class QuviClient:
    """Official QUVIAI Python SDK client.

    Do not instantiate directly — use the class-method constructors::

        # Email / password
        client = QuviClient.login("you@example.com", "password")

        # Existing tokens (e.g. stored from a previous session)
        client = QuviClient.from_tokens(access_token, refresh_token)

        # Google OAuth (exchange server-auth-code obtained externally)
        client = QuviClient.login_with_google(auth_code, redirect_uri)

        # Apple Sign In
        client = QuviClient.login_with_apple(identity_token=token)
    """

    def __init__(
        self,
        *,
        auth: JWTAuth,
        base_url: str = BASE_URL,
        timeout: int = 120,
        poll_interval: float = 3.0,
        poll_timeout: float = 120.0,
    ) -> None:
        self._auth = auth
        self._http = HTTPClient(auth=auth, base_url=base_url, timeout=timeout)
        self._poll_interval = poll_interval
        self._poll_timeout = poll_timeout
        self._last_credit: int | None = None  # updated from API responses

    # ------------------------------------------------------------------
    # Auth: class-method constructors
    # ------------------------------------------------------------------

    @classmethod
    def login(
        cls,
        email: str,
        password: str,
        base_url: str = BASE_URL,
        client_key: str | None = None,
        **kwargs,
    ) -> "QuviClient":
        """Log in with email and password, return an authenticated client."""
        data = cls._unauthenticated_post(
            f"{base_url.rstrip('/')}/auth/jwt/create/",
            {"email": email, "password": password},
            client_key=client_key,
        )
        auth = JWTAuth(
            access_token=data["access"],
            refresh_token=data.get("refresh"),
            client_key=client_key,
        )
        return cls(auth=auth, base_url=base_url, **kwargs)

    @classmethod
    def from_tokens(
        cls,
        access_token: str,
        refresh_token: str | None = None,
        base_url: str = BASE_URL,
        client_key: str | None = None,
        **kwargs,
    ) -> "QuviClient":
        """Create a client from previously stored JWT tokens."""
        auth = JWTAuth(
            access_token=access_token,
            refresh_token=refresh_token,
            client_key=client_key,
        )
        return cls(auth=auth, base_url=base_url, **kwargs)

    @classmethod
    def login_with_google(
        cls,
        auth_code: str,
        redirect_uri: str,
        client_type: str = "android",
        base_url: str = BASE_URL,
        client_key: str | None = None,
        **kwargs,
    ) -> "QuviClient":
        """Exchange a Google serverAuthCode for QUVIAI JWT tokens.

        The ``auth_code`` must be obtained from a standard OAuth2 browser flow.
        ``redirect_uri`` must match exactly what was used when initiating the flow.
        """
        data = cls._unauthenticated_post(
            f"{base_url.rstrip('/')}/api/auth/google/native/",
            {"code": auth_code, "redirect_uri": redirect_uri, "client_type": client_type},
            client_key=client_key,
        )
        auth = JWTAuth(
            access_token=data["access"],
            refresh_token=data.get("refresh"),
            client_key=client_key,
        )
        return cls(auth=auth, base_url=base_url, **kwargs)

    @classmethod
    def login_with_apple(
        cls,
        identity_token: str | None = None,
        authorization_code: str | None = None,
        base_url: str = BASE_URL,
        client_key: str | None = None,
        **kwargs,
    ) -> "QuviClient":
        """Exchange an Apple Sign In token for QUVIAI JWT tokens.

        Pass ``identity_token`` for iOS native flows, or ``authorization_code``
        for web/Android flows. Exactly one must be provided.
        """
        if not identity_token and not authorization_code:
            raise ValueError("Provide either identity_token (iOS) or authorization_code (web/Android).")
        body: dict = {}
        if identity_token:
            body["identity_token"] = identity_token
        if authorization_code:
            body["authorization_code"] = authorization_code
        data = cls._unauthenticated_post(
            f"{base_url.rstrip('/')}/api/auth/apple/native/",
            body,
            client_key=client_key,
        )
        auth = JWTAuth(
            access_token=data["access"],
            refresh_token=data.get("refresh"),
            client_key=client_key,
        )
        return cls(auth=auth, base_url=base_url, **kwargs)

    # ------------------------------------------------------------------
    # Token access (for persistence between sessions)
    # ------------------------------------------------------------------

    @property
    def access_token(self) -> str:
        return self._auth.access_token

    @property
    def refresh_token(self) -> str | None:
        return self._auth.refresh_token

    # ------------------------------------------------------------------
    # Generation endpoints
    # ------------------------------------------------------------------

    def render_3d(
        self,
        prompt: str,
        style: str = "no style",
        day_time: str | None = None,
        weather: str | None = None,
        render_type: str | None = None,
        image: str | Path | bytes | None = None,
        ref_image: str | Path | bytes | None = None,
        on_status: Callable[[TaskStatus], None] | None = None,
    ) -> GenerateResult:
        """Submit a 3D render request and block until complete.

        Args:
            prompt: Text description of the scene to render.
            style: Architectural/artistic style (e.g. "Modern", "Art Deco").
            day_time: "day" or "night".
            weather: "sunny", "cloudy", "rainy", "snowy", "windy", or "foggy".
            render_type: "site", "exterior", "interior", or other.
            image: Optional canvas/reference image (path or bytes).
            ref_image: Optional secondary reference image.
            on_status: Callback invoked on each poll with a TaskStatus.

        Returns:
            GenerateResult with either ``url`` or ``image_data`` populated.
        """
        task_id = self.submit_render_3d(
            prompt=prompt,
            style=style,
            day_time=day_time,
            weather=weather,
            render_type=render_type,
            image=image,
            ref_image=ref_image,
        )
        return self.poll_task(task_id, on_status=on_status)

    def submit_render_3d(
        self,
        prompt: str,
        style: str = "no style",
        day_time: str | None = None,
        weather: str | None = None,
        render_type: str | None = None,
        image: str | Path | bytes | None = None,
        ref_image: str | Path | bytes | None = None,
    ) -> str:
        """Submit a 3D render and return the task_id without waiting."""
        body: dict = {"prompt": prompt, "style": style}
        if day_time:
            body["dayTime"] = day_time
        if weather:
            body["weather"] = weather
        if render_type:
            body["renderType"] = render_type
        if image is not None:
            body["image"] = self._encode(image)
        if ref_image is not None:
            body["ref_image"] = self._encode(ref_image)
        resp = self._http.post("/api/render-td/", body)
        if resp.get("credit") is not None:
            self._last_credit = int(resp["credit"])
        return resp["task_id"]

    def generate_canvas(
        self,
        image: str | Path | bytes,
        prompt: str = "",
        is_sketch: bool = False,
        on_status: Callable[[TaskStatus], None] | None = None,
    ) -> GenerateResult:
        """Submit a canvas image for AI generation/editing and block until complete.

        Args:
            image: The canvas image to use as input (path or bytes).
            prompt: Optional text prompt to guide the generation.
            is_sketch: If True, treats the image as a sketch and recomposes it.
            on_status: Callback invoked on each poll with a TaskStatus.

        Returns:
            GenerateResult with either ``url`` or ``image_data`` populated.
        """
        task_id = self.submit_canvas(image=image, prompt=prompt, is_sketch=is_sketch)
        return self.poll_task(task_id, on_status=on_status)

    def submit_canvas(
        self,
        image: str | Path | bytes,
        prompt: str = "",
        is_sketch: bool = False,
    ) -> str:
        """Submit a canvas generation and return the task_id without waiting."""
        body: dict = {
            "image": self._encode(image),
            "prompt": prompt,
            "isSketch": 1 if is_sketch else 0,
        }
        resp = self._http.post("/api/generate-canvas-react/", body)
        return resp["task_id"]

    def generate_image(
        self,
        prompt: str,
        style: str = "no style",
        width: int = 1024,
        height: int = 1024,
        on_status: Callable[[TaskStatus], None] | None = None,
    ) -> GenerateResult:
        """Generate an image from a text prompt and block until complete."""
        task_id = self.submit_generate_image(prompt=prompt, style=style, width=width, height=height)
        return self.poll_task(task_id, on_status=on_status)

    def submit_generate_image(
        self,
        prompt: str,
        style: str = "no style",
        width: int = 1024,
        height: int = 1024,
    ) -> str:
        """Submit a text-to-image request and return the task_id without waiting."""
        resp = self._http.post("/api/generate-image/", {
            "prompt": prompt,
            "style": style,
            "width": width,
            "height": height,
        })
        return resp["task_id"]

    def remove_background(
        self,
        image: str | Path | bytes,
        on_status: Callable[[TaskStatus], None] | None = None,
    ) -> GenerateResult:
        """Remove the background from an image (free operation)."""
        task_id = self.submit_remove_background(image)
        return self.poll_task(task_id, on_status=on_status)

    def submit_remove_background(self, image: str | Path | bytes) -> str:
        """Submit a background-removal request and return the task_id."""
        resp = self._http.post("/api/remove-background/", {"image": self._encode(image)})
        return resp["task_id"]

    # ------------------------------------------------------------------
    # Polling & downloading
    # ------------------------------------------------------------------

    def poll_task(
        self,
        task_id: str,
        on_status: Callable[[TaskStatus], None] | None = None,
    ) -> GenerateResult:
        """Poll a previously submitted task until it completes."""
        # Use a short per-request timeout for status checks — the endpoint
        # should always respond in < 5s. A long timeout here blocks the thread
        # for minutes if the connection stalls, making the UI appear frozen.
        poll_http = HTTPClient(
            auth=self._auth,
            base_url=self._http._base_url,
            timeout=15,
        )
        poller = JobPoller(
            http_client=poll_http,
            interval=self._poll_interval,
            timeout=self._poll_timeout,
            on_status=on_status,
        )
        result = poller.poll(task_id)
        return self._parse_result(task_id, result)

    def get_user_data(self) -> dict:
        """Fetch current user data including credit balance from /api/user-data/."""
        return self._http.get("/api/user-data/")

    def get_credits(self) -> int:
        """Return the current credit balance, or -1 on failure."""
        try:
            return int(self.get_user_data().get("credit", -1))
        except Exception:
            return -1

    def download_result(self, result: GenerateResult) -> bytes:
        """Return raw image bytes from a GenerateResult.

        Returns ``image_data`` directly if already present (base64 response),
        otherwise fetches from the S3 URL.
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
        if isinstance(image, Path):
            return image_to_base64(image)
        try:
            if Path(image).is_file():
                return image_to_base64(image)
        except OSError:
            pass  # path too long or invalid — treat as pre-encoded base64
        return str(image)

    @staticmethod
    def _parse_result(task_id: str, result: dict) -> GenerateResult:
        outputs = normalize_result(result)
        if not outputs:
            raise QuviError(f"Task {task_id} completed but result payload is empty")
        first = outputs[0]
        try:
            with open("/tmp/quviai_debug.txt", "a") as _f:
                _f.write(f"parse_result type={type(result).__name__} first_50={repr(first[:50])}\n")
        except Exception:
            pass
        if first.startswith(("http://", "https://", "//")):
            return GenerateResult(task_id=task_id, url=first)
        return GenerateResult(task_id=task_id, image_data=base64_to_bytes(first))

    @staticmethod
    def _unauthenticated_post(url: str, body: dict, client_key: str | None = None) -> dict:
        """POST without user auth headers — used only for login endpoints."""
        data = json.dumps(body).encode()
        headers: dict[str, str] = {"Content-Type": "application/json", "Accept": "application/json"}
        if client_key:
            headers["X-API-Key"] = client_key
        req = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            try:
                error_body = json.loads(exc.read())
            except Exception:
                error_body = {}
            detail = (
                error_body.get("detail")
                or error_body.get("error")
                or error_body.get("non_field_errors", ["Login failed"])[0]
            )
            raise LoginError(str(detail), status_code=exc.code) from exc
