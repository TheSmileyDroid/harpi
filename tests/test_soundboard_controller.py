import threading
from unittest.mock import MagicMock


from src.HarpiLib.music.soundboard import SoundboardController


class TestSoundboardControllerInit:
    def test_initial_state(self, soundboard_controller: SoundboardController):
        sounds = soundboard_controller.get_playing_sounds()
        assert sounds == []


class TestAddRemoveLayer:
    def test_add_layer_returns_id(
        self, soundboard_controller: SoundboardController
    ):
        mock_source = MagicMock()
        mock_source.read.return_value = b"\x00" * 3840

        layer_id = soundboard_controller.add_layer(mock_source)
        assert isinstance(layer_id, str)
        assert len(layer_id) > 0

    def test_add_layer_appears_in_playing_sounds(
        self, soundboard_controller: SoundboardController
    ):
        mock_source = MagicMock()
        mock_source.read.return_value = b"\x00" * 3840

        soundboard_controller.add_layer(mock_source)
        sounds = soundboard_controller.get_playing_sounds()

        assert len(sounds) == 1
        source_type, source = sounds[0]
        assert source_type == "track"
        assert source == mock_source

    def test_remove_layer(self, soundboard_controller: SoundboardController):
        mock_source = MagicMock()
        mock_source.read.return_value = b"\x00" * 3840

        layer_id = soundboard_controller.add_layer(mock_source)
        soundboard_controller.remove_layer(layer_id)
        sounds = soundboard_controller.get_playing_sounds()

        assert sounds == []

    def test_remove_layer_calls_cleanup(
        self, soundboard_controller: SoundboardController
    ):
        mock_source = MagicMock()
        mock_source.read.return_value = b"\x00" * 3840
        mock_source.cleanup = MagicMock()

        layer_id = soundboard_controller.add_layer(mock_source)
        soundboard_controller.remove_layer(layer_id)

        mock_source.cleanup.assert_called_once()

    def test_remove_nonexistent_layer_no_error(
        self, soundboard_controller: SoundboardController
    ):
        soundboard_controller.remove_layer("nonexistent-id")

    def test_multiple_layers(
        self, soundboard_controller: SoundboardController
    ):
        mock_source1 = MagicMock()
        mock_source1.read.return_value = b"\x00" * 3840
        mock_source2 = MagicMock()
        mock_source2.read.return_value = b"\x00" * 3840

        id1 = soundboard_controller.add_layer(mock_source1)
        id2 = soundboard_controller.add_layer(mock_source2)

        assert id1 != id2
        sounds = soundboard_controller.get_playing_sounds()
        assert len(sounds) == 2


class TestSoundboardButton:
    def test_add_button_sound(
        self, soundboard_controller: SoundboardController
    ):
        mock_source = MagicMock()
        mock_source.read.return_value = b"\x00" * 3840

        button_id = soundboard_controller.add_button_sound(mock_source)
        assert isinstance(button_id, str)

        sounds = soundboard_controller.get_playing_sounds()
        assert len(sounds) == 1
        source_type, _ = sounds[0]
        assert source_type == "button"

    def test_remove_button_sound(
        self, soundboard_controller: SoundboardController
    ):
        mock_source = MagicMock()
        mock_source.read.return_value = b"\x00" * 3840
        mock_source.cleanup = MagicMock()

        button_id = soundboard_controller.add_button_sound(mock_source)
        soundboard_controller.remove_button_sound(button_id)

        assert soundboard_controller.get_playing_sounds() == []
        mock_source.cleanup.assert_called_once()


