"""Time and peak memory of the logged-in list endpoints vs total row count
(PERFORMANCE_ISSUES #13).

Calls the services in-process against a throwaway database, so the numbers are
the ranking itself, not HTTP. Run from backend/ with PostgreSQL up:

    uv run python ../tools/load_test/list_ranking_probe.py 200 2000 20000

Drops and recreates carbonsnap_probe_test on 127.0.0.1:5432.
"""

import os
import sys
import tempfile
import time
import tracemalloc
from datetime import UTC, datetime, timedelta
from pathlib import Path

URL = "postgresql+psycopg://carbonsnap:carbonsnap@127.0.0.1:5432/carbonsnap_probe_test"
_env_file = Path(tempfile.mkdtemp()) / "empty.env"
_env_file.write_text("")
os.environ.update(
    {
        "ENV_FILE": str(_env_file),
        "DATABASE_URL": URL,
        "JWT_SECRET_KEY": "probe-secret-at-least-32-bytes-long",
        "NO_PROXY": "*",
    }
)
sys.path.insert(0, os.getcwd())

from sqlalchemy import create_engine, event, insert, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

import app.models  # noqa: E402,F401
from app.db.base import Base  # noqa: E402
from app.models.forum import ForumComment, ForumPost, Like  # noqa: E402
from app.models.market import MarketItem  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.recommendation import ContentTopicAssignment, UserPreferenceProfile  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.forum import forum_service  # noqa: E402
from app.services.market import market_service  # noqa: E402
from app.services.project import project_service  # noqa: E402

TOPICS = ["plastic_recycling", "composting", "energy_saving", "transport", "uncategorized"]
AUTHOR, WITH_HISTORY, COLD_START = 1, 2, 3


def reset_db():
    admin = create_engine(URL.rsplit("/", 1)[0] + "/postgres", isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text('DROP DATABASE IF EXISTS "carbonsnap_probe_test" WITH (FORCE)'))
        conn.execute(text('CREATE DATABASE "carbonsnap_probe_test"'))
    admin.dispose()
    engine = create_engine(URL)
    Base.metadata.create_all(engine)
    return engine


def seed(engine, n):
    """n posts, n projects, n items, one every 5 minutes going back; a topic
    on each; a like on every 3rd post and a comment on every 4th."""
    now = datetime.now(UTC)
    ages = [now - timedelta(minutes=i * 5) for i in range(n)]
    with Session(engine) as s:
        s.execute(text("TRUNCATE users, content_topic_assignments RESTART IDENTITY CASCADE"))
        s.execute(
            insert(User),
            [{"username": f"u{i}", "email": f"u{i}@x.test", "password_hash": "x"} for i in (1, 2, 3)],
        )
        s.execute(
            insert(UserPreferenceProfile),
            [
                {
                    "user_id": WITH_HISTORY,
                    "profile_type": "content_interest",
                    "profile_key": "plastic_recycling",
                    "raw_score": 3.0,
                    "normalized_score": 0.9,
                    "confidence_score": 0.9,
                    "event_count": 5,
                }
            ],
        )
        s.execute(
            insert(ForumPost),
            [
                {"author_id": AUTHOR, "title": f"Post {i}", "content": "Rinse it. " * 40,
                 "created_at": ages[i]}
                for i in range(n)
            ],
        )
        s.execute(
            insert(Project),
            [
                {"creator_user_id": AUTHOR, "title": f"Project {i}", "description": "d " * 100,
                 "points_target": 1000, "deadline_at": now + timedelta(days=30 + i % 60),
                 "created_at": ages[i]}
                for i in range(n)
            ],
        )
        s.execute(
            insert(MarketItem),
            [
                {"seller_id": AUTHOR, "title": f"Item {i}", "description": "d " * 100,
                 "price_points": 10, "created_at": ages[i]}
                for i in range(n)
            ],
        )
        assignments = []
        for domain, content_type in (("forum", "post"), ("project", "project"), ("market", "item")):
            assignments += [
                {"domain": domain, "content_type": content_type, "content_id": i + 1,
                 "topic_id": TOPICS[i % len(TOPICS)], "confidence_score": 0.8, "source": "probe"}
                for i in range(n)
            ]
        s.execute(insert(ContentTopicAssignment), assignments)
        s.execute(
            insert(Like),
            [{"user_id": COLD_START, "target_type": "post", "target_id": i + 1}
             for i in range(0, n, 3)],
        )
        s.execute(
            insert(ForumComment),
            [{"post_id": i + 1, "user_id": COLD_START, "content": "Yes."} for i in range(0, n, 4)],
        )
        s.commit()
        s.execute(text("ANALYZE"))


CALLS = {
    "forum": lambda s, viewer, page: forum_service.list_posts(s, page, 20, viewer_user_id=viewer),
    "project": lambda s, viewer, page: project_service.list_projects(
        s, page, 20, viewer_user_id=viewer
    ),
    "market": lambda s, viewer, page: market_service.list_active_items(
        s, page, 20, viewer_user_id=viewer
    ),
}


def measure(engine, name, viewer, page):
    times = []
    for _ in range(3):
        with Session(engine) as s:
            t0 = time.perf_counter()
            result = CALLS[name](s, viewer, page)
            times.append(time.perf_counter() - t0)
    with Session(engine) as s:
        tracemalloc.start()
        CALLS[name](s, viewer, page)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    statements = []
    with engine.connect() as conn:
        event.listen(conn, "before_cursor_execute", lambda *a: statements.append(1))
        with Session(bind=conn) as s:
            CALLS[name](s, viewer, page)
    return sorted(times)[1], peak, len(statements), len(result["items"]), result["total"]


def main():
    engine = reset_db()
    sizes = [int(a) for a in sys.argv[1:]] or [200, 2000, 20000]
    page = int(os.environ.get("PROBE_PAGE", "1"))
    print(f"page {page}, 20 per page; median of 3 runs; peak = tracemalloc peak during one call")
    print(f"{'rows':>6} {'list':8} {'viewer':8} {'ms':>8} {'peak MB':>8} {'SQL':>4} {'items':>5} {'total':>6}")
    for n in sizes:
        seed(engine, n)
        for name in CALLS:
            for label, viewer in (("anon", None), ("cold", COLD_START), ("history", WITH_HISTORY)):
                ms, peak, sql, items, total = measure(engine, name, viewer, page)
                print(
                    f"{n:>6} {name:8} {label:8} {ms * 1000:>8.1f} {peak / 2**20:>8.1f} {sql:>4}"
                    f" {items:>5} {total:>6}",
                    flush=True,
                )


if __name__ == "__main__":
    main()
