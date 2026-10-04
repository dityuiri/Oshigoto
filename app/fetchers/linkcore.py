"""Title, jacket, year and track list from a TuneCore link page (linkco.re/...).

A link page is per release, so an album gives every track: the Japanese page for
titles and lyrics links, the English page (?lang=en) for the romanized titles.
TuneCore has no per-song listening page; /songs/<id>/lyrics exists only for
tracks with registered lyrics. Fail soft: None when the page can't be read.
"""
from __future__ import annotations

import html
import re

import httpx

from .twitter import UA

_META = re.compile(r"<meta\s+[^>]*>", re.I)
_ATTR = re.compile(r'(\w[\w:-]*)\s*=\s*"([^"]*)"|(\w[\w:-]*)\s*=\s*\'([^\']*)\'')
_NUM = re.compile(r"<div class=[\"']?list_number[\"']?>\s*(\d+)\s*</div>", re.I)
_TITLE = re.compile(r"list_song_title[\"']?>\s*<p>(.*?)<", re.S | re.I)
_LYRICS = re.compile(r"lyrics_btn[\"']?>\s*<a href=[\"']?([^\"'\s>]+)", re.I)
_CODE = re.compile(r"^https?://linkco\.re/(\w+)", re.I)


def _og_tags(page: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for tag in _META.findall(page):
        attrs = {}
        for m in _ATTR.finditer(tag):
            k = (m.group(1) or m.group(3)).lower()
            attrs[k] = m.group(2) if m.group(1) else m.group(4)
        key = attrs.get("property") or attrs.get("name")
        if key and "content" in attrs and key.lower() not in out:
            out[key.lower()] = html.unescape(attrs["content"]).strip()
    return out


def _page(url: str) -> str | None:
    try:
        r = httpx.get(url, headers={"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"},
                      timeout=20, follow_redirects=True)
        r.raise_for_status()
        return r.text
    except Exception:
        return None


def _tracks(page: str) -> list[dict]:
    """[{no, title, lyrics_url}] in album order, from the track list."""
    out = []
    marks = list(_NUM.finditer(page))
    for i, m in enumerate(marks):
        block = page[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(page)]
        t = _TITLE.search(block)
        if not t:
            continue
        lyr = _LYRICS.search(block)
        out.append({"no": int(m.group(1)), "title": html.unescape(t.group(1)).strip(),
                    "lyrics_url": html.unescape(lyr.group(1)).split("?")[0] if lyr else ""})
    return out


def fetch(url: str) -> dict | None:
    """{"title", "title_romaji", "image", "year", "tracks"} or None."""
    m = _CODE.match(url.strip())
    if not m:
        return None
    base = f"https://linkco.re/{m.group(1)}"
    ja = _page(base + "?lang=ja")
    if not ja:
        return None
    og = _og_tags(ja)
    image = og.get("og:image") or og.get("twitter:image") or ""
    y = re.search(r"(?<!\d)(?:19|20)\d{2}(?!\d)", og.get("og:description", ""))
    year = int(y.group(0)) if y else None

    tracks = _tracks(ja)
    en = _tracks(_page(base + "?lang=en") or "")
    romaji = {t["no"]: t["title"] for t in en}
    for t in tracks:
        r = romaji.get(t["no"], "")
        t["title_romaji"] = r if r != t["title"] else ""

    if len(tracks) == 1:          # a single: the song itself, no picking needed
        t = tracks[0]
        return {"title": t["title"], "title_romaji": t["title_romaji"], "image": image,
                "year": year, "tracks": [], "lyrics_url": t["lyrics_url"]}
    title = og.get("og:title") or og.get("twitter:title") or ""
    if not (title or image):
        return None
    return {"title": title, "title_romaji": "", "image": image, "year": year,
            "tracks": tracks, "lyrics_url": ""}
