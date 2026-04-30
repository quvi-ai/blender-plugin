from __future__ import annotations

import threading
import webbrowser

import bpy
from bpy.types import Operator

from .constants import CLIENT_KEY, GOOGLE_CLIENT_ID, GOOGLE_OAUTH_PORT
from .properties import STYLE_TO_API
from .utils import (
    capture_viewport,
    ensure_vendor_in_path,
    get_preferences,
    load_image_into_blender,
    open_in_image_editor,
)

RESULT_IMAGE_NAME = "QUVIAI_Result.png"


# ---------------------------------------------------------------------------
# Auth operators
# ---------------------------------------------------------------------------

class QUVIAI_OT_login_email(Operator):
    """Log in to QUVIAI with email and password"""

    bl_idname = "quviai.login_email"
    bl_label = "Log In to QUVIAI"
    bl_options = {"REGISTER"}

    def execute(self, context: bpy.types.Context):
        prefs = get_preferences(context)

        if not prefs.email or not prefs.password:
            self.report({"ERROR"}, "Enter your email and password first.")
            return {"CANCELLED"}

        ensure_vendor_in_path()
        try:
            from quviai import QuviClient, LoginError
        except ImportError:
            self.report({"ERROR"}, "SDK missing. Run scripts/update_vendor.sh.")
            return {"CANCELLED"}

        try:
            client = QuviClient.login(
                prefs.email,
                prefs.password,
                base_url=prefs.base_url,
                client_key=CLIENT_KEY,
            )
            prefs.access_token = client.access_token
            prefs.refresh_token = client.refresh_token or ""
            prefs.password = ""  # clear password from memory after login
            self.report({"INFO"}, "Logged in successfully.")
            return {"FINISHED"}
        except LoginError as exc:
            self.report({"ERROR"}, f"Login failed: {exc}")
            return {"CANCELLED"}
        except Exception as exc:
            self.report({"ERROR"}, f"Unexpected error: {exc}")
            return {"CANCELLED"}


class QUVIAI_OT_login_google(Operator):
    """Log in to QUVIAI with Google (opens browser, handles callback automatically)"""

    bl_idname = "quviai.login_google"
    bl_label = "Log In with Google"
    bl_options = {"REGISTER"}

    def execute(self, context: bpy.types.Context):
        prefs = get_preferences(context)
        ensure_vendor_in_path()
        try:
            from quviai import QuviClient, LoginError
        except ImportError:
            self.report({"ERROR"}, "SDK missing. Run scripts/update_vendor.sh.")
            return {"CANCELLED"}

        redirect_uri = f"http://localhost:{GOOGLE_OAUTH_PORT}"
        auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={GOOGLE_CLIENT_ID}"
            f"&redirect_uri={redirect_uri}"
            "&response_type=code"
            "&scope=email%20profile"
            "&access_type=offline"
        )

        webbrowser.open(auth_url)
        self.report({"INFO"}, "Browser opened — waiting for Google login…")

        # Run the local callback server in a background thread
        thread = threading.Thread(
            target=self._wait_for_callback,
            args=(prefs, redirect_uri),
            daemon=True,
        )
        thread.start()
        return {"FINISHED"}

    def _wait_for_callback(self, prefs, redirect_uri: str) -> None:
        import urllib.parse
        from http.server import BaseHTTPRequestHandler, HTTPServer

        received: dict = {}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                received["code"] = params.get("code", [None])[0]
                received["error"] = params.get("error", [None])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    b"<h2>Login successful! You can close this tab and return to Blender.</h2>"
                )

            def log_message(self, *args):
                pass  # suppress server log output

        server = HTTPServer(("localhost", GOOGLE_OAUTH_PORT), Handler)
        server.timeout = 120  # wait up to 2 minutes for the user to log in
        server.handle_request()
        server.server_close()

        code = received.get("code")
        error = received.get("error")

        if error or not code:
            bpy.app.timers.register(
                lambda: self._set_error(prefs, f"Google login failed: {error or 'no code received'}")
            )
            return

        ensure_vendor_in_path()
        try:
            from quviai import QuviClient, LoginError
            client = QuviClient.login_with_google(
                auth_code=code,
                redirect_uri=redirect_uri,
                client_type="android",
                base_url=prefs.base_url,
                client_key=CLIENT_KEY,
            )
            bpy.app.timers.register(
                lambda: self._save_tokens(prefs, client.access_token, client.refresh_token)
            )
        except Exception as exc:
            bpy.app.timers.register(
                lambda: self._set_error(prefs, str(exc))
            )

    @staticmethod
    def _save_tokens(prefs, access: str, refresh: str | None):
        prefs.access_token = access
        prefs.refresh_token = refresh or ""
        return None

    @staticmethod
    def _set_error(prefs, message: str):
        # Can't call self.report from a timer — use print as fallback
        print(f"QUVIAI Google login error: {message}")
        return None


