"""QUVI AI Render — Blender Add-on.

Captures the 3D Viewport and sends it to the QUVIAI API for AI rendering.
Results appear automatically in the Image Editor.
"""

bl_info = {
    "name": "QUVI AI Render",
    "author": "QUVIAI",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > N-Panel > QUVI AI",
    "description": "AI-powered viewport rendering via the QUVIAI API",
    "category": "Render",
    "doc_url": "https://github.com/quvi-ai/blender-plugin",
    "tracker_url": "https://github.com/quvi-ai/blender-plugin/issues",
}

from . import operators, panels, preferences, properties  # noqa: E402


def register() -> None:
    preferences.register()
    properties.register()
    operators.register()
    panels.register()


def unregister() -> None:
    panels.unregister()
    operators.unregister()
    properties.unregister()
    preferences.unregister()
