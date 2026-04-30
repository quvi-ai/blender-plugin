from __future__ import annotations

import threading
import webbrowser

import bpy
from bpy.types import Operator

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


class QUVIAI_OT_login_browser(Operator):
    """Open quvi.ai in the browser to log in with Google or Apple"""

    bl_idname = "quviai.login_browser"
    bl_label = "Open QUVIAI Login Page"
    bl_options = {"REGISTER"}

    def execute(self, context: bpy.types.Context):
        prefs = get_preferences(context)
        webbrowser.open(f"{prefs.base_url}/login")
        self.report(
            {"INFO"},
            "Browser opened. After logging in, paste your access token into "
            "the 'Paste Token' field in preferences (coming in next update).",
        )
        return {"FINISHED"}


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
            image_bytes = capture_viewport(context)
        except Exception as exc:
            self.report({"ERROR"}, f"Viewport capture failed: {exc}")
            return {"CANCELLED"}

        props.is_rendering = True
        props.status = "Submitting to QUVIAI..."
        props.result_image_name = ""

        thread = threading.Thread(
            target=self._run_in_thread,
            args=(prefs, props, image_bytes),
            daemon=True,
        )
        thread.start()
        return {"FINISHED"}

    def _run_in_thread(self, prefs, props, image_bytes: bytes) -> None:
        ensure_vendor_in_path()
        try:
            from quviai import QuviClient, QuviError, TokenExpiredError
        except ImportError:
            self._finish(props, error="SDK missing. Run scripts/update_vendor.sh.")
            return

        try:
            client = QuviClient.from_tokens(
                access_token=prefs.access_token,
                refresh_token=prefs.refresh_token or None,
                base_url=prefs.base_url,
                poll_interval=prefs.poll_interval,
                poll_timeout=prefs.poll_timeout,
            )

            def on_status(status):
                msg = f"Rendering… queue position: {status.queue_position}"
                if status.eta_formatted and status.eta_formatted != "Completed":
                    msg += f", ETA: {status.eta_formatted}"
                bpy.app.timers.register(lambda: self._set_status(props, msg))

            result = client.generate_canvas(
                image_bytes,
                prompt=props.prompt,
                is_sketch=props.is_sketch,
                on_status=on_status,
            )

            # If the token was refreshed during the request, save it
            if client.access_token != prefs.access_token:
                bpy.app.timers.register(
                    lambda: self._save_tokens(prefs, client.access_token, client.refresh_token)
                )

            final_bytes = client.download_result(result)
            self._finish(props, image_bytes=final_bytes)

        except TokenExpiredError:
            bpy.app.timers.register(lambda: self._clear_tokens(prefs))
            self._finish(props, error="Session expired. Please log in again.")
        except Exception as exc:
            self._finish(props, error=str(exc))

    @staticmethod
    def _set_status(props, message: str):
        props.status = message
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
            props.status = "Done — result loaded in Image Editor."
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
    bpy.utils.register_class(QUVIAI_OT_login_browser)
    bpy.utils.register_class(QUVIAI_OT_logout)
    bpy.utils.register_class(QUVIAI_OT_render)
    bpy.utils.register_class(QUVIAI_OT_cancel)
    bpy.utils.register_class(QUVIAI_OT_open_result)


def unregister() -> None:
    bpy.utils.unregister_class(QUVIAI_OT_open_result)
    bpy.utils.unregister_class(QUVIAI_OT_cancel)
    bpy.utils.unregister_class(QUVIAI_OT_render)
    bpy.utils.unregister_class(QUVIAI_OT_logout)
    bpy.utils.unregister_class(QUVIAI_OT_login_browser)
    bpy.utils.unregister_class(QUVIAI_OT_login_email)