class QUVIAI_OT_logout(Operator):
    """Clear stored QUVIAI login tokens"""

    bl_idname = "quviai.logout"
    bl_label = "Log Out from QUVIAI"
    bl_options = {"REGISTER"}

    def execute(self, context: bpy.types.Context):
        prefs = get_preferences(context)
        prefs.access_token = ""
        prefs.refresh_token = ""
        self.report({"INFO"}, "Logged out.")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Render operators
# ---------------------------------------------------------------------------

class QUVIAI_OT_render(Operator):
    """Capture the 3D Viewport and render it with QUVIAI"""

    bl_idname = "quviai.render"
    bl_label = "Render with QUVIAI"
    bl_options = {"REGISTER"}

    def execute(self, context: bpy.types.Context):
        prefs = get_preferences(context)
        props = context.scene.quviai

        if not prefs.access_token:
            self.report({"ERROR"}, "Not logged in. Go to Edit > Preferences > Add-ons > QUVIAI Render.")
            return {"CANCELLED"}

        if props.is_rendering:
            self.report({"WARNING"}, "A render is already in progress.")
            return {"CANCELLED"}

        try:
            image_b64 = capture_viewport(context)
        except Exception as exc:
            self.report({"ERROR"}, f"Viewport capture failed: {exc}")
            return {"CANCELLED"}

        # Snapshot all mutable UI state before handing off to the background thread
        params = {
            "prompt":      props.prompt,
            "style":       STYLE_TO_API.get(props.style, "no style"),
            "render_type": None if props.render_type == "NONE" else props.render_type,
            "day_time":    None if props.day_time    == "NONE" else props.day_time,
            "weather":     None if props.weather     == "NONE" else props.weather,
        }

        props.is_rendering = True
        props.progress = 0.0
        props.status = "Submitting to QUVIAI..."
        props.result_image_name = ""

        thread = threading.Thread(
            target=self._run_in_thread,
            args=(prefs, props, image_b64, params),
            daemon=True,
        )
        thread.start()
        return {"FINISHED"}

    def _run_in_thread(self, prefs, props, image_b64: str, params: dict) -> None:
        ensure_vendor_in_path()
        try:
            from quviai import QuviClient, TokenExpiredError
        except ImportError:
            bpy.app.timers.register(
                lambda: self._finish(props, error="SDK missing. Run scripts/update_vendor.sh.")
            )
            return

        try:
            client = QuviClient.from_tokens(
                access_token=prefs.access_token,
                refresh_token=prefs.refresh_token or None,
                base_url=prefs.base_url,
                client_key=CLIENT_KEY,
                poll_interval=prefs.poll_interval,
                poll_timeout=prefs.poll_timeout,
            )

            def on_status(status):
                parts = []
                if status.queue_position:
                    parts.append(f"Queue: {status.queue_position}")
                if status.eta_formatted and status.eta_formatted not in ("Completed", ""):
                    parts.append(f"ETA: {status.eta_formatted}")
                msg = " · ".join(parts) if parts else "Processing…"
                pct = status.progress_percentage
                bpy.app.timers.register(lambda: self._set_progress(props, msg, pct))

            result = client.render_3d(
                prompt=params["prompt"],
                style=params["style"],
                day_time=params["day_time"],
                weather=params["weather"],
                render_type=params["render_type"],
                image=image_b64,
                on_status=on_status,
            )

            if client.access_token != prefs.access_token:
                bpy.app.timers.register(
                    lambda: self._save_tokens(prefs, client.access_token, client.refresh_token)
                )

            final_bytes = client.download_result(result)
            bpy.app.timers.register(lambda: self._finish(props, image_bytes=final_bytes))

        except TokenExpiredError:
            bpy.app.timers.register(lambda: self._clear_tokens(prefs))
            bpy.app.timers.register(
                lambda: self._finish(props, error="Session expired. Please log in again.")
            )
        except Exception as exc:
            import traceback
            try:
                with open("/tmp/quviai_error.txt", "w") as _f:
                    _f.write(traceback.format_exc())
            except Exception:
                pass
            err_msg = str(exc)
            bpy.app.timers.register(lambda: self._finish(props, error=err_msg))

    @staticmethod
    def _set_progress(props, message: str, pct: float | None):
        props.status = message
        if pct is not None:
            props.progress = float(pct)
        return None

    @staticmethod
    def _save_tokens(prefs, access: str, refresh: str | None):
        prefs.access_token = access
        if refresh:
            prefs.refresh_token = refresh
        return None

    @staticmethod
    def _clear_tokens(prefs):
        prefs.access_token = ""
        prefs.refresh_token = ""
        return None

    @staticmethod
    def _finish(props, image_bytes: bytes | None = None, error: str | None = None):
        props.is_rendering = False
        if error:
            props.status = f"Error: {error}"
            return None
        if image_bytes:
            img = load_image_into_blender(RESULT_IMAGE_NAME, image_bytes)
            props.result_image_name = img.name
            opened = open_in_image_editor(bpy.context, img)
            props.status = "Done." if opened else "Done — open an Image Editor to view the result."
        return None


