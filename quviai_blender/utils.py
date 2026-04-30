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
    """Capture the active 3D Viewport and return a base64-encoded WebP string.

    Renders directly to WebP so only one temp file is ever written. If the
    image exceeds 2048 px on either edge it is scaled down and the file is
    overwritten before reading. The temp file is deleted after the read.
    Must be called from the main thread.
    """
    scene = context.scene
    tmp_path = os.path.join(tempfile.gettempdir(), "quviai_upload.webp")

    orig_filepath = scene.render.filepath
    orig_format = scene.render.image_settings.file_format
    orig_quality = scene.render.image_settings.quality
    scene.render.filepath = tmp_path
    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.quality = 90

    try:
        bpy.ops.render.opengl(write_still=True)
    finally:
        scene.render.filepath = orig_filepath
        scene.render.image_settings.file_format = orig_format
        scene.render.image_settings.quality = orig_quality

    img = bpy.data.images.load(tmp_path, check_existing=False)
    img.name = "_quviai_upload_tmp"
    try:
        w, h = img.size
        max_size = 2048
        if w > max_size or h > max_size:
            if w >= h:
                new_w, new_h = max_size, max(1, round(h * max_size / w))
            else:
                new_h, new_w = max_size, max(1, round(w * max_size / h))
            img.scale(new_w, new_h)
            scene.render.image_settings.file_format = "WEBP"
            scene.render.image_settings.quality = 90
            try:
                img.save_render(tmp_path, scene=scene)
            finally:
                scene.render.image_settings.file_format = orig_format
                scene.render.image_settings.quality = orig_quality

        data = Path(tmp_path).read_bytes()
        return base64.b64encode(data).decode()
    finally:
        bpy.data.images.remove(img)
        Path(tmp_path).unlink(missing_ok=True)


def load_image_into_blender(name: str, image_bytes: bytes) -> bpy.types.Image:
    """Write bytes to a temp file, load as Blender image, then pack into .blend.
    Must be called from the main thread.
    """
    tmp_path = os.path.join(tempfile.gettempdir(), name)
    Path(tmp_path).write_bytes(image_bytes)

    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])

    img = bpy.data.images.load(tmp_path)
    img.name = name
    img.pack()
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
