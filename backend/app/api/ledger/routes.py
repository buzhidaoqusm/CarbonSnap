from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.ledger import ledger_service
from app.utils.response import fail, ok

ledger_bp = Blueprint("ledger", __name__)


def _parse_pagination() -> tuple[int, int]:
    """Extract and clamp page / per_page from query string."""
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    except (TypeError, ValueError):
        per_page = 20
    return page, per_page


# ---------------------------------------------------------------------------
# POST /api/ledger/records
# Save an AI analysis result, earn points atomically.
# ---------------------------------------------------------------------------


@ledger_bp.post("/ledger/records")
@jwt_required()
def create_record():
    user_id = int(get_jwt_identity())
    body = request.get_json(silent=True) or {}

    waste_type = str(body.get("waste_type", "")).strip()
    if not waste_type:
        return fail(40001, "Field 'waste_type' is required.")

    try:
        co2_saved_kg = float(body.get("co2_saved_kg", 0))
        carbon_points = float(body.get("carbon_points", 0))
    except (TypeError, ValueError):
        return fail(40001, "Fields 'co2_saved_kg' and 'carbon_points' must be numbers.")

    if co2_saved_kg < 0 or carbon_points < 0:
        return fail(40001, "Fields 'co2_saved_kg' and 'carbon_points' must be non-negative.")

    result = ledger_service.record_waste_analysis(
        user_id=user_id,
        waste_type=waste_type,
        co2_saved_kg=co2_saved_kg,
        carbon_points=carbon_points,
        image_url=body.get("image_url") or None,
        raw_ai_response_json=body.get("raw_ai_response_json") or None,
    )
    return ok(result, status=201)


# ---------------------------------------------------------------------------
# GET /api/ledger/records
# List the current user's waste analysis history.
# ---------------------------------------------------------------------------


@ledger_bp.get("/ledger/records")
@jwt_required()
def list_records():
    user_id = int(get_jwt_identity())
    page, per_page = _parse_pagination()
    return ok(ledger_service.get_waste_records(user_id, page, per_page))


# ---------------------------------------------------------------------------
# GET /api/ledger/transactions
# List the current user's point transaction history.
# ---------------------------------------------------------------------------


@ledger_bp.get("/ledger/transactions")
@jwt_required()
def list_transactions():
    user_id = int(get_jwt_identity())
    page, per_page = _parse_pagination()
    return ok(ledger_service.get_transactions(user_id, page, per_page))


# ---------------------------------------------------------------------------
# GET /api/ledger/summary
# Return carbon total and current points for the current user.
# ---------------------------------------------------------------------------


@ledger_bp.get("/ledger/summary")
@jwt_required()
def summary():
    user_id = int(get_jwt_identity())
    data = ledger_service.get_summary(user_id)
    if data is None:
        return fail(40400, "User not found.", 404)
    return ok(data)


@ledger_bp.get("/ledger/gamification")
@jwt_required()
def gamification():
    user_id = int(get_jwt_identity())
    data = ledger_service.get_gamification(user_id)
    if data is None:
        return fail(40400, "User not found.", 404)
    return ok(data)


@ledger_bp.get("/ledger/leaderboard/weekly")
@jwt_required()
def weekly_leaderboard():
    user_id = int(get_jwt_identity())
    return ok(ledger_service.get_weekly_leaderboard(user_id))