class QUVIAI_OT_cancel(Operator):
    """Cancel the running QUVIAI render (stops polling; task may still run on server)"""

    bl_idname = "quviai.cancel"
    bl_label = "Cancel"
    bl_options = {"REGISTER"}

    def execute(self, context: bpy.types.Context):
        props = context.scene.quviai
        props.is_rendering = False
        props.status = "Cancelled."
        return {"FINISHED"}


class QUVIAI_OT_open_result(Operator):
    """Open the last QUVIAI result in the Image Editor"""

    bl_idname = "quviai.open_result"
    bl_label = "Open in Image Editor"

    def execute(self, context: bpy.types.Context):
        props = context.scene.quviai
        name = props.result_image_name

        if not name or name not in bpy.data.images:
            self.report({"WARNING"}, "No result image available.")
            return {"CANCELLED"}

        found = open_in_image_editor(context, bpy.data.images[name])
        if not found:
            self.report(
                {"INFO"},
                f"Image '{name}' is in bpy.data.images — open an Image Editor to view it.",
            )
        return {"FINISHED"}


def register() -> None:
    bpy.utils.register_class(QUVIAI_OT_login_email)
    bpy.utils.register_class(QUVIAI_OT_login_google)
    bpy.utils.register_class(QUVIAI_OT_logout)
    bpy.utils.register_class(QUVIAI_OT_render)
    bpy.utils.register_class(QUVIAI_OT_cancel)
    bpy.utils.register_class(QUVIAI_OT_open_result)


def unregister() -> None:
    bpy.utils.unregister_class(QUVIAI_OT_open_result)
    bpy.utils.unregister_class(QUVIAI_OT_cancel)
    bpy.utils.unregister_class(QUVIAI_OT_render)
    bpy.utils.unregister_class(QUVIAI_OT_logout)
    bpy.utils.unregister_class(QUVIAI_OT_login_google)
    bpy.utils.unregister_class(QUVIAI_OT_login_email)
