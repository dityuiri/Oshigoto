"""/admin: list + form CRUD for every table, driven by the ENTITIES registry.

Every route depends on require_admin (HTTP Basic + same-origin writes).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from typing import Callable
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..db import get_db
from ..fetchers import music, twitter
from ..models import IdolGroup, Oshi, Project, Song, WorkEntry
from ..services import media
from ..services.profile import SETTING_FIELDS, get_settings, save_settings
from ..templating import templates

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


@dataclass
class F:
    """One form field. kind: text, textarea, date, color, int, bool, group,
    image, x_handle (text + fetch icon), song_link (url + auto-fill)."""
    name: str
    label: str
    kind: str = "text"
    required: bool = False
    help: str = ""
    wide: bool = False


@dataclass
class Entity:
    model: type
    title: str
    fields: list[F]
    row: Callable[[object], dict]
    has_visible: bool = True
    numbered: bool = False
    hint: str = ""
    extra_actions: list[tuple[str, str]] = field(default_factory=list)  # (label, POST url)

    @property
    def image_fields(self) -> list[F]:
        return [f for f in self.fields if f.kind == "image"]


def _group_name(o) -> str:
    return o.group.name_ja if o.group else ""


ENTITIES: dict[str, Entity] = {
    "oshi": Entity(
        model=Oshi, title="推し", numbered=True,
        hint="ドラッグで並べ替え。番号はサイトの No. と同じ (非表示・卒業した推しは数えません)。"
             "同じグループの推しは2人まで (現役・卒業どちらでも): 上にいる方がメインでカードに表示され、"
             "もう1人は切り替えで見られます。卒業した推しは、同じグループに現役の推しがいればそのカードに、"
             "いなければ「卒業した推し」に表示されます。",
        extra_actions=[("全員のアイコンを X から更新", "/admin/oshi/refresh-icons")],
        fields=[
            F("x_handle", "X ハンドル", "x_handle", help="@なしでもURLでもOK。「取得」でアイコンと名前を取ってきます", wide=True),
            F("name_ja", "名前 (日本語)", required=True),
            F("name_romaji", "Romaji"),
            F("group_id", "グループ", "group", required=True),
            F("prev_group_id", "前のグループ (任意)", "group", help="解散・移籍前のグループ。カードに「元〇〇」と表示されます"),
            F("since", "推し始め", "date"),
            F("instagram", "Instagram", help="ハンドルかURL"),
            F("tiktok", "TikTok", help="ハンドルかURL"),
            F("color", "メンカラ", "color"),
            F("graduated_on", "卒業日 (任意)", "date"),
            F("note_ja", "ひとこと (JA)", "textarea"),
            F("note_en", "Note (EN)", "textarea"),
            F("icon_path", "アイコン", "image", wide=True),
            F("visible", "サイトに表示", "bool"),
        ],
        row=lambda o: dict(thumb=o.icon_path, color=o.color, initial=o.name_ja[:1],
                           title=o.name_ja, shown=o.visible, active=o.visible and not o.graduated_on, gid=o.group_id,
                           sub=" · ".join(x for x in [_group_name(o),
                                                       "元" + o.prev_group.name_ja if o.prev_group else "",
                                                       o.name_romaji or "",
                                                       "卒業" if o.graduated_on else ""] if x)),
    ),
    "songs": Entity(
        model=Song, title="好き曲",
        hint="サイトではグループごとのタブに表示されます (推しがいるグループのみ)。",
        fields=[
            F("linkcore_url", "配信リンク", "song_link", wide=True,
              help="TuneCore (linkco.re) / Spotify / Apple Music / YouTube Music。"
                   "「自動入力」でタイトルとジャケットを取得。TuneCore のアルバムなら曲を選べます"),
            F("title_ja", "タイトル", required=True),
            F("title_romaji", "Romaji / English"),
            F("group_id", "グループ", "group", required=True),
            F("year", "リリース年", "int"),
            F("mv_url", "MV (YouTube)"),
            F("live_url", "ライブ映像 (YouTube)", help="MV がなくてもライブ映像だけでもOK"),
            F("lyrics_url", "歌詞ページ", help="TuneCore の歌詞ページ。アルバムから曲を選ぶと自動で入ります"),
            F("comment_ja", "コメント (JA)", "textarea"),
            F("comment_en", "Comment (EN)", "textarea"),
            F("point_ja", "推しポイント (JA)", help="例: りんの落ちサビ 2:48"),
            F("point_en", "Oshi point (EN)"),
            F("jacket_path", "ジャケット", "image", wide=True),
            F("visible", "サイトに表示", "bool"),
        ],
        row=lambda s: dict(thumb=s.jacket_path, color="#888",
                           initial="♪", square=True, title=s.title_ja,
                           sub=" · ".join(x for x in [_group_name(s), str(s.year or "")] if x)),
    ),
    "groups": Entity(
        model=IdolGroup, title="グループ", has_visible=False,
        hint="サイトではアイコンでグループを表示します (未設定なら頭文字)。",
        extra_actions=[("全グループのアイコンを X から更新", "/admin/groups/refresh-icons")],
        fields=[
            F("x_handle", "公式X ハンドル", "x_handle", help="@なしでもURLでもOK。「取得」でアイコンと名前を取ってきます", wide=True),
            F("name_ja", "名前 (日本語)", required=True),
            F("name_en", "Name (EN / romaji)"),
            F("since", "グループ推し始め", "date", help="推しカードに表示されます (日数なし)"),
            F("instagram", "Instagram", help="ハンドルかURL"),
            F("tiktok", "TikTok", help="ハンドルかURL"),
            F("youtube", "YouTube", help="@ハンドルかチャンネルURL"),
            F("official_url", "公式サイト URL", wide=True),
            F("icon_path", "アイコン", "image", wide=True),
        ],
        row=lambda g: dict(thumb=g.icon_path, color="#888", initial=g.name_ja[:1], title=g.name_ja,
                           sub=" · ".join(x for x in [g.name_en or "",
                                                       g.since.strftime("%Y.%m~") if g.since else ""] if x)),
    ),
    "work": Entity(
        model=WorkEntry, title="経歴",
        hint="会社名は書かずに説明だけ (例: Fintech startup · Indonesia)。",
        fields=[
            F("start", "Start (e.g. 2022)", required=True),
            F("end", "End (empty = now)"),
            F("title_en", "Title (EN)", required=True),
            F("title_ja", "Title (JA)"),
            F("org_en", "Company description (EN)"),
            F("org_ja", "Company description (JA)"),
            F("note_en", "Note (EN)", "textarea"),
            F("note_ja", "Note (JA)", "textarea"),
            F("visible", "Show on site", "bool"),
        ],
        row=lambda e: dict(color="#1f6f6b", initial="💼", title=e.title_en,
                           sub=f"{e.start} – {e.end or 'now'} · {e.org_en or ''}"),
    ),
    "projects": Entity(
        model=Project, title="Projects",
        fields=[
            F("name", "Name", required=True),
            F("name_sub", "Sub name (e.g. MyGenba)"),
            F("sub_en", "Tagline (EN)"),
            F("sub_ja", "Tagline (JA)"),
            F("blurb_en", "Description (EN)", "textarea"),
            F("blurb_ja", "Description (JA)", "textarea"),
            F("url", "URL"),
            F("tags", "Tags (comma separated)"),
            F("logo_path", "Logo", "image", wide=True),
            F("visible", "Show on site", "bool"),
        ],
        row=lambda p: dict(thumb=p.logo_path, color="#1d1d1f", initial=p.name[:1],
                           square=True, title=p.name, sub=p.sub_en or ""),
    ),
}

NAV = [("oshi", "推し"), ("songs", "好き曲"), ("groups", "グループ"),
       ("work", "経歴"), ("projects", "Projects"), ("profile", "Profile")]


def _ent(kind: str) -> Entity:
    if kind not in ENTITIES:
        raise HTTPException(404)
    return ENTITIES[kind]


def _back(url: str, msg: str = "") -> RedirectResponse:
    return RedirectResponse(url + (f"?msg={quote(msg)}" if msg else ""), status_code=303)


def _ctx(request: Request, active: str, **kw) -> dict:
    return {"nav": NAV, "active": active, "msg": request.query_params.get("msg", ""), **kw}


# ---------------------------------------------------------------- fixed routes

@router.get("")
def home():
    return RedirectResponse("/admin/oshi", status_code=303)


@router.get("/profile")
def profile_form(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "admin/profile.html", _ctx(
        request, "profile", fields=SETTING_FIELDS, values=get_settings(db)))


@router.post("/profile")
async def profile_save(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    save_settings(db, {k: str(v) for k, v in form.items()})
    return _back("/admin/profile", "保存しました")


@router.get("/api/x-profile")
def api_x_profile(handle: str = ""):
    h = twitter.parse_handle(handle)
    if not h:
        return JSONResponse({"error": "ハンドルが正しくありません"}, status_code=400)
    prof = twitter.fetch_profile(h)
    if not prof:
        return JSONResponse({"error": "取得できませんでした (時間をおいて再試行)"}, status_code=502)
    return {"handle": h, **prof}


@router.get("/api/song-link")
def api_song_link(url: str = ""):
    if not music.service_of(url.strip()):
        return JSONResponse({"error": "TuneCore / Spotify / Apple Music / YouTube Music のリンクを貼ってください"},
                            status_code=400)
    data = music.fetch(url)
    if not data:
        return JSONResponse({"error": "取得できませんでした"}, status_code=502)
    return data


def _refresh_icons(db: Session, kind: str, model) -> RedirectResponse:
    """Re-download every row's X icon. Spaced out: the endpoint 429s quickly."""
    ok = fail = 0
    for o in db.query(model).filter(model.x_handle.isnot(None), model.x_handle != "").all():
        prof = twitter.fetch_profile(o.x_handle)
        rel = media.download(kind, prof["icon_url"]) if prof and prof["icon_url"] else None
        if rel:
            if rel != o.icon_path:
                _drop_image(db, model, "icon_path", o.icon_path, o.id)
                o.icon_path = rel
            ok += 1
        else:
            fail += 1
        time.sleep(1.5)
    db.commit()
    return _back(f"/admin/{kind}", f"アイコン更新: 成功 {ok} / 失敗 {fail}")


