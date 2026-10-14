"""Find design images in folders the user named, and embed them safely.

Only the folders given are read, only plain files directly inside them (no links), and only files
whose content really is the image type their name claims. SVG files are accepted only when they
hold no script, no external reference and no entity declarations.
"""

from __future__ import annotations

import base64
import xml.etree.ElementTree as ET
from pathlib import Path

IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}
BAD_SVG_TAGS = {"script", "foreignobject", "iframe", "object", "embed", "audio", "video"}


def is_link(path: Path) -> bool:
    """True for symbolic links and, on Windows, junctions."""
    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or bool(is_junction and is_junction())


def safe_svg(data: bytes) -> bool:
    lowered = data.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        return False
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return False
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1].lower() in BAD_SVG_TAGS:
            return False
        for name, value in element.attrib.items():
            local = name.rsplit("}", 1)[-1].lower()
            if local.startswith("on"):
                return False
            if local == "href" and not value.strip().startswith("#"):
                return False
    return True


def content_matches(data: bytes, suffix: str) -> bool:
    """True when the bytes are the image type the file name says."""
    if suffix == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix in (".jpg", ".jpeg"):
        return data.startswith(b"\xff\xd8\xff")
    if suffix == ".webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if suffix == ".svg":
        return safe_svg(data)
    return False


def find_design_images(
    root: Path, folders: list[str], max_bytes: int
) -> tuple[list[dict], int, list[str]]:
    """Return (images, number left out for size, notes on files or folders that were ignored).

    Each image is {"name": "Design image N", "file": <file name>, "uri": <data URI>}. The file
    name is for messages to the user only; it is never put in the deck.
    """
    base = root.resolve()
    images: list[dict] = []
    ignored: list[str] = []
    left_out = 0
    total = 0
    for folder in folders:
        directory = base / folder
        if is_link(directory) or not directory.is_dir():
            ignored.append(f"{folder}: not a plain folder")
            continue
        if not directory.resolve().is_relative_to(base):
            ignored.append(f"{folder}: outside the project folder")
            continue
        for path in sorted(directory.iterdir()):
            suffix = path.suffix.lower()
            if suffix not in IMAGE_TYPES:
                continue
            if is_link(path) or not path.is_file():
                ignored.append(f"{folder}/{path.name}: links and special files are not used")
                continue
            if total + path.stat().st_size > max_bytes:
                left_out += 1
                continue
            data = path.read_bytes()
            if not content_matches(data, suffix):
                ignored.append(f"{folder}/{path.name}: not a safe {suffix[1:].upper()} image")
                continue
            total += len(data)
            uri = f"data:{IMAGE_TYPES[suffix]};base64,{base64.b64encode(data).decode('ascii')}"
            images.append(
                {"name": f"Design image {len(images) + 1}", "file": path.name, "uri": uri}
            )
    return images, left_out, ignored
