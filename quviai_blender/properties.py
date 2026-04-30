from __future__ import annotations

import bpy
from bpy.props import BoolProperty, FloatProperty, IntProperty, StringProperty
from bpy.types import PropertyGroup


class QuviAIProperties(PropertyGroup):
    """Per-scene QUVIAI state, stored in scene.quviai."""

    # --- Canvas render settings ---
    prompt: StringProperty(
        name="Prompt",
        description="Optional text prompt to guide the AI render",
        default="",
    )  # type: ignore[assignment]

    is_sketch: BoolProperty(
        name="Sketch Mode",
        description="Treat the viewport screenshot as a sketch and recompose it",
        default=False,
    )  # type: ignore[assignment]

    # --- Task state ---
    is_rendering: BoolProperty(
        name="Is Rendering",
        default=False,
    )  # type: ignore[assignment]

    status: StringProperty(
        name="Status",
        description="Current render status message",
        default="",
    )  # type: ignore[assignment]

    result_image_name: StringProperty(
        name="Result Image",
        description="Name of the result image datablock in Blender",
        default="",
    )  # type: ignore[assignment]


def register() -> None:
    bpy.utils.register_class(QuviAIProperties)
    bpy.types.Scene.quviai = bpy.props.PointerProperty(type=QuviAIProperties)


def unregister() -> None:
    del bpy.types.Scene.quviai
    bpy.utils.unregister_class(QuviAIProperties)
