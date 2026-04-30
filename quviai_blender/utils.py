from __future__ import annotations

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


def capture_viewport(context: bpy.types.Context) -> bytes:
    """Capture the active 3D Viewport as PNG bytes using OpenGL render.

    Temporarily overrides scene.render.filepath to a temp file, runs
    render.opengl, then restores the original filepath.
    """
    scene = context.scene
    original_filepath = scene.render.filepath
    original_format = scene.render.image_settings.file_format

    tmp_path = os.path.join(tempfile.gettempdir(), "quviai_viewport.png")
    scene.render.filepath = tmp_path
    scene.render.image_settings.file_format = "PNG"

    try:
        bpy.ops.render.opengl(write_still=True)
        return Path(tmp_path).read_bytes()
    finally:
        scene.render.filepath = original_filepath
        scene.render.image_settings.file_format = original_format


def process_for_upload(raw_bytes: bytes, context: bpy.types.Context, max_size: int = 2048) -> bytes:
    """Resize so longest edge <= max_size and convert to WebP. Must run in main thread."""
    tmp_png = os.path.join(tempfile.gettempdir(), "quviai_raw.png")
    tmp_webp = os.path.join(tempfile.gettempdir(), "quviai_upload.webp")
    Path(tmp_png).write_bytes(raw_bytes)

    img = bpy.data.images.load(tmp_png, check_existing=False)
    img.name = "_quviai_upload_tmp"
    try:
        w, h = img.size
        if w > max_size or h > max_size:
            if w >= h:
                new_w = max_size
                new_h = max(1, round(h * max_size / w))
            else:
                new_h = max_size
                new_w = max(1, round(w * max_size / h))
            img.scale(new_w, new_h)

        scene = context.scene
        orig_format = scene.render.image_settings.file_format
        orig_quality = scene.render.image_settings.quality
        scene.render.image_settings.file_format = "WEBP"
        scene.render.image_settings.quality = 90
        try:
            img.save_render(tmp_webp, scene=scene)
        finally:
            scene.render.image_settings.file_format = orig_format
            scene.render.image_settings.quality = orig_quality

        return Path(tmp_webp).read_bytes()
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
