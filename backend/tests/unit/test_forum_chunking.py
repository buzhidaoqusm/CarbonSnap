from app.ai.rag.chunking import chunk_forum_post, normalize_forum_text


LONG_CONTENT = """
Plastic bottles should be rinsed before recycling. Remove obvious food residue and
check whether your local rules require the cap to be separated.

If the label peels off easily, remove it before disposal. If it does not, keep the
container clean and flatten it if your local system accepts flattened bottles.

Community experience suggests that mixed material lids and pumps may need separate
handling, especially when the bottle body and cap are made from different plastics.
"""


class TestForumChunking:
    def test_normalize_forum_text_collapses_whitespace(self, app):
        with app.app_context():
            assert normalize_forum_text("  hello \n   world  ") == "hello world"

    def test_chunk_post_text_preserves_title_and_generates_metadata(self, app):
        with app.app_context():
            app.config["FORUM_RAG_CHUNK_TARGET_TOKENS"] = 20
            app.config["FORUM_RAG_CHUNK_OVERLAP_TOKENS"] = 3

            chunks = chunk_forum_post(
                title="Bottle Recycling",
                content=LONG_CONTENT,
                version=3,
            )

            assert len(chunks) >= 2
            assert chunks[0]["chunk_index"] == 0
            assert chunks[0]["chunk_version"] == 3
            assert chunks[0]["section_title"] == "Main"
            assert "Bottle Recycling" in chunks[0]["chunk_text"]
