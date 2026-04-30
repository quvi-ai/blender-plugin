from __future__ import annotations

import threading

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


class QUVIAI_OT_render(Operator):
    """Capture the 3D Viewport and render it with QUVIAI"""

    bl_idname = "quviai.render"
    bl_label = "Render with QUVIAI"
    bl_options = {"REGISTER"}

    def execute(self, context: bpy.types.Context):
        prefs = get_preferences(context)
        props = context.scene.quviai

        if not prefs.api_key:
            self.report(
                {"ERROR"},
                "API key not set. Go to Edit > Preferences > Add-ons > QUVIAI Render.",
            )
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
            from quviai import QuviClient, QuviError
        except ImportError:
            self._finish(props, error="SDK missing. Run scripts/update_vendor.sh.")
            return

        try:
            client = QuviClient(
                api_key=prefs.api_key,
                base_url=prefs.base_url,
                poll_interval=prefs.poll_interval,
                poll_timeout=prefs.poll_timeout,
            )

            def on_status(status):
                msg = f"Rendering… queue position: {status.queue_position}"
                if status.eta_formatted and status.eta_formatted != "Completed":
                    msg += f", ETA: {status.eta_formatted}"
                bpy.app.timers.register(lambda: self._set_status(props, msg))

            result = client.generate_from_image(
                image_bytes,
                h_angle=props.h_angle,
                v_angle=props.v_angle,
                zoom=props.zoom,
                on_status=on_status,
            )
            final_bytes = client.download_result(result)
            self._finish(props, image_bytes=final_bytes)

        except Exception as exc:
            self._finish(props, error=str(exc))

    @staticmethod
    def _set_status(props, message: str):
        props.status = message
        return None  # tells Blender not to repeat the timer

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
    bpy.utils.register_class(QUVIAI_OT_render)
    bpy.utils.register_class(QUVIAI_OT_cancel)
    bpy.utils.register_class(QUVIAI_OT_open_result)


def unregister() -> None:
    bpy.utils.unregister_class(QUVIAI_OT_open_result)
    bpy.utils.unregister_class(QUVIAI_OT_cancel)
    bpy.utils.unregister_class(QUVIAI_OT_render)
