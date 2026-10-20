"""Interleave the exploit / explore / fallback pools of a personalised list.

Each slot of `pattern` says which pool to prefer; the other two follow as
backups. The diversity guard skips a row whose dominant topic would make
`max_run + 1` rows of one topic in a row, unless every remaining row would.

The guard only ever blocks one topic: the topic of the last `max_run` rows,
when they all share it. So each pool keeps one queue per topic, in pool order,
and "the first usable row" is the queue head with the smallest position,
skipping the blocked topic's queue. A row already taken through another pool
stays in its queues and is dropped when it reaches a head. Each pick costs
O(topics), so a merge is O(rows x topics) instead of rescanning the pools from
the start for every pick.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence


class _TopicQueues[T]:
    def __init__(self, rows: Sequence[T], topic_by_id: dict[int, str], id_of: Callable[[T], int]):
        self._id_of = id_of
        self._queues: dict[str, deque[tuple[int, T]]] = {}
        for position, row in enumerate(rows):
            topic = topic_by_id[id_of(row)]
            self._queues.setdefault(topic, deque()).append((position, row))

    def first(self, used_ids: set[int], blocked_topic: str | None) -> tuple[str, T] | None:
        best: tuple[int, str, T] | None = None
        for topic, queue in self._queues.items():
            if topic == blocked_topic:
                continue
            while queue and self._id_of(queue[0][1]) in used_ids:
                queue.popleft()
            if queue and (best is None or queue[0][0] < best[0]):
                best = (queue[0][0], topic, queue[0][1])
        return None if best is None else (best[1], best[2])

    def take(self, topic: str) -> None:
        self._queues[topic].popleft()


def merge_ranked[T](
    *,
    exploit: Sequence[T],
    explore: Sequence[T],
    fallback: Sequence[T],
    pattern: Sequence[str],
    max_run: int,
    topic_of: Callable[[T], str],
    id_of: Callable[[T], int],
    target_size: int,
) -> list[T]:
    topic_by_id: dict[int, str] = {}
    for row in (*exploit, *explore, *fallback):
        row_id = id_of(row)
        if row_id not in topic_by_id:
            topic_by_id[row_id] = topic_of(row)

    exploit_pool = _TopicQueues(exploit, topic_by_id, id_of)
    explore_pool = _TopicQueues(explore, topic_by_id, id_of)
    fallback_pool = _TopicQueues(fallback, topic_by_id, id_of)
    explore_first = [explore_pool, exploit_pool, fallback_pool]
    exploit_first = [exploit_pool, fallback_pool, explore_pool]

    merged: list[T] = []
    merged_topics: list[str] = []
    used_ids: set[int] = set()

    def pick(pools: list[_TopicQueues[T]], blocked_topic: str | None) -> T | None:
        for pool in pools:
            found = pool.first(used_ids, blocked_topic)
            if found is not None:
                topic, row = found
                pool.take(topic)
                return row
        return None

    while len(merged) < target_size:
        if pattern[len(merged) % len(pattern)] == "explore":
            pools = explore_first
        else:
            pools = exploit_first

        blocked_topic = None
        recent = merged_topics[-max_run:]
        if len(merged_topics) >= max_run and all(topic == recent[0] for topic in recent):
            blocked_topic = recent[0]

        candidate = pick(pools, blocked_topic)
        if candidate is None and blocked_topic is not None:
            candidate = pick(pools, None)
        if candidate is None:
            break
        merged.append(candidate)
        merged_topics.append(topic_by_id[id_of(candidate)])
        used_ids.add(id_of(candidate))

    return merged
