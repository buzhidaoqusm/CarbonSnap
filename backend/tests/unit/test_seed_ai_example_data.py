from __future__ import annotations

from scripts import seed_ai_example_data

from app.extensions.db import db
from app.models.ai import AIConversation
from app.models.ledger import Transaction
from app.models.memory import UserMemoryItem
from app.models.user import User


def test_collect_referenced_user_seed_keys_includes_ai_demo_user():
    refs = seed_ai_example_data._collect_referenced_user_seed_keys()

    assert "demo-ai-recycler" in refs


def test_sync_seed_user_reuses_existing_user_and_updates_seed_fields(app):
    with app.app_context():
        existing_user = User(
            username="demo_ai_recycler",
            email="ai-recycler@example.com",
            password_hash="old-hash",
            bio="Old bio",
            total_carbon_amount=99.0,
            current_points=999,
        )
        db.session.add(existing_user)
        db.session.commit()

        registry: dict[str, dict[str, int]] = {}
        result = seed_ai_example_data._sync_seed_user(
            seed_key="demo-ai-recycler",
            registry=registry,
        )
        db.session.commit()

        refreshed_user = db.session.get(User, existing_user.id)
        assert result == "updated"
        assert refreshed_user is not None
        assert refreshed_user.id == existing_user.id
        assert refreshed_user.bio == (
            "Uses the AI recycling workspace to sort everyday drink containers "
            "and verify completed drop-offs."
        )
        assert refreshed_user.current_points == 1
        assert registry["users"]["demo-ai-recycler"] == existing_user.id


def test_clear_ai_tables_preserves_non_ai_transactions(app):
    with app.app_context():
        user = User(
            username="seed-ai-clear-user",
            email="seed-ai-clear-user@example.com",
            password_hash="pw",
        )
        db.session.add(user)
        db.session.flush()

        conversation = AIConversation(
            user_id=user.id,
            title="Temporary AI chat",
            status="active",
            current_pending_action="none",
        )
        db.session.add(conversation)
        db.session.flush()

        memory_item = UserMemoryItem(
            user_id=user.id,
            memory_type="preference",
            memory_key="prefer_nearby_options",
            value_json='{"value": true}',
            source_type="conversation",
            conversation_id=conversation.id,
            status="active",
        )
        waste_analysis_transaction = Transaction(
            user_id=user.id,
            type="earn",
            points_delta=3,
            co2_delta_kg=0.2,
            source_type="waste_analysis",
            source_id=101,
        )
        market_transaction = Transaction(
            user_id=user.id,
            type="spend",
            points_delta=5,
            co2_delta_kg=0.0,
            source_type="market_order",
            source_id=202,
        )
        db.session.add_all([memory_item, waste_analysis_transaction, market_transaction])
        db.session.commit()

        summary = seed_ai_example_data._clear_ai_tables()

        assert summary["transactions"] == 1
        assert db.session.query(AIConversation).count() == 0
        assert db.session.query(UserMemoryItem).count() == 0
        remaining_transactions = db.session.query(Transaction).order_by(Transaction.id.asc()).all()
        assert len(remaining_transactions) == 1
        assert remaining_transactions[0].source_type == "market_order"
