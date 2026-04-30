from __future__ import annotations

import bpy
from bpy.props import FloatProperty, StringProperty
from bpy.types import AddonPreferences


class QuviAIPreferences(AddonPreferences):
    bl_idname = __package__

    api_key: StringProperty(
        name="API Key",
        description="Your QUVIAI API key — get one at quvi.ai",
        default="",
        subtype="PASSWORD",
    )  # type: ignore[assignment]

    base_url: StringProperty(
        name="Base URL",
        description="QUVIAI API base URL (do not change unless instructed)",
        default="https://quvi.ai",
    )  # type: ignore[assignment]

    poll_interval: FloatProperty(
        name="Poll Interval (s)",
        description="How often to check render status",
        default=3.0,
        min=1.0,
        max=30.0,
    )  # type: ignore[assignment]

    poll_timeout: FloatProperty(
        name="Poll Timeout (s)",
        description="Maximum time to wait for a render task",
        default=120.0,
        min=30.0,
        max=600.0,
    )  # type: ignore[assignment]

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout

        box = layout.box()
        box.label(text="Authentication", icon="KEY_HLT")
        box.prop(self, "api_key")
        if not self.api_key:
            box.label(text="API key required — get one at quvi.ai", icon="ERROR")

        box = layout.box()
        box.label(text="Advanced", icon="PREFERENCES")
        box.prop(self, "base_url")
        row = box.row()
        row.prop(self, "poll_interval")
        row.prop(self, "poll_timeout")


def register() -> None:
    bpy.utils.register_class(QuviAIPreferences)


def unregister() -> None:
    bpy.utils.unregister_class(QuviAIPreferences)
