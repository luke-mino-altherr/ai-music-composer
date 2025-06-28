"""Tests for the InstrumentManager class."""

import pytest

from src.midi_generator import InstrumentManager, Note, Sequence


class MockNotePlayer:
    """Mock implementation of NotePlayerProtocol for testing."""

    def __init__(self):
        """Initialize the mock note player."""
        self.played_notes = []
        self.stopped_notes = []

    def play_note(
        self, pitch: int, velocity: int, channel: int, duration: float
    ) -> None:
        """Mock play_note method."""
        self.played_notes.append((pitch, velocity, channel, duration))

    def stop_note(self, pitch: int, channel: int) -> None:
        """Mock stop_note method."""
        self.stopped_notes.append((pitch, channel))


class MockSequencePlayer:
    """Mock implementation of SequencePlayerProtocol for testing."""

    def __init__(self):
        """Initialize the mock sequence player."""
        self.played_sequences = []
        self.stopped_sequences = []
        self._next_id = 1

    def play_sequence(self, sequence: Sequence) -> int:
        """Mock play_sequence method."""
        seq_id = self._next_id
        self._next_id += 1
        self.played_sequences.append((seq_id, sequence))
        return seq_id

    def stop_sequence(self, sequence_id: int) -> None:
        """Mock stop_sequence method."""
        self.stopped_sequences.append(sequence_id)


