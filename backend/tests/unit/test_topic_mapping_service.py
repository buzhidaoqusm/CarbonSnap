from app.services.recommendation import topic_mapping_service


class TestTopicMappingService:
    def test_assign_forum_post_topics_uses_llm_selection_when_candidates_exist(self, monkeypatch):
        monkeypatch.setattr(
            topic_mapping_service,
            "complete_json_diagnostic",
            lambda **kwargs: {
                "payload": {
                    "selected_topics": [
                        {"topic_id": "upcycling", "confidence_score": 0.84},
                        {"topic_id": "plastic-recycling", "confidence_score": 0.22},
                    ]
                }
            },
        )

        topics = topic_mapping_service.assign_forum_post_topics(
            title="Bottle lamp craft",
            content="We turned a bottle into a lamp.",
        )

        assert topics[0]["topic_id"] == "upcycling"
        assert topics[0]["confidence_score"] == 0.84

    def test_assign_forum_post_topics_falls_back_to_uncategorized_when_no_candidates(
        self, monkeypatch
    ):
        called = {"value": False}

        def _fail_if_called(**kwargs):
            called["value"] = True
            raise AssertionError("LLM should not be called without candidates")

        monkeypatch.setattr(topic_mapping_service, "complete_json_diagnostic", _fail_if_called)

        topics = topic_mapping_service.assign_forum_post_topics(
            title="Hello",
            content="Just a casual message.",
        )

        assert topics == [
            {
                "topic_id": "uncategorized",
                "confidence_score": 1.0,
                "source": "fallback",
            }
        ]
        assert called["value"] is False

    def test_invalid_llm_payload_falls_back_to_rule_candidate(self, monkeypatch):
        monkeypatch.setattr(
            topic_mapping_service,
            "complete_json_diagnostic",
            lambda **kwargs: {
                "payload": {"selected_topics": [{"topic_id": "unknown", "confidence_score": 0.9}]}
            },
        )

        topics = topic_mapping_service.assign_forum_post_topics(
            title="Battery charger question",
            content="What to do with an old charger?",
        )

        assert topics[0]["topic_id"] == "battery-recycling"
