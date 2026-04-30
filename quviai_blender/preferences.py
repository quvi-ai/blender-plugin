from __future__ import annotations

import bpy
from bpy.props import FloatProperty, StringProperty
from bpy.types import AddonPreferences


class QuviAIPreferences(AddonPreferences):
    bl_idname = __package__

    # --- Auth ---
    email: StringProperty(
        name="Email",
        description="Your QUVIAI account email",
        default="",
    )  # type: ignore[assignment]

    password: StringProperty(
        name="Password",
        description="Your QUVIAI account password",
        default="",
        subtype="PASSWORD",
    )  # type: ignore[assignment]

    # Tokens are stored here after a successful login — not shown in UI
    access_token: StringProperty(
        name="Access Token",
        description="JWT access token (auto-filled after login)",
        default="",
        options={"HIDDEN"},
    )  # type: ignore[assignment]

    refresh_token: StringProperty(
        name="Refresh Token",
        description="JWT refresh token (auto-filled after login)",
        default="",
        options={"HIDDEN"},
    )  # type: ignore[assignment]

    # --- Connection ---
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
        is_logged_in = bool(self.access_token)

        # --- Auth section ---
        box = layout.box()
        box.label(text="Account", icon="USER")

        if is_logged_in:
            row = box.row()
            row.label(text="Logged in", icon="CHECKMARK")
            row.operator("quviai.logout", text="Log Out", icon="X")
        else:
            box.prop(self, "email")
            box.prop(self, "password")
            col = box.column(align=True)
            col.operator("quviai.login_email", text="Log In", icon="PLAY")
            col.separator()
            col.label(text="Or log in via your browser:")
            col.operator("quviai.login_browser", text="Log In with Google / Apple", icon="URL")

        # --- Advanced ---
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
