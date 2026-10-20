"""Characterization tests for merge_ranked_posts / _projects / _items.

The merge was rewritten from a rescan-every-pick loop to topic buckets. These
tests pin the order the original loop produced: a few hand-written cases, plus
random inputs checked against a verbatim copy of the original loop.
"""

from __future__ import annotations

import random
from types import SimpleNamespace

import pytest

from app.services.recommendation import (
    forum_recommendation_service,
    market_recommendation_service,
    project_recommendation_service,
)

SERVICES = [
    pytest.param(
        forum_recommendation_service.merge_ranked_posts,
        ("exploit_posts", "explore_posts", "fallback_posts"),
        "topic_assignments_by_post_id",
        forum_recommendation_service._dominant_topic_for_post,
        id="forum",
    ),
    pytest.param(
        project_recommendation_service.merge_ranked_projects,
        ("exploit_projects", "explore_projects", "fallback_projects"),
        "topic_assignments_by_project_id",
        project_recommendation_service._dominant_topic_for_project,
        id="project",
    ),
    pytest.param(
        market_recommendation_service.merge_ranked_items,
        ("exploit_items", "explore_items", "fallback_items"),
        "topic_assignments_by_item_id",
        market_recommendation_service._dominant_topic_for_item,
        id="market",
    ),
]

MERGE_PATTERN = forum_recommendation_service.MERGE_PATTERN
MAX_RUN = 2


def _reference_merge(*, pools, ranking_context, target_size, dominant_topic):
    """The original O(N^2) loop, kept as the oracle."""

    def would_violate(candidate, merged):
        if len(merged) < MAX_RUN:
            return False
        candidate_topic = dominant_topic(candidate, ranking_context)
        recent = [dominant_topic(row, ranking_context) for row in merged[-MAX_RUN:]]
        return all(topic == candidate_topic for topic in recent)

    def pop_next(preferred, used, merged, guard):
        for pool in preferred:
            for index, row in enumerate(pool):
                if int(row.id) in used:
                    continue
                if guard and would_violate(row, merged):
                    continue
                return pool.pop(index)
        return None

    exploit_pool, explore_pool, fallback_pool = (list(pool) for pool in pools)
    merged: list = []
    used: set[int] = set()
    while len(merged) < target_size:
        if MERGE_PATTERN[len(merged) % len(MERGE_PATTERN)] == "explore":
            preferred = [explore_pool, exploit_pool, fallback_pool]
        else:
            preferred = [exploit_pool, fallback_pool, explore_pool]
        candidate = pop_next(preferred, used, merged, True)
        if candidate is None:
            candidate = pop_next(preferred, used, merged, False)
        if candidate is None:
            break
        merged.append(candidate)
        used.add(int(candidate.id))
    return merged


def _row(row_id):
    return SimpleNamespace(id=row_id)


def _assignment(topic_id, confidence=0.9):
    return SimpleNamespace(topic_id=topic_id, confidence_score=confidence)


def _merge(merge, kwargs, context_key, pools, assignments, target_size):
    exploit, explore, fallback = pools
    return merge(
        **{kwargs[0]: exploit, kwargs[1]: explore, kwargs[2]: fallback},
        ranking_context={context_key: assignments},
        target_size=target_size,
    )


@pytest.mark.parametrize(("merge", "kwargs", "context_key", "dominant_topic"), SERVICES)
class TestMergeOrder:
    def test_every_candidate_in_one_topic_keeps_pool_order(
        self, merge, kwargs, context_key, dominant_topic
    ):
        rows = [_row(i) for i in range(1, 13)]
        assignments = {row.id: [_assignment("battery")] for row in rows}

        merged = _merge(merge, kwargs, context_key, (rows[:8], rows[8:], []), assignments, 12)

        # Nothing can satisfy the guard, so every pick after the second falls
        # back to the unguarded order: exploit three times, then explore.
        assert [row.id for row in merged] == [1, 2, 3, 9, 4, 5, 6, 7, 10, 8, 11, 12]

    def test_guard_pulls_the_next_other_topic_forward(
        self, merge, kwargs, context_key, dominant_topic
    ):
        rows = [_row(i) for i in range(1, 9)]
        topics = ["a", "a", "a", "a", "b", "a", "c", "a"]
        assignments = {row.id: [_assignment(t)] for row, t in zip(rows, topics, strict=True)}

        merged = _merge(merge, kwargs, context_key, (rows, [], []), assignments, 8)

        assert [row.id for row in merged] == [1, 2, 5, 3, 4, 7, 6, 8]

    def test_overlapping_pools_use_each_row_once(self, merge, kwargs, context_key, dominant_topic):
        rows = [_row(i) for i in range(1, 7)]
        topics = ["a", "b", "a", "b", "a", "b"]
        assignments = {row.id: [_assignment(t)] for row, t in zip(rows, topics, strict=True)}
        exploit = [rows[0], rows[1], rows[2], rows[3]]
        explore = [rows[3], rows[4], rows[0]]
        fallback = [rows[5], rows[1]]

        merged = _merge(merge, kwargs, context_key, (exploit, explore, fallback), assignments, 10)

        assert [row.id for row in merged] == [1, 2, 3, 4, 6, 5]

    def test_dominant_topic_is_highest_confidence(self, merge, kwargs, context_key, dominant_topic):
        rows = [_row(i) for i in range(1, 5)]
        assignments = {
            1: [_assignment("x", 0.4), _assignment("a", 0.8)],
            2: [_assignment("a", 0.9)],
            3: [_assignment("a", 0.5), _assignment("b", 0.7)],
            4: [_assignment("a", 0.6)],
        }

        merged = _merge(
            merge,
            kwargs,
            context_key,
            ([rows[0], rows[1], rows[3], rows[2]], [], []),
            assignments,
            4,
        )

        assert [row.id for row in merged] == [1, 2, 3, 4]

    def test_stops_at_target_size_and_on_empty_pools(
        self, merge, kwargs, context_key, dominant_topic
    ):
        rows = [_row(i) for i in range(1, 6)]
        assignments = {row.id: [_assignment("a")] for row in rows}

        assert [
            row.id for row in _merge(merge, kwargs, context_key, (rows, [], []), assignments, 3)
        ] == [1, 2, 3]
        assert _merge(merge, kwargs, context_key, ([], [], []), assignments, 3) == []

    def test_matches_original_loop_on_random_inputs(
        self, merge, kwargs, context_key, dominant_topic
    ):
        rng = random.Random(20261020)
        for _ in range(300):
            n = rng.randint(0, 40)
            topic_count = rng.choice([1, 1, 2, 3, 5])
            rows = [_row(i) for i in range(1, n + 1)]
            assignments = {}
            for row in rows:
                if rng.random() < 0.1:
                    continue  # no assignment -> "uncategorized"
                assignments[row.id] = [
                    _assignment(f"t{rng.randrange(topic_count)}", rng.choice([0.3, 0.6, 0.9]))
                    for _ in range(rng.randint(1, 2))
                ]
            pools = tuple(rng.sample(rows, rng.randint(0, n)) if n else [] for _ in range(3))
            target_size = rng.choice([n, n // 2, n + 3])
            context = {context_key: assignments}

            expected = _reference_merge(
                pools=pools,
                ranking_context=context,
                target_size=target_size,
                dominant_topic=dominant_topic,
            )
            merged = _merge(merge, kwargs, context_key, pools, assignments, target_size)

            assert [row.id for row in merged] == [row.id for row in expected]
