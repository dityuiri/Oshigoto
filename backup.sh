#!/usr/bin/env bash
# Daily backup of おしごと: gzipped pg_dump of the oshigoto database + a tarball of
# data/uploads (icons and jackets are files, not rows). Keeps the newest 14 of each.
# Add to cron on the VM:   15 5 * * * /path/to/Oshigoto/backup.sh
# pg_dump runs from a throwaway postgres:16 container on MyGenba's network, using
# DATABASE_URL from data/.env, so it needs nothing installed on the host.
set -euo pipefail
cd "$(dirname "$0")"
BACKUP_DIR="${OSHIGOTO_BACKUPS:-backups}"
mkdir -p "$BACKUP_DIR"
STAMP=$(date +%Y%m%d-%H%M%S)

URL=$( (grep '^DATABASE_URL=' data/.env || true) | cut -d= -f2- | tr -d '[:space:]')
[ -n "$URL" ] || { echo "backup FAILED: DATABASE_URL missing in data/.env" >&2; exit 1; }
URL="${URL/postgresql+psycopg:/postgresql:}"      # SQLAlchemy URL -> libpq URL

OUT="$BACKUP_DIR/oshigoto-$STAMP.sql.gz"
# write to .part and promote only on success, so a failed dump never looks like a backup
if docker run --rm --network "${MYGENBA_NETWORK:-mygenba_default}" postgres:16 \
     pg_dump --no-owner "$URL" | gzip > "$OUT.part"; then
  mv "$OUT.part" "$OUT"
else
  rm -f "$OUT.part"
  echo "backup FAILED: pg_dump error" >&2
  exit 1
fi
tar -czf "$BACKUP_DIR/uploads-$STAMP.tar.gz" -C data uploads

ls -t "$BACKUP_DIR"/oshigoto-*.sql.gz | tail -n +15 | xargs -r rm --
ls -t "$BACKUP_DIR"/uploads-*.tar.gz | tail -n +15 | xargs -r rm --
echo "backup done: oshigoto-$STAMP.sql.gz ($(du -h "$OUT" | cut -f1)) + uploads-$STAMP.tar.gz"
