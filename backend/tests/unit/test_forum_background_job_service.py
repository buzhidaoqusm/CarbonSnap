from __future__ import annotations

from app.services.forum import forum_background_job_service


class FakeExecutor:
    def __init__(self):
        self.submissions = []

    def submit(self, func, *args, **kwargs):
        self.submissions.append((func, args, kwargs))
        return "future"


def test_enqueue_post_refresh_runs_inline_in_tests(monkeypatch, app):
    indexed = {}
    mapped = {}

    monkeypatch.setattr(
        forum_background_job_service.forum_indexing_service,
        "reindex_post",
        lambda **kwargs: indexed.update(kwargs) or [],
    )
    monkeypatch.setattr(
        forum_background_job_service.topic_mapping_service,
        "refresh_forum_post_topics",
        lambda **kwargs: mapped.update(kwargs) or [],
    )

    with app.app_context():
        result = forum_background_job_service.enqueue_post_refresh(
            post_id=12,
            title="Bottle",
            content="Reuse tips",
        )

    assert result is None
    assert indexed == {"post_id": 12, "title": "Bottle", "content": "Reuse tips"}
    assert mapped == {"post_id": 12, "title": "Bottle", "content": "Reuse tips"}


def test_enqueue_post_refresh_uses_background_executor_outside_tests(monkeypatch, app):
    fake_executor = FakeExecutor()
    monkeypatch.setattr(forum_background_job_service, "_EXECUTOR", fake_executor)

    with app.app_context():
        app.config["TESTING"] = False
        try:
            result = forum_background_job_service.enqueue_post_refresh(
                post_id=7,
                title="Fast post",
                content="Return before indexing",
            )
        finally:
            app.config["TESTING"] = True

    assert result == "future"
    assert len(fake_executor.submissions) == 1
    func, args, kwargs = fake_executor.submissions[0]
    assert func is forum_background_job_service._run_with_app_context
    assert args[1] is forum_background_job_service._refresh_post_search_surfaces
    assert args[2] == {
        "post_id": 7,
        "title": "Fast post",
        "content": "Return before indexing",
    }
    assert kwargs == {}
