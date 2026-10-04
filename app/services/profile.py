"""Profile settings (key/value) and first-boot defaults."""
from sqlalchemy.orm import Session

from ..models import Project, Setting

# (key, label, kind) in the order the admin form shows them
SETTING_FIELDS: list[tuple[str, str, str]] = [
    ("nickname", "Nickname", "text"),
    ("role_en", "Role (EN)", "text"),
    ("role_ja", "Role (JA)", "text"),
    ("bio_en", "Bio (EN)", "textarea"),
    ("bio_ja", "Bio (JA)", "textarea"),
    ("github_url", "GitHub URL", "text"),
    ("linkedin_url", "LinkedIn URL", "text"),
    ("email", "Email (mail button; empty = hidden)", "text"),
    ("stack", "Stack (comma separated)", "text"),
    ("languages_en", "Languages (EN, one per line: Name | Level)", "textarea"),
    ("languages_ja", "Languages (JA, one per line: Name | Level)", "textarea"),
    ("fan_name", "Fan side name (e.g. katakana; shown in both languages)", "text"),
    ("home_en", "Based in (EN; both sides)", "text"),
    ("home_ja", "Based in (JA; both sides)", "text"),
    ("fan_title_en", "Fan side title (EN, HTML allowed)", "text"),
    ("fan_title_ja", "Fan side title (JA, HTML allowed)", "text"),
    ("fan_bio_en", "Fan side bio (EN)", "textarea"),
    ("fan_bio_ja", "Fan side bio (JA)", "textarea"),
    ("x_url", "X URL", "text"),
    ("instagram_url", "Instagram URL", "text"),
    ("tiktok_url", "TikTok URL", "text"),
    ("x_label", "X button label (e.g. @handle)", "text"),
    ("mygenba_url", "マイ現場 URL (fan side footer)", "text"),
]

DEFAULTS = {
    "nickname": "Dity",
    "role_en": "Backend Software Engineer",
    "role_ja": "バックエンドエンジニア",
    "bio_en": "I design and build backend systems for a living: APIs, data pipelines, and "
              "the infra that keeps them boring. Off the clock I build tools for my other "
              "job, being an idol fan. Lately I've been putting agentic coding into practice, "
              "working alongside AI agents to plan, build, and review code.",
    "bio_ja": "本業はバックエンドシステムの設計・開発。API、データパイプライン、そしてそれを安定して"
              "動かすインフラを作っています。仕事の外では、もうひとつのおしごと(オタク活動)のための"
              "ツールを作っています。最近は AI エージェントと一緒に設計・実装・レビューを進める、"
              "エージェント型コーディングを実践しています。",
    "github_url": "https://github.com/dityuiri",
    "linkedin_url": "",
    "email": "",
    "stack": "Go, Python, PostgreSQL, Redis, Docker",
    "languages_en": "Bahasa Indonesia | Native\n"
                    "English | Professional working proficiency\n"
                    "Japanese | JLPT N2",
    "languages_ja": "インドネシア語 | ネイティブ\n"
                    "英語 | ビジネスレベル\n"
                    "日本語 | JLPT N2",
    "fan_name": "ディティ",
    "home_en": "Based in Jakarta, Indonesia",
    "home_ja": "インドネシア・ジャカルタ在住",
    "fan_title_en": 'Fan life, <span class="grad">full power.</span>',
    "fan_title_ja": '<span class="grad">推し事</span>も全力。',
    "fan_bio_en": "I go to underground idol lives, and travel for them too.",
    "fan_bio_ja": "地下アイドル中心に現場に通っています。遠征もします。",
    "x_url": "",
    "instagram_url": "",
    "tiktok_url": "",
    "x_label": "X",
    "mygenba_url": "https://mygenba.dityuiri.my.id",
}


def get_settings(db: Session) -> dict[str, str]:
    out = dict(DEFAULTS)
    out.update({s.key: s.value or "" for s in db.query(Setting).all()})
    return out


def save_settings(db: Session, values: dict[str, str]) -> None:
    for key, _label, _kind in SETTING_FIELDS:
        if key not in values:
            continue
        row = db.get(Setting, key) or Setting(key=key)
        row.value = values[key].strip()
        db.add(row)
    db.commit()


def seed_defaults(db: Session) -> None:
    """First boot only (empty settings table): write defaults + the MyGenba card.
    Never runs again, so deleting the project later won't resurrect it."""
    if db.query(Setting).first():
        return
    for key, val in DEFAULTS.items():
        db.add(Setting(key=key, value=val))
    if not db.query(Project).first():
        db.add(Project(
            name="マイ現場", name_sub="MyGenba",
            sub_en="Idol schedule aggregator for fans",
            sub_ja="アイドルファンのためのスケジュール集約アプリ",
            blurb_en="Pulls idol groups' schedules from their public calendars into one "
                     "mobile-friendly calendar, then lets you plan a trip around the lives "
                     "you want to go to. Multi-user, open for sign-ups.",
            blurb_ja="アイドルグループの公開カレンダーからスケジュールを集めて、スマホで見やすい"
                     "ひとつのカレンダーに。行きたい現場を選んで遠征プランも作れます。"
                     "マルチユーザー対応、登録受付中。",
            url="https://mygenba.dityuiri.my.id",
            tags="FastAPI, PostgreSQL, Jinja2, Docker, Caddy",
            logo_path="static:img/mygenba_logo.png",
        ))
    db.commit()
