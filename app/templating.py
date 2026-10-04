from fastapi.templating import Jinja2Templates

from .config import APP_DIR
from .fetchers.music import service_of
from .services.media import url_for

templates = Jinja2Templates(directory=APP_DIR / "templates")

_SNS = {
    "x": "https://x.com/{}",
    "instagram": "https://www.instagram.com/{}/",
    "tiktok": "https://www.tiktok.com/@{}",
    "youtube": "https://www.youtube.com/@{}",
}


def static_url(path: str) -> str:
    """/static URL with the file's mtime appended, so browsers drop their cached
    copy whenever the file changes (otherwise new HTML can run with old JS)."""
    try:
        v = int((APP_DIR / "static" / path).stat().st_mtime)
    except OSError:
        return f"/static/{path}"
    return f"/static/{path}?v={v}"


_LISTEN_ICONS = {
    "spotify": "fa-brands fa-spotify",
    "apple": "fa-brands fa-apple",
    "ytmusic": "fa-brands fa-youtube",
    "youtube": "fa-brands fa-youtube",
}


def listen_icon(url: str | None) -> str:
    """Icon for the 配信で聴く button: the service's logo, headphones for TuneCore."""
    return _LISTEN_ICONS.get(service_of(url or ""), "fa-solid fa-headphones")


def sns_url(kind: str, value: str | None) -> str:
    """Admin fields take a handle or a full URL; the page always gets a URL."""
    v = (value or "").strip()
    if not v or v.startswith(("http://", "https://")):
        return v
    return _SNS[kind].format(v.lstrip("@"))


templates.env.globals.update(media_url=url_for, sns_url=sns_url, static_url=static_url,
                             listen_icon=listen_icon)
