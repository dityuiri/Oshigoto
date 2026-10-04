"""HTTP Basic auth for /admin, plus a same-origin check on writes (browsers
resend Basic credentials automatically, so a cross-site form post would
otherwise ride on them)."""
from secrets import compare_digest
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .config import ADMIN_PASSWORD, ADMIN_USER

_basic = HTTPBasic(auto_error=False)


def require_admin(request: Request,
                  creds: HTTPBasicCredentials | None = Depends(_basic)) -> None:
    if not ADMIN_PASSWORD:
        raise HTTPException(503, "Admin is disabled: set ADMIN_PASSWORD in .env")
    ok = creds is not None and \
        compare_digest(creds.username.encode(), ADMIN_USER.encode()) and \
        compare_digest(creds.password.encode(), ADMIN_PASSWORD.encode())
    if not ok:
        raise HTTPException(401, "Unauthorized",
                            headers={"WWW-Authenticate": 'Basic realm="oshigoto admin"'})
    if request.method not in ("GET", "HEAD"):
        source = request.headers.get("origin") or request.headers.get("referer") or ""
        if urlparse(source).netloc != request.headers.get("host"):
            raise HTTPException(403, "Cross-origin write refused")
