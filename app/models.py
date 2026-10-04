"""Everything shown on the page. Bilingual text is stored as *_en / *_ja pairs;
the page falls back to the other language when one side is empty."""
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Setting(Base):
    """Free-form profile text and links (nickname, bio, SNS URLs, ...)."""
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    name_sub: Mapped[str | None] = mapped_column(String(120))     # e.g. romaji/English name
    sub_en: Mapped[str | None] = mapped_column(String(200))
    sub_ja: Mapped[str | None] = mapped_column(String(200))
    blurb_en: Mapped[str | None] = mapped_column(Text)
    blurb_ja: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(500))
    tags: Mapped[str | None] = mapped_column(String(300))         # comma separated
    logo_path: Mapped[str | None] = mapped_column(String(300))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)


class WorkEntry(Base):
    """One job. No company names by design: org_* is a description."""
    __tablename__ = "work_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    start: Mapped[str] = mapped_column(String(20))                 # "2022" or "2022.04"
    end: Mapped[str | None] = mapped_column(String(20))            # empty = present
    title_en: Mapped[str] = mapped_column(String(120))
    title_ja: Mapped[str | None] = mapped_column(String(120))
    org_en: Mapped[str | None] = mapped_column(String(200))
    org_ja: Mapped[str | None] = mapped_column(String(200))
    note_en: Mapped[str | None] = mapped_column(Text)
    note_ja: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)


class IdolGroup(Base):
    __tablename__ = "idol_groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    name_ja: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str | None] = mapped_column(String(120))
    color: Mapped[str] = mapped_column(String(9), default="#ff6fae")
    x_handle: Mapped[str | None] = mapped_column(String(40))
    official_url: Mapped[str | None] = mapped_column(String(500))
    instagram: Mapped[str | None] = mapped_column(String(200))    # handle or URL
    tiktok: Mapped[str | None] = mapped_column(String(200))       # handle or URL
    youtube: Mapped[str | None] = mapped_column(String(200))      # @handle or channel URL
    icon_path: Mapped[str | None] = mapped_column(String(300))
    since: Mapped[date | None] = mapped_column(Date)               # when I started on the group itself

    oshis: Mapped[list["Oshi"]] = relationship(back_populates="group", foreign_keys="Oshi.group_id")
    songs: Mapped[list["Song"]] = relationship(back_populates="group")


class Oshi(Base):
    __tablename__ = "oshis"
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("idol_groups.id"))
    prev_group_id: Mapped[int | None] = mapped_column(ForeignKey("idol_groups.id"))  # before a disband / move
    name_ja: Mapped[str] = mapped_column(String(120))
    name_romaji: Mapped[str | None] = mapped_column(String(120))
    x_handle: Mapped[str | None] = mapped_column(String(40))
    instagram: Mapped[str | None] = mapped_column(String(200))    # handle or URL
    tiktok: Mapped[str | None] = mapped_column(String(200))       # handle or URL
    color: Mapped[str] = mapped_column(String(9), default="#ff6fae")   # メンカラ
    since: Mapped[date | None] = mapped_column(Date)
    graduated_on: Mapped[date | None] = mapped_column(Date)
    note_en: Mapped[str | None] = mapped_column(Text)
    note_ja: Mapped[str | None] = mapped_column(Text)
    icon_path: Mapped[str | None] = mapped_column(String(300))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)

    group: Mapped[IdolGroup] = relationship(back_populates="oshis", foreign_keys=[group_id])
    prev_group: Mapped[IdolGroup | None] = relationship(foreign_keys=[prev_group_id])


class Song(Base):
    __tablename__ = "songs"
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("idol_groups.id"))
    title_ja: Mapped[str] = mapped_column(String(200))
    title_romaji: Mapped[str | None] = mapped_column(String(200))
    year: Mapped[int | None] = mapped_column(Integer)
    linkcore_url: Mapped[str | None] = mapped_column(String(500))  # listen link: TuneCore / Spotify / Apple Music / YT Music
    lyrics_url: Mapped[str | None] = mapped_column(String(500))    # TuneCore lyrics page
    mv_url: Mapped[str | None] = mapped_column(String(500))
    live_url: Mapped[str | None] = mapped_column(String(500))      # live performance video
    jacket_path: Mapped[str | None] = mapped_column(String(300))
    comment_en: Mapped[str | None] = mapped_column(Text)
    comment_ja: Mapped[str | None] = mapped_column(Text)
    point_en: Mapped[str | None] = mapped_column(String(200))      # 推しポイント
    point_ja: Mapped[str | None] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)

    group: Mapped[IdolGroup] = relationship(back_populates="songs")
