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

        if not bool(prefs.access_token):
            box = layout.box()
            box.label(text="Not logged in", icon="ERROR")
            box.label(text="Edit > Preferences > Add-ons > QUVIAI Render")
            return

        # --- Credits ---
        cred_row = layout.row(align=True)
        cred_label = f"Credits: {prefs.credits}" if prefs.credits >= 0 else "Credits: —"
        cred_row.label(text=cred_label, icon="FUND")
        cred_row.operator("quviai.refresh_credits", text="", icon="FILE_REFRESH")
        cred_row.operator("wm.url_open", text="", icon="URL").url = "https://quvi.ai/pricing"

        layout.separator()

        # --- Render settings ---
        col = layout.column(align=True)
        col.prop(props, "prompt", text="Prompt")
        col.prop(props, "style", text="Style")
        col.prop(props, "render_type", text="Render Type")
        row = col.row(align=True)
        row.prop(props, "day_time", text="Time")
        row.prop(props, "weather", text="Weather")

        layout.separator()

        # --- Action / status ---
        if props.is_rendering:
            box = layout.box()
            if props.progress > 0:
                box.progress(
                    factor=props.progress / 100.0,
                    text=f"{int(props.progress)}%",
                )
            box.label(text=props.status or "Rendering…", icon="SORTTIME")
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
