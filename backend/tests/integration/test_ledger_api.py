from datetime import UTC, datetime, timedelta

from app.models.ledger import Transaction
from app.models.user import User
from tests.support.database import db


class TestLedgerSummaryApi:
    def test_summary_and_gamification_use_lifetime_earned_points(self, client, make_auth_headers):
        user_id, headers = make_auth_headers(points=60)

        _seed_transaction(user_id=user_id, points_delta=100)
        _seed_transaction(user_id=user_id, points_delta=120)
        _seed_transaction(
            user_id=user_id,
            points_delta=160,
            txn_type="spend",
        )
        db.session.commit()

        summary_response = client.get("/api/ledger/summary", headers=headers)
        gamification_response = client.get("/api/ledger/gamification", headers=headers)

        assert summary_response.status_code == 200
        summary = summary_response.json()["data"]
        assert summary["current_points"] == 60
        assert summary["total_points_earned"] == 220

        assert gamification_response.status_code == 200
        gamification = gamification_response.json()["data"]
        assert gamification["current_points"] == 60
        assert gamification["total_points_earned"] == 220
        assert gamification["score"] == 220
        assert gamification["level"] == 2
        assert {badge["id"] for badge in gamification["badges"]} == {"points_100"}


def _seed_transaction(
    *,
    user_id: int,
    points_delta: int,
    txn_type: str = "earn",
    days_ago: int = 0,
    hours_ago: int = 0,
) -> None:
    created_at = datetime.now(UTC) - timedelta(days=days_ago, hours=hours_ago)
    db.session.add(
        Transaction(
            user_id=user_id,
            type=txn_type,
            points_delta=points_delta,
            co2_delta_kg=0.0,
            source_type="test_seed",
            created_at=created_at,
        )
    )


