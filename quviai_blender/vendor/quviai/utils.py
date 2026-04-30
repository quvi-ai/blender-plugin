from __future__ import annotations

import base64
import re
from pathlib import Path


def image_to_base64(path: str | Path) -> str:
    """Read an image file and return its base64-encoded string."""
    return base64.b64encode(Path(path).read_bytes()).decode()


def bytes_to_base64(data: bytes) -> str:
    """Encode raw bytes to a base64 string."""
    return base64.b64encode(data).decode()


def base64_to_bytes(b64: str) -> bytes:
    """Decode a base64 string — strips data URI prefix and normalizes padding."""
    b64 = re.sub(r"^data:[^;]+;base64,", "", b64).strip()
    b64 += "=" * (-len(b64) % 4)  # pad to a multiple of 4 chars
    return base64.b64decode(b64)


def normalize_result(result) -> list[str]:
    """Return the list of output URLs or base64 strings from a completed task.

    The API returns result as a list of URLs for video/3D tasks, or as a dict
    with an 'images' key for image generation tasks.
    """
    if not result:
        return []
    if isinstance(result, list):
        return result
    return result.get("urls") or result.get("images") or []