class TestInstrumentManager:
    """Test InstrumentManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.note_player = MockNotePlayer()
        self.sequence_player = MockSequencePlayer()
        self.manager = InstrumentManager(self.note_player, self.sequence_player)

    def test_create_instrument_success(self):
        """Test successful instrument creation."""
        result = self.manager.create_instrument("piano", 0, 100, 0)
        assert result is True
        assert "piano" in self.manager.instruments

        instrument = self.manager.get_instrument("piano")
        assert instrument is not None
        assert instrument.channel == 0
        assert instrument.config.default_velocity == 100
        assert instrument.config.transpose == 0

    def test_create_instrument_duplicate_name(self):
        """Test that duplicate instrument names are rejected."""
        self.manager.create_instrument("piano", 0)
        result = self.manager.create_instrument("piano", 1)
        assert result is False

        # Should still only have one instrument
        instruments = self.manager.list_instruments()
        assert len(instruments) == 1
        assert instruments["piano"].channel == 0  # Original channel

    def test_create_instrument_invalid_params(self):
        """Test that invalid parameters are rejected."""
        # Invalid channel
        result = self.manager.create_instrument("test", 16)
        assert result is False

        # Invalid velocity
        result = self.manager.create_instrument("test", 0, 128)
        assert result is False

        # Invalid transpose
        result = self.manager.create_instrument("test", 0, 100, 128)
        assert result is False

    def test_get_instrument_not_found(self):
        """Test getting non-existent instrument returns None."""
        result = self.manager.get_instrument("nonexistent")
        assert result is None

    def test_list_instruments(self):
        """Test listing instruments."""
        # Empty initially
        instruments = self.manager.list_instruments()
        assert len(instruments) == 0

        # Add some instruments
        self.manager.create_instrument("piano", 0)
        self.manager.create_instrument("bass", 1, 80, -12)

        instruments = self.manager.list_instruments()
        assert len(instruments) == 2
        assert "piano" in instruments
        assert "bass" in instruments

        # Verify it returns a copy (not the original dict)
        instruments["test"] = "should not affect original"
        original_instruments = self.manager.list_instruments()
        assert "test" not in original_instruments

    def test_remove_instrument_success(self):
        """Test successful instrument removal."""
        self.manager.create_instrument("piano", 0)

        # Create and play a sequence to test cleanup
        instrument = self.manager.get_instrument("piano")
        notes = [Note(pitch=60, velocity=100, duration=0.5, start_beat=0.0)]
        sequence = Sequence(notes=notes)
        seq_id = instrument.play_sequence(sequence)

        # Verify sequence is active
        assert len(instrument.get_active_sequences()) == 1

        # Remove instrument
        result = self.manager.remove_instrument("piano")
        assert result is True
        assert self.manager.get_instrument("piano") is None

        # Verify sequence was stopped (would be in stopped_sequences)
        assert seq_id in self.sequence_player.stopped_sequences

    def test_remove_instrument_not_found(self):
        """Test removing non-existent instrument."""
        result = self.manager.remove_instrument("nonexistent")
        assert result is False

    def test_stop_all_instruments(self):
        """Test stopping all sequences on all instruments."""
        # Create instruments with sequences
        self.manager.create_instrument("piano", 0)
        self.manager.create_instrument("bass", 1)

        piano = self.manager.get_instrument("piano")
        bass = self.manager.get_instrument("bass")

        # Add sequences to both instruments
        notes = [Note(pitch=60, velocity=100, duration=0.5, start_beat=0.0)]
        sequence = Sequence(notes=notes)

        piano.play_sequence(sequence)
        piano.play_sequence(sequence)
        bass.play_sequence(sequence)

        # Verify sequences are active
        assert len(piano.get_active_sequences()) == 2
        assert len(bass.get_active_sequences()) == 1

        # Stop all instruments
        total_stopped = self.manager.stop_all_instruments()
        assert total_stopped == 3

        # Verify all sequences are stopped
        assert len(piano.get_active_sequences()) == 0
        assert len(bass.get_active_sequences()) == 1

    def test_get_instrument_names(self):
        """Test getting list of instrument names."""
        assert self.manager.get_instrument_names() == []

        self.manager.create_instrument("piano", 0)
        self.manager.create_instrument("bass", 1)

        names = self.manager.get_instrument_names()
        assert set(names) == {"piano", "bass"}

    def test_has_instrument(self):
        """Test checking if instrument exists."""
        assert not self.manager.has_instrument("piano")

        self.manager.create_instrument("piano", 0)
        assert self.manager.has_instrument("piano")
        assert not self.manager.has_instrument("bass")

    def test_get_total_active_sequences(self):
        """Test getting total active sequences across all instruments."""
        assert self.manager.get_total_active_sequences() == 0

        # Create instruments and add sequences
        self.manager.create_instrument("piano", 0)
        self.manager.create_instrument("bass", 1)

        piano = self.manager.get_instrument("piano")
        bass = self.manager.get_instrument("bass")

        notes = [Note(pitch=60, velocity=100, duration=0.5, start_beat=0.0)]
        sequence = Sequence(notes=notes)

        piano.play_sequence(sequence)
        piano.play_sequence(sequence)
        bass.play_sequence(sequence)

        assert self.manager.get_total_active_sequences() == 3

    def test_get_instruments_by_channel(self):
        """Test getting instruments by channel."""
        self.manager.create_instrument("piano1", 0)
        self.manager.create_instrument("piano2", 0)
        self.manager.create_instrument("bass", 1)

        channel_0_instruments = self.manager.get_instruments_by_channel(0)
        assert len(channel_0_instruments) == 2

        channel_1_instruments = self.manager.get_instruments_by_channel(1)
        assert len(channel_1_instruments) == 1

        channel_2_instruments = self.manager.get_instruments_by_channel(2)
        assert len(channel_2_instruments) == 0

    def test_clear_all_instruments(self):
        """Test clearing all instruments."""
        # Create instruments with sequences
        self.manager.create_instrument("piano", 0)
        self.manager.create_instrument("bass", 1)

        piano = self.manager.get_instrument("piano")
        notes = [Note(pitch=60, velocity=100, duration=0.5, start_beat=0.0)]
        sequence = Sequence(notes=notes)
        piano.play_sequence(sequence)

        # Clear all instruments
        count = self.manager.clear_all_instruments()
        assert count == 2

        # Verify all instruments are gone
        assert len(self.manager.list_instruments()) == 0
        assert not self.manager.has_instrument("piano")
        assert not self.manager.has_instrument("bass")


if __name__ == "__main__":
    pytest.main([__file__])
