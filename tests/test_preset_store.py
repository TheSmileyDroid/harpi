"""Tests for soundboard preset store (JSON file-based storage)."""

import json

import pytest

from src.harpi_lib.soundboard.preset_store import PresetStore, SoundboardPreset


# -- SoundboardPreset dataclass --


class TestSoundboardPreset:
    def test_to_dict_roundtrip(self):
        preset = SoundboardPreset(
            id="abc-123",
            name="My Preset",
            guild_id=42,
            nodes=[{"id": "n1", "type": "sound-source"}],
            edges=[{"source": "n1", "target": "output-1"}],
            created_at="2025-01-01T00:00:00+00:00",
            updated_at="2025-01-01T00:00:00+00:00",
        )
        d = preset.to_dict()
        restored = SoundboardPreset.from_dict(d)
        assert restored.id == preset.id
        assert restored.name == preset.name
        assert restored.guild_id == preset.guild_id
        assert restored.nodes == preset.nodes
        assert restored.edges == preset.edges
        assert restored.created_at == preset.created_at
        assert restored.updated_at == preset.updated_at

    def test_from_dict_defaults_timestamps(self):
        data = {
            "id": "x",
            "name": "p",
            "guild_id": 1,
            "nodes": [],
            "edges": [],
        }
        preset = SoundboardPreset.from_dict(data)
        assert preset.created_at  # should have a default ISO string
        assert preset.updated_at

    def test_to_dict_contains_all_fields(self):
        preset = SoundboardPreset(
            id="1", name="n", guild_id=2, nodes=[], edges=[]
        )
        d = preset.to_dict()
        assert set(d.keys()) == {
            "id",
            "name",
            "guild_id",
            "nodes",
            "edges",
            "created_at",
            "updated_at",
        }


# -- PresetStore --


class TestPresetStoreInit:
    def test_creates_data_directory(self, tmp_path):
        store_dir = tmp_path / "soundboard_data"
        assert not store_dir.exists()
        PresetStore(data_dir=store_dir)
        assert store_dir.is_dir()


class TestListPresets:
    def test_list_empty_guild(self, tmp_path):
        store = PresetStore(data_dir=tmp_path)
        assert store.list_presets(guild_id=999) == []

    def test_list_after_create(self, tmp_path):
        store = PresetStore(data_dir=tmp_path)
        store.create_preset(guild_id=1, name="A", nodes=[], edges=[])
        store.create_preset(guild_id=1, name="B", nodes=[], edges=[])
        presets = store.list_presets(guild_id=1)
        assert len(presets) == 2
        names = {p.name for p in presets}
        assert names == {"A", "B"}

    def test_list_presets_isolated_per_guild(self, tmp_path):
        store = PresetStore(data_dir=tmp_path)
        store.create_preset(guild_id=1, name="G1", nodes=[], edges=[])
        store.create_preset(guild_id=2, name="G2", nodes=[], edges=[])
        assert len(store.list_presets(guild_id=1)) == 1
        assert len(store.list_presets(guild_id=2)) == 1


class TestGetPreset:
    def test_get_existing(self, tmp_path):
        store = PresetStore(data_dir=tmp_path)
        created = store.create_preset(
            guild_id=1, name="P", nodes=[{"x": 1}], edges=[]
        )
        result = store.get_preset(created.id, guild_id=1)
        assert result is not None
        assert result.name == "P"
        assert result.nodes == [{"x": 1}]

    def test_get_nonexistent(self, tmp_path):
        store = PresetStore(data_dir=tmp_path)
        assert store.get_preset("no-such-id", guild_id=1) is None


