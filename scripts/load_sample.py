"""Fill an EMPTY local database with made-up groups/oshi/songs/work history so
the page has something to show while you build it. All names are fictional.

    .venv/bin/python -m scripts.load_sample

Refuses to run when any oshi already exists. To start over, stop the server
and delete data/oshigoto.db.
"""
from datetime import date

from app.db import Base, SessionLocal, engine
from app.models import IdolGroup, Oshi, Song, WorkEntry
from app.services.profile import seed_defaults

GROUPS = [  # (name, english, color, group since)
    ("ステラリウム", "Stellarium", "#8b6cff", "2022-12-10"),
    ("はるいろ☆パレット", "Haruiro Palette", "#ff7aa8", "2023-08-05"),
    ("ネオン少女隊", "Neon Shoujo-tai", "#ff8a3d", "2022-06-18"),
    ("もふもふ放課後", "Mofumofu Houkago", "#ffc94d", "2023-09-10"),
    ("黒薔薇ノクターン", "Kurobara Nocturne", "#d14b6a", None),
    ("空色サイダー", "Sorairo Cider", "#4fd1e8", "2024-07-27"),
    ("ミントチョコ症候群", "Mint Choco Syndrome", "#6fe3c1", None),
]
OSHIS = [  # (name, romaji, group index, color, since)
    ("月城りん", "Tsukishiro Rin", 0, "#8b6cff", "2023-04-16"),
    ("朝比奈ひな", "Asahina Hina", 1, "#ff7aa8", "2024-01-08"),
    ("紅葉まい", "Momiji Mai", 2, "#ff8a3d", "2022-11-03"),
    ("水瀬あお", "Minase Ao", 1, "#43b8ff", "2024-06-22"),
    ("白雪ねね", "Shirayuki Nene", 0, "#c9c9e0", "2025-03-01"),
    ("小春ぽぽ", "Koharu Popo", 3, "#ffc94d", "2023-09-10"),
    ("夜宵くろえ", "Yayoi Kuroe", 4, "#d14b6a", "2024-03-30"),
    ("天音そら", "Amane Sora", 5, "#4fd1e8", "2024-10-05"),
    ("若葉みどり", "Wakaba Midori", 2, "#3ecf8e", "2025-08-10"),
    ("綿貫もも", "Watanuki Momo", 3, "#ffa0c8", "2025-01-19"),
    ("星河ゆめ", "Hoshikawa Yume", 5, "#b48cff", "2025-05-24"),
    ("薄荷ちょこ", "Hakka Choco", 6, "#6fe3c1", "2025-09-14"),
]
SONGS = [  # (group index, title, romaji, year, comment ja/en, point ja/en)
    (0, "銀河の端で待ってて", "Ginga no Hashi de Mattete", 2024,
     ("ライブで一番エモくなる曲。ラスサビのコール必聴。", "The one that hits hardest live."),
     ("りんの落ちサビ 2:48", "Rin's quiet solo at 2:48")),
    (0, "スノードーム", "Snow Dome", 2025, ("冬になると毎日聴いてる。", "On repeat every winter."),
     ("ねねの歌い出し", "Nene opens the song")),
    (1, "ハッピーエンドしか知らない", "Happy End Shika Shiranai", 2025,
     ("初見でも絶対楽しい。現場デビューにおすすめ。", "Great first-live song."),
     ("ひな×あおのハモり 1:12", "Hina × Ao harmony at 1:12")),
    (2, "午前零時のネオンサイン", "Gozen Reiji no Neon Sign", 2023,
     ("イントロで沸く。ネオンの代表曲。", "Their signature song."), None),
    (3, "放課後マシュマロ", "Houkago Marshmallow", 2024,
     ("ふわふわなのに振りが激しい。", "Fluffy song, intense choreo."), None),
    (4, "月下のレクイエム", "Gekka no Requiem", 2024, ("ヘドバン必至。", "Headbanging guaranteed."),
     ("くろえのシャウト 3:05", "Kuroe's scream at 3:05")),
    (5, "サイダー・ブルー", "Cider Blue", 2025, ("夏フェスで聴きたい。", "Made for summer festivals."), None),
]
WORK = [  # (start, end, title en/ja, org en/ja)
    ("2022", None, ("Backend Engineer", "バックエンドエンジニア"), ("(sample) Tech company · SEA", "(サンプル) テック企業")),
    ("2019", "2022", ("Software Engineer", "ソフトウェアエンジニア"), ("(sample) Startup", "(サンプル) スタートアップ")),
]


def main() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_defaults(db)
        if db.query(Oshi).first():
            raise SystemExit("oshi already exist; refusing to mix sample data into real data")
        groups = [IdolGroup(name_ja=ja, name_en=en, color=c,
                            since=date.fromisoformat(since) if since else None)
                  for ja, en, c, since in GROUPS]
        db.add_all(groups)
        db.flush()
        for i, (ja, rm, gi, c, since) in enumerate(OSHIS):
            db.add(Oshi(name_ja=ja, name_romaji=rm, group_id=groups[gi].id, color=c,
                        since=date.fromisoformat(since), sort_order=i))
        for i, (gi, ja, rm, y, cm, pt) in enumerate(SONGS):
            db.add(Song(group_id=groups[gi].id, title_ja=ja, title_romaji=rm, year=y,
                        comment_ja=cm[0], comment_en=cm[1],
                        point_ja=pt[0] if pt else None, point_en=pt[1] if pt else None,
                        linkcore_url="https://linkco.re/", sort_order=i))
        if not db.query(WorkEntry).first():
            for i, (start, end, title, org) in enumerate(WORK):
                db.add(WorkEntry(start=start, end=end, title_en=title[0], title_ja=title[1],
                                 org_en=org[0], org_ja=org[1], sort_order=i))
        db.commit()
    print(f"loaded {len(GROUPS)} groups, {len(OSHIS)} oshi, {len(SONGS)} songs")


if __name__ == "__main__":
    main()
