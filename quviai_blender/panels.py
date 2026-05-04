from __future__ import annotations

import bpy
from bpy.types import Panel

from .utils import get_preferences


def _draw_wrapped(layout, text: str, char_width: int = 28) -> None:
    words = text.split()
    line = ""
    for word in words:
        candidate = (line + " " + word).strip()
        if len(candidate) <= char_width:
            line = candidate
        else:
            if line:
                layout.label(text=line)
            line = word
    if line:
        layout.label(text=line)


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

        # --- Category + Style ---
        col = layout.column(align=True)
        col.prop(props, "style_category", text="Category")

        if props.style_category == "architectural":
            col.prop(props, "arch_style", text="Style")
        else:
            col.prop(props, "general_style", text="Style")

        # --- Prompt ---
        layout.separator(factor=0.5)
        layout.label(text="Prompt")
        box = layout.box()
        if props.prompt:
            _draw_wrapped(box, props.prompt)
        else:
            box.label(text="(empty — click Edit to add)", icon="INFO")
        layout.operator("quviai.edit_prompt", text="Edit Prompt", icon="GREASEPENCIL")

        # --- Architectural-only controls ---
        if props.style_category == "architectural":
            layout.separator()
            col2 = layout.column(align=True)
            col2.prop(props, "render_type", text="Render Type")

            if props.render_type == "exterior":
                row = col2.row(align=True)
                row.prop(props, "day_time", text="Time")
                row.prop(props, "weather", text="Weather")
            elif props.render_type == "interior":
                col2.prop(props, "day_time", text="Time")

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


class QUVIAI_PT_object(Panel):
    bl_label = "3D Object Generation"
    bl_idname = "QUVIAI_PT_object"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "QUVIAI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        props = context.scene.quviai
        prefs = get_preferences(context)

        if not bool(prefs.access_token):
            layout.label(text="Not logged in", icon="ERROR")
            return

        # Mode toggle
        row = layout.row(align=True)
        row.prop(props, "obj_mode", expand=True)

        layout.separator(factor=0.5)

        if props.obj_mode == "prompt":
            layout.label(text="Prompt")
            box = layout.box()
            if props.obj_prompt:
                _draw_wrapped(box, props.obj_prompt)
            else:
                box.label(text="(empty — click Edit to add)", icon="INFO")
            op = layout.operator("quviai.edit_prompt", text="Edit Prompt", icon="GREASEPENCIL")
            op.target_prop = "obj_prompt"
        else:
            layout.label(text="Image")
            layout.prop(props, "obj_image_path", text="")

        layout.separator()

        if props.obj_is_generating:
            box = layout.box()
            if props.obj_progress > 0:
                box.progress(
                    factor=props.obj_progress / 100.0,
                    text=f"{int(props.obj_progress)}%",
                )
            box.label(text=props.obj_status or "Generating…", icon="SORTTIME")
        else:
            layout.operator("quviai.generate_object", icon="MESH_ICOSPHERE")

            if props.obj_status:
                box = layout.box()
                icon = "ERROR" if props.obj_status.startswith("Error") else "CHECKMARK"
                box.label(text=props.obj_status, icon=icon)


def register() -> None:
    bpy.utils.register_class(QUVIAI_PT_main)
    bpy.utils.register_class(QUVIAI_PT_object)


def unregister() -> None:
    bpy.utils.unregister_class(QUVIAI_PT_object)
    bpy.utils.unregister_class(QUVIAI_PT_main)
