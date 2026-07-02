from app.services.recommendation.topic_taxonomy import (
    PHASE1_TOPIC_IDS,
    map_recycling_item_to_topics,
    normalize_topic_id,
    recall_topic_candidates,
    topic_label,
)


class TestTopicTaxonomy:
    def test_phase1_taxonomy_includes_core_topics(self):
        assert "plastic-recycling" in PHASE1_TOPIC_IDS
        assert "battery-recycling" in PHASE1_TOPIC_IDS
        assert "uncategorized" in PHASE1_TOPIC_IDS

    def test_normalize_topic_id_accepts_labels_and_aliases(self):
        assert normalize_topic_id("Plastic Recycling") == "plastic-recycling"
        assert normalize_topic_id("battery") == "battery-recycling"

    def test_topic_label_uses_fixed_registry(self):
        assert topic_label("upcycling") == "Upcycling"

    def test_recycling_item_mapping_is_deterministic(self):
        topics = map_recycling_item_to_topics("plastic bottle")

        assert topics[0]["topic_id"] == "plastic-recycling"
        assert topics[0]["confidence_score"] == 1.0

    def test_forum_candidate_recall_finds_related_topics(self):
        candidates = recall_topic_candidates("DIY bottle craft and reuse ideas")

        candidate_ids = {item["topic_id"] for item in candidates}
        assert "upcycling" in candidate_ids
