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
    """Decode a base64 string.

    Strips data URI prefix, normalizes URL-safe characters, strips any
    existing padding, then re-pads correctly before decoding.
    """
    b64 = re.sub(r"^data:[^;]+;base64,", "", b64).strip()
    b64 = b64.replace("-", "+").replace("_", "/")  # URL-safe → standard
    b64 = b64.rstrip("=")                           # drop existing padding
    b64 += "=" * (-len(b64) % 4)                   # re-pad correctly
    return base64.b64decode(b64)


def normalize_result(result) -> list[str]:
    """Return the list of output URLs or base64 strings from a completed task.

    Checks the same candidate fields as the web frontend to handle all API
    response variants (list, dict with urls/images/url/image/file_url, nested).
    """
    if not result:
        return []

    if isinstance(result, list):
        return [v for v in result if isinstance(v, str) and v]

    def _extract(d: dict) -> list[str]:
        for key in ("urls", "images", "image", "url", "file_url"):
            val = d.get(key)
            if isinstance(val, list):
                items = [v for v in val if isinstance(v, str) and v]
                if items:
                    return items
            if isinstance(val, str) and val:
                return [val]
        return []

    found = _extract(result)
    if found:
        return found

    # Check one level deeper under a nested "result" key
    nested = result.get("result")
    if isinstance(nested, dict):
        return _extract(nested)

    return []
