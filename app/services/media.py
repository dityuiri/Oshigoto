"""Icons, jackets and logos are copied to DATA_DIR/uploads and served from
/media, so the page never hotlinks X/TuneCore (their URLs rotate and rate-limit)."""
from __future__ import annotations

import hashlib

import httpx

from ..config import UPLOAD_DIR
from ..fetchers.twitter import UA

MAX_BYTES = 5 * 1024 * 1024
EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}


def save_bytes(kind: str, data: bytes, content_type: str) -> str | None:
    """Store under uploads/<kind>/ and return the path relative to UPLOAD_DIR.
    Content-addressed, so a changed image gets a new URL (no stale caches)."""
    ext = EXT.get(content_type.split(";")[0].strip().lower())
    if not ext or not data or len(data) > MAX_BYTES:
        return None
    rel = f"{kind}/{hashlib.sha1(data).hexdigest()[:16]}.{ext}"
    dest = UPLOAD_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        dest.write_bytes(data)
    return rel


def download(kind: str, url: str) -> str | None:
    if not url.startswith(("http://", "https://")):
        return None
    try:
        r = httpx.get(url, headers={"User-Agent": UA}, timeout=20, follow_redirects=True)
        r.raise_for_status()
    except Exception:
        return None
    return save_bytes(kind, r.content, r.headers.get("content-type", ""))


def delete(rel: str | None) -> None:
    """Remove an uploaded file. Bundled static assets ("static:...") are left alone."""
    if not rel or rel.startswith("static:"):
        return
    path = (UPLOAD_DIR / rel).resolve()
    if UPLOAD_DIR.resolve() in path.parents:
        path.unlink(missing_ok=True)


def url_for(rel: str | None) -> str:
    if not rel:
        return ""
    if rel.startswith("static:"):
        return "/static/" + rel.removeprefix("static:")
    return "/media/" + rel

