from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.market import MarketItem, Order
from app.models.project import Project
from app.repositories.ai import recycling_case_repository
from app.repositories.forum import forum_repository
from app.repositories.market import market_repository
from app.repositories.project import project_repository
from app.repositories.recommendation import behavior_event_repository, preference_profile_repository
from app.services.recommendation.topic_taxonomy import map_recycling_item_to_topics


def record_behavior_event(
    session: Session,
    *,
    user_id: int,
    domain: str,
    action_type: str,
    target_type: str,
    target_id: int,
    topic_payload: list[dict] | None = None,
    context: dict | None = None,
    created_at: datetime | None = None,
):
    return behavior_event_repository.create_behavior_event(
        session,
        user_id=user_id,
        domain=domain,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        topic_payload=topic_payload,
        context=context,
        created_at=created_at,
    )


def _require_post_exists(session: Session, post_id: int) -> None:
    if forum_repository.get_post_by_id(session, post_id) is None:
        raise ValueError(f"Forum post {post_id} not found.")


def _require_case_exists(session: Session, case_id: int, user_id: int) -> None:
    if recycling_case_repository.get_case(session, case_id, user_id) is None:
        raise ValueError(f"Recycling case {case_id} not found for user {user_id}.")


def _forum_post_topics(session: Session, post_id: int) -> list[dict]:
    assignments = preference_profile_repository.list_content_topic_assignments(
        session,
        domain="forum",
        content_type="post",
        content_id=post_id,
    )
    if assignments:
        return [
            {
                "topic_id": assignment.topic_id,
                "confidence_score": float(assignment.confidence_score or 0.0),
            }
            for assignment in assignments
        ]
    return [{"topic_id": "uncategorized", "confidence_score": 1.0}]


def _require_item(session: Session, item_id: int) -> MarketItem:
    item = market_repository.get_item_by_id(session, item_id)
    if item is None:
        raise ValueError(f"Market item {item_id} not found.")
    return item


def _require_order(session: Session, order_id: int) -> Order:
    order = market_repository.get_order_by_id(session, order_id)
    if order is None:
        raise ValueError(f"Market order {order_id} not found.")
    return order


def _require_project(session: Session, project_id: int) -> Project:
    project = project_repository.get_project_by_id(session, project_id)
    if project is None:
        raise ValueError(f"Project {project_id} not found.")
    return project


def _market_item_topics(session: Session, item_id: int) -> list[dict]:
    assignments = preference_profile_repository.list_content_topic_assignments(
        session,
        domain="market",
        content_type="item",
        content_id=item_id,
    )
    if assignments:
        return [
            {
                "topic_id": assignment.topic_id,
                "confidence_score": float(assignment.confidence_score or 0.0),
            }
            for assignment in assignments
        ]
    return [{"topic_id": "uncategorized", "confidence_score": 1.0}]


def _project_topics(session: Session, project_id: int) -> list[dict]:
    assignments = preference_profile_repository.list_content_topic_assignments(
        session,
        domain="project",
        content_type="project",
        content_id=project_id,
    )
    if assignments:
        return [
            {
                "topic_id": assignment.topic_id,
                "confidence_score": float(assignment.confidence_score or 0.0),
            }
            for assignment in assignments
        ]
    return [{"topic_id": "uncategorized", "confidence_score": 1.0}]


def _resolve_post_id_for_forum_target(session: Session, *, target_type: str, target_id: int) -> int:
    normalized_target_type = str(target_type).strip().lower()
    if normalized_target_type == "post":
        _require_post_exists(session, target_id)
        return target_id
    if normalized_target_type == "comment":
        comment = forum_repository.get_comment_by_id(session, target_id)
        if comment is None:
            raise ValueError(f"Forum comment {target_id} not found.")
        return int(comment.post_id)
    raise ValueError(f"Unsupported forum target_type: {target_type}")


def record_forum_view(
    session: Session, *, user_id: int, post_id: int, created_at: datetime | None = None
):
    _require_post_exists(session, post_id)
    return record_behavior_event(
        session,
        user_id=user_id,
        domain="forum",
        action_type="view",
        target_type="post",
        target_id=post_id,
        topic_payload=_forum_post_topics(session, post_id),
        context={"post_id": post_id},
        created_at=created_at,
    )


