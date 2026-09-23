from app.services.ai import memory_extractor


class TestMemoryExtractor:
    def test_extracts_concise_response_style_preference(self, monkeypatch):
        monkeypatch.setattr(
            memory_extractor,
            "complete_json_diagnostic",
            lambda **kwargs: {
                "payload": {
                    "is_explicit_preference": True,
                    "memory_candidates": [
                        {
                            "memory_type": "response_style",
                            "memory_key": "response_style",
                            "value": {"value": "concise"},
                        }
                    ],
                },
                "raw_reply": '{"is_explicit_preference":true}',
                "error": None,
            },
        )
        items = memory_extractor.extract_explicit_memory_candidates(
            "Please answer more concisely next time."
        )

        assert items == [
            {
                "memory_type": "response_style",
                "memory_key": "response_style",
                "value": {"value": "concise"},
            }
        ]

    def test_extracts_item_method_preference_for_battery(self, monkeypatch):
        monkeypatch.setattr(
            memory_extractor,
            "complete_json_diagnostic",
            lambda **kwargs: {
                "payload": {
                    "is_explicit_preference": True,
                    "memory_candidates": [
                        {
                            "memory_type": "item_method_preference",
                            "memory_key": "battery",
                            "value": {
                                "item_type": "battery",
                                "preferred_method": "specialized_dropoff",
                            },
                        }
                    ],
                },
                "raw_reply": '{"is_explicit_preference":true}',
                "error": None,
            },
        )
        items = memory_extractor.extract_explicit_memory_candidates(
            "For batteries, only show specialized drop-off options.",
        )

        assert items[0]["memory_type"] == "item_method_preference"
        assert items[0]["memory_key"] == "battery"
        assert items[0]["value"]["preferred_method"] == "specialized_dropoff"

    def test_small_talk_does_not_create_memory_candidates(self, monkeypatch):
        monkeypatch.setattr(
            memory_extractor,
            "complete_json_diagnostic",
            lambda **kwargs: {
                "payload": {"is_explicit_preference": False, "memory_candidates": []},
                "raw_reply": '{"is_explicit_preference":false,"memory_candidates":[]}',
                "error": None,
            },
        )
        assert memory_extractor.extract_explicit_memory_candidates("hello there") == []