@router.post("/oshi/refresh-icons")
def refresh_oshi_icons(db: Session = Depends(get_db)):
    return _refresh_icons(db, "oshi", Oshi)


@router.post("/groups/refresh-icons")
def refresh_group_icons(db: Session = Depends(get_db)):
    return _refresh_icons(db, "groups", IdolGroup)


# ---------------------------------------------------------------- generic CRUD

@router.get("/{kind}")
def list_view(kind: str, request: Request, db: Session = Depends(get_db)):
    ent = _ent(kind)
    q = db.query(ent.model)
    q = q.order_by(ent.model.name_ja) if kind == "groups" else q.order_by(ent.model.sort_order, ent.model.id)
    rows = [{"id": o.id, "visible": getattr(o, "visible", True), **ent.row(o)} for o in q.all()]
    if kind == "oshi":
        _number_oshi(rows)
    return templates.TemplateResponse(request, "admin/list.html", _ctx(
        request, kind, kind=kind, ent=ent, rows=rows))


@router.post("/{kind}/reorder")
async def reorder(kind: str, request: Request, db: Session = Depends(get_db)):
    ent = _ent(kind)
    if not hasattr(ent.model, "sort_order"):
        raise HTTPException(400)
    ids = [int(i) for i in (await request.json()).get("ids", [])]
    objs = {o.id: o for o in db.query(ent.model).filter(ent.model.id.in_(ids)).all()}
    for pos, i in enumerate(ids):
        if i in objs:
            objs[i].sort_order = pos
    db.commit()
    return {"ok": True}


