#!/usr/bin/env python3
"""One-off SQLite → Postgres data copy for おしごと (same approach as MyGenba's).

Reuses the app's SQLAlchemy models, so Boolean 0/1 and Date strings come out as
the app expects. Builds the schema in Postgres from ``Base.metadata``, copies
every table in FK order, then moves the id sequences past the copied ids.

Imports ``app.models`` only (never ``app.main``), so nothing boots and the
first-boot seeding never runs against the target.

Images are files, not rows: copy ``data/uploads/`` to the server separately.

Run on the VM (the image ships only ``app/``, so mount this script in):

    docker compose run --rm --no-deps \\
      -v "$PWD/scripts:/app/scripts" \\
      -e SRC_SQLITE=/data/snapshot.db \\
      oshigoto python scripts/sqlite_to_pg.py

The target is DATABASE_URL (from data/.env), or PG_DSN when set.

Safety: refuses if the target already has rows. ``--force`` drops and recreates
the app's tables and reloads from scratch.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, func, insert, select, text

from app.config import DATABASE_URL
from app.models import Base


def main() -> int:
    src_path = os.environ.get("SRC_SQLITE")
    pg_dsn = os.environ.get("PG_DSN") or DATABASE_URL
    force = "--force" in sys.argv[1:]

    if not src_path or not pg_dsn:
        print("error: SRC_SQLITE and DATABASE_URL (or PG_DSN) are required", file=sys.stderr)
        return 2
    if not pg_dsn.startswith("postgresql"):
        print(f"error: target is not Postgres: {pg_dsn.split(':', 1)[0]}", file=sys.stderr)
        return 2
    if not os.path.exists(src_path):
        print(f"error: source sqlite not found: {src_path}", file=sys.stderr)
        return 2

    src = create_engine(f"sqlite:///{src_path}")
    dst = create_engine(pg_dsn)
    tables = Base.metadata.sorted_tables            # parents first

    if force:
        print("--force: dropping & recreating all app tables in Postgres")
        Base.metadata.drop_all(dst)
    Base.metadata.create_all(dst)

    with dst.connect() as d:
        existing = sum(d.execute(select(func.count()).select_from(t)).scalar() or 0
                       for t in tables)
    if existing and not force:
        print(f"error: target already holds {existing} rows, refusing to append.\n"
              f"       (did the app boot first and seed defaults?) re-run with --force "
              f"to wipe and reload.", file=sys.stderr)
        return 1

    print(f"copying {len(tables)} tables  {src_path}  ->  postgres")
    total = 0
    with src.connect() as s, dst.begin() as d:       # one transaction: all or nothing
        for t in tables:
            rows = [dict(r) for r in s.execute(select(t)).mappings()]
            if rows:
                d.execute(insert(t), rows)
            total += len(rows)
            print(f"  {t.name:16} {len(rows):>5}")

    # rows carry explicit ids, so the sequences are still at 1; the next INSERT
    # would collide unless they're moved past max(id)
    with dst.begin() as d:
        for t in tables:
            for c in t.primary_key.columns:
                seq = d.execute(text("SELECT pg_get_serial_sequence(:t, :c)"),
                                {"t": t.name, "c": c.name}).scalar()
                if seq:
                    d.execute(text(f"SELECT setval('{seq}', COALESCE((SELECT MAX({c.name}) "
                                   f"FROM {t.name}), 0) + 1, false)"))

    print(f"done: {total} rows across {len(tables)} tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
