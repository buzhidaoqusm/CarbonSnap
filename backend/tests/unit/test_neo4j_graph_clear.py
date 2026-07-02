from __future__ import annotations

import pytest

from scripts import clear_recycling_graph


class FakeResult:
    def __init__(self, record):
        self.record = record

    def single(self):
        return self.record


class FakeSession:
    def __init__(self, deleted_counts):
        self.deleted_counts = list(deleted_counts)
        self.runs = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, cypher):
        self.runs.append(cypher)
        return FakeResult({"deleted_count": self.deleted_counts.pop(0)})


class FakeDriver:
    def __init__(self, deleted_counts):
        self.session_instance = FakeSession(deleted_counts)

    def session(self):
        return self.session_instance


def test_clear_graph_deletes_nodes_in_batches_without_dropping_schema():
    driver = FakeDriver([2, 1, 0])

    deleted_count = clear_recycling_graph.clear_graph(driver, batch_size=50)

    assert deleted_count == 3
    assert len(driver.session_instance.runs) == 3
    for cypher in driver.session_instance.runs:
        assert "DETACH DELETE node" in cypher
        assert "LIMIT 50" in cypher
        assert "DROP" not in cypher


def test_build_clear_batch_cypher_rejects_invalid_batch_size():
    with pytest.raises(ValueError, match="batch_size"):
        clear_recycling_graph.build_clear_batch_cypher(0)
