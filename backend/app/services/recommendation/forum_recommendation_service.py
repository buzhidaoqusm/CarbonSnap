from __future__ import annotations

from datetime import datetime, timezone
from math import exp

from app.models.forum import ForumPost
from app.repositories.forum import forum_repository
from app.repositories.recommendation import behavior_event_repository
from app.repositories.recommendation import preference_profile_repository
from app.services.recommendation import preference_profile_service

NOVELTY_UNSEEN_SCORE = 1.0
NOVELTY_VIEW_SCORE = 0.8
NOVELTY_LONG_VIEW_SCORE = 0.65
NOVELTY_ENGAGED_SCORE = 0.55
EXPLORATION_WEAK_AFFINITY_MAX = 0.35
EXPLORATION_LOW_EXPOSURE_MAX = 2
EXPLOITATION_MIN_ENGAGEMENT_SCORE = 0.2
EXPLOITATION_MIN_RECENCY_SCORE = 0.6
MERGE_PATTERN = (
    "exploit",
    "exploit",
    "exploit",
    "explore",
    "exploit",
    "exploit",
    "exploit",
    "exploit",
    "explore",
)
MAX_CONSECUTIVE_DOMINANT_TOPIC_POSTS = 2


def _ensure_aware_utc(value):
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _clamp_unit_interval(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


def _recency_score(post: ForumPost) -> float:
    age_days = max((datetime.now(timezone.utc) - _ensure_aware_utc(post.created_at)).total_seconds() / 86400.0, 0.0)
    if age_days <= 3:
        return 1.0
    if age_days <= 14:
        return 0.6
    return 0.3


def _topic_assignments_for_post(post: ForumPost, ranking_context: dict) -> list:
    assignments_by_post_id = ranking_context.get("topic_assignments_by_post_id") or {}
    return list(assignments_by_post_id.get(int(post.id), []))


def _topic_ids_for_post(post: ForumPost, ranking_context: dict) -> list[str]:
    topic_ids: list[str] = []
    for assignment in _topic_assignments_for_post(post, ranking_context):
        topic_id = str(getattr(assignment, "topic_id", "") or "").strip().lower()
        if topic_id and topic_id not in topic_ids:
            topic_ids.append(topic_id)
    return topic_ids


def _dominant_topic_for_post(post: ForumPost, ranking_context: dict) -> str:
    assignments = _topic_assignments_for_post(post, ranking_context)
    ranked_topics: list[tuple[float, str]] = []
    for assignment in assignments:
        topic_id = str(getattr(assignment, "topic_id", "") or "").strip().lower() or "uncategorized"
        ranked_topics.append((float(getattr(assignment, "confidence_score", 0.0) or 0.0), topic_id))
    if not ranked_topics:
        return "uncategorized"
    ranked_topics.sort(key=lambda item: (-item[0], item[1]))
    return ranked_topics[0][1]


def _max_recent_topic_exposure(post: ForumPost, ranking_context: dict) -> int:
    recent_topic_exposure = ranking_context.get("recent_topic_exposure") or {}
    topic_ids = _topic_ids_for_post(post, ranking_context)
    if not topic_ids:
        topic_ids = ["uncategorized"]
    return max(int(recent_topic_exposure.get(topic_id, 0) or 0) for topic_id in topic_ids)


def _has_uncategorized_only_assignments(post: ForumPost, ranking_context: dict) -> bool:
    topic_ids = _topic_ids_for_post(post, ranking_context)
    if not topic_ids:
        return True
    return all(topic_id == "uncategorized" for topic_id in topic_ids)


def _topic_match_score(post: ForumPost, ranking_context: dict) -> float:
    profile_snapshot = ranking_context.get("profile_snapshot") or {}
    assignments = _topic_assignments_for_post(post, ranking_context)
    if not assignments:
        return 0.0
    score = 0.0
    for assignment in assignments:
        score += float(profile_snapshot.get(assignment.topic_id, 0.0)) * float(assignment.confidence_score or 0.0)
    return score


def _preference_match_score(post: ForumPost, ranking_context: dict) -> float:
    profile_snapshot = ranking_context.get("profile_snapshot") or {}
    assignments = _topic_assignments_for_post(post, ranking_context)
    if not assignments:
        return 0.0
    weighted_score = 0.0
    for assignment in assignments:
        weighted_score += float(profile_snapshot.get(assignment.topic_id, 0.0)) * float(assignment.confidence_score or 0.0)
    return round(_clamp_unit_interval(weighted_score), 6)


def _engagement_score(post: ForumPost) -> float:
    likes = forum_repository.count_likes("post", post.id)
    comments = forum_repository.count_comments(post.id)
    raw_score = float(likes) + (float(comments) * 1.5)
    if raw_score <= 0:
        return 0.0
    return round(1.0 - exp(-raw_score / 5.0), 6)


def _novelty_score(post: ForumPost, ranking_context: dict) -> float:
    viewed_post_ids = ranking_context.get("viewed_post_ids") or set()
    long_viewed_post_ids = ranking_context.get("long_viewed_post_ids") or set()
    engaged_post_ids = ranking_context.get("engaged_post_ids") or set()
    if post.id in engaged_post_ids:
        return NOVELTY_ENGAGED_SCORE
    if post.id in long_viewed_post_ids:
        return NOVELTY_LONG_VIEW_SCORE
    if post.id in viewed_post_ids:
        return NOVELTY_VIEW_SCORE
    return NOVELTY_UNSEEN_SCORE


def _novelty_adjustment(
    post: ForumPost,
    *,
    ranking_context: dict,
) -> float:
    viewed_post_ids = ranking_context.get("viewed_post_ids") or set()
    engaged_post_ids = ranking_context.get("engaged_post_ids") or set()
    if post.id in engaged_post_ids:
        return 1.0
    if post.id in viewed_post_ids:
        return 0.85
    return 1.0


def _unfamiliarity_score(post: ForumPost, ranking_context: dict) -> float:
    profile_snapshot = ranking_context.get("profile_snapshot") or {}
    assignments = _topic_assignments_for_post(post, ranking_context)
    if not assignments:
        return 0.5
    non_fallback_assignments = [assignment for assignment in assignments if assignment.topic_id != "uncategorized"]
    if not non_fallback_assignments:
        return 0.5
    max_topic_match = max(float(profile_snapshot.get(assignment.topic_id, 0.0)) for assignment in non_fallback_assignments)
    return round(1.0 - _clamp_unit_interval(max_topic_match), 6)


def is_exploitation_candidate(post: ForumPost, *, ranking_context: dict) -> bool:
    preference_match = _preference_match_score(post, ranking_context)
    if preference_match > 0.0:
        return True
    if _engagement_score(post) >= EXPLOITATION_MIN_ENGAGEMENT_SCORE:
        return True
    if _recency_score(post) >= EXPLOITATION_MIN_RECENCY_SCORE:
        return True
    return False


def is_exploration_candidate(post: ForumPost, *, ranking_context: dict) -> bool:
    if post.id in (ranking_context.get("viewed_post_ids") or set()):
        return False

    preference_match = _preference_match_score(post, ranking_context)
    weak_affinity = 0.0 < preference_match <= EXPLORATION_WEAK_AFFINITY_MAX
    low_exposure = _max_recent_topic_exposure(post, ranking_context) <= EXPLORATION_LOW_EXPOSURE_MAX
    uncategorized_fallback = _has_uncategorized_only_assignments(post, ranking_context)

    return (weak_affinity and low_exposure) or (uncategorized_fallback and low_exposure)


def exploit_score(post: ForumPost, *, ranking_context: dict) -> float:
    preference_match = _preference_match_score(post, ranking_context)
    recency = _recency_score(post)
    engagement = _engagement_score(post)
    novelty = _novelty_score(post, ranking_context)
    quality_floor = max(recency, engagement)
    return round(
        (0.50 * preference_match)
        + (0.20 * recency)
        + (0.15 * engagement)
        + (0.10 * novelty)
        + (0.05 * quality_floor),
        6,
    )


def explore_score(post: ForumPost, *, ranking_context: dict) -> float:
    unfamiliarity = _unfamiliarity_score(post, ranking_context)
    recency = _recency_score(post)
    engagement = _engagement_score(post)
    novelty = _novelty_score(post, ranking_context)
    return round(
        (0.40 * unfamiliarity)
        + (0.25 * recency)
        + (0.20 * engagement)
        + (0.15 * novelty),
        6,
    )


def recommendation_score(
    post: ForumPost,
    *,
    ranking_context: dict,
) -> float:
    base_score = (
        (_topic_match_score(post, ranking_context) * 0.55)
        + (_recency_score(post) * 0.3)
        + (_engagement_score(post) * 0.15)
    )
    return round(
        base_score
        * _novelty_adjustment(
            post,
            ranking_context=ranking_context,
        ),
        6,
    )


def _cold_start_score(post: ForumPost) -> float:
    return round((_recency_score(post) * 0.75) + (_engagement_score(post) * 0.25), 6)


def _source_index_for_post(post: ForumPost, source_index_by_post_id: dict[int, int]) -> int:
    return int(source_index_by_post_id.get(int(post.id), 0))


def _sort_posts_with_scores(
    *,
    posts: list[ForumPost],
    score_getter,
    ranking_context: dict,
    source_index_by_post_id: dict[int, int],
) -> list[ForumPost]:
    return sorted(
        posts,
        key=lambda post: (
            score_getter(post, ranking_context=ranking_context),
            _ensure_aware_utc(post.created_at),
            post.id,
            -_source_index_for_post(post, source_index_by_post_id),
        ),
        reverse=True,
    )


def _would_violate_diversity_guard(
    *,
    candidate: ForumPost,
    merged_posts: list[ForumPost],
    ranking_context: dict,
) -> bool:
    if len(merged_posts) < MAX_CONSECUTIVE_DOMINANT_TOPIC_POSTS:
        return False
    candidate_topic = _dominant_topic_for_post(candidate, ranking_context)
    recent_topics = [
        _dominant_topic_for_post(post, ranking_context)
        for post in merged_posts[-MAX_CONSECUTIVE_DOMINANT_TOPIC_POSTS:]
    ]
    return all(topic == candidate_topic for topic in recent_topics)


def _pop_next_candidate_from_pools(
    *,
    pools: list[list[ForumPost]],
    used_post_ids: set[int],
    merged_posts: list[ForumPost],
    ranking_context: dict,
    enforce_diversity_guard: bool,
) -> ForumPost | None:
    for pool in pools:
        for index, post in enumerate(pool):
            post_id = int(post.id)
            if post_id in used_post_ids:
                continue
            if enforce_diversity_guard and _would_violate_diversity_guard(
                candidate=post,
                merged_posts=merged_posts,
                ranking_context=ranking_context,
            ):
                continue
            return pool.pop(index)
    return None


def merge_ranked_posts(
    *,
    exploit_posts: list[ForumPost],
    explore_posts: list[ForumPost],
    fallback_posts: list[ForumPost] | None = None,
    ranking_context: dict,
    target_size: int,
) -> list[ForumPost]:
    exploit_pool = list(exploit_posts)
    explore_pool = list(explore_posts)
    fallback_pool = list(fallback_posts or [])
    merged_posts: list[ForumPost] = []
    used_post_ids: set[int] = set()

    while len(merged_posts) < target_size:
        preferred_source = MERGE_PATTERN[len(merged_posts) % len(MERGE_PATTERN)]
        if preferred_source == "explore":
            preferred_pools = [explore_pool, exploit_pool, fallback_pool]
        else:
            preferred_pools = [exploit_pool, fallback_pool, explore_pool]

        candidate = _pop_next_candidate_from_pools(
            pools=preferred_pools,
            used_post_ids=used_post_ids,
            merged_posts=merged_posts,
            ranking_context=ranking_context,
            enforce_diversity_guard=True,
        )
        if candidate is None:
            candidate = _pop_next_candidate_from_pools(
                pools=preferred_pools,
                used_post_ids=used_post_ids,
                merged_posts=merged_posts,
                ranking_context=ranking_context,
                enforce_diversity_guard=False,
            )
        if candidate is None:
            break
        merged_posts.append(candidate)
        used_post_ids.add(int(candidate.id))

    return merged_posts


def build_ranking_context(*, user_id: int, posts: list[ForumPost]) -> dict:
    post_ids = [int(post.id) for post in posts if post is not None and post.id is not None]
    has_history = preference_profile_service.has_sufficient_history(user_id)
    profile_snapshot = preference_profile_service.get_profile_snapshot(user_id) if has_history else {}
    topic_assignments_by_post_id = preference_profile_repository.list_content_topic_assignments_for_content_ids(
        domain="forum",
        content_type="post",
        content_ids=post_ids,
    )
    viewed_post_ids = behavior_event_repository.list_behavior_target_ids_for_user(
        user_id,
        domain="forum",
        target_type="post",
        action_types=["view", "long_view"],
    )
    long_viewed_post_ids = behavior_event_repository.list_behavior_target_ids_for_user(
        user_id,
        domain="forum",
        target_type="post",
        action_types=["long_view"],
    )
    active_liked_post_ids = behavior_event_repository.list_active_forum_like_target_ids_for_user(
        user_id,
        target_type="post",
    )
    commented_post_ids = behavior_event_repository.list_behavior_target_ids_for_user(
        user_id,
        domain="forum",
        target_type="post",
        action_types=["comment_or_reply"],
    )
    recent_topic_exposure = behavior_event_repository.list_recent_topic_exposure_counts_for_user(
        user_id,
        domain="forum",
    )
    return {
        "has_history": has_history,
        "profile_snapshot": profile_snapshot,
        "viewed_post_ids": viewed_post_ids,
        "long_viewed_post_ids": long_viewed_post_ids,
        "engaged_post_ids": active_liked_post_ids | commented_post_ids,
        "recent_topic_exposure": recent_topic_exposure,
        "topic_assignments_by_post_id": topic_assignments_by_post_id,
    }


def rank_posts_for_user(*, posts: list[ForumPost], user_id: int) -> list[ForumPost]:
    if not posts:
        return []
    ranking_context = build_ranking_context(user_id=user_id, posts=posts)
    if not ranking_context["has_history"]:
        return sorted(
            posts,
            key=lambda post: (
                _cold_start_score(post),
                _ensure_aware_utc(post.created_at),
                post.id,
            ),
            reverse=True,
        )

    source_index_by_post_id = {
        int(post.id): index
        for index, post in enumerate(posts)
        if post is not None and post.id is not None
    }
    exploitation_posts = _sort_posts_with_scores(
        posts=[post for post in posts if is_exploitation_candidate(post, ranking_context=ranking_context)],
        score_getter=exploit_score,
        ranking_context=ranking_context,
        source_index_by_post_id=source_index_by_post_id,
    )
    exploration_posts = _sort_posts_with_scores(
        posts=[post for post in posts if is_exploration_candidate(post, ranking_context=ranking_context)],
        score_getter=explore_score,
        ranking_context=ranking_context,
        source_index_by_post_id=source_index_by_post_id,
    )
    ranked_pool_post_ids = {
        int(post.id)
        for post in exploitation_posts + exploration_posts
        if post is not None and post.id is not None
    }
    fallback_posts = _sort_posts_with_scores(
        posts=[
            post
            for post in posts
            if post is not None and post.id is not None and int(post.id) not in ranked_pool_post_ids
        ],
        score_getter=exploit_score,
        ranking_context=ranking_context,
        source_index_by_post_id=source_index_by_post_id,
    )

    return merge_ranked_posts(
        exploit_posts=exploitation_posts,
        explore_posts=exploration_posts,
        fallback_posts=fallback_posts,
        ranking_context=ranking_context,
        target_size=len(posts),
    )
