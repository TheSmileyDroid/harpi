from src.HarpiLib.soundboard.models import Node, Soundboard


class TestNode:
    def test_node_creation(self):
        node = Node(x=10, y=20, sound_uuid="abc123", volume=50)
        assert node.x == 10
        assert node.y == 20
        assert node.sound_uuid == "abc123"
        assert node.volume == 50

    def test_node_equality(self):
        node1 = Node(x=10, y=20, sound_uuid="abc", volume=50)
        node2 = Node(x=10, y=20, sound_uuid="abc", volume=50)
        assert node1 == node2

    def test_node_inequality(self):
        node1 = Node(x=10, y=20, sound_uuid="abc", volume=50)
        node2 = Node(x=10, y=20, sound_uuid="def", volume=50)
        assert node1 != node2


class TestSoundboard:
    def test_soundboard_default_empty_nodes(self):
        soundboard = Soundboard()
        assert soundboard.nodes == []

    def test_soundboard_with_nodes(self):
        node1 = Node(x=0, y=0, sound_uuid="sound1", volume=100)
        node2 = Node(x=1, y=1, sound_uuid="sound2", volume=80)
        soundboard = Soundboard(nodes=[node1, node2])
        assert len(soundboard.nodes) == 2
        assert soundboard.nodes[0] == node1
        assert soundboard.nodes[1] == node2

    def test_soundboard_mutability(self):
        soundboard = Soundboard()
        node = Node(x=5, y=5, sound_uuid="sound", volume=100)
        soundboard.nodes.append(node)
        assert len(soundboard.nodes) == 1

    def test_multiple_soundboards_independent(self):
        sb1 = Soundboard()
        sb2 = Soundboard()
        node = Node(x=0, y=0, sound_uuid="sound", volume=100)
        sb1.nodes.append(node)
        assert len(sb1.nodes) == 1
        assert len(sb2.nodes) == 0
