from __future__ import annotations

import os
import tempfile
import threading
import webbrowser
from pathlib import Path

import bpy
from bpy.types import Operator

from .constants import CLIENT_KEY, GOOGLE_CLIENT_ID, GOOGLE_OAUTH_PORT
from .properties import STYLE_TO_API
from .utils import (
    capture_viewport,
    ensure_vendor_in_path,
    get_preferences,
    image_file_to_base64,
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
                client_key=CLIENT_KEY,
            )
            prefs.access_token = client.access_token
            prefs.refresh_token = client.refresh_token or ""
            prefs.password = ""  # clear password from memory after login
            prefs.credits = -1   # reset until fetch completes
            self.report({"INFO"}, "Logged in successfully.")
            # Fetch credits in background so we don't block the UI
            threading.Thread(
                target=self._fetch_credits,
                args=(prefs,),
                daemon=True,
            ).start()
            return {"FINISHED"}
        except LoginError as exc:
            self.report({"ERROR"}, f"Login failed: {exc}")
            return {"CANCELLED"}
        except Exception as exc:
            self.report({"ERROR"}, f"Unexpected error: {exc}")
            return {"CANCELLED"}

    @staticmethod
    def _fetch_credits(prefs) -> None:
        ensure_vendor_in_path()
        try:
            from quviai import QuviClient
            client = QuviClient.from_tokens(
                access_token=prefs.access_token,
                refresh_token=prefs.refresh_token or None,
            )
            credits = client.get_credits()
            bpy.app.timers.register(lambda: _set_credits(prefs, credits))
        except Exception:
            pass


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
                pass

        server = HTTPServer(("localhost", GOOGLE_OAUTH_PORT), Handler)
        server.timeout = 120
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
                client_key=CLIENT_KEY,
            )
            bpy.app.timers.register(
                lambda: self._save_tokens(prefs, client.access_token, client.refresh_token)
            )
            credits = client.get_credits()
            bpy.app.timers.register(lambda: _set_credits(prefs, credits))
        except Exception as exc:
            bpy.app.timers.register(
                lambda: self._set_error(prefs, str(exc))
            )

    @staticmethod
    def _save_tokens(prefs, access: str, refresh: str | None):
        prefs.access_token = access
        prefs.refresh_token = refresh or ""
        prefs.credits = -1
        return None

    @staticmethod
    def _set_error(prefs, message: str):
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
        prefs.credits = -1
        self.report({"INFO"}, "Logged out.")
        return {"FINISHED"}


class QUVIAI_OT_refresh_credits(Operator):
    """Fetch the current credit balance from QUVIAI"""

    bl_idname = "quviai.refresh_credits"
    bl_label = "Refresh Credits"
    bl_options = {"REGISTER"}

    def execute(self, context: bpy.types.Context):
        prefs = get_preferences(context)
        if not prefs.access_token:
            self.report({"ERROR"}, "Not logged in.")
            return {"CANCELLED"}

        ensure_vendor_in_path()
        try:
            from quviai import QuviClient
        except ImportError:
            self.report({"ERROR"}, "SDK missing.")
            return {"CANCELLED"}

        try:
            client = QuviClient.from_tokens(
                access_token=prefs.access_token,
                refresh_token=prefs.refresh_token or None,
                client_key=CLIENT_KEY,
            )
            credits = client.get_credits()
            prefs.credits = credits
            if client.access_token != prefs.access_token:
                prefs.access_token = client.access_token
                if client.refresh_token:
                    prefs.refresh_token = client.refresh_token
            self.report({"INFO"}, f"Credits: {credits}")
            return {"FINISHED"}
        except Exception as exc:
            self.report({"ERROR"}, f"Failed to fetch credits: {exc}")
            return {"CANCELLED"}


# ---------------------------------------------------------------------------
# Prompt editor operator
# ---------------------------------------------------------------------------

