from datetime import datetime, timedelta, timezone

from app.extensions.db import db
from app.models.ledger import Transaction
from app.models.user import User


class TestLedgerSummaryApi:
    def test_summary_and_gamification_use_lifetime_earned_points(
        self, app, client, make_auth_headers
    ):
        user_id, headers = make_auth_headers(points=60)

        with app.app_context():
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
        summary = summary_response.get_json()["data"]
        assert summary["current_points"] == 60
        assert summary["total_points_earned"] == 220

        assert gamification_response.status_code == 200
        gamification = gamification_response.get_json()["data"]
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
    created_at = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours_ago)
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

    def test_returns_ranked_weekly_points_growth(self, app, client, make_auth_headers):
        current_user_id, current_headers = make_auth_headers()
        second_user_id, _ = make_auth_headers()
        third_user_id, _ = make_auth_headers()

        with app.app_context():
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
        data = response.get_json()["data"]
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
