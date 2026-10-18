"""Bounded candidate sets for the personalised lists.

Ranking scores every candidate in Python, so a logged-in list hands it only the
first RANKING_CANDIDATE_LIMIT rows in the list's plain SQL order. Pages past
those continue in that same order, straight from SQL: the ranked window and the
tail never overlap, so walking every page still shows each row exactly once.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

RANKING_CANDIDATE_LIMIT = 200


def page_of_ranked_then_tail[T](
    ranked: Sequence[T],
    *,
    start: int,
    per_page: int,
    window: int,
    total: int,
    fetch_tail: Callable[[int, int], Sequence[T]],
) -> list[T]:
    """Rows [start, start + per_page) of `ranked` followed by the SQL tail.

    `ranked` holds the first `window` rows of the plain order, re-ordered.
    `fetch_tail(offset, limit)` returns rows of that plain order from `offset`
    on, and is only called when the page runs past the window and there are
    rows left (`total` counts them all).
    """
    page = list(ranked[start : start + per_page])
    missing = per_page - len(page)
    if missing <= 0:
        return page
    offset = max(start, window)
    if offset >= total:
        return page
    return page + list(fetch_tail(offset, missing))
