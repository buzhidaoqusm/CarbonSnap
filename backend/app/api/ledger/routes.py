"""Points ledger: recycling records, transactions, totals and the leaderboard.

Read-only. Records and transactions are written only when a recycling audit
passes (recycling_audit_service), never from a request body.
"""

from fastapi import APIRouter

from app.api.deps import CurrentUserId, DbSession, PageParams
from app.api.errors import ApiError
from app.schemas.common import Envelope, ok
from app.schemas.ledger import (
    Gamification,
    LedgerSummary,
    TransactionPage,
    WasteRecordPage,
    WeeklyLeaderboard,
)
from app.services.ledger import ledger_service

router = APIRouter(prefix="/api/ledger", tags=["ledger"])


def _user_not_found() -> ApiError:
    # A valid token whose user has since been deleted.
    return ApiError(40400, "User not found.", 404)


@router.get("/records", response_model=Envelope[WasteRecordPage])
def list_records(user_id: CurrentUserId, session: DbSession, paging: PageParams):
    return ok(ledger_service.get_waste_records(session, user_id, paging.page, paging.per_page))


@router.get("/transactions", response_model=Envelope[TransactionPage])
def list_transactions(user_id: CurrentUserId, session: DbSession, paging: PageParams):
    return ok(ledger_service.get_transactions(session, user_id, paging.page, paging.per_page))


@router.get("/summary", response_model=Envelope[LedgerSummary])
def summary(user_id: CurrentUserId, session: DbSession):
    data = ledger_service.get_summary(session, user_id)
    if data is None:
        raise _user_not_found()
    return ok(data)


@router.get("/gamification", response_model=Envelope[Gamification])
def gamification(user_id: CurrentUserId, session: DbSession):
    data = ledger_service.get_gamification(session, user_id)
    if data is None:
        raise _user_not_found()
    return ok(data)


@router.get("/leaderboard/weekly", response_model=Envelope[WeeklyLeaderboard])
def weekly_leaderboard(user_id: CurrentUserId, session: DbSession):
    return ok(ledger_service.get_weekly_leaderboard(session, user_id))
