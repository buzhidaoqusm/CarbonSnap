from app.models.recommendation import (
    ContentTopicAssignment,
    UserBehaviorEvent,
    UserPreferenceProfile,
)


class TestRecommendationModels:
    def test_user_behavior_event_exposes_new_recommendation_columns(self):
        columns = set(UserBehaviorEvent.__table__.columns.keys())

        assert {"target_type", "topic_payload_json", "context_json"} <= columns

    def test_content_topic_assignment_model_has_expected_shape(self):
        row = ContentTopicAssignment(
            domain="forum",
            content_type="post",
            content_id=42,
            topic_id="upcycling",
            confidence_score=0.84,
            source="ai_constrained",
        )

        assert row.domain == "forum"
        assert row.content_type == "post"
        assert row.topic_id == "upcycling"
        assert row.confidence_score == 0.84

    def test_user_preference_profile_model_has_expected_shape(self):
        row = UserPreferenceProfile(
            user_id=7,
            profile_type="content_interest",
            profile_key="plastic-recycling",
            raw_score=2.5,
            normalized_score=0.27,
            confidence_score=0.63,
            event_count=4,
            source_domains_json='["forum", "ai"]',
        )

        assert row.profile_key == "plastic-recycling"
        assert row.event_count == 4
        assert row.source_domains_json == '["forum", "ai"]'
