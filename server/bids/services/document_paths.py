"""Portable document references rooted in this installation's media directory."""

from pathlib import Path, PureWindowsPath

from django.conf import settings


def resolve_document_source(source):
    """Read media-relative references and old Windows/Linux installation paths."""
    text = str(source).replace("\\", "/")
    media_root = Path(settings.MEDIA_ROOT).resolve()
    if text.startswith("media://"):
        relative = text[len("media://"):]
    elif "/server/media/" in text:
        relative = text.split("/server/media/", 1)[1]
    else:
        return Path(source).resolve()
    # Windows drives and traversal must not escape the current media root.
    if PureWindowsPath(relative).drive:
        raise ValueError("문서 경로가 미디어 폴더 밖을 가리킵니다.")
    target = (media_root / relative).resolve()
    if not target.is_relative_to(media_root):
        raise ValueError("문서 경로가 미디어 폴더 밖을 가리킵니다.")
    return target


def portable_document_source(source):
    path = resolve_document_source(source)
    media_root = Path(settings.MEDIA_ROOT).resolve()
    if path.is_relative_to(media_root):
        return "media://" + path.relative_to(media_root).as_posix()
    return str(path)
