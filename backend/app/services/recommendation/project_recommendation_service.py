from __future__ import annotations

from datetime import UTC, datetime
from math import exp

from app.models.project import Project
from app.repositories.project import project_repository
from app.repositories.recommendation import behavior_event_repository, preference_profile_repository
from app.services.recommendation import preference_profile_service

NOVELTY_UNSEEN_SCORE = 1.0
NOVELTY_VIEW_SCORE = 0.8
NOVELTY_CONTRIBUTED_SCORE = 0.55
EXPLORATION_WEAK_AFFINITY_MAX = 0.35
EXPLORATION_LOW_EXPOSURE_MAX = 2
EXPLOITATION_MIN_ENGAGEMENT_SCORE = 0.2
EXPLOITATION_MIN_RECENCY_SCORE = 0.6
MERGE_PATTERN = (
    "exploit",
    "exploit",
    "exploit",
    "explore",
    "exploit",
    "exploit",
    "exploit",
    "exploit",
    "explore",
)
MAX_CONSECUTIVE_DOMINANT_TOPIC_PROJECTS = 2


def _ensure_aware_utc(value):
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _clamp_unit_interval(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


def _is_expired(project: Project) -> bool:
    deadline = _ensure_aware_utc(project.deadline_at)
    return _utc_now() > deadline and str(project.status or "").strip().lower() != "completed"


def _supportability_score(project: Project) -> float:
    if str(project.status or "").strip().lower() == "completed":
        return 0.55
    if _is_expired(project):
        return 0.35
    return 1.0


def _recency_score(project: Project) -> float:
    age_days = max(
        (_utc_now() - _ensure_aware_utc(project.created_at)).total_seconds() / 86400.0, 0.0
    )
    if age_days <= 3:
        return 1.0
    if age_days <= 14:
        return 0.6
    return 0.3


def _topic_assignments_for_project(project: Project, ranking_context: dict) -> list:
    assignments_by_project_id = ranking_context.get("topic_assignments_by_project_id") or {}
    return list(assignments_by_project_id.get(int(project.id), []))


def _topic_ids_for_project(project: Project, ranking_context: dict) -> list[str]:
    topic_ids: list[str] = []
    for assignment in _topic_assignments_for_project(project, ranking_context):
        topic_id = str(getattr(assignment, "topic_id", "") or "").strip().lower()
        if topic_id and topic_id not in topic_ids:
            topic_ids.append(topic_id)
    return topic_ids


def _dominant_topic_for_project(project: Project, ranking_context: dict) -> str:
    assignments = _topic_assignments_for_project(project, ranking_context)
    ranked_topics: list[tuple[float, str]] = []
    for assignment in assignments:
        topic_id = str(getattr(assignment, "topic_id", "") or "").strip().lower() or "uncategorized"
        ranked_topics.append((float(getattr(assignment, "confidence_score", 0.0) or 0.0), topic_id))
    if not ranked_topics:
        return "uncategorized"
    ranked_topics.sort(key=lambda item: (-item[0], item[1]))
    return ranked_topics[0][1]


def _max_recent_topic_exposure(project: Project, ranking_context: dict) -> int:
    recent_topic_exposure = ranking_context.get("recent_topic_exposure") or {}
    topic_ids = _topic_ids_for_project(project, ranking_context)
    if not topic_ids:
        topic_ids = ["uncategorized"]
    return max(int(recent_topic_exposure.get(topic_id, 0) or 0) for topic_id in topic_ids)


def _has_uncategorized_only_assignments(project: Project, ranking_context: dict) -> bool:
    topic_ids = _topic_ids_for_project(project, ranking_context)
    if not topic_ids:
        return True
    return all(topic_id == "uncategorized" for topic_id in topic_ids)


def _preference_match_score(project: Project, ranking_context: dict) -> float:
    profile_snapshot = ranking_context.get("profile_snapshot") or {}
    assignments = _topic_assignments_for_project(project, ranking_context)
    if not assignments:
        return 0.0
    weighted_score = 0.0
    for assignment in assignments:
        weighted_score += float(profile_snapshot.get(assignment.topic_id, 0.0)) * float(
            assignment.confidence_score or 0.0
        )
    return round(_clamp_unit_interval(weighted_score), 6)


def _engagement_score(project: Project, ranking_context: dict) -> float:
    contribution_counts = ranking_context.get("contribution_counts_by_project_id") or {}
    contributor_counts = ranking_context.get("contributor_counts_by_project_id") or {}
    contribution_count = float(contribution_counts.get(int(project.id), 0) or 0)
    contributor_count = float(contributor_counts.get(int(project.id), 0) or 0)
    progress_ratio = float(getattr(project, "points_raised", 0) or 0) / max(
        float(getattr(project, "points_target", 1) or 1), 1.0
    )
    raw_score = contribution_count + (contributor_count * 1.5) + (progress_ratio * 2.0)
    if raw_score <= 0:
        return 0.0
    return round(1.0 - exp(-raw_score / 4.0), 6)


def _novelty_score(project: Project, ranking_context: dict) -> float:
    viewed_project_ids = ranking_context.get("viewed_project_ids") or set()
    contributed_project_ids = ranking_context.get("contributed_project_ids") or set()
    if project.id in contributed_project_ids:
        return NOVELTY_CONTRIBUTED_SCORE
    if project.id in viewed_project_ids:
        return NOVELTY_VIEW_SCORE
    return NOVELTY_UNSEEN_SCORE


def _unfamiliarity_score(project: Project, ranking_context: dict) -> float:
    profile_snapshot = ranking_context.get("profile_snapshot") or {}
    assignments = _topic_assignments_for_project(project, ranking_context)
    if not assignments:
        return 0.5
    non_fallback_assignments = [
        assignment for assignment in assignments if assignment.topic_id != "uncategorized"
    ]
    if not non_fallback_assignments:
        return 0.5
    max_topic_match = max(
        float(profile_snapshot.get(assignment.topic_id, 0.0))
        for assignment in non_fallback_assignments
    )
    return round(1.0 - _clamp_unit_interval(max_topic_match), 6)


def is_exploitation_candidate(project: Project, *, ranking_context: dict) -> bool:
    if _preference_match_score(project, ranking_context) > 0.0:
        return True
    if _engagement_score(project, ranking_context) >= EXPLOITATION_MIN_ENGAGEMENT_SCORE:
        return True
    if _recency_score(project) >= EXPLOITATION_MIN_RECENCY_SCORE:
        return True
    return False


def is_exploration_candidate(project: Project, *, ranking_context: dict) -> bool:
    if project.id in (ranking_context.get("viewed_project_ids") or set()):
        return False
    preference_match = _preference_match_score(project, ranking_context)
    weak_affinity = 0.0 < preference_match <= EXPLORATION_WEAK_AFFINITY_MAX
    low_exposure = (
        _max_recent_topic_exposure(project, ranking_context) <= EXPLORATION_LOW_EXPOSURE_MAX
    )
    uncategorized_fallback = _has_uncategorized_only_assignments(project, ranking_context)
    return (weak_affinity and low_exposure) or (uncategorized_fallback and low_exposure)


def exploit_score(project: Project, *, ranking_context: dict) -> float:
    preference_match = _preference_match_score(project, ranking_context)
    recency = _recency_score(project)
    engagement = _engagement_score(project, ranking_context)
    novelty = _novelty_score(project, ranking_context)
    supportability = _supportability_score(project)
    quality_floor = max(recency, engagement, supportability)
    base = (
        (0.50 * preference_match)
        + (0.20 * recency)
        + (0.15 * engagement)
        + (0.10 * novelty)
        + (0.05 * quality_floor)
    )
    return round(base * supportability, 6)


def explore_score(project: Project, *, ranking_context: dict) -> float:
    unfamiliarity = _unfamiliarity_score(project, ranking_context)
    recency = _recency_score(project)
    engagement = _engagement_score(project, ranking_context)
    novelty = _novelty_score(project, ranking_context)
    supportability = _supportability_score(project)
    base = (0.40 * unfamiliarity) + (0.25 * recency) + (0.20 * engagement) + (0.15 * novelty)
    return round(base * supportability, 6)


def _cold_start_score(project: Project, ranking_context: dict) -> float:
    supportability = _supportability_score(project)
    base = (
        (_recency_score(project) * 0.65)
        + (_engagement_score(project, ranking_context) * 0.25)
        + (supportability * 0.10)
    )
    return round(base * supportability, 6)


def _source_index_for_project(project: Project, source_index_by_project_id: dict[int, int]) -> int:
    return int(source_index_by_project_id.get(int(project.id), 0))


def _sort_projects_with_scores(
    *,
    projects: list[Project],
    score_getter,
    ranking_context: dict,
    source_index_by_project_id: dict[int, int],
) -> list[Project]:
    return sorted(
        projects,
        key=lambda project: (
            score_getter(project, ranking_context=ranking_context),
            _ensure_aware_utc(project.created_at),
            project.id,
            -_source_index_for_project(project, source_index_by_project_id),
        ),
        reverse=True,
    )


def _would_violate_diversity_guard(
    *,
    candidate: Project,
    merged_projects: list[Project],
    ranking_context: dict,
) -> bool:
    if len(merged_projects) < MAX_CONSECUTIVE_DOMINANT_TOPIC_PROJECTS:
        return False
    candidate_topic = _dominant_topic_for_project(candidate, ranking_context)
    recent_topics = [
        _dominant_topic_for_project(project, ranking_context)
        for project in merged_projects[-MAX_CONSECUTIVE_DOMINANT_TOPIC_PROJECTS:]
    ]
    return all(topic == candidate_topic for topic in recent_topics)


def _pop_next_candidate_from_pools(
    *,
    pools: list[list[Project]],
    used_project_ids: set[int],
    merged_projects: list[Project],
    ranking_context: dict,
    enforce_diversity_guard: bool,
) -> Project | None:
    for pool in pools:
        for index, project in enumerate(pool):
            project_id = int(project.id)
            if project_id in used_project_ids:
                continue
            if enforce_diversity_guard and _would_violate_diversity_guard(
                candidate=project,
                merged_projects=merged_projects,
                ranking_context=ranking_context,
            ):
                continue
            return pool.pop(index)
    return None


def merge_ranked_projects(
    *,
    exploit_projects: list[Project],
    explore_projects: list[Project],
    fallback_projects: list[Project] | None = None,
    ranking_context: dict,
    target_size: int,
) -> list[Project]:
    exploit_pool = list(exploit_projects)
    explore_pool = list(explore_projects)
    fallback_pool = list(fallback_projects or [])
    merged_projects: list[Project] = []
    used_project_ids: set[int] = set()

    while len(merged_projects) < target_size:
        preferred_source = MERGE_PATTERN[len(merged_projects) % len(MERGE_PATTERN)]
        if preferred_source == "explore":
            preferred_pools = [explore_pool, exploit_pool, fallback_pool]
        else:
            preferred_pools = [exploit_pool, fallback_pool, explore_pool]

        candidate = _pop_next_candidate_from_pools(
            pools=preferred_pools,
            used_project_ids=used_project_ids,
            merged_projects=merged_projects,
            ranking_context=ranking_context,
            enforce_diversity_guard=True,
        )
        if candidate is None:
            candidate = _pop_next_candidate_from_pools(
                pools=preferred_pools,
                used_project_ids=used_project_ids,
                merged_projects=merged_projects,
                ranking_context=ranking_context,
                enforce_diversity_guard=False,
            )
        if candidate is None:
            break
        merged_projects.append(candidate)
        used_project_ids.add(int(candidate.id))

    return merged_projects


def build_ranking_context(*, user_id: int, projects: list[Project]) -> dict:
    project_ids = [
        int(project.id) for project in projects if project is not None and project.id is not None
    ]
    has_history = preference_profile_service.has_sufficient_history(user_id)
    profile_snapshot = (
        preference_profile_service.get_profile_snapshot(user_id) if has_history else {}
    )
    topic_assignments_by_project_id = (
        preference_profile_repository.list_content_topic_assignments_for_content_ids(
            domain="project",
            content_type="project",
            content_ids=project_ids,
        )
    )
    viewed_project_ids = behavior_event_repository.list_behavior_target_ids_for_user(
        user_id,
        domain="project",
        target_type="project",
        action_types=["view"],
    )
    contributed_project_ids = behavior_event_repository.list_behavior_target_ids_for_user(
        user_id,
        domain="project",
        target_type="project",
        action_types=["project_contribute"],
    )
    recent_topic_exposure = behavior_event_repository.list_recent_topic_exposure_counts_for_user(
        user_id,
        domain="project",
    )
    contribution_counts_by_project_id = project_repository.list_contribution_counts_for_project_ids(
        project_ids
    )
    contributor_counts_by_project_id = (
        project_repository.list_unique_contributor_counts_for_project_ids(project_ids)
    )
    return {
        "has_history": has_history,
        "profile_snapshot": profile_snapshot,
        "viewed_project_ids": viewed_project_ids,
        "contributed_project_ids": contributed_project_ids,
        "recent_topic_exposure": recent_topic_exposure,
        "topic_assignments_by_project_id": topic_assignments_by_project_id,
        "contribution_counts_by_project_id": contribution_counts_by_project_id,
        "contributor_counts_by_project_id": contributor_counts_by_project_id,
    }


def rank_projects_for_user(*, projects: list[Project], user_id: int) -> list[Project]:
    if not projects:
        return []

    ranking_context = build_ranking_context(user_id=user_id, projects=projects)
    if not ranking_context["has_history"]:
        return sorted(
            projects,
            key=lambda project: (
                _cold_start_score(project, ranking_context),
                _ensure_aware_utc(project.created_at),
                project.id,
            ),
            reverse=True,
        )

    source_index_by_project_id = {
        int(project.id): index
        for index, project in enumerate(projects)
        if project is not None and project.id is not None
    }

    exploitation_projects = _sort_projects_with_scores(
        projects=[
            project
            for project in projects
            if is_exploitation_candidate(project, ranking_context=ranking_context)
        ],
        score_getter=exploit_score,
        ranking_context=ranking_context,
        source_index_by_project_id=source_index_by_project_id,
    )
    exploration_projects = _sort_projects_with_scores(
        projects=[
            project
            for project in projects
            if is_exploration_candidate(project, ranking_context=ranking_context)
        ],
        score_getter=explore_score,
        ranking_context=ranking_context,
        source_index_by_project_id=source_index_by_project_id,
    )
    ranked_pool_project_ids = {
        int(project.id)
        for project in exploitation_projects + exploration_projects
        if project is not None and project.id is not None
    }
    fallback_projects = _sort_projects_with_scores(
        projects=[
            project
            for project in projects
            if project is not None
            and project.id is not None
            and int(project.id) not in ranked_pool_project_ids
        ],
        score_getter=exploit_score,
        ranking_context=ranking_context,
        source_index_by_project_id=source_index_by_project_id,
    )

    return merge_ranked_projects(
        exploit_projects=exploitation_projects,
        explore_projects=exploration_projects,
        fallback_projects=fallback_projects,
        ranking_context=ranking_context,
        target_size=len(projects),
    )
