from app.repositories.ledger import ledger_repository
from app.repositories.profile import user_repository

# Gamification: one "segment" = 200 score units (points + carbon*10).
_SEGMENT = 200
_MAX_LEVEL = 50


def record_waste_analysis(
    *,
    user_id: int,
    waste_type: str,
    co2_saved_kg: float,
    carbon_points: float,
    image_url: str | None = None,
    raw_ai_response_json: str | None = None,
) -> dict:
    """Persist an AI analysis result, earn points, and return summary dict."""
    pts = int(round(carbon_points))
    record, _txn, user = ledger_repository.record_analysis_and_earn(
        user_id=user_id,
        waste_type=waste_type,
        co2_saved_kg=co2_saved_kg,
        carbon_points=pts,
        image_url=image_url,
        raw_ai_response_json=raw_ai_response_json,
    )
    return {
        "record_id": record.id,
        "waste_type": record.waste_type,
        "co2_saved_kg": record.co2_saved_kg,
        "carbon_points": record.carbon_points,
        "new_total_carbon": user.total_carbon_amount,
        "new_total_points": user.current_points,
    }


def get_waste_records(user_id: int, page: int, per_page: int) -> dict:
    records, total = ledger_repository.get_waste_records_page(user_id, page, per_page)
    return {
        "items": [
            {
                "id": r.id,
                "waste_type": r.waste_type,
                "co2_saved_kg": r.co2_saved_kg,
                "carbon_points": r.carbon_points,
                "image_url": r.image_url,
                "created_at": r.created_at.isoformat(),
            }
            for r in records
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


def get_transactions(user_id: int, page: int, per_page: int) -> dict:
    txns, total = ledger_repository.get_transactions_page(user_id, page, per_page)
    return {
        "items": [
            {
                "id": t.id,
                "type": t.type,
                "points_delta": t.points_delta,
                "co2_delta_kg": t.co2_delta_kg,
                "source_type": t.source_type,
                "source_id": t.source_id,
                "created_at": t.created_at.isoformat(),
            }
            for t in txns
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


def get_summary(user_id: int) -> dict | None:
    user = user_repository.get_by_id(user_id)
    if not user:
        return None
    total_points_earned = ledger_repository.sum_earned_points(user_id)
    return {
        "total_carbon_amount": user.total_carbon_amount,
        "current_points": user.current_points,
        "total_points_earned": total_points_earned,
    }


def get_gamification(user_id: int) -> dict | None:
    """Derive level, XP bar, and unlocked badges from ledger totals (no extra tables)."""
    user = user_repository.get_by_id(user_id)
    if not user:
        return None

    total_carbon = float(user.total_carbon_amount or 0.0)
    current_points = int(user.current_points or 0)
    total_points_earned = ledger_repository.sum_earned_points(user_id)
    contribution_points = max(total_points_earned, current_points)
    score = contribution_points + int(round(total_carbon * 10.0))

    level = min(_MAX_LEVEL, max(1, score // _SEGMENT + 1))
    xp_in_level = score % _SEGMENT
    xp_to_next = _SEGMENT

    tier_index = min(level - 1, len(_LEVEL_TITLES) - 1)
    level_title = _LEVEL_TITLES[max(0, tier_index)]

    badges = _compute_badges(total_carbon=total_carbon, points=contribution_points)

    return {
        "level": level,
        "level_title": level_title,
        "xp_in_level": xp_in_level,
        "xp_to_next": xp_to_next,
        "total_carbon_amount": total_carbon,
        "current_points": current_points,
        "total_points_earned": contribution_points,
        "score": score,
        "badges": badges,
    }


def get_weekly_leaderboard(
    user_id: int,
    *,
    window_days: int = 7,
    limit: int = 5,
) -> dict:
    rows = ledger_repository.get_weekly_points_gains(window_days)
    ranked_rows = []
    current_user_rank = None

    for index, row in enumerate(rows, start=1):
        ranked_entry = {
            "user_id": row["user_id"],
            "avatar_url": row["avatar_url"],
            "weekly_points_gain": row["weekly_points_gain"],
            "rank": index,
        }
        ranked_rows.append(ranked_entry)
        if row["user_id"] == user_id:
            current_user_rank = ranked_entry

    return {
        "window_days": window_days,
        "top_users": ranked_rows[:limit],
        "current_user_rank": current_user_rank,
    }


_LEVEL_TITLES = (
    "Carbon sprout",
    "Green apprentice",
    "Loop learner",
    "Low-carbon walker",
    "Footprint explorer",
    "Sustainability scout",
    "Eco guardian",
    "Net-zero pathfinder",
    "Planet partner",
    "Carbon legend",
)


def _compute_badges(*, total_carbon: float, points: int) -> list[dict]:
    out: list[dict] = []
    if total_carbon >= 0.01:
        out.append(
            {
                "id": "first_carbon",
                "name": "First step",
                "description": "Saved over 0.01 kg CO₂ (total)",
            }
        )
    if total_carbon >= 10:
        out.append(
            {
                "id": "carbon_10",
                "name": "Ten kilo club",
                "description": "Reached 10 kg CO₂ saved (total)",
            }
        )
    if points >= 100:
        out.append(
            {
                "id": "points_100",
                "name": "Hundred points",
                "description": "Lifetime earned points reached 100",
            }
        )
    if points >= 500:
        out.append(
            {
                "id": "points_500",
                "name": "Points whale",
                "description": "Lifetime earned points reached 500",
            }
        )
    # Streak / forum badges need extra data; omitted for lean schema.
    return out
