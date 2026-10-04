"""Song details from a streaming link: TuneCore (linkco.re), Spotify, Apple Music,
YouTube Music. All key-free public endpoints; fail soft (None).

Result: {"service", "title", "title_romaji", "image", "year", "lyrics_url",
"tracks"}; any of them may be empty. "tracks" is only set for a TuneCore album, so the admin can
pick one song out of it.
"""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

import httpx

from . import linkcore
from .twitter import UA

_JA = re.compile(r"[぀-ヿ㐀-鿿ｦ-ﾟ]")


def _get(url: str, **kw) -> httpx.Response | None:
    try:
        r = httpx.get(url, headers={"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"},
                      timeout=20, follow_redirects=True, **kw)
        r.raise_for_status()
        return r
    except Exception:
        return None


def _result(service: str, title: str = "", image: str = "", year: int | None = None,
            title_romaji: str = "", lyrics_url: str = "", tracks: list | None = None) -> dict:
    return {"service": service, "title": title, "title_romaji": title_romaji, "image": image,
            "year": year, "lyrics_url": lyrics_url, "tracks": tracks or []}


def service_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host.endswith("linkco.re"):
        return "tunecore"
    if host == "open.spotify.com":
        return "spotify"
    if host in ("music.apple.com", "itunes.apple.com"):
        return "apple"
    if host == "music.youtube.com":
        return "ytmusic"
    if host in ("youtu.be", "youtube.com", "www.youtube.com", "m.youtube.com"):
        return "youtube"
    return ""


def _spotify(url: str) -> dict | None:
    r = _get("https://open.spotify.com/oembed", params={"url": url})
    if not r:
        return None
    d = r.json()
    title = d.get("title", "")
    # 300px thumbnail; the same image id with this prefix is the 640px one
    image = (d.get("thumbnail_url") or "").replace("ab67616d00001e02", "ab67616d0000b273")
    # Spotify serves the romanized title for Japanese songs, whatever language is asked
    romaji = "" if _JA.search(title) else title
    return _result("spotify", title, image, title_romaji=romaji)


def _apple(url: str) -> dict | None:
    u = urlparse(url)
    q = parse_qs(u.query)
    parts = [p for p in u.path.split("/") if p]
    country = parts[0] if parts and len(parts[0]) == 2 else "jp"
    if "i" in q:                                   # /album/<name>/<album id>?i=<song id>
        item = q["i"][0]
    elif len(parts) >= 2 and parts[-1].isdigit():  # /song/<name>/<id> or a whole album
        item = parts[-1]
    else:
        return None
    r = _get("https://itunes.apple.com/lookup", params={"id": item, "country": country})
    res = (r.json().get("results") or []) if r else []
    if not res:
        return None
    d = res[0]
    title = d.get("trackName") or d.get("collectionName") or ""
    image = (d.get("artworkUrl100") or "").replace("100x100bb", "600x600bb")
    year = int(d["releaseDate"][:4]) if d.get("releaseDate") else None
    return _result("apple", title, image, year)


def _youtube_id(url: str) -> str | None:
    u = urlparse(url)
    if u.hostname == "youtu.be":
        return u.path.strip("/") or None
    return (parse_qs(u.query).get("v") or [None])[0]


def _youtube(url: str, service: str) -> dict | None:
    vid = _youtube_id(url)
    if not vid:
        return None
    r = _get("https://www.youtube.com/oembed",
             params={"url": f"https://www.youtube.com/watch?v={vid}", "format": "json"})
    if not r:
        return None
    # maxres is the 16:9 frame without letterboxing; for a YouTube Music track the
    # jacket sits in the middle, and the site crops jackets to a centered square
    image = f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg"
    if not _get(image):
        image = r.json().get("thumbnail_url", "")
    return _result(service, r.json().get("title", ""), image)


def fetch(url: str) -> dict | None:
    url = url.strip()
    service = service_of(url)
    if service == "tunecore":
        d = linkcore.fetch(url)
        return _result("tunecore", **d) if d else None
    if service == "spotify":
        return _spotify(url)
    if service == "apple":
        return _apple(url)
    if service in ("ytmusic", "youtube"):
        return _youtube(url, service)
    return None