def record_forum_long_view(
    session: Session, *, user_id: int, post_id: int, created_at: datetime | None = None
):
    _require_post_exists(session, post_id)
    return record_behavior_event(
        session,
        user_id=user_id,
        domain="forum",
        action_type="long_view",
        target_type="post",
        target_id=post_id,
        topic_payload=_forum_post_topics(session, post_id),
        context={"post_id": post_id},
        created_at=created_at,
    )


def record_forum_like(
    session: Session,
    *,
    user_id: int,
    target_type: str,
    target_id: int,
    created_at: datetime | None = None,
):
    post_id = _resolve_post_id_for_forum_target(
        session, target_type=target_type, target_id=target_id
    )
    return record_behavior_event(
        session,
        user_id=user_id,
        domain="forum",
        action_type="like",
        target_type=str(target_type).strip().lower(),
        target_id=target_id,
        topic_payload=_forum_post_topics(session, post_id),
        context={"post_id": post_id, "target_type": target_type},
        created_at=created_at,
    )


def record_forum_unlike(
    session: Session,
    *,
    user_id: int,
    target_type: str,
    target_id: int,
    created_at: datetime | None = None,
):
    post_id = _resolve_post_id_for_forum_target(
        session, target_type=target_type, target_id=target_id
    )
    return record_behavior_event(
        session,
        user_id=user_id,
        domain="forum",
        action_type="unlike",
        target_type=str(target_type).strip().lower(),
        target_id=target_id,
        topic_payload=_forum_post_topics(session, post_id),
        context={"post_id": post_id, "target_type": target_type},
        created_at=created_at,
    )


def record_forum_comment_or_reply(
    session: Session,
    *,
    user_id: int,
    post_id: int,
    created_at: datetime | None = None,
):
    _require_post_exists(session, post_id)
    return record_behavior_event(
        session,
        user_id=user_id,
        domain="forum",
        action_type="comment_or_reply",
        target_type="post",
        target_id=post_id,
        topic_payload=_forum_post_topics(session, post_id),
        context={"post_id": post_id},
        created_at=created_at,
    )


def _recycling_case_topics(session: Session, *, user_id: int, recycling_case_id: int) -> list[dict]:
    case = recycling_case_repository.get_case(session, recycling_case_id, user_id)
    if case is None:
        raise ValueError(f"Recycling case {recycling_case_id} not found for user {user_id}.")
    return map_recycling_item_to_topics(case.waste_type_predicted)


def record_ai_recycling_case_pending_audit(
    session: Session,
    *,
    user_id: int,
    recycling_case_id: int,
    created_at: datetime | None = None,
):
    _require_case_exists(session, recycling_case_id, user_id)
    return record_behavior_event(
        session,
        user_id=user_id,
        domain="ai",
        action_type="recycling_case_pending_audit",
        target_type="recycling_case",
        target_id=recycling_case_id,
        topic_payload=_recycling_case_topics(
            session, user_id=user_id, recycling_case_id=recycling_case_id
        ),
        context={"recycling_case_id": recycling_case_id, "status": "pending_audit"},
        created_at=created_at,
    )


def record_ai_recycling_case_failed_audit(
    session: Session,
    *,
    user_id: int,
    recycling_case_id: int,
    created_at: datetime | None = None,
):
    _require_case_exists(session, recycling_case_id, user_id)
    return record_behavior_event(
        session,
        user_id=user_id,
        domain="ai",
        action_type="recycling_case_failed_audit",
        target_type="recycling_case",
        target_id=recycling_case_id,
        topic_payload=_recycling_case_topics(
            session, user_id=user_id, recycling_case_id=recycling_case_id
        ),
        context={"recycling_case_id": recycling_case_id, "status": "audit_failed"},
        created_at=created_at,
    )


def record_ai_recycling_case_passed_audit(
    session: Session,
    *,
    user_id: int,
    recycling_case_id: int,
    created_at: datetime | None = None,
):
    _require_case_exists(session, recycling_case_id, user_id)
    return record_behavior_event(
        session,
        user_id=user_id,
        domain="ai",
        action_type="recycling_case_passed_audit",
        target_type="recycling_case",
        target_id=recycling_case_id,
        topic_payload=_recycling_case_topics(
            session, user_id=user_id, recycling_case_id=recycling_case_id
        ),
        context={"recycling_case_id": recycling_case_id, "status": "audit_passed"},
        created_at=created_at,
    )


