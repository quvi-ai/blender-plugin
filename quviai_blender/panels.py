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
        is_logged_in = bool(prefs.access_token)

        if not is_logged_in:
            box = layout.box()
            box.label(text="Not logged in", icon="ERROR")
            box.label(text="Edit > Preferences > Add-ons > QUVIAI Render")
            return

        layout.prop(props, "mode", text="Mode")
        layout.separator()

        col = layout.column(align=True)

        if props.mode == "CANVAS":
            col.prop(props, "prompt", text="Prompt")
            col.prop(props, "is_sketch")

        elif props.mode == "RENDER_3D":
            col.prop(props, "prompt", text="Prompt")
            col.prop(props, "style", text="Style")
            col.prop(props, "render_type", text="Render Type")
            row = col.row(align=True)
            row.prop(props, "day_time", text="Time")
            row.prop(props, "weather", text="Weather")

        else:  # TEXT_IMAGE
            col.prop(props, "prompt", text="Prompt")
            col.prop(props, "style", text="Style")
            row = col.row(align=True)
            row.prop(props, "width", text="W")
            row.prop(props, "height", text="H")

        layout.separator()

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
                icon = "ERROR" if props.status.startswith("Error") else "CHECKMARK"
                box.label(text=props.status, icon=icon)


def register() -> None:
    bpy.utils.register_class(QUVIAI_PT_main)


def unregister() -> None:
    bpy.utils.unregister_class(QUVIAI_PT_main)
