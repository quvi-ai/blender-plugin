from __future__ import annotations

import bpy
from bpy.props import BoolProperty, FloatProperty, IntProperty, StringProperty
from bpy.types import PropertyGroup


class QuviAIProperties(PropertyGroup):
    """Per-scene QUVIAI state, stored in scene.quviai."""

    h_angle: IntProperty(
        name="Horizontal Angle",
        description="Horizontal camera angle sent to the AI renderer (0–360°)",
        default=63,
        min=0,
        max=360,
    )  # type: ignore[assignment]

    v_angle: IntProperty(
        name="Vertical Angle",
        description="Vertical camera angle sent to the AI renderer (-90–90°)",
        default=29,
        min=-90,
        max=90,
    )  # type: ignore[assignment]

    zoom: FloatProperty(
        name="Zoom",
        description="Camera zoom level sent to the AI renderer",
        default=5.0,
        min=1.0,
        max=20.0,
        step=10,
    )  # type: ignore[assignment]

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
