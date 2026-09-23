from __future__ import annotations

from datetime import UTC, datetime
from math import exp

from app.models.market import MarketItem
from app.repositories.market import market_repository
from app.repositories.recommendation import behavior_event_repository, preference_profile_repository
from app.services.recommendation import preference_profile_service

NOVELTY_UNSEEN_SCORE = 1.0
NOVELTY_VIEW_SCORE = 0.8
NOVELTY_LONG_VIEW_SCORE = 0.65
NOVELTY_ORDERED_SCORE = 0.55
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
MAX_CONSECUTIVE_DOMINANT_TOPIC_ITEMS = 2


def _ensure_aware_utc(value):
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _clamp_unit_interval(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


def _recency_score(item: MarketItem) -> float:
    age_days = max(
        (datetime.now(UTC) - _ensure_aware_utc(item.created_at)).total_seconds() / 86400.0, 0.0
    )
    if age_days <= 3:
        return 1.0
    if age_days <= 14:
        return 0.6
    return 0.3


def _topic_assignments_for_item(item: MarketItem, ranking_context: dict) -> list:
    assignments_by_item_id = ranking_context.get("topic_assignments_by_item_id") or {}
    return list(assignments_by_item_id.get(int(item.id), []))


def _topic_ids_for_item(item: MarketItem, ranking_context: dict) -> list[str]:
    topic_ids: list[str] = []
    for assignment in _topic_assignments_for_item(item, ranking_context):
        topic_id = str(getattr(assignment, "topic_id", "") or "").strip().lower()
        if topic_id and topic_id not in topic_ids:
            topic_ids.append(topic_id)
    return topic_ids


def _dominant_topic_for_item(item: MarketItem, ranking_context: dict) -> str:
    assignments = _topic_assignments_for_item(item, ranking_context)
    ranked_topics: list[tuple[float, str]] = []
    for assignment in assignments:
        topic_id = str(getattr(assignment, "topic_id", "") or "").strip().lower() or "uncategorized"
        ranked_topics.append((float(getattr(assignment, "confidence_score", 0.0) or 0.0), topic_id))
    if not ranked_topics:
        return "uncategorized"
    ranked_topics.sort(key=lambda entry: (-entry[0], entry[1]))
    return ranked_topics[0][1]


def _max_recent_topic_exposure(item: MarketItem, ranking_context: dict) -> int:
    recent_topic_exposure = ranking_context.get("recent_topic_exposure") or {}
    topic_ids = _topic_ids_for_item(item, ranking_context)
    if not topic_ids:
        topic_ids = ["uncategorized"]
    return max(int(recent_topic_exposure.get(topic_id, 0) or 0) for topic_id in topic_ids)


def _has_uncategorized_only_assignments(item: MarketItem, ranking_context: dict) -> bool:
    topic_ids = _topic_ids_for_item(item, ranking_context)
    if not topic_ids:
        return True
    return all(topic_id == "uncategorized" for topic_id in topic_ids)


def _preference_match_score(item: MarketItem, ranking_context: dict) -> float:
    profile_snapshot = ranking_context.get("profile_snapshot") or {}
    assignments = _topic_assignments_for_item(item, ranking_context)
    if not assignments:
        return 0.0
    weighted_score = 0.0
    for assignment in assignments:
        weighted_score += float(profile_snapshot.get(assignment.topic_id, 0.0)) * float(
            assignment.confidence_score or 0.0
        )
    return round(_clamp_unit_interval(weighted_score), 6)


def _engagement_score(item: MarketItem, ranking_context: dict) -> float:
    total_order_counts = ranking_context.get("total_order_counts_by_item_id") or {}
    completed_order_counts = ranking_context.get("completed_order_counts_by_item_id") or {}
    total_orders = float(total_order_counts.get(int(item.id), 0) or 0)
    completed_orders = float(completed_order_counts.get(int(item.id), 0) or 0)
    raw_score = total_orders + (completed_orders * 1.5)
    if raw_score <= 0:
        return 0.0
    return round(1.0 - exp(-raw_score / 4.0), 6)


def _novelty_score(item: MarketItem, ranking_context: dict) -> float:
    viewed_item_ids = ranking_context.get("viewed_item_ids") or set()
    long_viewed_item_ids = ranking_context.get("long_viewed_item_ids") or set()
    ordered_item_ids = ranking_context.get("ordered_item_ids") or set()
    if item.id in ordered_item_ids:
        return NOVELTY_ORDERED_SCORE
    if item.id in long_viewed_item_ids:
        return NOVELTY_LONG_VIEW_SCORE
    if item.id in viewed_item_ids:
        return NOVELTY_VIEW_SCORE
    return NOVELTY_UNSEEN_SCORE


def _unfamiliarity_score(item: MarketItem, ranking_context: dict) -> float:
    profile_snapshot = ranking_context.get("profile_snapshot") or {}
    assignments = _topic_assignments_for_item(item, ranking_context)
    if not assignments:
        return 0.5
    non_fallback_assignments = [
        assignment for assignment in assignments if assignment.topic_id != "uncategorized"
    ]
    if not non_fallback_assignments:
        return 0.5
    max_topic_match = max(
        float(profile_snapshot.get(assignment.topic_id, 0.0))
        for assignment in non_fallback_assignments
    )
    return round(1.0 - _clamp_unit_interval(max_topic_match), 6)


def is_exploitation_candidate(item: MarketItem, *, ranking_context: dict) -> bool:
    preference_match = _preference_match_score(item, ranking_context)
    if preference_match > 0.0:
        return True
    if _engagement_score(item, ranking_context) >= EXPLOITATION_MIN_ENGAGEMENT_SCORE:
        return True
    if _recency_score(item) >= EXPLOITATION_MIN_RECENCY_SCORE:
        return True
    return False


def is_exploration_candidate(item: MarketItem, *, ranking_context: dict) -> bool:
    if item.id in (ranking_context.get("viewed_item_ids") or set()):
        return False

    preference_match = _preference_match_score(item, ranking_context)
    weak_affinity = 0.0 < preference_match <= EXPLORATION_WEAK_AFFINITY_MAX
    low_exposure = _max_recent_topic_exposure(item, ranking_context) <= EXPLORATION_LOW_EXPOSURE_MAX
    uncategorized_fallback = _has_uncategorized_only_assignments(item, ranking_context)

    return (weak_affinity and low_exposure) or (uncategorized_fallback and low_exposure)


def exploit_score(item: MarketItem, *, ranking_context: dict) -> float:
    preference_match = _preference_match_score(item, ranking_context)
    recency = _recency_score(item)
    engagement = _engagement_score(item, ranking_context)
    novelty = _novelty_score(item, ranking_context)
    quality_floor = max(recency, engagement)
    return round(
        (0.50 * preference_match)
        + (0.20 * recency)
        + (0.15 * engagement)
        + (0.10 * novelty)
        + (0.05 * quality_floor),
        6,
    )


def explore_score(item: MarketItem, *, ranking_context: dict) -> float:
    unfamiliarity = _unfamiliarity_score(item, ranking_context)
    recency = _recency_score(item)
    engagement = _engagement_score(item, ranking_context)
    novelty = _novelty_score(item, ranking_context)
    return round(
        (0.40 * unfamiliarity) + (0.25 * recency) + (0.20 * engagement) + (0.15 * novelty),
        6,
    )


def _cold_start_score(item: MarketItem, ranking_context: dict) -> float:
    return round(
        (_recency_score(item) * 0.75) + (_engagement_score(item, ranking_context) * 0.25), 6
    )


def _source_index_for_item(item: MarketItem, source_index_by_item_id: dict[int, int]) -> int:
    return int(source_index_by_item_id.get(int(item.id), 0))


def _sort_items_with_scores(
    *,
    items: list[MarketItem],
    score_getter,
    ranking_context: dict,
    source_index_by_item_id: dict[int, int],
) -> list[MarketItem]:
    return sorted(
        items,
        key=lambda item: (
            score_getter(item, ranking_context=ranking_context),
            _ensure_aware_utc(item.created_at),
            item.id,
            -_source_index_for_item(item, source_index_by_item_id),
        ),
        reverse=True,
    )


def _would_violate_diversity_guard(
    *,
    candidate: MarketItem,
    merged_items: list[MarketItem],
    ranking_context: dict,
) -> bool:
    if len(merged_items) < MAX_CONSECUTIVE_DOMINANT_TOPIC_ITEMS:
        return False
    candidate_topic = _dominant_topic_for_item(candidate, ranking_context)
    recent_topics = [
        _dominant_topic_for_item(item, ranking_context)
        for item in merged_items[-MAX_CONSECUTIVE_DOMINANT_TOPIC_ITEMS:]
    ]
    return all(topic == candidate_topic for topic in recent_topics)


def _pop_next_candidate_from_pools(
    *,
    pools: list[list[MarketItem]],
    used_item_ids: set[int],
    merged_items: list[MarketItem],
    ranking_context: dict,
    enforce_diversity_guard: bool,
) -> MarketItem | None:
    for pool in pools:
        for index, item in enumerate(pool):
            item_id = int(item.id)
            if item_id in used_item_ids:
                continue
            if enforce_diversity_guard and _would_violate_diversity_guard(
                candidate=item,
                merged_items=merged_items,
                ranking_context=ranking_context,
            ):
                continue
            return pool.pop(index)
    return None


def merge_ranked_items(
    *,
    exploit_items: list[MarketItem],
    explore_items: list[MarketItem],
    fallback_items: list[MarketItem] | None = None,
    ranking_context: dict,
    target_size: int,
) -> list[MarketItem]:
    exploit_pool = list(exploit_items)
    explore_pool = list(explore_items)
    fallback_pool = list(fallback_items or [])
    merged_items: list[MarketItem] = []
    used_item_ids: set[int] = set()

    while len(merged_items) < target_size:
        preferred_source = MERGE_PATTERN[len(merged_items) % len(MERGE_PATTERN)]
        if preferred_source == "explore":
            preferred_pools = [explore_pool, exploit_pool, fallback_pool]
        else:
            preferred_pools = [exploit_pool, fallback_pool, explore_pool]

        candidate = _pop_next_candidate_from_pools(
            pools=preferred_pools,
            used_item_ids=used_item_ids,
            merged_items=merged_items,
            ranking_context=ranking_context,
            enforce_diversity_guard=True,
        )
        if candidate is None:
            candidate = _pop_next_candidate_from_pools(
                pools=preferred_pools,
                used_item_ids=used_item_ids,
                merged_items=merged_items,
                ranking_context=ranking_context,
                enforce_diversity_guard=False,
            )
        if candidate is None:
            break
        merged_items.append(candidate)
        used_item_ids.add(int(candidate.id))

    return merged_items


def build_ranking_context(*, user_id: int, items: list[MarketItem]) -> dict:
    item_ids = [int(item.id) for item in items if item is not None and item.id is not None]
    has_history = preference_profile_service.has_sufficient_history(user_id)
    profile_snapshot = (
        preference_profile_service.get_profile_snapshot(user_id) if has_history else {}
    )
    topic_assignments_by_item_id = (
        preference_profile_repository.list_content_topic_assignments_for_content_ids(
            domain="market",
            content_type="item",
            content_ids=item_ids,
        )
    )
    viewed_item_ids = behavior_event_repository.list_behavior_target_ids_for_user(
        user_id,
        domain="market",
        target_type="item",
        action_types=["view", "long_view"],
    )
    long_viewed_item_ids = behavior_event_repository.list_behavior_target_ids_for_user(
        user_id,
        domain="market",
        target_type="item",
        action_types=["long_view"],
    )
    ordered_item_ids = market_repository.list_ordered_item_ids_by_buyer(user_id)
    recent_topic_exposure = behavior_event_repository.list_recent_topic_exposure_counts_for_user(
        user_id,
        domain="market",
    )
    total_order_counts_by_item_id = market_repository.list_order_counts_for_item_ids(item_ids)
    completed_order_counts_by_item_id = market_repository.list_order_counts_for_item_ids(
        item_ids,
        statuses=["completed"],
    )
    return {
        "has_history": has_history,
        "profile_snapshot": profile_snapshot,
        "viewed_item_ids": viewed_item_ids,
        "long_viewed_item_ids": long_viewed_item_ids,
        "ordered_item_ids": ordered_item_ids,
        "recent_topic_exposure": recent_topic_exposure,
        "topic_assignments_by_item_id": topic_assignments_by_item_id,
        "total_order_counts_by_item_id": total_order_counts_by_item_id,
        "completed_order_counts_by_item_id": completed_order_counts_by_item_id,
    }


def rank_items_for_user(*, items: list[MarketItem], user_id: int) -> list[MarketItem]:
    if not items:
        return []

    ranking_context = build_ranking_context(user_id=user_id, items=items)
    if not ranking_context["has_history"]:
        return sorted(
            items,
            key=lambda item: (
                _cold_start_score(item, ranking_context),
                _ensure_aware_utc(item.created_at),
                item.id,
            ),
            reverse=True,
        )

    source_index_by_item_id = {
        int(item.id): index
        for index, item in enumerate(items)
        if item is not None and item.id is not None
    }

    exploitation_items = _sort_items_with_scores(
        items=[
            item
            for item in items
            if is_exploitation_candidate(item, ranking_context=ranking_context)
        ],
        score_getter=exploit_score,
        ranking_context=ranking_context,
        source_index_by_item_id=source_index_by_item_id,
    )
    exploration_items = _sort_items_with_scores(
        items=[
            item
            for item in items
            if is_exploration_candidate(item, ranking_context=ranking_context)
        ],
        score_getter=explore_score,
        ranking_context=ranking_context,
        source_index_by_item_id=source_index_by_item_id,
    )
    ranked_pool_item_ids = {
        int(item.id)
        for item in exploitation_items + exploration_items
        if item is not None and item.id is not None
    }
    fallback_items = _sort_items_with_scores(
        items=[
            item
            for item in items
            if item is not None and item.id is not None and int(item.id) not in ranked_pool_item_ids
        ],
        score_getter=exploit_score,
        ranking_context=ranking_context,
        source_index_by_item_id=source_index_by_item_id,
    )

    return merge_ranked_items(
        exploit_items=exploitation_items,
        explore_items=exploration_items,
        fallback_items=fallback_items,
        ranking_context=ranking_context,
        target_size=len(items),
    )