class TestLedgerWeeklyLeaderboardApi:
    def test_requires_authentication(self, client):
        response = client.get("/api/ledger/leaderboard/weekly")

        assert response.status_code == 401

    def test_returns_ranked_weekly_points_growth(self, client, make_auth_headers):
        current_user_id, current_headers = make_auth_headers()
        second_user_id, _ = make_auth_headers()
        third_user_id, _ = make_auth_headers()

        users = {
            current_user_id: db.session.get(User, current_user_id),
            second_user_id: db.session.get(User, second_user_id),
            third_user_id: db.session.get(User, third_user_id),
        }
        users[current_user_id].avatar_url = "https://example.com/avatars/current.png"
        users[second_user_id].avatar_url = "https://example.com/avatars/second.png"
        users[third_user_id].avatar_url = "https://example.com/avatars/third.png"

        _seed_transaction(user_id=current_user_id, points_delta=45, days_ago=1)
        _seed_transaction(user_id=current_user_id, points_delta=25, days_ago=3)
        _seed_transaction(user_id=current_user_id, points_delta=500, days_ago=10)
        _seed_transaction(
            user_id=current_user_id,
            points_delta=30,
            txn_type="spend",
            days_ago=2,
        )

        _seed_transaction(user_id=second_user_id, points_delta=120, hours_ago=2)
        _seed_transaction(user_id=second_user_id, points_delta=15, days_ago=6)

        _seed_transaction(user_id=third_user_id, points_delta=40, days_ago=2)

        db.session.commit()

        response = client.get("/api/ledger/leaderboard/weekly", headers=current_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["window_days"] == 7

        top_users = data["top_users"]
        assert [item["rank"] for item in top_users] == [1, 2, 3]
        assert [item["weekly_points_gain"] for item in top_users] == [135, 70, 40]
        assert [item["avatar_url"] for item in top_users] == [
            "https://example.com/avatars/second.png",
            "https://example.com/avatars/current.png",
            "https://example.com/avatars/third.png",
        ]
        assert all("username" not in item for item in top_users)

        current_user_rank = data["current_user_rank"]
        assert current_user_rank == {
            "rank": 2,
            "user_id": current_user_id,
            "avatar_url": "https://example.com/avatars/current.png",
            "weekly_points_gain": 70,
        }


class TestLedgerRecordsApi:
    def test_post_cannot_mint_points(self, client, make_auth_headers):
        # Points are earned only when a recycling audit passes; a client that
        # names its own reward must get nothing.
        _, headers = make_auth_headers(points=60)

        response = client.post(
            "/api/ledger/records",
            json={"waste_type": "x", "co2_saved_kg": 1000, "carbon_points": 100000},
            headers=headers,
        )

        summary = client.get("/api/ledger/summary", headers=headers).json()["data"]
        assert summary["current_points"] == 60
        assert summary["total_carbon_amount"] == 0
        assert summary["total_points_earned"] == 0
        records = client.get("/api/ledger/records", headers=headers).json()["data"]
        assert records["total"] == 0
        assert response.status_code == 405


# ---------------------------------------------------------------------------
# Response shapes and paging, pinned before the routes moved to FastAPI.
# ---------------------------------------------------------------------------

_NAIVE_ISO = r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?"


def _seed_record(*, user_id: int, waste_type: str, points: int, days_ago: int = 0) -> None:
    from app.models.ai import WasteAnalysisRecord

    db.session.add(
        WasteAnalysisRecord(
            user_id=user_id,
            waste_type=waste_type,
            co2_saved_kg=points / 10,
            carbon_points=points,
            image_url=f"/api/uploads/ai/{waste_type}.png",
            created_at=datetime.now(UTC) - timedelta(days=days_ago),
        )
    )


class TestLedgerListsApi:
    def test_records_newest_first_with_paging(self, client, make_auth_headers):
        import re

        user_id, headers = make_auth_headers()
        other_id, _ = make_auth_headers()
        _seed_record(user_id=user_id, waste_type="glass", points=5, days_ago=2)
        _seed_record(user_id=user_id, waste_type="paper", points=3, days_ago=1)
        _seed_record(user_id=user_id, waste_type="plastic", points=8)
        _seed_record(user_id=other_id, waste_type="metal", points=9)
        db.session.commit()

        response = client.get("/api/ledger/records?page=1&per_page=2", headers=headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert (data["total"], data["page"], data["per_page"]) == (3, 1, 2)
        assert [item["waste_type"] for item in data["items"]] == ["plastic", "paper"]
        item = data["items"][0]
        assert set(item) == {
            "id",
            "waste_type",
            "co2_saved_kg",
            "carbon_points",
            "image_url",
            "created_at",
        }
        assert (item["co2_saved_kg"], item["carbon_points"]) == (0.8, 8)
        assert item["image_url"] == "/api/uploads/ai/plastic.png"
        assert re.fullmatch(_NAIVE_ISO, item["created_at"])

        page_two = client.get("/api/ledger/records?page=2&per_page=2", headers=headers)
        assert [i["waste_type"] for i in page_two.json()["data"]["items"]] == ["glass"]

    def test_transactions_newest_first(self, client, make_auth_headers):
        user_id, headers = make_auth_headers()
        _seed_transaction(user_id=user_id, points_delta=10, days_ago=1)
        _seed_transaction(user_id=user_id, points_delta=4, txn_type="spend")
        db.session.commit()

        response = client.get("/api/ledger/transactions", headers=headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert (data["total"], data["page"], data["per_page"]) == (2, 1, 20)
        assert [(t["type"], t["points_delta"]) for t in data["items"]] == [
            ("spend", 4),
            ("earn", 10),
        ]
        assert set(data["items"][0]) == {
            "id",
            "type",
            "points_delta",
            "co2_delta_kg",
            "source_type",
            "source_id",
            "created_at",
        }
        assert data["items"][0]["source_type"] == "test_seed"
        assert data["items"][0]["source_id"] is None

    def test_out_of_range_paging_is_clamped(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = client.get("/api/ledger/transactions?page=0&per_page=500", headers=headers)

        data = response.json()["data"]
        assert (data["page"], data["per_page"]) == (1, 100)

    def test_empty_ledger(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        summary = client.get("/api/ledger/summary", headers=headers).json()["data"]
        gamification = client.get("/api/ledger/gamification", headers=headers).json()["data"]
        leaderboard = client.get("/api/ledger/leaderboard/weekly", headers=headers).json()["data"]

        assert summary == {
            "total_carbon_amount": 0.0,
            "current_points": 0,
            "total_points_earned": 0,
        }
        assert gamification == {
            "level": 1,
            "level_title": "Carbon sprout",
            "xp_in_level": 0,
            "xp_to_next": 200,
            "total_carbon_amount": 0.0,
            "current_points": 0,
            "total_points_earned": 0,
            "score": 0,
            "badges": [],
        }
        assert leaderboard == {"window_days": 7, "top_users": [], "current_user_rank": None}

    def test_badge_fields(self, client, make_auth_headers):
        user_id, headers = make_auth_headers()
        db.session.get(User, user_id).total_carbon_amount = 12.5
        db.session.commit()

        badges = client.get("/api/ledger/gamification", headers=headers).json()["data"]["badges"]

        assert badges == [
            {
                "id": "first_carbon",
                "name": "First step",
                "description": "Saved over 0.01 kg CO₂ (total)",
            },
            {
                "id": "carbon_10",
                "name": "Ten kilo club",
                "description": "Reached 10 kg CO₂ saved (total)",
            },
        ]

    def test_summary_for_a_deleted_user(self, make_user, client):
        # A valid token whose user no longer exists.
        from app.core.security import create_access_token

        headers = {"Authorization": f"Bearer {create_access_token(999_999)}"}

        for path in ("/api/ledger/summary", "/api/ledger/gamification"):
            response = client.get(path, headers=headers)
            assert response.status_code == 404
            assert response.json() == {"code": 40400, "message": "User not found.", "data": {}}

    def test_legacy_token_with_username_subject(self, client, make_user):
        from app.core.security import create_access_token

        make_user(username="legacy", email="legacy@example.com")
        token = create_access_token("legacy")

        response = client.get("/api/ledger/summary", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