class QUVIAI_OT_edit_prompt(Operator):
    """Edit a prompt string in a wide popup dialog"""

    bl_idname = "quviai.edit_prompt"
    bl_label = "Edit Prompt"
    bl_options = {"REGISTER", "UNDO"}

    target_prop: bpy.props.StringProperty(default="prompt")  # type: ignore[assignment]
    prompt: bpy.props.StringProperty(name="Prompt", default="")  # type: ignore[assignment]

    def invoke(self, context: bpy.types.Context, event):
        self.prompt = getattr(context.scene.quviai, self.target_prop, "")
        return context.window_manager.invoke_props_dialog(self, width=600)

    def draw(self, context: bpy.types.Context) -> None:
        self.layout.prop(self, "prompt", text="")

    def execute(self, context: bpy.types.Context):
        setattr(context.scene.quviai, self.target_prop, self.prompt)
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

        if props.style_category == "architectural":
            style_id = props.arch_style
            render_type = props.render_type
            day_time = props.day_time if render_type in ("exterior", "interior") else None
            weather  = props.weather  if render_type == "exterior" else None
        else:
            style_id = props.general_style
            render_type = None
            day_time    = None
            weather     = None

        params = {
            "prompt":      props.prompt,
            "style":       STYLE_TO_API.get(style_id, "no style"),
            "render_type": render_type,
            "day_time":    day_time,
            "weather":     weather,
        }

        props.is_rendering = True
        props.progress = 0.0
        props.status = "Submitting to QUVIAI..."
        props.result_image_name = ""

        import time as _time
        thread = threading.Thread(
            target=self._run_in_thread,
            args=(prefs, props, image_b64, params, _time.monotonic()),
            daemon=True,
        )
        thread.start()
        return {"FINISHED"}

    def _run_in_thread(self, prefs, props, image_b64: str, params: dict, start_time: float) -> None:
        ensure_vendor_in_path()
        try:
            from quviai import (
                QuviClient,
                TokenExpiredError,
                RateLimitError,
                InsufficientCreditsError,
                ContentModerationError,
            )
        except ImportError:
            bpy.app.timers.register(
                lambda: self._finish(props, error="SDK missing. Run scripts/update_vendor.sh.")
            )
            return

        try:
            client = QuviClient.from_tokens(
                access_token=prefs.access_token,
                refresh_token=prefs.refresh_token or None,
                client_key=CLIENT_KEY,
                poll_interval=2.0,
                poll_timeout=900.0,
            )

            def on_status(status):
                import time as _time
                elapsed = int(_time.monotonic() - start_time)
                parts = []
                if status.queue_position:
                    parts.append(f"Queue: {status.queue_position}")
                if status.eta_formatted and status.eta_formatted not in ("Completed", ""):
                    parts.append(f"ETA: {status.eta_formatted}")
                parts.append(f"{elapsed}s")
                msg = " · ".join(parts)
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

            if client._last_credit is not None:
                new_credit = client._last_credit
                bpy.app.timers.register(lambda: _set_credits(prefs, new_credit))

            final_bytes = client.download_result(result)
            bpy.app.timers.register(lambda: self._finish(props, image_bytes=final_bytes))

        except TokenExpiredError:
            bpy.app.timers.register(lambda: self._clear_tokens(prefs))
            bpy.app.timers.register(
                lambda: self._finish(props, error="Session expired. Please log in again.")
            )
        except InsufficientCreditsError:
            bpy.app.timers.register(
                lambda: self._finish(props, error="Insufficient credits. Visit quvi.ai to top up.")
            )
        except RateLimitError:
            bpy.app.timers.register(
                lambda: self._finish(props, error="Rate limit exceeded. Please wait a moment and try again.")
            )
        except ContentModerationError as exc:
            reason = exc.reason or exc.category or "prompt rejected by content policy"
            bpy.app.timers.register(
                lambda: self._finish(props, error=f"Content policy violation: {reason}")
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
        _tag_redraw()
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
            _tag_redraw()
            return None
        if image_bytes:
            img = load_image_into_blender(RESULT_IMAGE_NAME, image_bytes)
            props.result_image_name = img.name
            opened = open_in_image_editor(bpy.context, img)
            props.status = "Done." if opened else "Done — open an Image Editor to view the result."
        _tag_redraw()
        return None


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


# ---------------------------------------------------------------------------
# 3D Object generation operator
# ---------------------------------------------------------------------------

class QUVIAI_OT_generate_object(Operator):
    """Generate a 3D object from text or image and import it into the scene"""

    bl_idname = "quviai.generate_object"
    bl_label = "Generate 3D Object"
    bl_options = {"REGISTER"}

    def execute(self, context: bpy.types.Context):
        prefs = get_preferences(context)
        props = context.scene.quviai

        if not prefs.access_token:
            self.report({"ERROR"}, "Not logged in.")
            return {"CANCELLED"}

        if props.obj_is_generating:
            self.report({"WARNING"}, "Generation already in progress.")
            return {"CANCELLED"}

        if props.obj_mode == "prompt":
            if not props.obj_prompt.strip():
                self.report({"ERROR"}, "Enter a prompt first.")
                return {"CANCELLED"}
            image_b64 = None
            prompt = props.obj_prompt.strip()
        else:
            if not props.obj_image_path:
                self.report({"ERROR"}, "Select an image file first.")
                return {"CANCELLED"}
            try:
                image_b64 = image_file_to_base64(props.obj_image_path)
            except Exception as exc:
                self.report({"ERROR"}, f"Could not load image: {exc}")
                return {"CANCELLED"}
            prompt = ""

        props.obj_is_generating = True
        props.obj_progress = 0.0
        props.obj_status = "Submitting…"

        import time as _time
        thread = threading.Thread(
            target=self._run_in_thread,
            args=(prefs, props, prompt, image_b64, _time.monotonic()),
            daemon=True,
        )
        thread.start()
        return {"FINISHED"}

    def _run_in_thread(self, prefs, props, prompt: str, image_b64: str | None, start_time: float) -> None:
        ensure_vendor_in_path()
        try:
            from quviai import (
                QuviClient,
                TokenExpiredError,
                RateLimitError,
                InsufficientCreditsError,
                ContentModerationError,
            )
        except ImportError:
            bpy.app.timers.register(lambda: self._finish(props, error="SDK missing."))
            return

        try:
            client = QuviClient.from_tokens(
                access_token=prefs.access_token,
                refresh_token=prefs.refresh_token or None,
                client_key=CLIENT_KEY,
                poll_interval=2.0,
                poll_timeout=900.0,
            )

            def on_status(status):
                import time as _time
                elapsed = int(_time.monotonic() - start_time)
                parts = []
                if status.queue_position:
                    parts.append(f"Queue: {status.queue_position}")
                if status.eta_formatted and status.eta_formatted not in ("Completed", ""):
                    parts.append(f"ETA: {status.eta_formatted}")
                parts.append(f"{elapsed}s")
                msg = " · ".join(parts)
                pct = status.progress_percentage
                bpy.app.timers.register(lambda: self._set_progress(props, msg, pct))

            glb_bytes = client.generate_object_3d(
                prompt=prompt,
                image=image_b64,
                on_status=on_status,
            )

            if client.access_token != prefs.access_token:
                bpy.app.timers.register(
                    lambda: self._save_tokens(prefs, client.access_token, client.refresh_token)
                )
            if client._last_credit is not None:
                new_credit = client._last_credit
                bpy.app.timers.register(lambda: _set_credits(prefs, new_credit))

            bpy.app.timers.register(lambda: self._finish(props, glb_bytes=glb_bytes))

        except TokenExpiredError:
            bpy.app.timers.register(lambda: self._clear_tokens(prefs))
            bpy.app.timers.register(
                lambda: self._finish(props, error="Session expired. Please log in again.")
            )
        except InsufficientCreditsError:
            bpy.app.timers.register(
                lambda: self._finish(props, error="Insufficient credits. Visit quvi.ai to top up.")
            )
        except RateLimitError:
            bpy.app.timers.register(
                lambda: self._finish(props, error="Rate limit exceeded. Please wait a moment.")
            )
        except ContentModerationError as exc:
            reason = exc.reason or exc.category or "prompt rejected by content policy"
            bpy.app.timers.register(
                lambda: self._finish(props, error=f"Content policy violation: {reason}")
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
        props.obj_status = message
        if pct is not None:
            props.obj_progress = float(pct)
        _tag_redraw()
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
    def _finish(props, glb_bytes: bytes | None = None, error: str | None = None):
        props.obj_is_generating = False
        if error:
            props.obj_status = f"Error: {error}"
            _tag_redraw()
            return None
        if glb_bytes:
            tmp_path = os.path.join(tempfile.gettempdir(), "quviai_object.glb")
            try:
                Path(tmp_path).write_bytes(glb_bytes)
                # Find a VIEW_3D area for a valid operator context (required in Blender 4.x)
                ctx_window = ctx_area = None
                for window in bpy.context.window_manager.windows:
                    for area in window.screen.areas:
                        if area.type == "VIEW_3D":
                            ctx_window, ctx_area = window, area
                            break
                    if ctx_area:
                        break
                if ctx_area:
                    with bpy.context.temp_override(window=ctx_window, area=ctx_area):
                        bpy.ops.import_scene.gltf(filepath=tmp_path)
                else:
                    bpy.ops.import_scene.gltf(filepath=tmp_path)
                props.obj_status = "Done — object imported into scene."
            except Exception as exc:
                props.obj_status = f"Error importing GLB: {exc}"
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        _tag_redraw()
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tag_redraw() -> None:
    """Force all VIEW_3D areas to redraw so the N-panel updates immediately."""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _set_credits(prefs, credits: int) -> None:
    prefs.credits = credits
    return None


def register() -> None:
    bpy.utils.register_class(QUVIAI_OT_login_email)
    bpy.utils.register_class(QUVIAI_OT_login_google)
    bpy.utils.register_class(QUVIAI_OT_logout)
    bpy.utils.register_class(QUVIAI_OT_refresh_credits)
    bpy.utils.register_class(QUVIAI_OT_edit_prompt)
    bpy.utils.register_class(QUVIAI_OT_render)
    bpy.utils.register_class(QUVIAI_OT_open_result)
    bpy.utils.register_class(QUVIAI_OT_generate_object)


def unregister() -> None:
    bpy.utils.unregister_class(QUVIAI_OT_generate_object)
    bpy.utils.unregister_class(QUVIAI_OT_open_result)
    bpy.utils.unregister_class(QUVIAI_OT_render)
    bpy.utils.unregister_class(QUVIAI_OT_edit_prompt)
    bpy.utils.unregister_class(QUVIAI_OT_refresh_credits)
    bpy.utils.unregister_class(QUVIAI_OT_logout)
    bpy.utils.unregister_class(QUVIAI_OT_login_google)
    bpy.utils.unregister_class(QUVIAI_OT_login_email)
