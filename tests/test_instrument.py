"""Tests for the Instrument abstraction."""

import pytest
from src.composer import (
    Instrument,
    InstrumentConfig,
    Note,
    Sequence,
)


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


class TestInstrumentConfig:
    """Test InstrumentConfig validation."""

    def test_valid_config(self):
        """Test valid configuration."""
        config = InstrumentConfig(
            channel=5, name="Test", default_velocity=64, transpose=12
        )
        assert config.channel == 5
        assert config.name == "Test"
        assert config.default_velocity == 64
        assert config.transpose == 12

    def test_invalid_channel(self):
        """Test invalid channel raises ValueError."""
        with pytest.raises(ValueError, match="Channel must be 0-15"):
            InstrumentConfig(channel=16)

        with pytest.raises(ValueError, match="Channel must be 0-15"):
            InstrumentConfig(channel=-1)

    def test_invalid_velocity(self):
        """Test invalid default velocity raises ValueError."""
        with pytest.raises(ValueError, match="Default velocity must be 0-127"):
            InstrumentConfig(channel=0, default_velocity=128)

        with pytest.raises(ValueError, match="Default velocity must be 0-127"):
            InstrumentConfig(channel=0, default_velocity=-1)

    def test_invalid_transpose(self):
        """Test invalid transpose raises ValueError."""
        with pytest.raises(ValueError, match="Transpose must be -127 to 127"):
            InstrumentConfig(channel=0, transpose=128)

        with pytest.raises(ValueError, match="Transpose must be -127 to 127"):
            InstrumentConfig(channel=0, transpose=-128)


class TestInstrument:
    """Test Instrument functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = InstrumentConfig(
            channel=3, name="Test Instrument", default_velocity=80, transpose=5
        )
        self.note_player = MockNotePlayer()
        self.sequence_player = MockSequencePlayer()
        self.instrument = Instrument(
            self.config, self.note_player, self.sequence_player
        )

    def test_properties(self):
        """Test instrument properties."""
        assert self.instrument.channel == 3
        assert self.instrument.name == "Test Instrument"

    def test_name_default(self):
        """Test default name generation."""
        config = InstrumentConfig(channel=7)
        instrument = Instrument(config, self.note_player, self.sequence_player)
        assert instrument.name == "Instrument on Channel 7"

    def test_transpose_application(self):
        """Test transpose functionality."""
        # Test normal case
        assert self.instrument._apply_transpose(60) == 65  # C4 + 5 semitones

        # Test clamping at boundaries
        assert self.instrument._apply_transpose(127) == 127  # Already at max
        assert self.instrument._apply_transpose(125) == 127  # Clamped to max
        assert self.instrument._apply_transpose(0) == 5  # Minimum with transpose

        # Test negative transpose
        config = InstrumentConfig(channel=0, transpose=-10)
        instrument = Instrument(config, self.note_player, self.sequence_player)
        assert instrument._apply_transpose(60) == 50
        assert instrument._apply_transpose(5) == 0  # Clamped to minimum

    def test_play_note_basic(self):
        """Test basic note playing."""
        self.instrument.play_note(60, velocity=100, duration=1.0)

        # Check that note was played with transpose applied
        assert len(self.note_player.played_notes) == 1
        pitch, velocity, channel, duration = self.note_player.played_notes[0]
        assert pitch == 65  # 60 + 5 transpose
        assert velocity == 100
        assert channel == 3
        assert duration == 1.0

    def test_play_note_default_velocity(self):
        """Test note playing with default velocity."""
        self.instrument.play_note(60, duration=0.5)

        assert len(self.note_player.played_notes) == 1
        pitch, velocity, channel, duration = self.note_player.played_notes[0]
        assert velocity == 80  # Default velocity from config

    def test_play_note_validation(self):
        """Test note playing parameter validation."""
        with pytest.raises(ValueError, match="Velocity must be 0-127"):
            self.instrument.play_note(60, velocity=128)

        with pytest.raises(ValueError, match="Duration must be positive"):
            self.instrument.play_note(60, duration=0)

    def test_stop_note(self):
        """Test note stopping."""
        self.instrument.stop_note(60)

        assert len(self.note_player.stopped_notes) == 1
        pitch, channel = self.note_player.stopped_notes[0]
        assert pitch == 65  # 60 + 5 transpose
        assert channel == 3

    def test_play_sequence(self):
        """Test sequence playing."""
        notes = [
            Note(pitch=60, velocity=100, duration=0.5, start_beat=0.0, channel=0),
            Note(pitch=64, velocity=90, duration=0.25, start_beat=0.5, channel=1),
        ]
        sequence = Sequence(notes=notes, name="Test Sequence")

        seq_id = self.instrument.play_sequence(sequence)

        # Check sequence was played
        assert len(self.sequence_player.played_sequences) == 1
        played_id, played_sequence = self.sequence_player.played_sequences[0]
        assert played_id == seq_id

        # Check that notes were modified correctly
        modified_notes = played_sequence.notes
        assert len(modified_notes) == 2

        # First note: transpose applied, channel overridden
        assert modified_notes[0].pitch == 65  # 60 + 5
        assert modified_notes[0].velocity == 100
        assert modified_notes[0].channel == 3  # Instrument channel
        assert modified_notes[0].duration == 0.5
        assert modified_notes[0].start_beat == 0.0

        # Second note: transpose applied, channel overridden
        assert modified_notes[1].pitch == 69  # 64 + 5
        assert modified_notes[1].velocity == 90
        assert modified_notes[1].channel == 3  # Instrument channel

        # Check sequence is tracked
        assert seq_id in self.instrument.get_active_sequences()

    def test_play_sequence_no_channel_override(self):
        """Test sequence playing without channel override."""
        notes = [Note(pitch=60, velocity=100, duration=0.5, start_beat=0.0, channel=5)]
        sequence = Sequence(notes=notes)

        self.instrument.play_sequence(sequence, override_channel=False)

        # Check that original channel was preserved
        played_sequence = self.sequence_player.played_sequences[0][1]
        assert played_sequence.notes[0].channel == 5  # Original channel preserved
        assert played_sequence.notes[0].pitch == 65  # But transpose still applied

    def test_stop_sequence(self):
        """Test sequence stopping."""
        notes = [Note(pitch=60, velocity=100, duration=0.5, start_beat=0.0)]
        sequence = Sequence(notes=notes)

        seq_id = self.instrument.play_sequence(sequence)
        assert seq_id in self.instrument.get_active_sequences()

        self.instrument.stop_sequence(seq_id)

        # Check sequence was stopped
        assert seq_id in self.sequence_player.stopped_sequences
        assert seq_id not in self.instrument.get_active_sequences()

    def test_stop_all_sequences(self):
        """Test stopping all sequences."""
        # Play multiple sequences
        notes = [Note(pitch=60, velocity=100, duration=0.5, start_beat=0.0)]
        sequence = Sequence(notes=notes)

        self.instrument.play_sequence(sequence)
        self.instrument.play_sequence(sequence)

        assert len(self.instrument.get_active_sequences()) == 2

        self.instrument.stop_all_sequences()

        # Check all sequences were stopped
        assert len(self.sequence_player.stopped_sequences) == 2
        assert len(self.instrument.get_active_sequences()) == 0


if __name__ == "__main__":
    pytest.main([__file__])