def _number_oshi(rows: list[dict]) -> None:
    """Same numbering as the site: one No. per group that has an active oshi,
    at its first shown member; the 2nd oshi (active or graduated) shares it."""
    carded = {r["gid"] for r in rows if r["active"]}
    slot_of: dict[int, int] = {}
    for r in rows:
        if not (r["shown"] and r["gid"] in carded):
            continue
        if r["gid"] in slot_of:
            r["num"], r["pair"] = slot_of[r["gid"]], True
        else:
            r["num"] = slot_of[r["gid"]] = len(slot_of) + 1


PAIR_MAX = 2


def _pair_full(db: Session, o: Oshi) -> bool:
    """Max 2 shown oshi per group, active and graduated together."""
    if not o.visible or not o.group_id:
        return False
    q = db.query(func.count()).select_from(Oshi).filter(
        Oshi.group_id == o.group_id, Oshi.visible.is_(True), Oshi.id != (o.id or 0))
    return q.scalar() >= PAIR_MAX


PAIR_ERROR = f"同じグループの推しは{PAIR_MAX}人まで (現役・卒業あわせて)。どちらかを非表示にしてください"


def _groups(db: Session) -> list[IdolGroup]:
    return db.query(IdolGroup).order_by(IdolGroup.name_ja).all()


def _form(request: Request, db: Session, kind: str, obj, error: str = "", status: int = 200):
    ent = _ent(kind)
    return templates.TemplateResponse(request, "admin/form.html", _ctx(
        request, kind, kind=kind, ent=ent, obj=obj, groups=_groups(db), error=error),
        status_code=status)


@router.get("/{kind}/new")
def new_form(kind: str, request: Request, db: Session = Depends(get_db)):
    ent = _ent(kind)
    obj = ent.model()
    for f in ent.fields:          # column defaults only apply on insert; prefill the form
        if f.kind == "bool":
            setattr(obj, f.name, True)
        elif f.kind == "color":
            setattr(obj, f.name, "#ff6fae")
    if kind == "songs" and request.query_params.get("group"):
        obj.group_id = int(request.query_params["group"])
    return _form(request, db, kind, obj)


