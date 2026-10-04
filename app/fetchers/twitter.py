"""Display name + icon from an X profile via the free syndication endpoint.

Ported from MyGenba: no API key, best-effort, fail soft. The endpoint 429s
quickly per IP, so callers should space out bulk refreshes.
"""
from __future__ import annotations

import json
import re
import time

import httpx

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_TIMELINE = "https://syndication.twitter.com/srv/timeline-profile/screen-name/{}"
_NEXT_DATA = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S
)
_HANDLE_RE = re.compile(r"^[A-Za-z0-9_]{1,15}$")


def parse_handle(raw: str | None) -> str | None:
    """Accept '@name', bare 'name', or an x.com/twitter.com profile URL."""
    s = (raw or "").strip().lstrip("@")
    m = re.search(r"(?:twitter\.com|x\.com)/(?:#!/)?@?([A-Za-z0-9_]{1,15})", s)
    if m:
        s = m.group(1)
    return s if _HANDLE_RE.match(s) else None


def fetch_profile(handle: str, retries: int = 2) -> dict | None:
    """{"name": ..., "icon_url": ...} or None on any failure."""
    try:
        for attempt in range(retries + 1):
            r = httpx.get(
                _TIMELINE.format(handle),
                headers={"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"},
                timeout=20,
                follow_redirects=True,
            )
            if r.status_code == 429 and attempt < retries:
                time.sleep(2.5 * (attempt + 1))
                continue
            break
        r.raise_for_status()
        m = _NEXT_DATA.search(r.text)
        if not m:
            return None
        entries = json.loads(m.group(1))["props"]["pageProps"]["timeline"]["entries"]
        # entries can include retweets of other users, so match the owner by handle
        for e in entries:
            user = (e.get("content", {}).get("tweet", {}) or {}).get("user", {}) or {}
            if user.get("screen_name", "").lower() == handle.lower():
                icon = (user.get("profile_image_url_https") or "").replace(
                    "_normal.", "_400x400."
                )
                return {"name": user.get("name", "") or handle, "icon_url": icon}
        return None
    except Exception:
        return None
