"""Instrument abstraction for musical instruments with MIDI channel management."""

from dataclasses import dataclass
from typing import Optional, Protocol
from .structures import Sequence, Note


@dataclass
class InstrumentConfig:
    """Configuration for an instrument."""

    channel: int  # MIDI channel (0-15)
    name: Optional[str] = None
    default_velocity: int = 100
    transpose: int = 0  # Semitones to transpose all notes

    def __post_init__(self):
        """Validate instrument configuration."""
        if not (0 <= self.channel <= 15):
            raise ValueError(f"Channel must be 0-15, got {self.channel}")
        if not (0 <= self.default_velocity <= 127):
            raise ValueError(
                f"Default velocity must be 0-127, got {self.default_velocity}"
            )
        if not (-127 <= self.transpose <= 127):
            raise ValueError(f"Transpose must be -127 to 127, got {self.transpose}")


class NotePlayerProtocol(Protocol):
    """Protocol for playing individual notes."""

    def play_note(
        self, pitch: int, velocity: int, channel: int, duration: float
    ) -> None:
        """Play a single note with specified parameters.

        Args:
            pitch: MIDI note number (0-127)
            velocity: Note velocity (0-127)
            channel: MIDI channel (0-15)
            duration: Note duration in seconds
        """
        ...

    def stop_note(self, pitch: int, channel: int) -> None:
        """Stop a specific note on a channel.

        Args:
            pitch: MIDI note number (0-127)
            channel: MIDI channel (0-15)
        """
        ...


class SequencePlayerProtocol(Protocol):
    """Protocol for playing musical sequences."""

    def play_sequence(self, sequence: Sequence) -> int:
        """Play a sequence and return a sequence ID.

        Args:
            sequence: Sequence object to play

        Returns:
            Sequence ID for later control
        """
        ...

    def stop_sequence(self, sequence_id: int) -> None:
        """Stop a playing sequence.

        Args:
            sequence_id: ID of sequence to stop
        """
        ...


class Instrument:
    """Represents a musical instrument on a specific MIDI channel."""

    def __init__(
        self,
        config: InstrumentConfig,
        note_player: NotePlayerProtocol,
        sequence_player: SequencePlayerProtocol,
    ):
        """Initialize instrument with configuration and player interfaces.

        Args:
            config: Instrument configuration
            note_player: Implementation for playing individual notes
            sequence_player: Implementation for playing sequences
        """
        self.config = config
        self._note_player = note_player
        self._sequence_player = sequence_player
        self._active_sequences = set()  # Track active sequence IDs

    @property
    def channel(self) -> int:
        """Get the instrument's MIDI channel."""
        return self.config.channel

    @property
    def name(self) -> str:
        """Get the instrument's name."""
        return self.config.name or f"Instrument on Channel {self.config.channel}"

    def _apply_transpose(self, pitch: int) -> int:
        """Apply transpose setting to a pitch, clamping to valid MIDI range.

        Args:
            pitch: Original MIDI pitch (0-127)

        Returns:
            Transposed pitch clamped to 0-127 range
        """
        transposed = pitch + self.config.transpose
        return max(0, min(127, transposed))

    def play_note(
        self, pitch: int, velocity: Optional[int] = None, duration: float = 0.5
    ) -> None:
        """Play a single note on this instrument's channel.

        Args:
            pitch: MIDI note number (0-127)
            velocity: Note velocity (0-127), uses default if None
            duration: Note duration in seconds
        """
        if velocity is None:
            velocity = self.config.default_velocity

        # Apply transpose and validate pitch
        transposed_pitch = self._apply_transpose(pitch)

        # Validate parameters
        if not (0 <= velocity <= 127):
            raise ValueError(f"Velocity must be 0-127, got {velocity}")
        if duration <= 0:
            raise ValueError(f"Duration must be positive, got {duration}")

        self._note_player.play_note(
            pitch=transposed_pitch,
            velocity=velocity,
            channel=self.config.channel,
            duration=duration,
        )

    def stop_note(self, pitch: int) -> None:
        """Stop a specific note on this instrument's channel.

        Args:
            pitch: MIDI note number (0-127) to stop
        """
        transposed_pitch = self._apply_transpose(pitch)
        self._note_player.stop_note(pitch=transposed_pitch, channel=self.config.channel)

    def play_sequence(self, sequence: Sequence, override_channel: bool = True) -> int:
        """Play a sequence on this instrument's channel.

        Args:
            sequence: Sequence to play
            override_channel: If True, override all note channels with
                instrument channel

        Returns:
            Sequence ID for later control
        """
        # Create a copy of the sequence to avoid modifying the original
        notes = []
        for note in sequence.notes:
            # Apply transpose
            transposed_pitch = self._apply_transpose(note.pitch)

            # Create new note with potentially modified channel and pitch
            new_note = Note(
                pitch=transposed_pitch,
                velocity=note.velocity,
                duration=note.duration,
                start_beat=note.start_beat,
                channel=(self.config.channel if override_channel else note.channel),
            )
            notes.append(new_note)

        # Create new sequence with modified notes
        modified_sequence = Sequence(
            notes=notes,
            tempo_bpm=sequence.tempo_bpm,
            loop=sequence.loop,
            name=sequence.name,
        )

        # Play the sequence and track it
        sequence_id = self._sequence_player.play_sequence(modified_sequence)
        self._active_sequences.add(sequence_id)

        return sequence_id

    def stop_sequence(self, sequence_id: int) -> None:
        """Stop a specific sequence playing on this instrument.

        Args:
            sequence_id: ID of sequence to stop
        """
        if sequence_id in self._active_sequences:
            self._sequence_player.stop_sequence(sequence_id)
            self._active_sequences.discard(sequence_id)

    def stop_all_sequences(self) -> None:
        """Stop all sequences currently playing on this instrument."""
        for sequence_id in list(self._active_sequences):
            self.stop_sequence(sequence_id)

    def get_active_sequences(self) -> set:
        """Get set of currently active sequence IDs.

        Returns:
            Set of active sequence IDs
        """
        return self._active_sequences.copy()