@router.get("/{kind}/{obj_id}")
def edit_form(kind: str, obj_id: int, request: Request, db: Session = Depends(get_db)):
    obj = db.get(_ent(kind).model, obj_id) or _404()
    return _form(request, db, kind, obj)


def _404():
    raise HTTPException(404)


def _parse(f: F, raw: str):
    raw = raw.strip()
    if f.kind == "bool":
        return raw in ("1", "on", "true")
    if not raw:
        return None
    if f.kind == "date":
        return date.fromisoformat(raw)
    if f.kind in ("int", "group"):
        return int(raw)
    if f.kind == "x_handle":
        return twitter.parse_handle(raw) or raw.lstrip("@")
    return raw


def _drop_image(db: Session, model, col: str, rel: str | None, keep_id: int | None) -> None:
    """Delete a replaced upload unless another row still points at it."""
    if not rel:
        return
    others = db.query(func.count()).select_from(model).filter(
        getattr(model, col) == rel, model.id != (keep_id or 0)).scalar()
    if not others:
        media.delete(rel)


@router.post("/{kind}/{obj_id}")
async def save(kind: str, obj_id: str, request: Request, db: Session = Depends(get_db)):
    ent = _ent(kind)
    is_new = obj_id == "new"
    obj = ent.model() if is_new else (db.get(ent.model, int(obj_id)) if obj_id.isdigit() else None)
    if obj is None:
        raise HTTPException(404)
    form = await request.form()

    errors = []
    for f in ent.fields:
        if f.kind == "image":
            continue
        try:
            val = _parse(f, str(form.get(f.name, "")))
        except ValueError:
            errors.append(f"{f.label}: 形式が正しくありません")
            continue
        if f.required and val in (None, ""):
            errors.append(f"{f.label} は必須です")
        if f.kind == "color" and not val:
            val = "#ff6fae"
        setattr(obj, f.name, val)
    if kind == "oshi" and not errors:
        with db.no_autoflush:
            if _pair_full(db, obj):
                errors.append(PAIR_ERROR)
    if errors:
        if obj in db:
            db.expunge(obj)   # keep the typed values for the re-rendered form, never flush them
        return _form(request, db, kind, obj, " / ".join(errors), status=400)

    # images last, so a failed validation never leaves orphan files behind
    for f in ent.image_fields:
        old = getattr(obj, f.name)
        new = old
        upload = form.get(f.name + "__file")
        fetch_url = str(form.get(f.name + "__url", "")).strip()
        if form.get(f.name + "__clear"):
            new = None
        elif upload is not None and getattr(upload, "filename", ""):
            data = await upload.read()
            new = media.save_bytes(kind, data, upload.content_type or "") or old
            if new == old and data:
                errors.append(f"{f.label}: 画像 (jpg/png/webp/gif, 5MB まで) を選んでください")
        elif fetch_url:
            new = media.download(kind, fetch_url) or old
            if new == old:
                errors.append(f"{f.label}: 画像をダウンロードできませんでした")
        if new != old:
            _drop_image(db, ent.model, f.name, old, obj.id)
            setattr(obj, f.name, new)

    if is_new and hasattr(ent.model, "sort_order"):
        obj.sort_order = (db.query(func.max(ent.model.sort_order)).scalar() or 0) + 1
        db.add(obj)
    elif is_new:
        db.add(obj)
    db.commit()
    return _back(f"/admin/{kind}", "保存しました" + (f" ({' / '.join(errors)})" if errors else ""))


@router.post("/{kind}/{obj_id}/toggle")
def toggle(kind: str, obj_id: int, db: Session = Depends(get_db)):
    obj = db.get(_ent(kind).model, obj_id) or _404()
    obj.visible = not obj.visible
    if kind == "oshi" and _pair_full(db, obj):
        db.rollback()
        return _back(f"/admin/{kind}", PAIR_ERROR)
    db.commit()
    return _back(f"/admin/{kind}")


@router.post("/{kind}/{obj_id}/delete")
def delete(kind: str, obj_id: int, db: Session = Depends(get_db)):
    ent = _ent(kind)
    obj = db.get(ent.model, obj_id) or _404()
    if kind == "groups" and (obj.oshis or obj.songs):
        return _back("/admin/groups", "推しか曲が登録されているグループは削除できません")
    if kind == "groups":
        db.query(Oshi).filter(Oshi.prev_group_id == obj.id).update({Oshi.prev_group_id: None})
    for f in ent.image_fields:
        _drop_image(db, ent.model, f.name, getattr(obj, f.name), obj.id)
    db.delete(obj)
    db.commit()
    return _back(f"/admin/{kind}", "削除しました")
