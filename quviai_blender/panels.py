from __future__ import annotations

import bpy
from bpy.types import Panel

from .utils import get_preferences


class QUVIAI_PT_main(Panel):
    bl_label = "QUVIAI Render"
    bl_idname = "QUVIAI_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "QUVIAI"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        props = context.scene.quviai
        prefs = get_preferences(context)

        # --- API key warning ---
        if not prefs.api_key:
            box = layout.box()
            box.label(text="API key not set!", icon="ERROR")
            box.label(text="Edit > Preferences > Add-ons > QUVIAI Render")
            return

        # --- Camera angle controls ---
        col = layout.column(align=True)
        col.label(text="Render Angle:", icon="CAMERA_DATA")
        col.prop(props, "h_angle", text="Horizontal")
        col.prop(props, "v_angle", text="Vertical")
        col.prop(props, "zoom", text="Zoom")

        layout.separator()

        # --- Action area ---
        if props.is_rendering:
            box = layout.box()
            box.label(text=props.status or "Rendering…", icon="SORTTIME")
            box.operator("quviai.cancel", icon="X")
        else:
            layout.operator("quviai.render", icon="RENDER_STILL")

            if props.result_image_name:
                layout.operator("quviai.open_result", icon="IMAGE_DATA")

            if props.status:
                box = layout.box()
                # Show success in green-ish, errors in red-ish via icon
                icon = "ERROR" if props.status.startswith("Error") else "CHECKMARK"
                box.label(text=props.status, icon=icon)


def register() -> None:
    bpy.utils.register_class(QUVIAI_PT_main)


def unregister() -> None:
    bpy.utils.unregister_class(QUVIAI_PT_main)