def record_ai_accept(
    session: Session,
    *,
    user_id: int,
    target_id: int,
    created_at: datetime | None = None,
):
    return record_behavior_event(
        session,
        user_id=user_id,
        domain="ai",
        action_type="ai_accept",
        target_type="assistant_suggestion",
        target_id=target_id,
        topic_payload=None,
        context={"target_id": target_id},
        created_at=created_at,
    )


def record_market_view(
    session: Session, *, user_id: int, item_id: int, created_at: datetime | None = None
):
    item = _require_item(session, item_id)
    return record_behavior_event(
        session,
        user_id=user_id,
        domain="market",
        action_type="view",
        target_type="item",
        target_id=item_id,
        topic_payload=_market_item_topics(session, item_id),
        context={"item_id": item_id, "seller_id": item.seller_id},
        created_at=created_at,
    )


def record_market_long_view(
    session: Session, *, user_id: int, item_id: int, created_at: datetime | None = None
):
    item = _require_item(session, item_id)
    return record_behavior_event(
        session,
        user_id=user_id,
        domain="market",
        action_type="long_view",
        target_type="item",
        target_id=item_id,
        topic_payload=_market_item_topics(session, item_id),
        context={"item_id": item_id, "seller_id": item.seller_id},
        created_at=created_at,
    )


def record_market_order(
    session: Session,
    *,
    user_id: int,
    order_id: int,
    item_id: int,
    created_at: datetime | None = None,
):
    order = _require_order(session, order_id)
    item = _require_item(session, item_id)
    if order.item_id != item_id:
        raise ValueError(f"Market order {order_id} does not belong to item {item_id}.")
    return record_behavior_event(
        session,
        user_id=user_id,
        domain="market",
        action_type="market_order",
        target_type="order",
        target_id=order_id,
        topic_payload=_market_item_topics(session, item_id),
        context={"order_id": order_id, "item_id": item_id, "seller_id": item.seller_id},
        created_at=created_at,
    )


def record_market_item_create(
    session: Session, *, user_id: int, item_id: int, created_at: datetime | None = None
):
    item = _require_item(session, item_id)
    return record_behavior_event(
        session,
        user_id=user_id,
        domain="market",
        action_type="market_item_create",
        target_type="item",
        target_id=item_id,
        topic_payload=_market_item_topics(session, item_id),
        context={"item_id": item_id, "price_points": item.price_points},
        created_at=created_at,
    )


def record_market_order_completed_as_seller(
    session: Session,
    *,
    user_id: int,
    order_id: int,
    item_id: int,
    created_at: datetime | None = None,
):
    order = _require_order(session, order_id)
    _require_item(session, item_id)
    if order.item_id != item_id:
        raise ValueError(f"Market order {order_id} does not belong to item {item_id}.")
    return record_behavior_event(
        session,
        user_id=user_id,
        domain="market",
        action_type="market_order_completed_as_seller",
        target_type="order",
        target_id=order_id,
        topic_payload=_market_item_topics(session, item_id),
        context={"order_id": order_id, "item_id": item_id, "buyer_id": order.buyer_id},
        created_at=created_at,
    )


def record_project_view(
    session: Session, *, user_id: int, project_id: int, created_at: datetime | None = None
):
    project = _require_project(session, project_id)
    return record_behavior_event(
        session,
        user_id=user_id,
        domain="project",
        action_type="view",
        target_type="project",
        target_id=project_id,
        topic_payload=_project_topics(session, project_id),
        context={"project_id": project_id, "creator_user_id": project.creator_user_id},
        created_at=created_at,
    )


def record_project_create(
    session: Session, *, user_id: int, project_id: int, created_at: datetime | None = None
):
    project = _require_project(session, project_id)
    return record_behavior_event(
        session,
        user_id=user_id,
        domain="project",
        action_type="project_create",
        target_type="project",
        target_id=project_id,
        topic_payload=_project_topics(session, project_id),
        context={"project_id": project_id, "points_target": project.points_target},
        created_at=created_at,
    )


def record_project_contribute(
    session: Session,
    *,
    user_id: int,
    project_id: int,
    contribution_id: int,
    created_at: datetime | None = None,
):
    project = _require_project(session, project_id)
    return record_behavior_event(
        session,
        user_id=user_id,
        domain="project",
        action_type="project_contribute",
        target_type="project",
        target_id=project_id,
        topic_payload=_project_topics(session, project_id),
        context={
            "project_id": project_id,
            "contribution_id": contribution_id,
            "creator_user_id": project.creator_user_id,
        },
        created_at=created_at,
    )
