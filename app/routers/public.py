from datetime import date

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..models import Oshi, Project, Song, WorkEntry
from ..services.profile import get_settings
from ..templating import templates

router = APIRouter()


def stack_by_group(oshis: list[Oshi]) -> list[list[Oshi]]:
    """One card slot per group, at the position of its first (main) oshi.
    Input order is kept, so the main one is whoever comes first in the admin."""
    slots: dict[int, list[Oshi]] = {}
    for o in oshis:
        slots.setdefault(o.group_id, []).append(o)
    return list(slots.values())


@router.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    oshis = (db.query(Oshi).options(joinedload(Oshi.group), joinedload(Oshi.prev_group))
             .filter(Oshi.visible.is_(True))
             .order_by(Oshi.sort_order, Oshi.id).all())
    current = [o for o in oshis if not o.graduated_on]
    # A group with an active oshi gets a card slot, and a graduated oshi of that
    # group shares it. Groups where everyone graduated go to the 卒業 row instead,
    # paired the same way, latest graduation first.
    active = {o.group_id for o in current}
    oshi_stacks = stack_by_group([o for o in oshis if o.group_id in active])
    graduated = sorted(stack_by_group([o for o in oshis if o.group_id not in active]),
                       key=lambda st: max(o.graduated_on for o in st), reverse=True)

    # 好き曲 tabs: one per group that has a current oshi, in oshi order
    groups, seen = [], set()
    for o in current:
        if o.group_id not in seen:
            seen.add(o.group_id)
            groups.append(o.group)
    songs = (db.query(Song).filter(Song.visible.is_(True), Song.group_id.in_(seen))
             .order_by(Song.sort_order, Song.id).all()) if seen else []
    songs_by_group = {g.id: [s for s in songs if s.group_id == g.id] for g in groups}
    members_by_group = {g.id: [o for o in current if o.group_id == g.id] for g in groups}

    return templates.TemplateResponse(request, "index.html", {
        "s": get_settings(db),
        "projects": db.query(Project).filter(Project.visible.is_(True))
                      .order_by(Project.sort_order, Project.id).all(),
        "work": db.query(WorkEntry).filter(WorkEntry.visible.is_(True))
                  .order_by(WorkEntry.sort_order, WorkEntry.id).all(),
        "oshis": current,
        "oshi_stacks": oshi_stacks,
        "graduated": graduated,
        "groups": groups,
        "songs_by_group": songs_by_group,
        "members_by_group": members_by_group,
        "today": date.today(),
    })
