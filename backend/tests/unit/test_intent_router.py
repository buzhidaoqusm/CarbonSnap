from app.services.ai import intent_router


class TestIntentRouter:
    def test_router_system_prompt_includes_boundary_examples(self):
        prompt = intent_router._router_system_prompt()

        assert "Where can I recycle it near me?" in prompt
        assert '"follow_up_type": "nearby_search"' in prompt
        assert "Can you give me another recycling method besides putting it in the recycling bin?" in prompt
        assert '"follow_up_type": "guidance_follow_up"' in prompt
        assert "Which bin should this glass jar go in?" in prompt
        assert '"intent": "recycling_analysis"' in prompt
        assert "The current message is the primary signal." in prompt
        assert "do not keep the request in guidance_follow_up" in prompt

    def test_router_user_prompt_marks_history_as_reference_only(self):
        payload = intent_router._build_router_user_prompt(
            message="Where can I recycle it near me?",
            recent_history=[
                {"role": "user", "content": "Can you give me another recycling method?"},
                {"role": "assistant", "content": "You could try upcycling it."},
            ],
            case_summaries=[{"case_id": 1, "predicted_item": "plastic bottle"}],
            conversation_state={"current_pending_action": "none"},
            prompt_memory={},
        )

        assert '"current_message": "Where can I recycle it near me?"' in payload
        assert '"recent_history_for_reference_only"' in payload
        assert '"active_case_summaries"' in payload

    def test_uses_model_payload_when_available(self, monkeypatch):
        monkeypatch.setattr(
            intent_router,
            "complete_json_diagnostic",
            lambda **kwargs: {
                "payload": {
                    "intent": "recycling_follow_up",
                    "follow_up_type": "nearby_search",
                    "confidence": 0.94,
                    "possible_preference_signal": False,
                    "needs_clarification": False,
                    "clarification_question": None,
                    "clarification_options": [],
                },
                "raw_reply": '{"intent":"recycling_follow_up"}',
                "error": None,
            },
        )

        result = intent_router.classify_intent(
            message="Can you find nearby recycling points for that bottle?",
            image_data_url=None,
            recent_history=[],
            case_summaries=[{"case_id": 1, "predicted_item": "plastic bottle"}],
            conversation_state={"current_pending_action": "none"},
            prompt_memory={},
        )

        assert result["intent"] == "recycling_follow_up"
        assert result["follow_up_type"] == "nearby_search"

    def test_detailed_router_safe_default_on_invalid_payload_in_llm_first_mode(self, monkeypatch):
        monkeypatch.setattr(
            intent_router,
            "complete_json_diagnostic",
            lambda **kwargs: {
                "payload": {"intent": "chat_memory_question"},
                "raw_reply": '{"intent":"chat_memory_question"}',
                "error": None,
            },
        )

        detail = intent_router.classify_intent_detailed(
            message="What did I just say?",
            image_data_url=None,
            recent_history=[],
            case_summaries=[],
            conversation_state={},
            prompt_memory={},
            allow_business_fallback=False,
        )

        assert detail["result"]["intent"] == "general_chat"
        assert detail["router_failure_reason"] == "invalid_intent"
        assert detail["fallback_mode"] == "safe_default"

    def test_business_fallback_can_route_guidance_follow_up(self, monkeypatch):
        monkeypatch.setattr(
            intent_router,
            "complete_json_diagnostic",
            lambda **kwargs: {
                "payload": None,
                "raw_reply": "not-json",
                "error": "invalid_json:ValueError",
            },
        )

        detail = intent_router.classify_intent_detailed(
            message="Do you have other recycling suggestions?",
            image_data_url=None,
            recent_history=[
                {"role": "user", "content": "How do I recycle it?"},
                {"role": "assistant", "content": "Here are recycling steps for the bottle."},
            ],
            case_summaries=[{"case_id": 2, "predicted_item": "PET bottle", "status": "audit_passed"}],
            conversation_state={},
            prompt_memory={},
            allow_business_fallback=True,
        )

        assert detail["result"]["intent"] == "recycling_follow_up"
        assert detail["result"]["follow_up_type"] == "guidance_follow_up"

    def test_business_fallback_keeps_recycling_ideation_as_general_chat(self, monkeypatch):
        monkeypatch.setattr(
            intent_router,
            "complete_json_diagnostic",
            lambda **kwargs: {
                "payload": None,
                "raw_reply": "not-json",
                "error": "invalid_json:ValueError",
            },
        )

        detail = intent_router.classify_intent_detailed(
            message="有没有比较有意思的回收塑料瓶的方法？",
            image_data_url=None,
            recent_history=[],
            case_summaries=[],
            conversation_state={},
            prompt_memory={},
            allow_business_fallback=True,
        )

        assert detail["result"]["intent"] == "general_chat"
        assert detail["result"]["follow_up_type"] is None