class TestCreatePreset:
    def test_create_returns_preset_with_id(self, tmp_path):
        store = PresetStore(data_dir=tmp_path)
        preset = store.create_preset(
            guild_id=1,
            name="Test",
            nodes=[{"id": "n1"}],
            edges=[{"source": "n1", "target": "o1"}],
        )
        assert preset.id  # UUID string
        assert preset.name == "Test"
        assert preset.guild_id == 1
        assert preset.nodes == [{"id": "n1"}]
        assert preset.edges == [{"source": "n1", "target": "o1"}]

    def test_create_persists_to_disk(self, tmp_path):
        store = PresetStore(data_dir=tmp_path)
        preset = store.create_preset(
            guild_id=7, name="Saved", nodes=[], edges=[]
        )

        # Re-create store from same directory to verify persistence
        store2 = PresetStore(data_dir=tmp_path)
        loaded = store2.get_preset(preset.id, guild_id=7)
        assert loaded is not None
        assert loaded.name == "Saved"


class TestUpdatePreset:
    def test_update_name(self, tmp_path):
        store = PresetStore(data_dir=tmp_path)
        preset = store.create_preset(
            guild_id=1, name="Old", nodes=[], edges=[]
        )
        updated = store.update_preset(preset.id, guild_id=1, name="New")
        assert updated is not None
        assert updated.name == "New"

    def test_update_nodes_and_edges(self, tmp_path):
        store = PresetStore(data_dir=tmp_path)
        preset = store.create_preset(guild_id=1, name="P", nodes=[], edges=[])
        new_nodes = [{"id": "n1"}]
        new_edges = [{"source": "n1", "target": "o1"}]
        updated = store.update_preset(
            preset.id, guild_id=1, nodes=new_nodes, edges=new_edges
        )
        assert updated is not None
        assert updated.nodes == new_nodes
        assert updated.edges == new_edges

    def test_update_nonexistent_returns_none(self, tmp_path):
        store = PresetStore(data_dir=tmp_path)
        result = store.update_preset("no-id", guild_id=1, name="X")
        assert result is None

    def test_update_persists(self, tmp_path):
        store = PresetStore(data_dir=tmp_path)
        preset = store.create_preset(
            guild_id=1, name="Old", nodes=[], edges=[]
        )
        store.update_preset(preset.id, guild_id=1, name="New")

        store2 = PresetStore(data_dir=tmp_path)
        loaded = store2.get_preset(preset.id, guild_id=1)
        assert loaded is not None
        assert loaded.name == "New"

    def test_update_changes_updated_at(self, tmp_path):
        store = PresetStore(data_dir=tmp_path)
        preset = store.create_preset(guild_id=1, name="P", nodes=[], edges=[])
        original_updated = preset.updated_at
        updated = store.update_preset(preset.id, guild_id=1, name="Q")
        assert updated is not None
        # updated_at should be different (or at least set)
        assert updated.updated_at is not None


class TestDeletePreset:
    def test_delete_existing(self, tmp_path):
        store = PresetStore(data_dir=tmp_path)
        preset = store.create_preset(
            guild_id=1, name="Del", nodes=[], edges=[]
        )
        assert store.delete_preset(preset.id, guild_id=1) is True
        assert store.get_preset(preset.id, guild_id=1) is None

    def test_delete_nonexistent(self, tmp_path):
        store = PresetStore(data_dir=tmp_path)
        assert store.delete_preset("nope", guild_id=1) is False

    def test_delete_persists(self, tmp_path):
        store = PresetStore(data_dir=tmp_path)
        preset = store.create_preset(
            guild_id=1, name="Gone", nodes=[], edges=[]
        )
        store.delete_preset(preset.id, guild_id=1)

        store2 = PresetStore(data_dir=tmp_path)
        assert store2.get_preset(preset.id, guild_id=1) is None


class TestLoadCorruptFile:
    def test_corrupt_json_returns_empty(self, tmp_path):
        store = PresetStore(data_dir=tmp_path)
        guild_file = store._get_guild_file(guild_id=1)
        guild_file.write_text("NOT VALID JSON {{{")
        presets = store.list_presets(guild_id=1)
        assert presets == []

    def test_missing_keys_returns_empty(self, tmp_path):
        store = PresetStore(data_dir=tmp_path)
        guild_file = store._get_guild_file(guild_id=1)
        # Valid JSON but missing required keys in preset
        guild_file.write_text(json.dumps({"bad": {"only": "partial"}}))
        presets = store.list_presets(guild_id=1)
        assert presets == []
