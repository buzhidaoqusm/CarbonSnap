from app.services.ai import case_resolver


class TestCaseResolver:
    def test_uses_model_resolution_when_available(self, monkeypatch):
        monkeypatch.setattr(
            case_resolver,
            "complete_json_diagnostic",
            lambda **kwargs: {
                "payload": {
                    "target_case_id": 12,
                    "confidence": 0.93,
                    "needs_clarification": False,
                    "clarification_question": None,
                    "clarification_options": [],
                },
                "raw_reply": '{"target_case_id":12}',
                "error": None,
            },
        )

        result = case_resolver.resolve_target_case(
            message="Please continue the battery one.",
            recent_history=[],
            case_summaries=[
                {
                    "case_id": 11,
                    "predicted_item": "plastic bottle",
                    "current_stage": "analysis_ready",
                },
                {"case_id": 12, "predicted_item": "battery", "current_stage": "awaiting_location"},
            ],
        )

        assert result["target_case_id"] == 12
        assert result["needs_clarification"] is False

    def test_fallback_asks_for_clarification_when_multiple_cases_match_poorly(self):
        result = case_resolver.resolve_target_case(
            message="Can you continue that recycling task?",
            recent_history=[],
            case_summaries=[
                {
                    "case_id": 1,
                    "predicted_item": "plastic bottle",
                    "current_stage": "analysis_ready",
                },
                {"case_id": 2, "predicted_item": "battery", "current_stage": "awaiting_location"},
            ],
        )

        assert result["target_case_id"] is None
        assert result["needs_clarification"] is True
        assert len(result["clarification_options"]) == 2
