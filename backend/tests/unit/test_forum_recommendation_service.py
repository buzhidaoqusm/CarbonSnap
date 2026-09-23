import uuid
from types import SimpleNamespace

import pytest
from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.forum import ForumPost
from app.models.user import User
from app.repositories.recommendation import preference_profile_repository
from app.services.recommendation import forum_recommendation_service


def _make_user(username: str = "ranker", email: str = "ranker@example.com") -> User:
    suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"{username}_{suffix}",
        email=f"{suffix}_{email}",
        password_hash=generate_password_hash("password123"),
    )
    db.session.add(user)
    db.session.flush()
    return user


def _make_post(author_id: int, title: str, content: str) -> ForumPost:
    post = ForumPost(author_id=author_id, title=title, content=content)
    db.session.add(post)
    db.session.flush()
    return post


def _topic_assignment(topic_id: str, confidence_score: float = 1.0) -> SimpleNamespace:
    return SimpleNamespace(topic_id=topic_id, confidence_score=confidence_score)


class TestForumRecommendationService:
    def test_build_ranking_context_loads_batched_features_once(self, monkeypatch):
        user = _make_user()
        first_post = _make_post(user.id, "Plastic bottle tips", "Bottle recycling guide")
        second_post = _make_post(user.id, "Battery recycling", "Old batteries")

        call_counts = {
            "topic_assignments": 0,
            "viewed": 0,
            "long_viewed": 0,
            "commented": 0,
            "likes": 0,
            "exposure": 0,
            "profile": 0,
        }

        monkeypatch.setattr(
            "app.services.recommendation.preference_profile_service.has_sufficient_history",
            lambda user_id: True,
        )

        def get_profile_snapshot(user_id):
            call_counts["profile"] += 1
            return {"battery-recycling": 0.9}

        monkeypatch.setattr(
            "app.services.recommendation.preference_profile_service.get_profile_snapshot",
            get_profile_snapshot,
        )

        def load_topic_assignments(*, domain, content_type, content_ids):
            call_counts["topic_assignments"] += 1
            assert domain == "forum"
            assert content_type == "post"
            assert content_ids == [first_post.id, second_post.id]
            return {
                first_post.id: [
                    SimpleNamespace(topic_id="plastic-recycling", confidence_score=1.0)
                ],
                second_post.id: [
                    SimpleNamespace(topic_id="battery-recycling", confidence_score=1.0)
                ],
            }

        monkeypatch.setattr(
            forum_recommendation_service.preference_profile_repository,
            "list_content_topic_assignments_for_content_ids",
            load_topic_assignments,
        )

        def load_viewed_post_ids(user_id, **kwargs):
            if kwargs.get("action_types") == ["view", "long_view"]:
                call_counts["viewed"] += 1
                return {first_post.id}
            if kwargs.get("action_types") == ["long_view"]:
                call_counts["long_viewed"] += 1
                return {second_post.id}
            if kwargs.get("action_types") == ["comment_or_reply"]:
                call_counts["commented"] += 1
                return {second_post.id}
            raise AssertionError(f"unexpected behavior lookup: {kwargs}")

        monkeypatch.setattr(
            forum_recommendation_service.behavior_event_repository,
            "list_behavior_target_ids_for_user",
            load_viewed_post_ids,
        )
        monkeypatch.setattr(
            forum_recommendation_service.behavior_event_repository,
            "list_active_forum_like_target_ids_for_user",
            lambda *args, **kwargs: (
                call_counts.__setitem__("likes", call_counts["likes"] + 1) or {second_post.id}
            ),
        )
        monkeypatch.setattr(
            forum_recommendation_service.behavior_event_repository,
            "list_recent_topic_exposure_counts_for_user",
            lambda *args, **kwargs: (
                call_counts.__setitem__("exposure", call_counts["exposure"] + 1)
                or {"battery-recycling": 2, "plastic-recycling": 1}
            ),
        )

        context = forum_recommendation_service.build_ranking_context(
            user_id=user.id,
            posts=[first_post, second_post],
        )

        assert call_counts == {
            "topic_assignments": 1,
            "viewed": 1,
            "long_viewed": 1,
            "commented": 1,
            "likes": 1,
            "exposure": 1,
            "profile": 1,
        }
        assert context["has_history"] is True
        assert context["profile_snapshot"] == {"battery-recycling": 0.9}
        assert context["viewed_post_ids"] == {first_post.id}
        assert context["long_viewed_post_ids"] == {second_post.id}
        assert context["engaged_post_ids"] == {second_post.id}
        assert context["recent_topic_exposure"] == {"battery-recycling": 2, "plastic-recycling": 1}
        assert [
            row.topic_id for row in context["topic_assignments_by_post_id"][second_post.id]
        ] == ["battery-recycling"]

    def test_preference_match_is_bounded_to_one(self):
        user = _make_user("bounded", "bounded@example.com")
        post = _make_post(user.id, "Mixed recycling", "Mixed recycling content")

        preference_profile_repository.replace_content_topic_assignments(
            domain="forum",
            content_type="post",
            content_id=post.id,
            topics=[
                {"topic_id": "plastic-recycling", "confidence_score": 1.0},
                {"topic_id": "battery-recycling", "confidence_score": 1.0},
            ],
        )

        context = {
            "profile_snapshot": {"plastic-recycling": 0.9, "battery-recycling": 0.8},
            "topic_assignments_by_post_id": {
                post.id: [
                    SimpleNamespace(topic_id="plastic-recycling", confidence_score=1.0),
                    SimpleNamespace(topic_id="battery-recycling", confidence_score=1.0),
                ]
            },
        }

        assert forum_recommendation_service._preference_match_score(post, context) == 1.0

    def test_novelty_score_distinguishes_view_states(self):
        user = _make_user("novelty-states", "novelty-states@example.com")
        unseen = _make_post(user.id, "Unseen", "Unseen content")
        viewed = _make_post(user.id, "Viewed", "Viewed content")
        long_viewed = _make_post(user.id, "Long viewed", "Long viewed content")
        engaged = _make_post(user.id, "Engaged", "Engaged content")

        context = {
            "viewed_post_ids": {viewed.id},
            "long_viewed_post_ids": {long_viewed.id},
            "engaged_post_ids": {engaged.id},
        }

        assert forum_recommendation_service._novelty_score(unseen, context) == 1.0
        assert forum_recommendation_service._novelty_score(viewed, context) == 0.8
        assert forum_recommendation_service._novelty_score(long_viewed, context) == 0.65
        assert forum_recommendation_service._novelty_score(engaged, context) == 0.55

    def test_unfamiliarity_uses_uncategorized_fallback(self):
        user = _make_user("unfamiliar", "unfamiliar@example.com")
        fallback_post = _make_post(user.id, "Fallback", "Fallback content")
        matched_post = _make_post(user.id, "Matched", "Matched content")

        preference_profile_repository.replace_content_topic_assignments(
            domain="forum",
            content_type="post",
            content_id=fallback_post.id,
            topics=[{"topic_id": "uncategorized", "confidence_score": 1.0}],
        )
        preference_profile_repository.replace_content_topic_assignments(
            domain="forum",
            content_type="post",
            content_id=matched_post.id,
            topics=[{"topic_id": "battery-recycling", "confidence_score": 1.0}],
        )

        context = {
            "profile_snapshot": {"battery-recycling": 0.7},
            "topic_assignments_by_post_id": {
                fallback_post.id: [SimpleNamespace(topic_id="uncategorized", confidence_score=1.0)],
                matched_post.id: [
                    SimpleNamespace(topic_id="battery-recycling", confidence_score=1.0)
                ],
            },
        }

        assert forum_recommendation_service._unfamiliarity_score(fallback_post, context) == 0.5
        assert forum_recommendation_service._unfamiliarity_score(matched_post, context) == 0.3

    def test_is_exploitation_candidate_accepts_preference_match_recency_or_engagement(
        self, monkeypatch
    ):
        user = _make_user("exploit-candidate", "exploit-candidate@example.com")
        matched_post = _make_post(user.id, "Battery guide", "Battery guide content")
        fallback_post = _make_post(user.id, "Recent fallback", "Recent fallback content")

        preference_profile_repository.replace_content_topic_assignments(
            domain="forum",
            content_type="post",
            content_id=matched_post.id,
            topics=[{"topic_id": "battery-recycling", "confidence_score": 1.0}],
        )

        matched_context = {
            "profile_snapshot": {"battery-recycling": 0.7},
            "viewed_post_ids": set(),
            "recent_topic_exposure": {},
            "topic_assignments_by_post_id": {
                matched_post.id: [
                    SimpleNamespace(topic_id="battery-recycling", confidence_score=1.0)
                ]
            },
        }

        assert forum_recommendation_service.is_exploitation_candidate(
            matched_post, ranking_context=matched_context
        )

        monkeypatch.setattr(forum_recommendation_service, "_recency_score", lambda post: 0.6)
        monkeypatch.setattr(forum_recommendation_service, "_engagement_score", lambda post: 0.0)

        fallback_context = {
            "profile_snapshot": {},
            "viewed_post_ids": set(),
            "recent_topic_exposure": {},
            "topic_assignments_by_post_id": {fallback_post.id: []},
        }

        assert forum_recommendation_service.is_exploitation_candidate(
            fallback_post,
            ranking_context=fallback_context,
        )

        monkeypatch.setattr(forum_recommendation_service, "_recency_score", lambda post: 0.0)
        monkeypatch.setattr(forum_recommendation_service, "_engagement_score", lambda post: 0.2)

        assert forum_recommendation_service.is_exploitation_candidate(
            fallback_post,
            ranking_context=fallback_context,
        )

    def test_is_exploration_candidate_requires_unseen_weak_affinity_and_low_exposure(self):
        user = _make_user("explore-candidate", "explore-candidate@example.com")
        weak_post = _make_post(user.id, "Weak battery match", "Weak battery content")
        strong_post = _make_post(user.id, "Strong battery match", "Strong battery content")

        preference_profile_repository.replace_content_topic_assignments(
            domain="forum",
            content_type="post",
            content_id=weak_post.id,
            topics=[{"topic_id": "battery-recycling", "confidence_score": 1.0}],
        )
        preference_profile_repository.replace_content_topic_assignments(
            domain="forum",
            content_type="post",
            content_id=strong_post.id,
            topics=[{"topic_id": "battery-recycling", "confidence_score": 1.0}],
        )

        weak_context = {
            "profile_snapshot": {"battery-recycling": 0.3},
            "viewed_post_ids": set(),
            "recent_topic_exposure": {"battery-recycling": 2},
            "topic_assignments_by_post_id": {
                weak_post.id: [SimpleNamespace(topic_id="battery-recycling", confidence_score=1.0)]
            },
        }
        seen_context = {
            "profile_snapshot": {"battery-recycling": 0.3},
            "viewed_post_ids": {weak_post.id},
            "recent_topic_exposure": {"battery-recycling": 2},
            "topic_assignments_by_post_id": {
                weak_post.id: [SimpleNamespace(topic_id="battery-recycling", confidence_score=1.0)]
            },
        }
        overexposed_context = {
            "profile_snapshot": {"battery-recycling": 0.3},
            "viewed_post_ids": set(),
            "recent_topic_exposure": {"battery-recycling": 3},
            "topic_assignments_by_post_id": {
                weak_post.id: [SimpleNamespace(topic_id="battery-recycling", confidence_score=1.0)]
            },
        }
        strong_context = {
            "profile_snapshot": {"battery-recycling": 0.9},
            "viewed_post_ids": set(),
            "recent_topic_exposure": {"battery-recycling": 1},
            "topic_assignments_by_post_id": {
                strong_post.id: [
                    SimpleNamespace(topic_id="battery-recycling", confidence_score=1.0)
                ]
            },
        }

        assert forum_recommendation_service.is_exploration_candidate(
            weak_post, ranking_context=weak_context
        )
        assert not forum_recommendation_service.is_exploration_candidate(
            weak_post, ranking_context=seen_context
        )
        assert not forum_recommendation_service.is_exploration_candidate(
            weak_post,
            ranking_context=overexposed_context,
        )
        assert not forum_recommendation_service.is_exploration_candidate(
            strong_post,
            ranking_context=strong_context,
        )

    def test_is_exploration_candidate_uses_uncategorized_fallback_when_assignments_are_missing(
        self,
    ):
        user = _make_user("explore-fallback", "explore-fallback@example.com")
        fallback_post = _make_post(user.id, "Fallback", "Fallback content")

        fallback_context = {
            "profile_snapshot": {},
            "viewed_post_ids": set(),
            "recent_topic_exposure": {"uncategorized": 2},
            "topic_assignments_by_post_id": {},
        }
        overexposed_context = {
            "profile_snapshot": {},
            "viewed_post_ids": set(),
            "recent_topic_exposure": {"uncategorized": 3},
            "topic_assignments_by_post_id": {},
        }

        assert forum_recommendation_service.is_exploration_candidate(
            fallback_post,
            ranking_context=fallback_context,
        )
        assert not forum_recommendation_service.is_exploration_candidate(
            fallback_post,
            ranking_context=overexposed_context,
        )

    def test_exploit_and_explore_scores_use_bounded_helpers(self, monkeypatch):
        user = _make_user("scores", "scores@example.com")
        post = _make_post(user.id, "Battery guide", "Battery guide content")

        preference_profile_repository.replace_content_topic_assignments(
            domain="forum",
            content_type="post",
            content_id=post.id,
            topics=[{"topic_id": "battery-recycling", "confidence_score": 1.0}],
        )

        context = {
            "profile_snapshot": {"battery-recycling": 0.7},
            "viewed_post_ids": set(),
            "long_viewed_post_ids": set(),
            "engaged_post_ids": set(),
            "topic_assignments_by_post_id": {
                post.id: [SimpleNamespace(topic_id="battery-recycling", confidence_score=1.0)]
            },
        }

        monkeypatch.setattr(forum_recommendation_service, "_recency_score", lambda post: 0.6)
        monkeypatch.setattr(forum_recommendation_service, "_engagement_score", lambda post: 0.4)
        monkeypatch.setattr(
            forum_recommendation_service, "_novelty_score", lambda post, ranking_context: 0.8
        )

        assert forum_recommendation_service.exploit_score(
            post, ranking_context=context
        ) == pytest.approx(0.64)
        assert forum_recommendation_service.explore_score(
            post, ranking_context=context
        ) == pytest.approx(0.47)

    def test_merge_ranked_posts_preserves_deterministic_exploration_slots(self):
        user = _make_user("merge", "merge@example.com")
        posts = [_make_post(user.id, f"Post {index}", "Content") for index in range(1, 10)]

        merged = forum_recommendation_service.merge_ranked_posts(
            exploit_posts=posts[:7],
            explore_posts=posts[7:],
            ranking_context={
                "topic_assignments_by_post_id": {
                    post.id: [_topic_assignment(f"topic-{index}")]
                    for index, post in enumerate(posts, start=1)
                }
            },
            target_size=len(posts),
        )

        assert [post.id for post in merged] == [
            posts[0].id,
            posts[1].id,
            posts[2].id,
            posts[7].id,
            posts[3].id,
            posts[4].id,
            posts[5].id,
            posts[6].id,
            posts[8].id,
        ]

    def test_merge_ranked_posts_avoids_three_same_dominant_topics_in_a_row_when_alternative_exists(
        self,
    ):
        user = _make_user("diverse", "diverse@example.com")
        same_topic_posts = [
            _make_post(user.id, f"Battery {index}", "Battery content") for index in range(1, 4)
        ]
        alternate_post = _make_post(user.id, "Plastic", "Plastic content")
        second_alternate_post = _make_post(user.id, "Glass", "Glass content")

        merged = forum_recommendation_service.merge_ranked_posts(
            exploit_posts=[
                same_topic_posts[0],
                same_topic_posts[1],
                same_topic_posts[2],
                alternate_post,
                second_alternate_post,
            ],
            explore_posts=[],
            ranking_context={
                "topic_assignments_by_post_id": {
                    same_topic_posts[0].id: [_topic_assignment("battery-recycling")],
                    same_topic_posts[1].id: [_topic_assignment("battery-recycling")],
                    same_topic_posts[2].id: [_topic_assignment("battery-recycling")],
                    alternate_post.id: [_topic_assignment("plastic-recycling")],
                    second_alternate_post.id: [_topic_assignment("glass-recycling")],
                }
            },
            target_size=5,
        )

        dominant_topics = [
            forum_recommendation_service._dominant_topic_for_post(
                post,
                {
                    "topic_assignments_by_post_id": {
                        same_topic_posts[0].id: [_topic_assignment("battery-recycling")],
                        same_topic_posts[1].id: [_topic_assignment("battery-recycling")],
                        same_topic_posts[2].id: [_topic_assignment("battery-recycling")],
                        alternate_post.id: [_topic_assignment("plastic-recycling")],
                        second_alternate_post.id: [_topic_assignment("glass-recycling")],
                    }
                },
            )
            for post in merged
        ]

        assert dominant_topics[:3] == [
            "battery-recycling",
            "battery-recycling",
            "plastic-recycling",
        ]
        assert not any(
            dominant_topics[index] == dominant_topics[index + 1] == dominant_topics[index + 2]
            for index in range(len(dominant_topics) - 2)
        )

    def test_rank_posts_for_user_prefers_matching_topic(self, monkeypatch):
        user = _make_user()
        plastic_post = _make_post(user.id, "Plastic bottle tips", "Bottle recycling guide")
        battery_post = _make_post(user.id, "Battery recycling", "Old batteries")

        preference_profile_repository.replace_content_topic_assignments(
            domain="forum",
            content_type="post",
            content_id=plastic_post.id,
            topics=[{"topic_id": "plastic-recycling", "confidence_score": 1.0}],
        )
        preference_profile_repository.replace_content_topic_assignments(
            domain="forum",
            content_type="post",
            content_id=battery_post.id,
            topics=[{"topic_id": "battery-recycling", "confidence_score": 1.0}],
        )

        monkeypatch.setattr(
            "app.services.recommendation.preference_profile_service.has_sufficient_history",
            lambda user_id: True,
        )
        monkeypatch.setattr(
            "app.services.recommendation.preference_profile_service.get_profile_snapshot",
            lambda user_id: {"battery-recycling": 0.9, "plastic-recycling": 0.1},
        )
        monkeypatch.setattr(
            forum_recommendation_service.behavior_event_repository,
            "list_behavior_target_ids_for_user",
            lambda *args, **kwargs: set(),
        )
        monkeypatch.setattr(forum_recommendation_service, "_engagement_score", lambda post: 0.0)

        ranked = forum_recommendation_service.rank_posts_for_user(
            posts=[plastic_post, battery_post],
            user_id=user.id,
        )

        assert ranked[0].id == battery_post.id

    def test_rank_posts_for_user_uses_batched_topic_assignments_from_context(self, monkeypatch):
        user = _make_user("context", "context@example.com")
        weak_post = _make_post(user.id, "Plastic organizer", "Plastic recycling")
        strong_post = _make_post(user.id, "Battery storage", "Battery recycling")

        monkeypatch.setattr(
            "app.services.recommendation.preference_profile_service.has_sufficient_history",
            lambda user_id: True,
        )
        monkeypatch.setattr(
            "app.services.recommendation.preference_profile_service.get_profile_snapshot",
            lambda user_id: {"battery-recycling": 0.9, "plastic-recycling": 0.1},
        )
        monkeypatch.setattr(
            forum_recommendation_service.preference_profile_repository,
            "list_content_topic_assignments_for_content_ids",
            lambda **kwargs: {
                weak_post.id: [SimpleNamespace(topic_id="plastic-recycling", confidence_score=1.0)],
                strong_post.id: [
                    SimpleNamespace(topic_id="battery-recycling", confidence_score=1.0)
                ],
            },
        )
        monkeypatch.setattr(
            forum_recommendation_service.preference_profile_repository,
            "list_content_topic_assignments",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("per-post lookup should not be used")
            ),
        )
        monkeypatch.setattr(
            forum_recommendation_service.behavior_event_repository,
            "list_behavior_target_ids_for_user",
            lambda *args, **kwargs: set(),
        )
        monkeypatch.setattr(
            forum_recommendation_service.behavior_event_repository,
            "list_active_forum_like_target_ids_for_user",
            lambda *args, **kwargs: set(),
        )
        monkeypatch.setattr(
            forum_recommendation_service.behavior_event_repository,
            "list_recent_topic_exposure_counts_for_user",
            lambda *args, **kwargs: {},
        )
        monkeypatch.setattr(forum_recommendation_service, "_engagement_score", lambda post: 0.0)

        ranked = forum_recommendation_service.rank_posts_for_user(
            posts=[weak_post, strong_post],
            user_id=user.id,
        )

        assert ranked[0].id == strong_post.id

    def test_rank_posts_for_user_falls_back_to_recency_without_history(self, monkeypatch):
        user = _make_user("cold", "cold@example.com")
        older = _make_post(user.id, "Old", "Older post")
        newer = _make_post(user.id, "New", "Newer post")

        monkeypatch.setattr(
            "app.services.recommendation.preference_profile_service.has_sufficient_history",
            lambda user_id: False,
        )
        monkeypatch.setattr(forum_recommendation_service, "_engagement_score", lambda post: 0.0)

        ranked = forum_recommendation_service.rank_posts_for_user(
            posts=[older, newer],
            user_id=user.id,
        )

        assert ranked[0].id == newer.id

    def test_cold_start_ranking_can_use_engagement_signal(self, monkeypatch):
        user = _make_user("engaged", "engaged@example.com")
        low_engagement = _make_post(user.id, "Fresh", "Fresh post")
        high_engagement = _make_post(user.id, "Popular", "Popular post")

        monkeypatch.setattr(
            "app.services.recommendation.preference_profile_service.has_sufficient_history",
            lambda user_id: False,
        )
        monkeypatch.setattr(forum_recommendation_service, "_recency_score", lambda post: 0.6)
        monkeypatch.setattr(
            forum_recommendation_service,
            "_engagement_score",
            lambda post: 0.9 if post.id == high_engagement.id else 0.0,
        )

        ranked = forum_recommendation_service.rank_posts_for_user(
            posts=[low_engagement, high_engagement],
            user_id=user.id,
        )

        assert ranked[0].id == high_engagement.id

    def test_rank_posts_for_user_penalizes_already_viewed_posts(self, monkeypatch):
        user = _make_user("novelty", "novelty@example.com")
        viewed = _make_post(user.id, "Viewed battery post", "Battery recycling")
        fresh = _make_post(user.id, "Fresh battery post", "Battery recycling")

        preference_profile_repository.replace_content_topic_assignments(
            domain="forum",
            content_type="post",
            content_id=viewed.id,
            topics=[{"topic_id": "battery-recycling", "confidence_score": 1.0}],
        )
        preference_profile_repository.replace_content_topic_assignments(
            domain="forum",
            content_type="post",
            content_id=fresh.id,
            topics=[{"topic_id": "battery-recycling", "confidence_score": 1.0}],
        )

        monkeypatch.setattr(
            "app.services.recommendation.preference_profile_service.has_sufficient_history",
            lambda user_id: True,
        )
        monkeypatch.setattr(
            "app.services.recommendation.preference_profile_service.get_profile_snapshot",
            lambda user_id: {"battery-recycling": 0.9},
        )
        monkeypatch.setattr(
            forum_recommendation_service.behavior_event_repository,
            "list_behavior_target_ids_for_user",
            lambda user_id, **kwargs: (
                {viewed.id} if kwargs.get("action_types") == ["view", "long_view"] else set()
            ),
        )
        monkeypatch.setattr(forum_recommendation_service, "_engagement_score", lambda post: 0.0)

        ranked = forum_recommendation_service.rank_posts_for_user(
            posts=[viewed, fresh],
            user_id=user.id,
        )

        assert ranked[0].id == fresh.id
