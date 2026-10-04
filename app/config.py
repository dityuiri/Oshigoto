"""Paths + env. A `.env` next to the project root (or at OSHIGOTO_ENV) is loaded
first; real environment variables always win over it."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"


def _load_env(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_env(Path(os.environ.get("OSHIGOTO_ENV", ROOT / ".env")))

# everything mutable (SQLite file, downloaded icons/jackets) lives here
DATA_DIR = Path(os.environ.get("OSHIGOTO_DATA", ROOT / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# /admin is HTTP Basic auth; with no password set the admin is disabled entirely
ADMIN_USER = os.environ.get("ADMIN_USER", "dity")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
