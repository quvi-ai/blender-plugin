from __future__ import annotations

import base64
import os
import sys
import tempfile
from pathlib import Path

import bpy


def ensure_vendor_in_path() -> None:
    """Add the add-on vendor directory to sys.path if not already present."""
    vendor = str(Path(__file__).parent / "vendor")
    if vendor not in sys.path:
        sys.path.insert(0, vendor)


def capture_viewport(context: bpy.types.Context) -> str:
    """Capture the active 3D Viewport as a base64-encoded WebP string.

    Resizes so the longest edge is at most 2048 px (aspect preserved),
    converts to WebP quality 90, and returns the base64 string.
    Must be called from the main thread.
    """
    scene = context.scene
    orig_filepath = scene.render.filepath
    orig_format = scene.render.image_settings.file_format
    orig_quality = scene.render.image_settings.quality

    tmp_capture = os.path.join(tempfile.gettempdir(), "quviai_capture.webp")
    scene.render.filepath = tmp_capture
    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.quality = 90

    try:
        bpy.ops.render.opengl(write_still=True)
    finally:
        scene.render.filepath = orig_filepath
        scene.render.image_settings.file_format = orig_format
        scene.render.image_settings.quality = orig_quality

    img = bpy.data.images.load(tmp_capture, check_existing=False)
    img.name = "_quviai_capture_tmp"
    try:
        w, h = img.size
        max_size = 2048
        if w > max_size or h > max_size:
            if w >= h:
                new_w, new_h = max_size, max(1, round(h * max_size / w))
            else:
                new_h, new_w = max_size, max(1, round(w * max_size / h))
            img.scale(new_w, new_h)

        tmp_webp = os.path.join(tempfile.gettempdir(), "quviai_upload.webp")
        scene.render.image_settings.file_format = "WEBP"
        scene.render.image_settings.quality = 90
        try:
            img.save_render(tmp_webp, scene=scene)
        finally:
            scene.render.image_settings.file_format = orig_format
            scene.render.image_settings.quality = orig_quality

        return base64.b64encode(Path(tmp_webp).read_bytes()).decode()
    finally:
        bpy.data.images.remove(img)


def load_image_into_blender(name: str, image_bytes: bytes) -> bpy.types.Image:
    """Write bytes to a temp file, load as Blender image, then pack into .blend."""
    tmp_path = os.path.join(tempfile.gettempdir(), name)
    Path(tmp_path).write_bytes(image_bytes)

    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])

    img = bpy.data.images.load(tmp_path)
    img.name = name
    img.pack()  # embed into .blend so temp file can be deleted
    return img


def get_preferences(context: bpy.types.Context):
    """Return the add-on AddonPreferences instance."""
    return context.preferences.addons[__package__].preferences


def open_in_image_editor(context: bpy.types.Context, image: bpy.types.Image) -> bool:
    """Switch an existing Image Editor area to show the given image.

    Returns True if an Image Editor was found, False otherwise.
    """
    for area in context.screen.areas:
        if area.type == "IMAGE_EDITOR":
            area.spaces.active.image = image
            return True
    return False
