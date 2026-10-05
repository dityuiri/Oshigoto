# おしごと (Oshigoto)

Personal profile site for `dityuiri.my.id`. Two sides that read the same:
お仕事 (o-shigoto, work) and 推し事 (oshigoto, fan life).

- **Work side** (English by default): nickname, role, bio, GitHub / LinkedIn / mail
  buttons, projects (MyGenba), experience without company names, stack.
- **Fan side** (Japanese by default): X / Instagram / TikTok, 推し cards in a fixed
  order with a small "No.01" serial, 好き曲 as one tab per group that has an oshi,
  and a quiet 卒業した推し row.

Each side has its own EN / 日本語 switch. `?work=ja&fan=en` overrides it for
shareable links; otherwise the visitor's last choice is remembered.
On phones the sides are tabs (お仕事 by default); `/#fan` opens 推し事, and
switching tabs updates the hash so the address bar always shares the open side.

## Stack

FastAPI + Jinja2 + SQLAlchemy. SQLite at `data/oshigoto.db` by default, Postgres
when `DATABASE_URL` is set. Icons and jackets are downloaded once into
`data/uploads/` and served from `/media`, never hotlinked.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # then set ADMIN_PASSWORD
./run.sh                      # http://localhost:8710
```

Optional, for a page with something on it while building:

```bash
.venv/bin/python -m scripts.load_sample   # fictional groups/oshi/songs, empty DB only
```

To start over, stop the server and delete `data/oshigoto.db`.

## Admin

`/admin`, HTTP Basic auth (`ADMIN_USER` / `ADMIN_PASSWORD`). Disabled while
`ADMIN_PASSWORD` is empty. Writes must come from the same origin.

- **推し**: drag to reorder (the number shown matches the site's No.), show/hide,
  「取得」 pulls the icon and name from an X handle, or upload an icon by hand.
  A graduation date moves the oshi to 卒業した推し. 前のグループ (when her group
  disbanded or she moved) shows as "ex-Group / 元Group" on her card.
  Up to 2 shown oshi per group (active or graduated): the higher one in the list
  is the main card, the other is one tap away via the ⇄ button on the card. A
  graduated oshi shares her group's card (dimmed, 卒業 badge) while you have an
  active oshi there, otherwise she sits in the 卒業した推し row. 「全員のアイコンを X から更新」
  re-downloads every icon.
- **好き曲**: paste a listen link (TuneCore `linkco.re`, Spotify, Apple Music or
  YouTube Music) and press 自動入力 for the title, jacket and year. A TuneCore
  album shows its track list: pick the song to fill its title, romaji and lyrics
  page (TuneCore has no per-song listen page, so 配信で聴く still opens the album;
  paste a Spotify / Apple Music track link instead for that exact song). Spotify
  only returns romanized titles. MV and ライブ映像 links are optional.
- **グループ**: name, icon, X / Instagram / TikTok / YouTube / official site, and
  グループ推し始め (when you started supporting the group itself; shown on each
  member card without a day count). 「取得」 pulls the icon and name from the
  official X handle, same as 推し.
- **経歴**, **Projects**, **Profile** (nickname, bio, links, mail
  address; the mail button is hidden while the address is empty).

The X icon fetch uses a free unofficial endpoint that rate-limits per IP (HTTP
429). When it fails, wait a bit or upload the image by hand.

## Deploy

Runs on the MyGenba VM as its own compose project, joined to MyGenba's network:
MyGenba's Caddy serves `dityuiri.my.id`, and MyGenba's Postgres holds an
`oshigoto` database. Host state lives in `./data` (`.env`, `uploads/`), never in
the image or git.

### First time

1. **DNS**: `@` A → the VM's IP (`www` is a CNAME to it; Caddy redirects it to the
   apex). Mail stays on the registrar's host: `mail` A → its IP, MX → `mail.dityuiri.my.id`.
2. **VM, clone** next to MyGenba and make the data dir:
   ```bash
   git clone <this repo> ~/Oshigoto && mkdir -p ~/Oshigoto/data/uploads
   ```
3. **VM, database** in MyGenba's Postgres (pick a URL-safe password, e.g.
   `python3 -c "import secrets; print(secrets.token_urlsafe(24))"`):
   ```bash
   cd ~/MyGenba && docker compose exec postgres psql -U mygenba -d mygenba \
     -c "CREATE ROLE oshigoto LOGIN PASSWORD '<db password>';" \
     -c "CREATE DATABASE oshigoto OWNER oshigoto;"
   ```
4. **VM, `~/Oshigoto/data/.env`** (never committed):
   ```
   ADMIN_USER=dity
   ADMIN_PASSWORD=<a new, long admin password>
   DATABASE_URL=postgresql+psycopg://oshigoto:<db password>@postgres:5432/oshigoto
   ```
5. **Local, ship the data**: a consistent snapshot of the SQLite DB plus the images.
   Stop editing locally from here on; the live admin becomes the source of truth.
   ```bash
   sqlite3 data/oshigoto.db ".backup /tmp/oshigoto-snapshot.db"
   scp /tmp/oshigoto-snapshot.db ubuntu@<VM IP>:~/Oshigoto/data/snapshot.db
   rsync -a data/uploads/ ubuntu@<VM IP>:~/Oshigoto/data/uploads/
   ```
6. **VM, migrate before the first start** (the app seeds defaults into an empty
   DB on boot; the script refuses a non-empty target, `--force` wipes it):
   ```bash
   cd ~/Oshigoto && docker compose build
   docker compose run --rm --no-deps -v "$PWD/scripts:/app/scripts" \
     -e SRC_SQLITE=/data/snapshot.db oshigoto python scripts/sqlite_to_pg.py
   docker compose up -d
   ```
   Keep `data/snapshot.db` until the live site checks out, then delete it.
7. **VM, Caddy**: pull MyGenba with the `dityuiri.my.id` and `www` blocks in its Caddyfile, then
   `cd ~/MyGenba && docker compose restart caddy`. A restart, not `caddy reload`:
   the Caddyfile is a single-file bind mount and `git pull` replaces the file, so
   the running container would keep seeing the old one. Certificates live in a
   volume and survive. Caddy gets the new one once DNS resolves.
8. **VM, backups**: `crontab -e` → `15 5 * * * ~/Oshigoto/backup.sh`
   (pg_dump + uploads tarball into `backups/`, newest 14 kept).

### Updates

`./update.sh` on the VM (git pull + rebuild). Data is untouched: rows stay in
Postgres, images in `./data/uploads`. New nullable columns are added on boot;
anything else (renames, NOT NULL columns) needs a manual migration.

If MyGenba's network isn't `mygenba_default` (`docker network ls`), set
`MYGENBA_NETWORK=<name>` in a `.env` next to `docker-compose.yml`.

## Layout

```
app/
  main.py            app + static/media mounts
  config.py, db.py   env, paths, engine
  models.py          settings, projects, work entries, groups, oshi, songs
  routers/public.py  the page
  routers/admin.py   generic list/form CRUD driven by the ENTITIES registry
  fetchers/          X profile icon, song links (TuneCore / Spotify / Apple / YT Music)
  services/          profile defaults, image storage
  templates/, static/
mockups/             the original static design mockups
scripts/            load_sample.py (dev), sqlite_to_pg.py (one-off migration)
docker-compose.yml, update.sh, backup.sh   production on the MyGenba VM
```