class TestQueueManagement:
    def test_add_to_queue(self, soundboard_controller: SoundboardController):
        mock_source = MagicMock()
        mock_source.read.return_value = b"\x00" * 3840

        soundboard_controller.add_to_queue(mock_source)
        sounds = soundboard_controller.get_playing_sounds()

        queue_sounds = [s for t, s in sounds if t == "queue"]
        assert len(queue_sounds) == 1

    def test_queue_auto_advance(
        self, soundboard_controller: SoundboardController
    ):
        finished_source = MagicMock()
        finished_source.read.return_value = b""
        finished_source.cleanup = MagicMock()

        next_source = MagicMock()
        next_source.read.return_value = b"\x00" * 3840

        soundboard_controller.add_to_queue(finished_source)
        soundboard_controller.add_to_queue(next_source)

        soundboard_controller._on_track_finished(finished_source)

        sounds = soundboard_controller.get_playing_sounds()
        queue_sounds = [s for t, s in sounds if t == "queue"]
        assert len(queue_sounds) == 1
        assert queue_sounds[0] == next_source

    def test_queue_empty_notification(
        self, soundboard_controller: SoundboardController
    ):
        callback = MagicMock()
        soundboard_controller.on_queue_empty(callback)

        mock_source = MagicMock()
        mock_source.read.return_value = b""
        soundboard_controller.add_to_queue(mock_source)

        soundboard_controller._on_track_finished(mock_source)

        callback.assert_called_once()

    def test_clear_queue(self, soundboard_controller: SoundboardController):
        mock_source1 = MagicMock()
        mock_source1.cleanup = MagicMock()
        mock_source2 = MagicMock()
        mock_source2.cleanup = MagicMock()

        soundboard_controller.add_to_queue(mock_source1)
        soundboard_controller.add_to_queue(mock_source2)
        soundboard_controller.clear_queue()

        assert soundboard_controller.get_playing_sounds() == []
        mock_source1.cleanup.assert_called()
        mock_source2.cleanup.assert_called()


class TestTTSTrack:
    def test_set_tts_track(self, soundboard_controller: SoundboardController):
        mock_source = MagicMock()
        mock_source.read.return_value = b"\x00" * 3840

        soundboard_controller.set_tts_track(mock_source)
        sounds = soundboard_controller.get_playing_sounds()

        tts_sounds = [s for t, s in sounds if t == "tts"]
        assert len(tts_sounds) == 1

    def test_set_tts_track_replaces_previous(
        self, soundboard_controller: SoundboardController
    ):
        old_source = MagicMock()
        old_source.read.return_value = b"\x00" * 3840
        old_source.cleanup = MagicMock()

        new_source = MagicMock()
        new_source.read.return_value = b"\x00" * 3840

        soundboard_controller.set_tts_track(old_source)
        soundboard_controller.set_tts_track(new_source)

        old_source.cleanup.assert_called_once()
        sounds = soundboard_controller.get_playing_sounds()
        tts_sounds = [s for t, s in sounds if t == "tts"]
        assert tts_sounds[0] == new_source

    def test_clear_tts_track(
        self, soundboard_controller: SoundboardController
    ):
        mock_source = MagicMock()
        mock_source.read.return_value = b"\x00" * 3840
        mock_source.cleanup = MagicMock()

        soundboard_controller.set_tts_track(mock_source)
        soundboard_controller.set_tts_track(None)

        assert mock_source.cleanup.called
        sounds = soundboard_controller.get_playing_sounds()
        tts_sounds = [s for t, s in sounds if t == "tts"]
        assert tts_sounds == []


class TestGetPlayingSounds:
    def test_returns_all_types(
        self, soundboard_controller: SoundboardController
    ):
        track = MagicMock()
        track.read.return_value = b"\x00" * 3840
        button = MagicMock()
        button.read.return_value = b"\x00" * 3840
        queue = MagicMock()
        queue.read.return_value = b"\x00" * 3840
        tts = MagicMock()
        tts.read.return_value = b"\x00" * 3840

        soundboard_controller.add_layer(track)
        soundboard_controller.add_button_sound(button)
        soundboard_controller.add_to_queue(queue)
        soundboard_controller.set_tts_track(tts)

        sounds = soundboard_controller.get_playing_sounds()
        types = {t for t, _ in sounds}

        assert types == {"track", "button", "queue", "tts"}
        assert len(sounds) == 4


class TestThreadSafety:
    def test_concurrent_add_remove(
        self, soundboard_controller: SoundboardController
    ):
        errors = []
        added_ids = []

        def add_layers():
            try:
                for i in range(100):
                    mock_source = MagicMock()
                    mock_source.read.return_value = b"\x00" * 3840
                    layer_id = soundboard_controller.add_layer(mock_source)
                    added_ids.append(layer_id)
            except Exception as e:
                errors.append(e)

        def remove_layers():
            try:
                for i in range(50):
                    if added_ids:
                        soundboard_controller.remove_layer(added_ids.pop(0))
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=add_layers)
        t2 = threading.Thread(target=remove_layers)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(errors) == 0
