from __future__ import annotations

import bpy
from bpy.props import IntProperty, StringProperty
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

    credits: IntProperty(
        name="Credits",
        description="Available QUVIAI credits (auto-filled after login)",
        default=-1,
        options={"HIDDEN"},
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
            cred_row = box.row()
            cred_label = f"Credits: {self.credits}" if self.credits >= 0 else "Credits: —"
            cred_row.label(text=cred_label, icon="FUND")
            cred_row.operator("quviai.refresh_credits", text="", icon="FILE_REFRESH")
        else:
            box.prop(self, "email")
            box.prop(self, "password")
            col = box.column(align=True)
            col.operator("quviai.login_email", text="Log In", icon="PLAY")
            col.separator()
            col.label(text="Or:")
            col.operator("quviai.login_google", text="Log In with Google", icon="URL")



def register() -> None:
    bpy.utils.register_class(QuviAIPreferences)


def unregister() -> None:
    bpy.utils.unregister_class(QuviAIPreferences)
