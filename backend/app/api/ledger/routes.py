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
# GET /api/ledger/records
# List the current user's waste analysis history. Records are written only
# when a recycling audit passes (recycling_audit_service), never from a
# request body, so this resource is read-only.
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
