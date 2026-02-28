"""Tests for api.py graph helper functions (_has_path_to_output, _find_connected_source_nodes)."""

from src.harpi_lib.api import _find_connected_source_nodes, _has_path_to_output


class TestHasPathToOutput:
    def test_direct_edge_to_output(self):
        nodes = [
            {"id": "s1", "type": "sound-source"},
            {"id": "o1", "type": "output"},
        ]
        edges = [{"source": "s1", "target": "o1"}]
        assert _has_path_to_output("s1", nodes, edges) is True

    def test_multi_hop_path(self):
        nodes = [
            {"id": "s1", "type": "sound-source"},
            {"id": "m1", "type": "mixer"},
            {"id": "o1", "type": "output"},
        ]
        edges = [
            {"source": "s1", "target": "m1"},
            {"source": "m1", "target": "o1"},
        ]
        assert _has_path_to_output("s1", nodes, edges) is True

    def test_no_path_to_output(self):
        nodes = [
            {"id": "s1", "type": "sound-source"},
            {"id": "s2", "type": "sound-source"},
            {"id": "o1", "type": "output"},
        ]
        edges = [{"source": "s2", "target": "o1"}]
        assert _has_path_to_output("s1", nodes, edges) is False

    def test_node_is_output(self):
        nodes = [{"id": "o1", "type": "output"}]
        edges = []
        assert _has_path_to_output("o1", nodes, edges) is True

    def test_disconnected_graph(self):
        nodes = [
            {"id": "s1", "type": "sound-source"},
            {"id": "o1", "type": "output"},
        ]
        edges = []  # no edges
        assert _has_path_to_output("s1", nodes, edges) is False

    def test_cycle_does_not_infinite_loop(self):
        nodes = [
            {"id": "a", "type": "mixer"},
            {"id": "b", "type": "mixer"},
            {"id": "o1", "type": "output"},
        ]
        edges = [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "a"},  # cycle
        ]
        assert _has_path_to_output("a", nodes, edges) is False

    def test_cycle_with_path_to_output(self):
        nodes = [
            {"id": "a", "type": "mixer"},
            {"id": "b", "type": "mixer"},
            {"id": "o1", "type": "output"},
        ]
        edges = [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "a"},
            {"source": "b", "target": "o1"},
        ]
        assert _has_path_to_output("a", nodes, edges) is True

    def test_edge_with_missing_fields_ignored(self):
        nodes = [
            {"id": "s1", "type": "sound-source"},
            {"id": "o1", "type": "output"},
        ]
        edges = [
            {"source": "s1"},  # missing target
            {"target": "o1"},  # missing source
        ]
        assert _has_path_to_output("s1", nodes, edges) is False


class TestFindConnectedSourceNodes:
    def test_finds_connected_sources(self):
        nodes = [
            {"id": "s1", "type": "sound-source"},
            {"id": "s2", "type": "sound-source"},
            {"id": "o1", "type": "output"},
        ]
        edges = [{"source": "s1", "target": "o1"}]
        result = _find_connected_source_nodes(nodes, edges)
        assert result == {"s1"}

    def test_ignores_non_source_nodes(self):
        nodes = [
            {"id": "m1", "type": "mixer"},
            {"id": "o1", "type": "output"},
        ]
        edges = [{"source": "m1", "target": "o1"}]
        result = _find_connected_source_nodes(nodes, edges)
        assert result == set()

    def test_empty_graph(self):
        assert _find_connected_source_nodes([], []) == set()

    def test_source_with_no_path(self):
        nodes = [
            {"id": "s1", "type": "sound-source"},
            {"id": "o1", "type": "output"},
        ]
        edges = []
        result = _find_connected_source_nodes(nodes, edges)
        assert result == set()

    def test_multiple_sources_mixed_connectivity(self):
        nodes = [
            {"id": "s1", "type": "sound-source"},
            {"id": "s2", "type": "sound-source"},
            {"id": "s3", "type": "sound-source"},
            {"id": "o1", "type": "output"},
        ]
        edges = [
            {"source": "s1", "target": "o1"},
            {"source": "s3", "target": "o1"},
        ]
        result = _find_connected_source_nodes(nodes, edges)
        assert result == {"s1", "s3"}
