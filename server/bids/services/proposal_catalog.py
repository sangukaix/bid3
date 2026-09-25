"""Local, versioned template catalog; no external accounts or AI calls required."""

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile


def load_studio_templates(directory):
    directory = Path(directory)
    catalog_path = directory / "catalog.json"
    if not catalog_path.exists():
        return {}
    entries = json.loads(catalog_path.read_text(encoding="utf-8"))
    result = {}
    for entry in entries:
        template_id = entry["id"]
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,60}", template_id):
            raise ValueError("Invalid template identifier")
        if template_id in result or entry["file"] != f"{template_id}.pptx":
            raise ValueError("Duplicate identifier or invalid template filename")
        result[template_id] = {
            **entry,
            "path": directory / entry["file"],
            "preview_directory": directory / "previews" / template_id,
        }
    return result


@lru_cache(maxsize=128)
def _slide_count(path, modified_ns, size):
    with ZipFile(path) as package:
        xml = ElementTree.fromstring(package.read("ppt/presentation.xml"))
    return len(xml.findall("{http://schemas.openxmlformats.org/presentationml/2006/main}sldIdLst/*"))


def template_slide_count(path):
    path = Path(path)
    stat = path.stat()
    return _slide_count(str(path.resolve()), stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=128)
def _source_digest(path, modified_ns, size):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bundled_previews(template):
    """Use pre-rendered slides only if they belong to the exact installed PPTX."""
    directory = template.get("preview_directory")
    if not directory:
        return []
    directory = Path(directory)
    try:
        metadata = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        source = Path(template["path"]).resolve()
        stat = source.stat()
        digest = _source_digest(str(source), stat.st_mtime_ns, stat.st_size)
        if metadata["source_sha256"] != digest:
            return []
        count = template_slide_count(source)
        if metadata["slide_count"] != count:
            return []
        images = [directory / f"slide_{number:03d}.png" for number in range(1, count + 1)]
        return images if all(image.is_file() for image in images) else []
    except (OSError, ValueError, KeyError, TypeError):
        return []
